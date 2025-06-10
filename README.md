# WMS Service Application

A FastAPI-based Warehouse Material Service (WMS) for tracking material locations. Includes a local Tkinter-based management application for service control and data interaction.

## Features

**API (WMS Service):**
*   Create, Read, Update, Delete (CRUD) operations for material locations.
*   Batch updates and batch clear for material locations.
*   Efficient server-side filtering for GET /locations/ by MaterialID and/or TrayNumber.
*   Dedicated endpoint to clear a location by MaterialID and TrayNumber.
*   Stores data in an SQLite database (`wms.db`).
*   Automatic API documentation via Swagger UI (`/docs`) and ReDoc (`/redoc`).

**Management Application (`management_app.py`):**
*   **Service Control:**
    *   GUI for starting, stopping, and restarting the WMS service.
    *   Enable/Disable auto-start of the WMS service on user logon (uses Windows Task Scheduler).
    *   Displays current service status.
*   **Data Management:**
    *   Form to add new material location records.
    *   Form to update existing material location records (populated by selection from a table).
    *   Query interface to search for records by MaterialID and/or TrayNumber.
    *   Table display for query results.
    *   Function to "clear" a location based on MaterialID and TrayNumber (sets MaterialID to empty, updates timestamp).
*   Logs management and API interaction actions to `management_app.log`.

## Prerequisites

*   Python 3.7+
*   `requests` library (included in `requirements.txt`).
*   For auto-start functionality: Windows Operating System (uses Task Scheduler).

## Project Structure

```
.
├── main.py                 # FastAPI application for the WMS service.
├── database.py             # Handles SQLite database interactions.
├── models.py               # Pydantic models for data validation and serialization.
├── test_main.py            # Pytest unit tests for the API.
├── management_app.py       # Tkinter GUI application for managing the WMS service and data.
├── requirements.txt        # Python dependencies.
├── wms.db                  # SQLite database file (created automatically).
├── wms_service.pid         # Stores PID of running WMS service (managed by management_app.py).
├── management_app.log      # Log file for management_app.py.
├── run_wms_service.bat     # Helper script for Task Scheduler (created by management_app.py).
└── README.md               # This file.
```

## Setup & Installation

1.  **Clone the Repository (if applicable):**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the WMS Service

The WMS service is a FastAPI application.

1.  **Run Directly with Uvicorn:**
    Open your terminal in the project root directory and run:
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    *   `--reload`: Enables auto-reload on code changes (for development).
    *   `--host 0.0.0.0` (or `127.0.0.1` as configured in `management_app.py`'s `API_BASE_URL` for Uvicorn): Makes the service accessible.
    *   `--port 8000`: Runs the service on port 8000.

2.  **API Documentation:**
    Once the service is running, you can access the interactive API documentation (Swagger UI) in your browser at:
    [http://localhost:8000/docs](http://localhost:8000/docs) (Adjust host if changed from `localhost`)

    ReDoc documentation is also available at:
    [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Using the Management Application (`management_app.py`)

The management application provides a GUI to control the WMS service and manage its data.

1.  **Run the Application:**
    Ensure you are in the project root directory and your virtual environment (if used) is active.
    ```bash
    python management_app.py
    ```
    The application window is divided into "Service Control" and "Data Management" sections.

2.  **Service Control Features:**
    *   **Status Display:** Shows if the WMS service is "Running", "Stopped", etc.
    *   **Start/Stop/Restart Service:** Buttons to control the Uvicorn process running the WMS service.
    *   **Enable/Disable Auto-start:** Manages Windows Task Scheduler entry for automatic service start on logon.

3.  **Data Management in GUI:**
    This section allows direct interaction with the WMS API for CRUD operations.

    *   **Record Details Frame:**
        *   **Input Fields:** `MaterialID`, `TrayNumber`, `ProcessID`, `TaskID`, and `StatusNotes` (multi-line). `LocationID` and `Timestamp` are display-only.
        *   **Add Record Button:** Collects data from the input fields (MaterialID is required) and calls the API to create a new location record.
        *   **Update Selected Record Button:** Enabled when a record is selected from the "Query Results" table. Collects data from the form and calls the API to update the selected record.
        *   **Clear Form Button:** Clears all fields in the "Record Details" section, disables the "Update" button, and resets selection state.

    *   **Query Locations Frame:**
        *   **Input Fields:** "Query by MaterialID" and "Query by TrayNumber".
        *   **Search Button:** Retrieves records from the API based on the provided MaterialID and/or TrayNumber. If both are empty, it fetches all records. Results are displayed in the "Query Results" table.
        *   *API Note:* Search operations use efficient server-side filtering.

    *   **Query Results Table:**
        *   **Display:** Shows records retrieved from the API. Columns include: `Loc. ID`, `Material ID`, `Tray No.`, `Timestamp`, `Process ID`, `Task ID`, and `Status Notes`.
        *   **Selection:** Clicking a row in this table populates the "Record Details" form with that record's data, allowing for viewing or updating.

    *   **Clear Location by Criteria Frame:**
        *   **Input Fields:** "MaterialID for Clear" and "TrayNumber for Clear".
        *   **Clear by Mtrl+Tray Button:** Uses the API to "clear" a specific record (sets its MaterialID to empty and updates the timestamp) matching both provided criteria.
        *   **Confirmation:** Requires both MaterialID and TrayNumber, and prompts for user confirmation before proceeding.
        *   *API Note:* This uses a dedicated, efficient API endpoint.

## Database

*   The application uses an SQLite database named `wms.db`.
*   This file will be automatically created in the project root directory when the WMS service starts for the first time.

## Testing

Unit tests for the API are written using Pytest.

1.  **Ensure Test Dependencies are Installed:**
    They are included in `requirements.txt`.

2.  **Run Tests:**
    From the project root directory, run:
    ```bash
    pytest
    ```
    The tests use an in-memory SQLite database and do not affect `wms.db`.
