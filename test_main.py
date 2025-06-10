import pytest
from fastapi.testclient import TestClient
# from sqlalchemy import create_engine # Unused
# from sqlalchemy.orm import sessionmaker # Unused
from typing import Generator
from datetime import datetime # Ensure datetime is imported here
import sqlite3 # Needed for the new connection management strategy

# Adjust imports based on your project structure
from main import app # Removed get_db as it's not part of the fix for now
import database as db_module  # Using db_module to avoid conflict with 'database' fixture
from models import MaterialLocation, MaterialLocationCreate, MaterialLocationUpdate, BatchUpdateItem, BatchUpdateRequest, ClearLocationRequest, BatchClearLocationRequest

# --- Test Database Setup ---

# Global connection for the test session, managed by fixtures
_test_db_conn_wrapper = None # Will hold the wrapper instance

# Wrapper class to make the 'close' method a no-op for the shared connection
class NoOpCloseConnectionWrapper:
    def __init__(self, real_conn):
        self._real_conn = real_conn

    def close(self):
        # This is the no-op close for the duration of tests
        # print(f"NoOpCloseConnectionWrapper: Intentionally not closing connection {id(self._real_conn)}")
        pass

    def __getattr__(self, name):
        # Delegate all other attribute/method access to the real connection
        return getattr(self._real_conn, name)

@pytest.fixture(scope="session", autouse=True)
def manage_test_db_connection():
    global _test_db_conn_wrapper
    original_db_url = db_module.DATABASE_URL
    db_module.DATABASE_URL = ":memory:" # Fallback DATABASE_URL

    # Create the single real connection for the entire test session
    real_conn = sqlite3.connect(":memory:", check_same_thread=False)
    real_conn.row_factory = sqlite3.Row

    # Wrap it for the tests
    _test_db_conn_wrapper = NoOpCloseConnectionWrapper(real_conn)

    # Patch database.get_db_connection to always return this wrapper
    original_get_db_connection = db_module.get_db_connection
    def mock_get_db_connection():
        return _test_db_conn_wrapper # Return the wrapper
    db_module.get_db_connection = mock_get_db_connection

    yield # Tests run here, using the wrapper

    # Teardown: restore original get_db_connection and close the real underlying connection
    db_module.get_db_connection = original_get_db_connection
    if _test_db_conn_wrapper and hasattr(_test_db_conn_wrapper, '_real_conn'):
        _test_db_conn_wrapper._real_conn.close() # Close the actual underlying connection

    db_module.DATABASE_URL = original_db_url

@pytest.fixture(autouse=True) # Function-scoped, runs for every test
def setup_test_database_tables():
    # create_table will use the globally managed _test_db_conn via the patched get_db_connection
    db_module.create_table()
    yield
    # Clean up data after each test by deleting all rows
    # This also uses the patched get_db_connection to get _test_db_conn
    conn = db_module.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM MaterialLocations")
    # If there were other tables, add DELETE statements for them too
    conn.commit()
    # No need to close _test_db_conn here; it's managed by the session-scoped fixture


client = TestClient(app) # TestClient uses the app, which will now use the patched db connection

# --- Test Cases ---

def test_create_location():
    response = client.post(
        "/locations/",
        json={"MaterialID": "MAT001", "TrayNumber": "T01", "ProcessID": "PROC001", "TaskID": "TASK001", "StatusNotes": "Initial entry"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["MaterialID"] == "MAT001"
    assert data["TrayNumber"] == "T01"
    assert "LocationID" in data
    assert "Timestamp" in data
    # Check if it's in the DB (optional, as response implies success)
    db_loc = db_module.get_material_location(data["LocationID"])
    assert db_loc is not None
    assert db_loc.MaterialID == "MAT001"

def test_read_locations_empty():
    response = client.get("/locations/")
    assert response.status_code == 200
    assert response.json() == []

def test_read_locations_with_data():
    # Create a couple of locations
    client.post("/locations/", json={"MaterialID": "MAT002", "TrayNumber": "T02"})
    client.post("/locations/", json={"MaterialID": "MAT003", "TrayNumber": "T03"})

    response = client.get("/locations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["MaterialID"] == "MAT002"
    assert data[1]["MaterialID"] == "MAT003"

def test_read_specific_location():
    create_response = client.post("/locations/", json={"MaterialID": "MAT004", "TrayNumber": "T04"})
    location_id = create_response.json()["LocationID"]

    response = client.get(f"/locations/{location_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["MaterialID"] == "MAT004"
    assert data["LocationID"] == location_id

def test_read_specific_location_not_found():
    response = client.get("/locations/99999") # Non-existent ID
    assert response.status_code == 404
    assert response.json() == {"detail": "Location not found"}

def test_update_location():
    create_response = client.post("/locations/", json={"MaterialID": "MAT005", "TrayNumber": "T05", "StatusNotes": "Old note"})
    location_id = create_response.json()["LocationID"]
    original_timestamp = create_response.json()["Timestamp"]

    update_data = {"MaterialID": "MAT005_Updated", "StatusNotes": "New note"}
    response = client.put(f"/locations/{location_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["MaterialID"] == "MAT005_Updated"
    assert data["StatusNotes"] == "New note"
    assert data["TrayNumber"] == "T05" # Unchanged field
    assert data["LocationID"] == location_id
    assert data["Timestamp"] != original_timestamp # Timestamp should update

    # Verify in DB
    db_loc = db_module.get_material_location(location_id)
    assert db_loc.MaterialID == "MAT005_Updated"
    assert db_loc.StatusNotes == "New note"

def test_update_location_partial():
    create_response = client.post("/locations/", json={"MaterialID": "MAT006", "TrayNumber": "T06", "ProcessID": "PROC006"})
    location_id = create_response.json()["LocationID"]
    original_timestamp = create_response.json()["Timestamp"]

    update_data = {"ProcessID": "PROC006_Updated"}
    response = client.put(f"/locations/{location_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["MaterialID"] == "MAT006" # Unchanged
    assert data["ProcessID"] == "PROC006_Updated"
    assert data["LocationID"] == location_id
    assert data["Timestamp"] != original_timestamp

def test_update_location_not_found():
    response = client.put("/locations/99999", json={"MaterialID": "MAT_NON_EXISTENT"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Location not found"}

def test_delete_location():
    create_response = client.post("/locations/", json={"MaterialID": "MAT007", "TrayNumber": "T07"})
    location_id = create_response.json()["LocationID"]

    response = client.delete(f"/locations/{location_id}")
    assert response.status_code == 204 # No content

    # Verify it's deleted from DB
    assert db_module.get_material_location(location_id) is None

def test_delete_location_not_found():
    response = client.delete("/locations/99999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Location not found"}

def test_batch_update_locations():
    loc1 = client.post("/locations/", json={"MaterialID": "BATCH01", "TrayNumber": "B01"}).json()
    loc2 = client.post("/locations/", json={"MaterialID": "BATCH02", "TrayNumber": "B02", "StatusNotes": "Note B02"}).json()

    update_requests = [
        {"LocationID": loc1["LocationID"], "data": {"MaterialID": "BATCH01_UPDATED", "StatusNotes": "Updated B01"}},
        {"LocationID": loc2["LocationID"], "data": {"TrayNumber": "B02_UPDATED"}},
        {"LocationID": 99999, "data": {"MaterialID": "NON_EXISTENT"}} # Non-existent ID
    ]

    response = client.post("/locations/batch-update/", json={"updates": update_requests})
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2 # Only two should succeed

    updated_loc1_data = next(item for item in data if item["LocationID"] == loc1["LocationID"])
    updated_loc2_data = next(item for item in data if item["LocationID"] == loc2["LocationID"])

    assert updated_loc1_data["MaterialID"] == "BATCH01_UPDATED"
    assert updated_loc1_data["StatusNotes"] == "Updated B01"
    assert updated_loc1_data["Timestamp"] != loc1["Timestamp"] # Timestamp should update

    assert updated_loc2_data["MaterialID"] == "BATCH02" # Original MaterialID
    assert updated_loc2_data["TrayNumber"] == "B02_UPDATED"
    assert updated_loc2_data["StatusNotes"] == "Note B02" # Original StatusNotes
    assert updated_loc2_data["Timestamp"] != loc2["Timestamp"] # Timestamp should update

def test_clear_one_location():
    create_response = client.post("/locations/", json={"MaterialID": "MAT_TO_CLEAR", "TrayNumber": "TC01"})
    location_id = create_response.json()["LocationID"]
    original_timestamp = create_response.json()["Timestamp"]

    response = client.post("/locations/clear-one/", json={"LocationID": location_id})
    assert response.status_code == 200
    data = response.json()
    assert data["LocationID"] == location_id
    assert data["MaterialID"] == "" # MaterialID should be cleared
    assert data["TrayNumber"] == "TC01" # Other fields remain
    assert data["Timestamp"] != original_timestamp # Timestamp should update

    db_loc = db_module.get_material_location(location_id)
    assert db_loc.MaterialID == ""

def test_clear_one_location_not_found():
    response = client.post("/locations/clear-one/", json={"LocationID": 99999})
    assert response.status_code == 404
    assert response.json() == {"detail": "Location not found"}

def test_batch_clear_locations():
    loc1 = client.post("/locations/", json={"MaterialID": "BATCH_CLEAR01", "TrayNumber": "BC01"}).json()
    loc2 = client.post("/locations/", json={"MaterialID": "BATCH_CLEAR02", "TrayNumber": "BC02"}).json()

    clear_request = {"LocationIDs": [loc1["LocationID"], loc2["LocationID"], 99999]} # include a non-existent ID

    response = client.post("/locations/batch-clear/", json=clear_request)
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2 # Only two should succeed

    cleared_loc1_data = next(item for item in data if item["LocationID"] == loc1["LocationID"])
    cleared_loc2_data = next(item for item in data if item["LocationID"] == loc2["LocationID"])

    assert cleared_loc1_data["MaterialID"] == ""
    assert cleared_loc1_data["Timestamp"] != loc1["Timestamp"]
    assert cleared_loc1_data["TrayNumber"] == "BC01" # Other fields remain

    assert cleared_loc2_data["MaterialID"] == ""
    assert cleared_loc2_data["Timestamp"] != loc2["Timestamp"]
    assert cleared_loc2_data["TrayNumber"] == "BC02" # Other fields remain

    # Verify in DB
    assert db_module.get_material_location(loc1["LocationID"]).MaterialID == ""
    assert db_module.get_material_location(loc2["LocationID"]).MaterialID == ""

# Example of a test for required fields (though Pydantic handles this, good for completeness)
def test_create_location_missing_fields():
    # Assuming MaterialID is effectively required for a meaningful entry,
    # though model allows Optional. The API behavior depends on this.
    # If the API logic expects certain fields to always be there for a create,
    # even if Pydantic model says Optional, test that.
    # For this MaterialLocationCreate, all fields are optional.
    # Let's test creating a truly empty record.
    response = client.post("/locations/", json={})
    assert response.status_code == 201 # Should still create with defaults or nulls
    data = response.json()
    assert data["MaterialID"] is None # or "" depending on model/db default
    assert data["TrayNumber"] is None
    # ... and so on for other fields
    assert "LocationID" in data
    assert "Timestamp" in data

    # Test with some fields null
    response_partial_null = client.post(
        "/locations/",
        json={"MaterialID": "MAT_NULL_TEST", "TrayNumber": None, "StatusNotes": "Some notes here"},
    )
    assert response_partial_null.status_code == 201
    data_partial_null = response_partial_null.json()
    assert data_partial_null["MaterialID"] == "MAT_NULL_TEST"
    assert data_partial_null["TrayNumber"] is None
    assert data_partial_null["StatusNotes"] == "Some notes here"

# Test for PUT with empty payload (should not change anything, or be disallowed)
def test_update_location_empty_payload():
    create_response = client.post("/locations/", json={"MaterialID": "MAT_EMPTY_UPDATE", "TrayNumber": "T_EU"})
    location_id = create_response.json()["LocationID"]
    original_data = create_response.json()

    response = client.put(f"/locations/{location_id}", json={}) # Empty JSON object
    assert response.status_code == 200 # Or 422 if not allowed/no change
    updated_data = response.json()

        # Check that timestamp is NOT updated, and other fields remain the same,
        # because an empty payload results in no operation.
    assert updated_data["MaterialID"] == original_data["MaterialID"]
    assert updated_data["TrayNumber"] == original_data["TrayNumber"]
    assert updated_data["Timestamp"] == original_data["Timestamp"] # Timestamp should NOT change with current logic

    # If the logic were to prevent updates with no actual data change (excluding timestamp),
    # this test would need to be adjusted. Current `update_material_location` updates timestamp always.
    # And if all fields in MaterialLocationUpdate are optional, an empty JSON means no fields are being *explicitly* set.
    # The behavior of `exclude_unset=True` in `location_update.dict(exclude_unset=True)` is key here.
    # If the payload is `{}`, `update_data` in `update_material_location` will be empty.
    # The current code has a check: `if not update_data: conn.close(); return get_material_location(location_id)`
        # This means it returns the current state, and the timestamp is NOT updated because the logic path that
        # assigns `update_data["Timestamp"] = datetime.utcnow()` is skipped.
        # The test now reflects this understanding.

    # Let's re-verify this specific behavior of update_material_location regarding timestamp
    db_loc_after_empty_put = db_module.get_material_location(location_id)
    assert db_loc_after_empty_put.Timestamp.replace(microsecond=0) == datetime.fromisoformat(updated_data["Timestamp"]).replace(microsecond=0)
    assert updated_data["MaterialID"] == "MAT_EMPTY_UPDATE"

# A helper to create a location and return its ID for other tests if needed
def create_sample_location(material_id: str, tray_number: str) -> int:
    response = client.post("/locations/", json={"MaterialID": material_id, "TrayNumber": tray_number})
    assert response.status_code == 201
    return response.json()["LocationID"]

# More specific tests for batch operations if needed
def test_batch_update_only_one_field():
    loc_id = create_sample_location("BATCH_SINGLE_FIELD", "BSF01")
    original_loc = db_module.get_material_location(loc_id)

    update_requests = [
        {"LocationID": loc_id, "data": {"StatusNotes": "Single field update"}}
    ]
    response = client.post("/locations/batch-update/", json={"updates": update_requests})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["StatusNotes"] == "Single field update"
    assert data[0]["MaterialID"] == "BATCH_SINGLE_FIELD" # Unchanged
    assert data[0]["Timestamp"] != original_loc.Timestamp.isoformat() # Timestamp updated

def test_batch_clear_non_existent_only():
    response = client.post("/locations/batch-clear/", json={"LocationIDs": [88888, 99999]})
    assert response.status_code == 200
    assert response.json() == [] # No locations were found to clear
