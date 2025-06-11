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
    *   Configuration of the WMS service's host IP and port, saved locally in `service_config.json`.
    *   Language selection for the GUI, with settings saved in `service_config.json`.
    *   Enable/Disable auto-start of the WMS service on user logon (uses Windows Task Scheduler).
    *   Displays current service status.
*   **Data Management:**
    *   Form to add new material location records.
    *   Form to update existing material location records (populated by selection from a table).
    *   Query interface to search for records by MaterialID and/or TrayNumber.
    *   Table display for query results.
    *   Function to "clear" a location based on MaterialID and TrayNumber (sets MaterialID to empty, updates timestamp).
*   Logs management and API interaction actions to `management_app.log`.
*   Internationalized interface (English and placeholder Chinese translations provided).

## Prerequisites

*   Python 3.7+
*   `requests` library (included in `requirements.txt`).
*   For auto-start functionality: Windows Operating System (uses Task Scheduler).
*   For viewing translations other than English: `gettext` utilities (e.g., `msgfmt`) to compile `.po` files into `.mo` files.

## Project Structure

```
.
├── locale/                   # Directory for localization files
│   ├── en/LC_MESSAGES/
│   │   ├── management_app.po # English translations
│   │   └── management_app.mo # Compiled English translations (if user compiles)
│   ├── zh/LC_MESSAGES/
│   │   ├── management_app.po # Chinese placeholder translations
│   │   └── management_app.mo # Compiled Chinese translations (if user compiles)
│   └── management_app.pot    # Template for translations
├── main.py                 # FastAPI application for the WMS service.
├── database.py             # Handles SQLite database interactions.
├── models.py               # Pydantic models for data validation and serialization.
├── test_main.py            # Pytest unit tests for the API.
├── management_app.py       # Tkinter GUI application for managing the WMS service and data.
├── requirements.txt        # Python dependencies.
├── service_config.json     # Stores host/port/language configuration for the WMS service.
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

The WMS service is a FastAPI application. The host and port it listens on are configured via the Management Application (see below) and default to `127.0.0.1:8000`.

1.  **Run Directly with Uvicorn (using default or configured settings):**
    To run the service manually, you should use the host and port configured in the Management Application. For example, if configured for `127.0.0.1:8000`:
    ```bash
    uvicorn main:app --host 127.0.0.1 --port 8000
    ```
    *   Add `--reload` for development: `uvicorn main:app --reload --host 127.0.0.1 --port 8000`.

2.  **API Documentation:**
    Once the service is running, you can access the interactive API documentation (Swagger UI) in your browser. If the service is running on `127.0.0.1:8000`:
    [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Adjust host if changed from `localhost`)

    ReDoc documentation is also available at:
    [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

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
    *   **Start/Stop/Restart Service:** Buttons to control the Uvicorn process running the WMS service. These actions use the host and port defined in the "Service Host/Port Configuration" section.
    *   **Enable/Disable Auto-start:** Manages Windows Task Scheduler entry for automatic service start on logon. The scheduled task also uses the configured host and port.
    *   **Service Host/Port Configuration & Language Selection:** This section, found within "Service Control", allows customization of service parameters and GUI language.

        *   **Host IP Address:** Enter the IP address the WMS service should listen on.
            -   `127.0.0.1` (default): The service will only be accessible from your local machine.
            -   `0.0.0.0`: The service will be accessible from other computers on your network (if your firewall allows).
        *   **Port Number:** Specify the port number for the service (default: `8000`).
        *   **Language:** Select the display language for the management application.
            -   Currently available: "English", "中文 (Chinese)" (Chinese translations are placeholders).
        *   Click the **"Save Configuration"** button to save these settings (Host, Port, Language). They are stored in a `service_config.json` file in the application's directory. If the file doesn't exist or is invalid, defaults are used on startup.
        *   **How these settings are used:**
            -   The Host IP and Port are used when you click "Start Service" and for the auto-start task.
            -   The Data Management features will use the configured Host IP and Port to connect to the service (updated immediately on save).
            -   The Language setting determines the UI language of the management application.
        *   **IMPORTANT: Application Restart Required for Language Change:**
            -   If the WMS service is already running and you change Host/Port, the *running* service itself will not use the new settings until it is **restarted**.
            -   Language changes require a **full restart** of the `management_app.py` application to take effect.

3.  **Data Management Features:**
    This section allows direct interaction with the WMS API for CRUD operations, using the host and port configured above.

    *   **Record Details Frame:**
        *   **Input Fields:** `MaterialID`, `TrayNumber`, `ProcessID`, `TaskID`, and `StatusNotes` (multi-line). `LocationID` and `Timestamp` are display-only, populated when a record is selected.
        *   **Add Record Button:** Collects data from the input fields (MaterialID is required) and calls the API to create a new location record.
        *   **Update Selected Record Button:** Enabled when a record is selected from the "Query Results" table. Collects data from the form and calls the API to update the selected record.
        *   **Clear Form Button:** Clears all fields in the "Record Details" section, disables the "Update" button, and resets selection state.

    *   **Query Locations Frame:**
        *   **Input Fields:** "Query by MaterialID" and "Query by TrayNumber".
        *   **Search Button:** Retrieves records from the API based on the provided MaterialID and/or TrayNumber using efficient server-side filtering. If both fields are empty, it fetches all records. Results are displayed in the "Query Results" table.

    *   **Query Results Table:**
        *   **Display:** Shows records retrieved from the API. Columns include: `Loc. ID`, `Material ID`, `Tray No.`, `Timestamp`, `Process ID`, `Task ID`, and `Status Notes`.
        *   **Selection:** Clicking a row in this table populates the "Record Details" form with that record's data, allowing for viewing or updating.

    *   **Clear Location by Criteria Frame:**
        *   **Input Fields:** "MaterialID for Clear" and "TrayNumber for Clear".
        *   **Clear by Mtrl+Tray Button:** Uses a dedicated API endpoint to "clear" a specific record (sets its MaterialID to empty and updates the timestamp) matching both provided criteria.
        *   **Confirmation:** Requires both MaterialID and TrayNumber, and prompts for user confirmation before proceeding.

## Internationalization (i18n)

The management application GUI supports multiple languages.

*   **Language Selection:** Change the display language via the "Language" dropdown in the "Service Host/Port Configuration" section (under "Service Control") and click "Save Configuration". **A restart of `management_app.py` is required for language changes to take effect.**
*   **Translation Files:**
    - This application uses the `gettext` system. Translation files are located in the `locale/` directory.
    - The template file is `locale/management_app.pot`.
    - Language-specific files include:
        - `locale/en/LC_MESSAGES/management_app.po` (English)
        - `locale/zh/LC_MESSAGES/management_app.po` (Chinese, with placeholder `[zh]` prefixes)
*   **`.mo` File Compilation (User Action Required):**
    - For translations to be active, the `.po` files must be compiled into binary `.mo` files. These were **not pre-compiled** in the development environment due to tool limitations.
    - **To enable translations (e.g., see Chinese placeholders):** You need `gettext` utilities installed. Use the `msgfmt` command:
      ```bash
      # Example for Chinese:
      msgfmt -o locale/zh/LC_MESSAGES/management_app.mo locale/zh/LC_MESSAGES/management_app.po
      # Example for English (if you modify its .po):
      msgfmt -o locale/en/LC_MESSAGES/management_app.mo locale/en/LC_MESSAGES/management_app.po
      ```
    - Without the corresponding `.mo` file for a selected language (or if `gettext` setup fails), the application will default to English.
*   **Contributing Translations:**
    1.  Use `locale/management_app.pot` as a template to create or update a `<lang_code>/LC_MESSAGES/management_app.po` file.
    2.  Translate the `msgstr` entries in your `.po` file.
    3.  Compile it to a `.mo` file using `msgfmt`.
    4.  Add the new language code and its display name to the `supported_languages` dictionary in `management_app.py`.

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
