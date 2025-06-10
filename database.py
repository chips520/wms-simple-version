import sqlite3
from typing import List, Optional
from models import MaterialLocation, MaterialLocationCreate, MaterialLocationUpdate
from datetime import datetime

DATABASE_URL = "wms.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MaterialLocations (
            LocationID INTEGER PRIMARY KEY AUTOINCREMENT,
            MaterialID TEXT,
            Timestamp DATETIME NOT NULL,
            TrayNumber TEXT,
            ProcessID TEXT,
            TaskID TEXT,
            StatusNotes TEXT
        )
    """)
    conn.commit()
    conn.close()

# Initialize the table when the module is loaded
create_table()

def create_material_location(location: MaterialLocationCreate) -> MaterialLocation:
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow()
    cursor.execute("""
        INSERT INTO MaterialLocations (MaterialID, Timestamp, TrayNumber, ProcessID, TaskID, StatusNotes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (location.MaterialID, timestamp, location.TrayNumber, location.ProcessID, location.TaskID, location.StatusNotes))
    conn.commit()
    location_id = cursor.lastrowid
    conn.close()
    return MaterialLocation(LocationID=location_id, Timestamp=timestamp, **location.model_dump())

def get_material_locations(material_id: Optional[str] = None, tray_number: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[MaterialLocation]:
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM MaterialLocations"
    conditions = []
    params = []

    if material_id is not None:
        conditions.append("MaterialID = ?")
        params.append(material_id)

    if tray_number is not None:
        conditions.append("TrayNumber = ?")
        params.append(tray_number)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, skip])

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [MaterialLocation(**dict(row)) for row in rows] # Ensure row is dict for pydantic

def get_material_location(location_id: int) -> Optional[MaterialLocation]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM MaterialLocations WHERE LocationID = ?", (location_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return MaterialLocation(**row)
    return None

def update_material_location(location_id: int, location_update: MaterialLocationUpdate) -> Optional[MaterialLocation]:
    conn = get_db_connection()
    cursor = conn.cursor()

    update_data = location_update.model_dump(exclude_unset=True)
    if not update_data:
        conn.close()
        return get_material_location(location_id) # No fields to update

    # Add Timestamp to update_data as it should be updated on any change
    update_data["Timestamp"] = datetime.utcnow()

    set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values())
    values.append(location_id)

    cursor.execute(f"UPDATE MaterialLocations SET {set_clause} WHERE LocationID = ?", values)
    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        return None

    conn.close()
    return get_material_location(location_id)

def delete_material_location(location_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM MaterialLocations WHERE LocationID = ?", (location_id,))
    conn.commit()
    deleted_rows = cursor.rowcount
    conn.close()
    return deleted_rows > 0

def clear_material_location(location_id: int) -> Optional[MaterialLocation]:
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow()
    cursor.execute("""
        UPDATE MaterialLocations
        SET MaterialID = "", Timestamp = ?
        WHERE LocationID = ?
    """, (timestamp, location_id))
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        return None
    conn.close()
    # Fetch the updated record to return it
    return get_material_location(location_id)

def clear_location_by_material_tray(material_id: str, tray_number: str) -> Optional[MaterialLocation]:
    """Clears a location's MaterialID by MaterialID and TrayNumber, returning the updated record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow()

    # First, find the LocationID to ensure we can return the full record later
    # And to check if the record exists and is unique for these criteria
    # (Though MaterialID + TrayNumber should ideally be unique if not primary key)
    cursor.execute("SELECT LocationID FROM MaterialLocations WHERE MaterialID = ? AND TrayNumber = ?", (material_id, tray_number))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None # Record not found

    location_id = row["LocationID"]

    # Now, update the record
    cursor.execute("""
        UPDATE MaterialLocations
        SET MaterialID = '', Timestamp = ?
        WHERE LocationID = ?
    """, (timestamp, location_id))
    conn.commit()

    if cursor.rowcount == 0:
        # This case should ideally not be reached if we found the LocationID just before,
        # unless a concurrent modification happened.
        conn.close()
        return None

    conn.close()
    # Fetch and return the updated record using its LocationID
    return get_material_location(location_id)
