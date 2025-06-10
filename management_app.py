import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import os
import logging
import sys
import requests # Added requests

# --- Configuration ---
APP_NAME = "WMS Service Management"
API_BASE_URL = "http://127.0.0.1:8000" # Added API base URL
PID_FILE = "wms_service.pid"
LOG_FILE = "management_app.log"
WMS_MAIN_PY = "main.py" # Assumes main.py is in the same directory
# WMS_HOST and WMS_PORT are now superseded by API_BASE_URL for uvicorn command generation.
# WMS_HOST = "0.0.0.0" # Kept for reference, but not directly used by uvicorn cmd if API_BASE_URL is parsed
# WMS_PORT = 8000      # Kept for reference
TASK_NAME = "WMSServiceAutoStart"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout) # Also print to console for immediate feedback
    ]
)

# --- API Service Client ---
class ApiService:
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__) # Use the app's logger

    def _handle_response(self, response):
        """Helper to handle HTTP response, returning (bool, data_or_error_msg)."""
        try:
            response.raise_for_status() # Raises HTTPError for 4xx/5xx
            if response.status_code == 204: # No content, like DELETE
                return True, "Operation successful (No Content)"
            return True, response.json()
        except requests.exceptions.HTTPError as e: # Corrected exception type
            self.logger.error(f"API request failed with HTTPError: {e.response.status_code} - {e.response.text}")
            try:
                detail = e.response.json().get("detail", e.response.text)
            except requests.exceptions.JSONDecodeError: # Check if response is JSON before parsing detail
                detail = e.response.text
            return False, f"API Error {e.response.status_code}: {detail}"
        except requests.exceptions.JSONDecodeError: # If initial response.json() fails
            self.logger.error(f"API response JSONDecodeError for URL: {response.url}, Status: {response.status_code}, Content: {response.text[:200]}")
            return False, "API Error: Could not decode JSON response."
        except requests.exceptions.RequestException as e: # Catch other request exceptions (timeout, connection error)
            self.logger.error(f"API request failed due to RequestException: {e}")
            return False, f"Request Error: {e}"

    def create_location_record(self, data: dict) -> tuple[bool, dict | str]:
        self.logger.info(f"API: Creating location record with data: {data}")
        try:
            response = requests.post(f"{self.base_url}/locations/", json=data, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e: # Catch specific request exceptions like timeout
            self.logger.error(f"API create_location_record failed: {e}")
            return False, f"Connection Error: {e}" # More generic message for RequestException

    def get_location_records(self, params: dict = None) -> tuple[bool, list | str]:
        self.logger.info(f"API: Getting location records with params: {params if params else 'all'}")
        try:
            response = requests.get(f"{self.base_url}/locations/", params=params, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API get_location_records failed: {e}")
            return False, f"Connection Error: {e}"

    def update_location_record(self, location_id: int, data: dict) -> tuple[bool, dict | str]:
        self.logger.info(f"API: Updating location record ID {location_id} with data: {data}")
        try:
            response = requests.put(f"{self.base_url}/locations/{location_id}", json=data, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API update_location_record failed for ID {location_id}: {e}")
            return False, f"Connection Error: {e}"

    def delete_location_record_by_id(self, location_id: int) -> tuple[bool, str]:
        """
        Helper to delete a location by its LocationID.
        Note: UI might prefer deleting by MaterialID+TrayNumber, which would use find_location_id first.
        A dedicated API endpoint for MaterialID+TrayNumber deletion would be more efficient. (Planned for API refinement)
        """
        self.logger.info(f"API: Deleting location record ID {location_id}")
        try:
            response = requests.delete(f"{self.base_url}/locations/{location_id}", timeout=5)
            return self._handle_response(response) # _handle_response handles 204
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API delete_location_record_by_id failed for ID {location_id}: {e}")
            return False, f"Connection Error: {e}"

    def find_location_id(self, material_id: str, tray_number: str) -> tuple[bool, int | str]:
        self.logger.info(f"API: Finding LocationID for MaterialID: '{material_id}', TrayNumber: '{tray_number}'")

        # The current GET /locations/ API does not support server-side filtering by MaterialID or TrayNumber.
        # It only supports skip and limit. So, we must fetch all and filter client-side.
        # This is inefficient and should be improved with a dedicated API endpoint or better filtering.

        # TODO: Add comment about future API improvement for direct lookup or server-side filtering.
        # This is inefficient and should be improved with a dedicated API endpoint or better filtering.

        # TODO: Add comment about future API improvement for direct lookup or server-side filtering. # This TODO can be removed
        # API now supports server-side filtering, so pass params directly.
        params_for_find = {}
        if material_id: # Ensure we don't add None or empty string if that's not desired for query
            params_for_find["MaterialID"] = material_id
        if tray_number:
            params_for_find["TrayNumber"] = tray_number

        if not params_for_find: # Should not happen if called with valid material_id/tray_number
             return False, "MaterialID and TrayNumber are required for find_location_id."

        success, records_or_error = self.get_location_records(params=params_for_find)

        if not success:
            return False, f"Failed to get records for search: {records_or_error}"

        if not isinstance(records_or_error, list):
             return False, f"Unexpected response format from get_location_records: {type(records_or_error)}"

        # Server should have filtered. The list `records_or_error` contains matches.
        found_locations = records_or_error

        if not found_locations:
            self.logger.info(f"API Query: No location found for MaterialID: '{material_id}', TrayNumber: '{tray_number}'")
            return False, "Not found"

        if len(found_locations) > 1:
            self.logger.warning(f"Multiple locations ({len(found_locations)}) found for MaterialID: '{material_id}', TrayNumber: '{tray_number}'. Returning first one.")
            # Depending on requirements, this could be an error or just return the first.
            # For now, let's stick to the original logic of returning the first one if multiple found, but log a warning.
            # The requirement was "return (True, location_id) if found and unique". So this should be an error.
            return False, "Not unique (multiple records found)"

        location_id = found_locations[0].get("LocationID")
        if location_id is None: # Should not happen if record is valid
            self.logger.error(f"Found record for MaterialID: '{material_id}', TrayNumber: '{tray_number}' has no LocationID: {found_locations[0]}")
            return False, "Found record is invalid (missing LocationID)"

        self.logger.info(f"Found LocationID: {location_id} for MaterialID: '{material_id}', TrayNumber: '{tray_number}'")
        return True, location_id

    def clear_location_record_by_id(self, location_id: int) -> tuple[bool, dict | str]:
        """Clears a location record by its LocationID, setting MaterialID to empty."""
        self.logger.info(f"API: Clearing location record ID {location_id} using clear-one.")
        try:
            # Endpoint POST /locations/clear-one/ expects {"LocationID": location_id}
            # and returns the updated (cleared) record.
            response = requests.post(f"{self.base_url}/locations/clear-one/", json={"LocationID": location_id}, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API clear_location_record_by_id failed for ID {location_id}: {e}")
            return False, f"Connection Error: {e}"

    def clear_record_by_material_tray(self, material_id: str, tray_number: str) -> tuple[bool, dict | str]:
        """Clears a location record by MaterialID and TrayNumber using the dedicated API endpoint."""
        self.logger.info(f"API: Clearing record by MaterialID='{material_id}', TrayNumber='{tray_number}'")
        try:
            payload = {"MaterialID": material_id, "TrayNumber": tray_number}
            response = requests.post(f"{self.base_url}/locations/clear-by-material-tray/", json=payload, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API clear_record_by_material_tray failed for MaterialID='{material_id}', TrayNumber='{tray_number}': {e}")
            return False, f"Connection Error: {e}"

class ServiceManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("600x700") # Increased size for data management UI

        self.service_pid = None
        self.api_service = ApiService()
        self.selected_location_id_for_update = None # For tracking selected LocationID

        # --- Main PanedWindow for layout ---
        main_paned_window = ttk.PanedWindow(root, orient=tk.VERTICAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Top frame for service controls ---
        service_control_frame = ttk.LabelFrame(main_paned_window, text="Service Control")
        main_paned_window.add(service_control_frame, weight=0) # Give less weight initially

        # Status Label
        self.status_var = tk.StringVar(value="Status: Unknown")
        self.status_label = ttk.Label(service_control_frame, textvariable=self.status_var, font=("Arial", 12))
        self.status_label.pack(pady=5)

        # Control Buttons Frame
        button_frame = ttk.Frame(service_control_frame)
        button_frame.pack(pady=5)
        self.start_button = ttk.Button(button_frame, text="Start Service", command=self.start_service)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)
        self.stop_button = ttk.Button(button_frame, text="Stop Service", command=self.stop_service, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)
        self.restart_button = ttk.Button(button_frame, text="Restart Service", command=self.restart_service)
        self.restart_button.grid(row=0, column=2, padx=5, pady=5)

        # Auto-start Buttons Frame
        auto_start_frame = ttk.Frame(service_control_frame)
        auto_start_frame.pack(pady=5)
        self.enable_auto_start_button = ttk.Button(auto_start_frame, text="Enable Auto-start", command=self.enable_auto_start)
        self.enable_auto_start_button.grid(row=0, column=0, padx=5, pady=5)
        self.disable_auto_start_button = ttk.Button(auto_start_frame, text="Disable Auto-start", command=self.disable_auto_start)
        self.disable_auto_start_button.grid(row=0, column=1, padx=5, pady=5)

        # --- Bottom frame for data management ---
        data_management_frame = ttk.LabelFrame(main_paned_window, text="Data Management")
        main_paned_window.add(data_management_frame, weight=1)

        # "Record Details" Frame
        record_details_frame = ttk.LabelFrame(data_management_frame, text="Record Details")
        record_details_frame.pack(pady=10, padx=10, fill=tk.X)

        # LocationID
        ttk.Label(record_details_frame, text="LocationID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.location_id_entry = ttk.Entry(record_details_frame, state="readonly")
        self.location_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        # MaterialID
        ttk.Label(record_details_frame, text="MaterialID:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.material_id_entry = ttk.Entry(record_details_frame)
        self.material_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        # TrayNumber
        ttk.Label(record_details_frame, text="TrayNumber:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.tray_number_entry = ttk.Entry(record_details_frame)
        self.tray_number_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)

        # ProcessID
        ttk.Label(record_details_frame, text="ProcessID:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.process_id_entry = ttk.Entry(record_details_frame)
        self.process_id_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)

        # TaskID
        ttk.Label(record_details_frame, text="TaskID:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.task_id_entry = ttk.Entry(record_details_frame)
        self.task_id_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)

        # StatusNotes
        ttk.Label(record_details_frame, text="StatusNotes:").grid(row=5, column=0, padx=5, pady=5, sticky=tk.NW)
        self.status_notes_text = tk.Text(record_details_frame, height=3, width=30) # Width is approx chars
        self.status_notes_text.grid(row=5, column=1, padx=5, pady=5, sticky=tk.EW)

        # Timestamp
        ttk.Label(record_details_frame, text="Timestamp:").grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
        self.timestamp_val_label = ttk.Label(record_details_frame, text="")
        self.timestamp_val_label.grid(row=6, column=1, padx=5, pady=5, sticky=tk.W)

        record_details_frame.columnconfigure(1, weight=1) # Make entry column expandable

        # Action Buttons for Record Details
        record_action_frame = ttk.Frame(data_management_frame)
        record_action_frame.pack(pady=5, padx=10, fill=tk.X)

        self.add_record_button = ttk.Button(record_action_frame, text="Add Record", command=self._add_record_handler)
        self.add_record_button.pack(side=tk.LEFT, padx=5)

        self.update_record_button = ttk.Button(record_action_frame, text="Update Selected Record", command=self._update_record_handler, state=tk.DISABLED)
        self.update_record_button.pack(side=tk.LEFT, padx=5)

        self.clear_form_button = ttk.Button(record_action_frame, text="Clear Form", command=self._clear_record_form_handler)
        self.clear_form_button.pack(side=tk.LEFT, padx=5)

        # --- Query Locations Frame ---
        query_frame = ttk.LabelFrame(data_management_frame, text="Query Locations")
        query_frame.pack(pady=10, padx=10, fill=tk.X)

        ttk.Label(query_frame, text="Query by MaterialID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.query_material_id_entry = ttk.Entry(query_frame)
        self.query_material_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(query_frame, text="Query by TrayNumber:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.query_tray_number_entry = ttk.Entry(query_frame)
        self.query_tray_number_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.EW)

        self.search_button = ttk.Button(query_frame, text="Search", command=self._search_records_handler)
        self.search_button.grid(row=0, column=4, padx=10, pady=5)

        query_frame.columnconfigure(1, weight=1)
        query_frame.columnconfigure(3, weight=1)

        # --- Query Results Frame ---
        results_frame = ttk.LabelFrame(data_management_frame, text="Query Results")
        results_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        columns = ("LocationID", "MaterialID", "TrayNumber", "Timestamp", "ProcessID", "TaskID", "StatusNotes")
        self.results_table = ttk.Treeview(results_frame, columns=columns, show="headings")

        # Define column headings and initial widths
        col_defs = {
            "LocationID": {"text": "Loc. ID", "width": 60},
            "MaterialID": {"text": "Material ID", "width": 100},
            "TrayNumber": {"text": "Tray No.", "width": 80},
            "Timestamp": {"text": "Timestamp", "width": 150},
            "ProcessID": {"text": "Process ID", "width": 100},
            "TaskID": {"text": "Task ID", "width": 100},
            "StatusNotes": {"text": "Status Notes", "width": 200}
        }

        for col_name in columns:
            self.results_table.heading(col_name, text=col_defs.get(col_name, {}).get("text", col_name))
            width = col_defs.get(col_name, {}).get("width", 100)
            self.results_table.column(col_name, width=width, anchor=tk.W)

        # Scrollbars
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_table.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_table.xview)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.results_table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.results_table.pack(fill=tk.BOTH, expand=True)
        self.results_table.bind("<<TreeviewSelect>>", self._on_table_row_select)

        # --- Clear Location by Criteria Frame ---
        clear_criteria_frame = ttk.LabelFrame(data_management_frame, text="Clear Location by Criteria")
        clear_criteria_frame.pack(pady=10, padx=10, fill=tk.X)

        ttk.Label(clear_criteria_frame, text="MaterialID for Clear:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.delete_material_id_entry = ttk.Entry(clear_criteria_frame) # Renamed to avoid confusion with actual delete later
        self.delete_material_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(clear_criteria_frame, text="TrayNumber for Clear:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.delete_tray_number_entry = ttk.Entry(clear_criteria_frame) # Renamed
        self.delete_tray_number_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        self.clear_by_material_tray_button = ttk.Button(clear_criteria_frame, text="Clear by Mtrl+Tray", command=self._clear_record_by_material_tray_handler)
        self.clear_by_material_tray_button.grid(row=2, column=0, columnspan=2, padx=5, pady=10)

        info_label_clear = "Note: Clears record's MaterialID. Requires both MaterialID and TrayNumber."
        ttk.Label(clear_criteria_frame, text=info_label_clear, font=("Arial", 8)).grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky=tk.W)

        clear_criteria_frame.columnconfigure(1, weight=1)


        self.initial_status_check()
        self.update_auto_start_buttons_status()
        self._clear_record_form_handler() # Initialize form state

    def _clear_record_form_handler(self):
        self._log_action("Clearing record form.")
        self.location_id_entry.config(state=tk.NORMAL)
        self.location_id_entry.delete(0, tk.END)
        self.location_id_entry.config(state="readonly")

        self.material_id_entry.delete(0, tk.END)
        self.tray_number_entry.delete(0, tk.END)
        self.process_id_entry.delete(0, tk.END)
        self.task_id_entry.delete(0, tk.END)
        self.status_notes_text.delete("1.0", tk.END)
        self.timestamp_val_label.config(text="")

        self.update_record_button.config(state=tk.DISABLED)
        self.selected_location_id_for_update = None
        self.material_id_entry.focus() # Set focus to MaterialID for new entry

    def _add_record_handler(self):
        self._log_action("Add record button clicked.")
        material_id = self.material_id_entry.get().strip()
        tray_number = self.tray_number_entry.get().strip()
        process_id = self.process_id_entry.get().strip()
        task_id = self.task_id_entry.get().strip()
        status_notes = self.status_notes_text.get("1.0", tk.END).strip()

        if not material_id: # Basic validation
            messagebox.showerror("Validation Error", "MaterialID cannot be empty.")
            self._log_action("Add record validation failed: MaterialID empty.", logging.WARNING)
            return

        payload = {
            "MaterialID": material_id,
            "TrayNumber": tray_number,
            "ProcessID": process_id,
            "TaskID": task_id,
            "StatusNotes": status_notes
        }

        success, response_data = self.api_service.create_location_record(payload)

        if success:
            messagebox.showinfo("Success", f"Record added successfully. LocationID: {response_data.get('LocationID')}")
            self._log_action(f"Record added via API: {response_data}")
            self._clear_record_form_handler()
            # Optionally, refresh a results table here if implemented
        else:
            messagebox.showerror("API Error", f"Failed to add record: {response_data}")
            self._log_action(f"API failed to add record: {response_data}", logging.ERROR)


    def _update_record_handler(self):
        self._log_action("Update record button clicked.")
        if self.selected_location_id_for_update is None:
            messagebox.showerror("Error", "No record selected for update. LocationID is missing.")
            self._log_action("Update record failed: No LocationID selected/available.", logging.WARNING)
            return

        location_id = self.selected_location_id_for_update # Or parse from self.location_id_entry.get()

        material_id = self.material_id_entry.get().strip()
        # MaterialID might be optional for update, depending on API rules, but for now, let's assume it can be updated.
        # if not material_id:
        #     messagebox.showerror("Validation Error", "MaterialID cannot be empty for update.")
        #     self._log_action("Update record validation failed: MaterialID empty.", logging.WARNING)
        #     return

        payload = {
            "MaterialID": material_id, # If MaterialID should not be updatable, remove from payload
            "TrayNumber": self.tray_number_entry.get().strip(),
            "ProcessID": self.process_id_entry.get().strip(),
            "TaskID": self.task_id_entry.get().strip(),
            "StatusNotes": self.status_notes_text.get("1.0", tk.END).strip()
        }
        # Filter out any fields that are empty strings, if API expects nulls or omissions for "no change"
        # For now, sending all fields as they are from the form.
        # An alternative: payload = {k: v for k, v in payload.items() if v} if empty strings mean "remove" or "no change"
        # Or, more precisely, use model_dump(exclude_none=True) if using Pydantic models for payload.

        success, response_data = self.api_service.update_location_record(location_id, payload)

        if success:
            messagebox.showinfo("Success", f"Record {location_id} updated successfully.")
            self._log_action(f"Record {location_id} updated via API: {response_data}")
            self._clear_record_form_handler()
            # Optionally, refresh a results table here
        else:
            messagebox.showerror("API Error", f"Failed to update record {location_id}: {response_data}")
            self._log_action(f"API failed to update record {location_id}: {response_data}", logging.ERROR)


    def _populate_form_on_selection(self, selected_record_data: dict):
        """Populates the form fields when a record is selected (e.g., from a Treeview)."""
        self._log_action(f"Populating form with selected record: {selected_record_data.get('LocationID')}")
        self._clear_record_form_handler() # Clear previous state first

        self.location_id_entry.config(state=tk.NORMAL)
        self.location_id_entry.delete(0, tk.END)
        self.location_id_entry.insert(0, str(selected_record_data.get("LocationID", "")))
        self.location_id_entry.config(state="readonly")

        self.material_id_entry.delete(0, tk.END)
        self.material_id_entry.insert(0, selected_record_data.get("MaterialID", ""))

        self.tray_number_entry.delete(0, tk.END)
        self.tray_number_entry.insert(0, selected_record_data.get("TrayNumber", ""))

        self.process_id_entry.delete(0, tk.END)
        self.process_id_entry.insert(0, selected_record_data.get("ProcessID", ""))

        self.task_id_entry.delete(0, tk.END)
        self.task_id_entry.insert(0, selected_record_data.get("TaskID", ""))

        self.status_notes_text.delete("1.0", tk.END)
        self.status_notes_text.insert("1.0", selected_record_data.get("StatusNotes", ""))

        self.timestamp_val_label.config(text=selected_record_data.get("Timestamp", ""))

        self.selected_location_id_for_update = selected_record_data.get("LocationID")
        if self.selected_location_id_for_update is not None:
            self.update_record_button.config(state=tk.NORMAL)
        else:
            self.update_record_button.config(state=tk.DISABLED) # Should not happen if LocationID is always present

    def _clear_results_table(self):
        self._log_action("Clearing results table.")
        for item in self.results_table.get_children():
            self.results_table.delete(item)

    def _populate_results_table(self, records: list):
        self._log_action(f"Populating results table with {len(records)} records.")
        self._clear_results_table()
        for record in records:
            # Ensure values are in the correct order of self.results_table["columns"]
            # ("LocationID", "MaterialID", "TrayNumber", "Timestamp", "ProcessID", "TaskID", "StatusNotes")
            # Handle cases where a key might be missing from a record, defaulting to ""
            values = (
                record.get("LocationID", ""),
                record.get("MaterialID", ""),
                record.get("TrayNumber", ""),
                record.get("Timestamp", ""),
                record.get("ProcessID", ""),
                record.get("TaskID", ""),
                record.get("StatusNotes", "")
            )
            self.results_table.insert("", tk.END, values=values)

    def _search_records_handler(self):
        self._log_action("Search records button clicked.")
        query_material_id = self.query_material_id_entry.get().strip()
        query_tray_number = self.query_tray_number_entry.get().strip()

        params = {}
        if query_material_id:
            params["MaterialID"] = query_material_id
        if query_tray_number:
            params["TrayNumber"] = query_tray_number

        # If no search terms, get_location_records will fetch all (current API behavior)
        # Or, we can decide to show a message if both are empty.
        # For now, allow empty search to fetch all as per ApiService.get_location_records behavior.
        # However, find_location_id in ApiService already filters by MaterialID and TrayNumber client-side
        # after fetching ALL records. This is inefficient.
        # The get_location_records in ApiService is called with params, but the FastAPI backend
        # currently does not use these specific params (MaterialID, TrayNumber) for filtering.
        # It only uses 'skip' and 'limit'.
        # So, for now, this search will also fetch all and then we filter client side, or rely on _populate_results_table
        # to display everything and the user to visually find.
        # API now supports server-side filtering, so client-side filtering is removed here.

        self._log_action(f"Searching records with params: {params}")
        # If params is empty, get_location_records will fetch all.
        success, data_or_error = self.api_service.get_location_records(params=params)

        if success:
            if isinstance(data_or_error, list):
                self._populate_results_table(data_or_error) # data_or_error is now the filtered list from server
                messagebox.showinfo("Search Results", f"Found {len(data_or_error)} record(s).")
                self._log_action(f"Search successful, {len(data_or_error)} record(s) displayed.")
            else:
                messagebox.showerror("API Error", "Received unexpected data format from API.")
                self._log_action(f"API search returned unexpected data format: {type(data_or_error)}", logging.ERROR)
                self._clear_results_table()
        else:
            messagebox.showerror("API Error", f"Failed to search records: {data_or_error}")
            self._log_action(f"API search failed: {data_or_error}", logging.ERROR)
            self._clear_results_table()

    def _on_table_row_select(self, event):
        selected_items = self.results_table.selection()
        if not selected_items: # No item selected or selection cleared
            # Optionally clear form if desired when selection is lost.
            # self._clear_record_form_handler()
            return

        selected_item = selected_items[0] # Get the first selected item
        record_values = self.results_table.item(selected_item, "values")

        if not record_values: # Should not happen if selection is valid
            self._clear_record_form_handler() # Clear form if selection is somehow invalid
            return

        # Column names must match the order in self.results_table["columns"]
        column_names = self.results_table["columns"]
        selected_record_data = dict(zip(column_names, record_values))

        self._log_action(f"Table row selected. Data: {selected_record_data}")
        self._populate_form_on_selection(selected_record_data)

    def _clear_record_by_material_tray_handler(self):
        material_id = self.delete_material_id_entry.get().strip()
        tray_number = self.delete_tray_number_entry.get().strip()

        self._log_action(f"Clear by Mtrl+Tray button clicked for MaterialID: '{material_id}', TrayNumber: '{tray_number}'.")

        if not material_id or not tray_number:
            messagebox.showerror("Validation Error", "Both MaterialID and TrayNumber are required to clear a record.")
            self._log_action("Clear by Mtrl+Tray validation failed: MaterialID or TrayNumber empty.", logging.WARNING)
            return

        confirm_msg = f"Are you sure you want to clear the record for Material ID: '{material_id}' and Tray Number: '{tray_number}'?\nThis will mark the location as empty."
        if not messagebox.askyesno("Confirm Clear", confirm_msg):
            self._log_action("Clear operation cancelled by user.")
            return

        self._log_action(f"Attempting to clear record directly for MaterialID='{material_id}', TrayNumber='{tray_number}'.")

        clear_success, clear_response_data = self.api_service.clear_record_by_material_tray(material_id, tray_number)

        if clear_success:
            # clear_response_data is the cleared record dict from the API
            cleared_loc_id = clear_response_data.get("LocationID", "N/A") if isinstance(clear_response_data, dict) else "N/A"
            success_msg = f"Record for MaterialID '{material_id}', TrayNumber '{tray_number}' (LocationID: {cleared_loc_id}) cleared successfully."

            self._log_action(f"Clear successful via API. Response: {clear_response_data}")
            messagebox.showinfo("Success", success_msg)

            self.delete_material_id_entry.delete(0, tk.END)
            self.delete_tray_number_entry.delete(0, tk.END)
            self._search_records_handler() # Refresh table
        else:
            # clear_response_data here is an error message string
            error_msg = f"Failed to clear record for MaterialID '{material_id}', TrayNumber '{tray_number}': {clear_response_data}"
            messagebox.showerror("API Error", error_msg)
            self._log_action(error_msg, logging.ERROR)


    def _log_action(self, message, level=logging.INFO):
        logging.log(level, message)
        # Could also update self.log_text here if it was enabled

    def _get_service_command(self):
        # Resolve the absolute path to python executable and main.py
        python_exe = sys.executable
        # script_path = os.path.abspath(WMS_MAIN_PY) # Not strictly needed for the command string itself if main.py is in CWD for uvicorn

        # Parse host and port from API_BASE_URL for the Uvicorn command
        try:
            parts = API_BASE_URL.split("//")[-1].split(":")
            uvicorn_host = parts[0]
            uvicorn_port = parts[1] if len(parts) > 1 else "8000" # Default port if not in URL
        except Exception as e:
            self._log_action(f"Error parsing API_BASE_URL ('{API_BASE_URL}') for host/port: {e}. Defaulting to 127.0.0.1:8000 for uvicorn.", level=logging.WARNING)
            uvicorn_host = "127.0.0.1"
            uvicorn_port = "8000"

        # Ensure main_module_name correctly refers to 'main' if WMS_MAIN_PY is 'main.py'
        main_module_name = os.path.splitext(WMS_MAIN_PY)[0]
        return [python_exe, "-m", "uvicorn", f"{main_module_name}:app", f"--host={uvicorn_host}", f"--port={uvicorn_port}"]

    def initial_status_check(self):
        self._log_action("Performing initial WMS service status check.")
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, "r") as f:
                    pid = int(f.read().strip())
                # Check if process is running (Windows specific)
                # A more cross-platform way would be psutil.pid_exists(pid)
                # For now, using tasklist command
                cmd = ["tasklist", "/FI", f"PID eq {pid}"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
                stdout, stderr = process.communicate()
                if str(pid) in stdout.decode(errors='ignore'):
                    self.service_pid = pid
                    self.status_var.set("Status: Running")
                    self._log_action(f"Service found running with PID: {pid} from PID file.")
                    self.start_button.config(state=tk.DISABLED)
                    self.stop_button.config(state=tk.NORMAL)
                    return
                else:
                    self._log_action(f"PID {pid} from PID file not found in tasklist. Cleaning up stale PID file.")
                    os.remove(PID_FILE)
            except ValueError:
                self._log_action("Invalid PID in PID file. Cleaning up.", level=logging.WARNING)
                os.remove(PID_FILE)
            except Exception as e:
                self._log_action(f"Error checking PID file: {e}", level=logging.ERROR)
                if os.path.exists(PID_FILE): # cleanup if error was not about file existence
                    os.remove(PID_FILE)

        self.status_var.set("Status: Stopped")
        self._log_action("Service is stopped (no valid PID file or process found).")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def update_button_states(self):
        if self.service_pid:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.restart_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.restart_button.config(state=tk.DISABLED) # Can't restart if not running

    def start_service(self):
        self._log_action("Attempting to start WMS service...")
        if self.service_pid:
            messagebox.showwarning("Service Info", "Service is already running.")
            self._log_action("Start attempt failed: Service already running.")
            return

        if not os.path.exists(WMS_MAIN_PY):
            messagebox.showerror("Error", f"{WMS_MAIN_PY} not found. Cannot start service.")
            self._log_action(f"Start attempt failed: {WMS_MAIN_PY} not found.", level=logging.ERROR)
            self.status_var.set(f"Status: Error - {WMS_MAIN_PY} not found")
            return

        try:
            command = self._get_service_command()
            self._log_action(f"Executing command: {' '.join(command)}")
            # CREATE_NEW_PROCESS_GROUP allows Uvicorn to handle Ctrl+C correctly if needed,
            # and makes it easier to kill the whole process tree.
            # CREATE_NO_WINDOW hides the console window.
            process = subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
            self.service_pid = process.pid
            with open(PID_FILE, "w") as f:
                f.write(str(self.service_pid))

            self.status_var.set(f"Status: Running (PID: {self.service_pid})")
            self._log_action(f"Service started successfully with PID: {self.service_pid}.")
            messagebox.showinfo("Service Control", "WMS Service started successfully.")
        except Exception as e:
            self.service_pid = None
            self.status_var.set("Status: Error starting")
            self._log_action(f"Failed to start service: {e}", level=logging.ERROR)
            messagebox.showerror("Service Control Error", f"Failed to start WMS service: {e}")

        self.update_button_states()

    def stop_service(self):
        self._log_action("Attempting to stop WMS service...")
        if not self.service_pid:
            # Try to read from PID file if app was restarted and service was running
            if os.path.exists(PID_FILE):
                try:
                    with open(PID_FILE, "r") as f:
                        self.service_pid = int(f.read().strip())
                        self._log_action(f"Read PID {self.service_pid} from file for stopping.")
                except Exception as e:
                    self._log_action(f"Could not read PID from file during stop: {e}", level=logging.WARNING)
                    messagebox.showwarning("Service Info", "Service PID not found, cannot stop if not started by this manager instance or PID file is missing/corrupt.")
                    self.initial_status_check() # Re-evaluate status
                    return
            else:
                messagebox.showwarning("Service Info", "Service is not recorded as running.")
                self._log_action("Stop attempt failed: Service not recorded as running.")
                self.initial_status_check() # Re-evaluate status
                return

        try:
            self._log_action(f"Stopping process with PID: {self.service_pid} using taskkill.")
            # /T kills child processes, /F forces termination
            subprocess.run(["taskkill", "/F", "/PID", str(self.service_pid), "/T"], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self._log_action("Service stopped successfully via taskkill.")
            self.status_var.set("Status: Stopped")
            messagebox.showinfo("Service Control", "WMS Service stopped successfully.")
        except subprocess.CalledProcessError as e:
            self._log_action(f"taskkill command failed: {e}. Output: {e.stdout} Stderr: {e.stderr}", level=logging.ERROR)
            # Check if process is actually still running
            cmd_check = ["tasklist", "/FI", f"PID eq {self.service_pid}"]
            process_check = subprocess.Popen(cmd_check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            stdout_check, _ = process_check.communicate()
            if str(self.service_pid) not in stdout_check.decode(errors='ignore'):
                self._log_action(f"Process PID {self.service_pid} not found after taskkill failure, assuming stopped.", level=logging.INFO)
                self.status_var.set("Status: Stopped (taskkill reported error but process gone)")
            else:
                self._log_action(f"Service with PID {self.service_pid} might still be running after taskkill error.", level=logging.WARNING)
                messagebox.showerror("Service Control Error", f"Failed to stop WMS service with taskkill: {e}. It might still be running.")
                # Don't clear PID here as it might still be running
                self.update_button_states()
                return # Keep PID to allow another stop attempt
        except Exception as e:
            self.status_var.set("Status: Error stopping")
            self._log_action(f"An unexpected error occurred during stop: {e}", level=logging.ERROR)
            messagebox.showerror("Service Control Error", f"An unexpected error occurred while stopping WMS service: {e}")
            self.update_button_states()
            return # Keep PID

        self.service_pid = None
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        self.update_button_states()


    def restart_service(self):
        self._log_action("Attempting to restart WMS service...")
        self.stop_service()
        # Add a small delay to ensure the port is freed, etc.
        self.root.after(1000, self.start_service)

    def _check_task_exists(self):
        try:
            # Query task and check return code. If errorlevel is 1, task not found.
            result = subprocess.run(['schtasks', '/Query', '/TN', TASK_NAME], capture_output=True, text=True, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
            return result.returncode == 0 and TASK_NAME in result.stdout
        except FileNotFoundError: # schtasks not found
            self._log_action("schtasks command not found. Cannot check auto-start status.", level=logging.ERROR)
            messagebox.showerror("Error", "schtasks command not found. Is this a Windows environment?")
            return False
        except Exception as e:
            self._log_action(f"Error checking task '{TASK_NAME}': {e}", level=logging.ERROR)
            return False

    def update_auto_start_buttons_status(self):
        if self._check_task_exists():
            self.enable_auto_start_button.config(state=tk.DISABLED)
            self.disable_auto_start_button.config(state=tk.NORMAL)
            self._log_action(f"Auto-start task '{TASK_NAME}' is enabled.")
        else:
            self.enable_auto_start_button.config(state=tk.NORMAL)
            self.disable_auto_start_button.config(state=tk.DISABLED)
            self._log_action(f"Auto-start task '{TASK_NAME}' is disabled or not found.")

    def enable_auto_start(self):
        self._log_action(f"Attempting to enable auto-start (Task: {TASK_NAME})...")
        python_exe = sys.executable # Path to current python interpreter
        script_dir = os.path.abspath(os.path.dirname(__file__)) # Directory of management_app.py

        # Command to run uvicorn. Using full path to python.exe and main.py
        # The command executed by Task Scheduler needs to be robust.
        # Note: Using sys.executable ensures we use the same python env.
        # The path to main.py needs to be absolute.
        # Working directory for the task is crucial.
        # wms_script_path = os.path.join(script_dir, WMS_MAIN_PY) # Not needed here, command uses module path

        # Construct the command Task Scheduler will run.
        # It should use the same host/port as parsed from API_BASE_URL for consistency.
        try:
            parts = API_BASE_URL.split("//")[-1].split(":")
            uvicorn_host_for_task = parts[0]
            uvicorn_port_for_task = parts[1] if len(parts) > 1 else "8000"
        except Exception as e:
            self._log_action(f"Error parsing API_BASE_URL for task scheduler command: {e}. Defaulting to 127.0.0.1:8000.", level=logging.WARNING)
            uvicorn_host_for_task = "127.0.0.1"
            uvicorn_port_for_task = "8000"

        main_module_name_for_task = os.path.splitext(WMS_MAIN_PY)[0]
        uvicorn_command = f'"{python_exe}" -m uvicorn {main_module_name_for_task}:app --host {uvicorn_host_for_task} --port {uvicorn_port_for_task}'

        # Create a simple batch script wrapper for robustness
        batch_script_name = "run_wms_service.bat"
        batch_script_path = os.path.join(script_dir, batch_script_name)

        try:
            with open(batch_script_path, "w") as bf:
                bf.write(f"@echo off\n")
                bf.write(f"cd /D \"{script_dir}\"\n") # Change to the script's directory
                bf.write(f"echo Starting WMS Service...\n")
                bf.write(f"{uvicorn_command}\n")
            self._log_action(f"Created helper batch script: {batch_script_path}")
        except Exception as e:
            self._log_action(f"Failed to create batch script {batch_script_name}: {e}", level=logging.ERROR)
            messagebox.showerror("Auto-start Error", f"Failed to create helper batch script: {e}")
            return

        # SCHTASKS command
        # /SC ONLOGON: Runs when any user logs on.
        # /RL HIGHEST: Runs with highest privileges if needed (Uvicorn might not need this but good for general tasks)
        # /IT : Run task only if user is logged on. (Consider /RU System for background service, but that's more complex)
        # /F : Force create
        # WorkingDirectory is crucial for uvicorn to find main:app
        # Note: Task Scheduler will run this from system32 or similar if TR (Task Run) path is not absolute or WD is not set.
        # We are using a batch file that cds to the correct directory.
        schtasks_command = [
            'schtasks', '/Create', '/TN', TASK_NAME,
            '/TR', f'"{batch_script_path}"',
            '/SC', 'ONLOGON', '/RL', 'HIGHEST', '/F',
            # '/RU', 'SYSTEM' # For running without user logged on, but more complex. ONLOGON is simpler.
        ]

        try:
            self._log_action(f"Executing schtasks command: {' '.join(schtasks_command)}")
            result = subprocess.run(schtasks_command, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self._log_action(f"schtasks /Create output: {result.stdout}")
            messagebox.showinfo("Auto-start", f"Auto-start enabled for WMS service via Task '{TASK_NAME}'.")
            self._log_action(f"Successfully enabled auto-start task '{TASK_NAME}'.")
        except subprocess.CalledProcessError as e:
            self._log_action(f"Failed to create scheduled task: {e}. Output: {e.stdout}, Stderr: {e.stderr}", level=logging.ERROR)
            messagebox.showerror("Auto-start Error", f"Failed to enable auto-start: {e.stderr}")
        except FileNotFoundError:
             self._log_action("schtasks command not found. Cannot enable auto-start.", level=logging.ERROR)
             messagebox.showerror("Error", "schtasks command not found. Is this a Windows environment?")
        except Exception as e:
            self._log_action(f"An unexpected error occurred enabling auto-start: {e}", level=logging.ERROR)
            messagebox.showerror("Auto-start Error", f"An unexpected error occurred: {e}")

        self.update_auto_start_buttons_status()

    def disable_auto_start(self):
        self._log_action(f"Attempting to disable auto-start (Task: {TASK_NAME})...")
        schtasks_command = ['schtasks', '/Delete', '/TN', TASK_NAME, '/F']
        try:
            self._log_action(f"Executing schtasks command: {' '.join(schtasks_command)}")
            result = subprocess.run(schtasks_command, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self._log_action(f"schtasks /Delete output: {result.stdout}")
            messagebox.showinfo("Auto-start", "Auto-start disabled for WMS service.")
            self._log_action(f"Successfully disabled auto-start task '{TASK_NAME}'.")
        except subprocess.CalledProcessError as e:
            # If errorlevel is 1, it often means the task was not found, which is fine for deletion.
            if "ERROR: The specified task name" in e.stderr or e.returncode == 1 : # Check specific error message or return code
                 self._log_action(f"Task '{TASK_NAME}' not found or already deleted. Output: {e.stderr}", level=logging.INFO)
                 messagebox.showinfo("Auto-start Info", f"Auto-start task '{TASK_NAME}' was not found (already disabled).")
            else:
                self._log_action(f"Failed to delete scheduled task: {e}. Output: {e.stdout}, Stderr: {e.stderr}", level=logging.ERROR)
                messagebox.showerror("Auto-start Error", f"Failed to disable auto-start: {e.stderr}")
        except FileNotFoundError:
             self._log_action("schtasks command not found. Cannot disable auto-start.", level=logging.ERROR)
             messagebox.showerror("Error", "schtasks command not found. Is this a Windows environment?")
        except Exception as e:
            self._log_action(f"An unexpected error occurred disabling auto-start: {e}", level=logging.ERROR)
            messagebox.showerror("Auto-start Error", f"An unexpected error occurred: {e}")

        self.update_auto_start_buttons_status()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServiceManagerApp(root)
    root.mainloop()

    # Clean up PID file if service was running and GUI is closed
    if app.service_pid and os.path.exists(PID_FILE):
        # This cleanup is debatable. If the app crashes, PID file might remain.
        # If service is meant to run beyond GUI lifetime (e.g. started by task scheduler),
        # then PID file should not be deleted here.
        # For now, let's assume if GUI closes, we might want to stop the service or at least clear its PID.
        # However, the current stop_service logic handles PID cleanup.
        # A robust solution might involve a system tray app or a service that runs independently.
        # For this exercise, if the app is closed, we are not explicitly stopping the service.
        # The PID file will remain, and on next launch, initial_status_check will verify.
        app._log_action("Management app closing.")
        pass
