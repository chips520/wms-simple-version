# WMS Service Application

A FastAPI-based Warehouse Material Service (WMS) for tracking material locations. Includes a local Tkinter-based management application for service control.

## Features

**API (WMS Service):**
*   Create, Read, Update, Delete (CRUD) operations for material locations.
*   Batch updates for material locations.
*   Clear material ID from locations (single and batch).
*   Stores data in an SQLite database (`wms.db`).
*   Automatic API documentation via Swagger UI (`/docs`) and ReDoc (`/redoc`).

**Management Application (`management_app.py`):**
*   GUI for starting, stopping, and restarting the WMS service.
*   Enable/Disable auto-start of the WMS service on user logon (uses Windows Task Scheduler).
*   Displays current service status.
*   Logs management actions to `management_app.log`.

## Prerequisites

*   Python 3.7+
*   For auto-start functionality: Windows Operating System (uses Task Scheduler).

## Project Structure

```
.
├── main.py                 # FastAPI application for the WMS service.
├── database.py             # Handles SQLite database interactions.
├── models.py               # Pydantic models for data validation and serialization.
├── test_main.py            # Pytest unit tests for the API.
├── management_app.py       # Tkinter GUI application for managing the WMS service.
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
    *   `--host 0.0.0.0`: Makes the service accessible from your local network.
    *   `--port 8000`: Runs the service on port 8000.

2.  **API Documentation:**
    Once the service is running, you can access the interactive API documentation (Swagger UI) in your browser at:
    [http://localhost:8000/docs](http://localhost:8000/docs)

    ReDoc documentation is also available at:
    [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Using the Management Application (`management_app.py`)

The management application provides a GUI to control the WMS service locally. This is particularly useful on Windows.

1.  **Run the Application:**
    Ensure you are in the project root directory and your virtual environment (if used) is active.
    ```bash
    python management_app.py
    ```

2.  **Features:**
    *   **Status Display:** Shows if the WMS service is "Running", "Stopped", or in an "Unknown/Error" state.
    *   **Start Service:** Starts the WMS service (`uvicorn main:app ...`) as a background process. The PID is stored in `wms_service.pid`.
    *   **Stop Service:** Stops the running WMS service by terminating the process using the stored PID.
    *   **Restart Service:** Stops and then starts the WMS service.
    *   **Enable Auto-start:** Creates a task in Windows Task Scheduler to automatically start the WMS service when any user logs on. A `run_wms_service.bat` helper script is created in the project directory to facilitate this.
    *   **Disable Auto-start:** Removes the auto-start task from Windows Task Scheduler.

## Database

*   The application uses an SQLite database named `wms.db`.
*   This file will be automatically created in the project root directory when the WMS service starts for the first time or when database operations are performed.

## Testing

Unit tests for the API are written using Pytest.

1.  **Ensure Test Dependencies are Installed:**
    They are included in `requirements.txt`. If you did a minimal install, ensure `pytest` and `httpx` are installed:
    ```bash
    # pip install pytest httpx
    ```

2.  **Run Tests:**
    From the project root directory, run:
    ```bash
    pytest
    ```
    The tests use an in-memory SQLite database and do not affect `wms.db`.

This README provides a comprehensive overview of the WMS application, its setup, and usage.
