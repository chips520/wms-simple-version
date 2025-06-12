import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import os
import logging
import sys
import requests
import json
import gettext
import builtins

# --- Configuration ---
APP_NAME = "WMS Service Management" # Default English, will be translated by _() call in __init__
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
CONFIG_FILE_NAME = "service_config.json"

PID_FILE = "wms_service.pid"
LOG_FILE = "management_app.log"
WMS_MAIN_PY = "main.py"
TASK_NAME = "WMSServiceAutoStart"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- API Service Client ---
class ApiService:
    def __init__(self, base_url):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)

    def update_base_url(self, new_base_url):
        self.base_url = new_base_url
        self.logger.info(f"ApiService base_url updated to: {self.base_url}") # Internal log

    def _handle_response(self, response):
        _ = builtins.__dict__.get('_', lambda s: s) # Ensure _ is available
        try:
            response.raise_for_status()
            if response.status_code == 204:
                return True, _("Operation successful (No Content)")
            return True, response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"API request failed with HTTPError: {e.response.status_code} - {e.response.text}")
            try:
                detail = e.response.json().get("detail", e.response.text)
            except requests.exceptions.JSONDecodeError:
                detail = e.response.text
            return False, _("API Error {status_code}: {detail}").format(status_code=e.response.status_code, detail=detail)
        except requests.exceptions.JSONDecodeError:
            self.logger.error(f"API response JSONDecodeError for URL: {response.url}, Status: {response.status_code}, Content: {response.text[:200]}")
            return False, _("API Error: Could not decode JSON response.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed due to RequestException: {e}")
            return False, _("Request Error: {error}").format(error=e)

    def create_location_record(self, data: dict) -> tuple[bool, dict | str]:
        _ = builtins.__dict__.get('_', lambda s: s)
        self.logger.info(f"API: Creating location record with data: {data}")
        try:
            response = requests.post(f"{self.base_url}/locations/", json=data, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API create_location_record failed: {e}")
            return False, _("Connection Error: {error}").format(error=e)

    def get_location_records(self, params: dict = None) -> tuple[bool, list | str]:
        _ = builtins.__dict__.get('_', lambda s: s)
        self.logger.info(f"API: Getting location records with params: {params if params else 'all'}")
        try:
            response = requests.get(f"{self.base_url}/locations/", params=params, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API get_location_records failed: {e}")
            return False, _("Connection Error: {error}").format(error=e)

    def update_location_record(self, location_id: int, data: dict) -> tuple[bool, dict | str]:
        _ = builtins.__dict__.get('_', lambda s: s)
        self.logger.info(f"API: Updating location record ID {location_id} with data: {data}")
        try:
            response = requests.put(f"{self.base_url}/locations/{location_id}", json=data, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API update_location_record failed for ID {location_id}: {e}")
            return False, _("Connection Error: {error}").format(error=e)

    def delete_location_record_by_id(self, location_id: int) -> tuple[bool, str]:
        _ = builtins.__dict__.get('_', lambda s: s)
        self.logger.info(f"API: Deleting location record ID {location_id}")
        try:
            response = requests.delete(f"{self.base_url}/locations/{location_id}", timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API delete_location_record_by_id failed for ID {location_id}: {e}")
            return False, _("Connection Error: {error}").format(error=e)

    def find_location_id(self, material_id: str, tray_number: str) -> tuple[bool, int | str]:
        _ = builtins.__dict__.get('_', lambda s: s)
        self.logger.info(f"API: Finding LocationID for MaterialID: '{material_id}', TrayNumber: '{tray_number}'")
        params_for_find = {}
        if material_id:
            params_for_find["MaterialID"] = material_id
        if tray_number:
            params_for_find["TrayNumber"] = tray_number
        if not params_for_find:
             return False, _("MaterialID and TrayNumber are required for find_location_id.")
        success, records_or_error = self.get_location_records(params=params_for_find)
        if not success:
            return False, _("Failed to get records for search: {error}").format(error=records_or_error)
        if not isinstance(records_or_error, list):
             return False, _("Unexpected response format from get_location_records: {error_type}").format(error_type=type(records_or_error))
        found_locations = records_or_error
        if not found_locations:
            self.logger.info(f"API Query: No location found for MaterialID: '{material_id}', TrayNumber: '{tray_number}'")
            return False, _("Not found")
        if len(found_locations) > 1:
            self.logger.warning(f"Multiple locations ({len(found_locations)}) found for MaterialID: '{material_id}', TrayNumber: '{tray_number}'.")
            return False, _("Not unique (multiple records found)")
        location_id = found_locations[0].get("LocationID")
        if location_id is None:
            self.logger.error(f"Found record for MaterialID: '{material_id}', TrayNumber: '{tray_number}' has no LocationID: {found_locations[0]}")
            return False, _("Found record is invalid (missing LocationID)")
        self.logger.info(f"Found LocationID: {location_id} for MaterialID: '{material_id}', TrayNumber: '{tray_number}'")
        return True, location_id

    def clear_location_record_by_id(self, location_id: int) -> tuple[bool, dict | str]:
        _ = builtins.__dict__.get('_', lambda s: s)
        self.logger.info(f"API: Clearing location record ID {location_id} using clear-one.")
        try:
            response = requests.post(f"{self.base_url}/locations/clear-one/", json={"LocationID": location_id}, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API clear_location_record_by_id failed for ID {location_id}: {e}")
            return False, _("Connection Error: {error}").format(error=e)

    def clear_record_by_material_tray(self, material_id: str, tray_number: str) -> tuple[bool, dict | str]:
        _ = builtins.__dict__.get('_', lambda s: s)
        self.logger.info(f"API: Clearing record by MaterialID='{material_id}', TrayNumber='{tray_number}'")
        try:
            payload = {"MaterialID": material_id, "TrayNumber": tray_number}
            response = requests.post(f"{self.base_url}/locations/clear-by-material-tray/", json=payload, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API clear_record_by_material_tray failed for MaterialID='{material_id}', TrayNumber='{tray_number}': {e}")
            return False, _("Connection Error: {error}").format(error=e)

class ServiceManagerApp:
    def __init__(self, root):
        self.root = root
        self.logger = logging.getLogger(__name__)
        self.config_file_path = os.path.abspath(CONFIG_FILE_NAME)
        self.service_config = self._load_config()

        self.setup_translations() # Setup translations early

        self.root.title(_(APP_NAME)) # Now _ should be defined by gettext or fallback
        self.root.geometry("600x800")

        self.service_pid = None
        self.current_api_base_url = f"http://{self.service_config['host']}:{self.service_config['port']}"
        self.api_service = ApiService(base_url=self.current_api_base_url)
        self.selected_location_id_for_update = None

        self.supported_languages = {"en": _("English"), "zh": _("中文 (Chinese)")}

        self._setup_ui(root)

        self.initial_status_check()
        self.update_auto_start_buttons_status()
        self._clear_record_form_handler()
        self._populate_config_ui_fields()
        self._populate_language_combo()


    def setup_translations(self):
        lang_code = self.service_config.get('language', 'en')
        self.logger.info(f"Attempting to set up translations for language: {lang_code}")
        try:
            localedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locale')
            lang = gettext.translation('management_app', localedir=localedir, languages=[lang_code], fallback=True)
            lang.install()
            # Verify by translating a known string immediately
            self.logger.info(f"Translations for language '{lang_code}' installed. Test: '{_('Service Control')}'")
        except Exception as e:
            self.logger.error(f"Failed to install translations for language '{lang_code}': {e}. Falling back to default strings.")
            builtins.__dict__['_'] = lambda s: s

    def _setup_ui(self, root):
        # This ensures _ is available from gettext or fallback before UI elements are created
        _ = builtins.__dict__.get('_', lambda s: s)

        main_paned_window = ttk.PanedWindow(root, orient=tk.VERTICAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        service_control_frame = ttk.LabelFrame(main_paned_window, text=_("Service Control"))
        main_paned_window.add(service_control_frame, weight=0)

        self.status_var = tk.StringVar(value=_("Status: Unknown"))
        self.status_label = ttk.Label(service_control_frame, textvariable=self.status_var, font=("Arial", 12))
        self.status_label.pack(pady=5)

        button_frame = ttk.Frame(service_control_frame)
        button_frame.pack(pady=5)
        self.start_button = ttk.Button(button_frame, text=_("Start Service"), command=self.start_service)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)
        self.stop_button = ttk.Button(button_frame, text=_("Stop Service"), command=self.stop_service, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)
        self.restart_button = ttk.Button(button_frame, text=_("Restart Service"), command=self.restart_service)
        self.restart_button.grid(row=0, column=2, padx=5, pady=5)

        auto_start_frame = ttk.Frame(service_control_frame)
        auto_start_frame.pack(pady=5)
        self.enable_auto_start_button = ttk.Button(auto_start_frame, text=_("Enable Auto-start"), command=self.enable_auto_start)
        self.enable_auto_start_button.grid(row=0, column=0, padx=5, pady=5)
        self.disable_auto_start_button = ttk.Button(auto_start_frame, text=_("Disable Auto-start"), command=self.disable_auto_start)
        self.disable_auto_start_button.grid(row=0, column=1, padx=5, pady=5)

        config_ui_frame = ttk.LabelFrame(service_control_frame, text=_("Service Host/Port Configuration"))
        config_ui_frame.pack(pady=10, padx=10, fill=tk.X, side=tk.BOTTOM, expand=False)

        ttk.Label(config_ui_frame, text=_("Host IP Address:")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.host_ip_entry = ttk.Entry(config_ui_frame, width=30)
        self.host_ip_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(config_ui_frame, text=_("Port Number:")).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_number_entry = ttk.Entry(config_ui_frame, width=15)
        self.port_number_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(config_ui_frame, text=_("Language:")).grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.language_var = tk.StringVar()
        self.language_combo = ttk.Combobox(config_ui_frame, textvariable=self.language_var,
                                           values=list(self.supported_languages.values()), state="readonly", width=27)
        self.language_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)

        self.save_config_button = ttk.Button(config_ui_frame, text=_("Save Configuration"), command=self._save_config_handler)
        self.save_config_button.grid(row=3, column=0, columnspan=2, padx=5, pady=10) # Adjusted row for save button
        config_ui_frame.columnconfigure(1, weight=1)

        data_management_frame = ttk.LabelFrame(main_paned_window, text=_("Data Management"))
        main_paned_window.add(data_management_frame, weight=1)

        # Create the Notebook widget for data management tabs
        self.data_notebook = ttk.Notebook(data_management_frame)
        self.data_notebook.pack(expand=True, fill='both', pady=5, padx=5)

        # --- Tab 1: Manage Records (Add, Update, Clear by Criteria) ---
        self.manage_records_tab = ttk.Frame(self.data_notebook) # Parent is the notebook
        self.data_notebook.add(self.manage_records_tab, text=_("Manage Records"))

        # "Record Details" Frame - now parented to manage_records_tab
        self.record_details_frame = ttk.LabelFrame(self.manage_records_tab, text=_("Record Details"))
        self.record_details_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5, expand=False)

        ttk.Label(self.record_details_frame, text=_("LocationID:")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.location_id_entry = ttk.Entry(self.record_details_frame, state="readonly")
        self.location_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(record_details_frame, text=_("MaterialID:")).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.material_id_entry = ttk.Entry(record_details_frame)
        self.material_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(record_details_frame, text=_("TrayNumber:")).grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.tray_number_entry = ttk.Entry(record_details_frame)
        self.tray_number_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(record_details_frame, text=_("ProcessID:")).grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.process_id_entry = ttk.Entry(record_details_frame)
        self.process_id_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(record_details_frame, text=_("TaskID:")).grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.task_id_entry = ttk.Entry(record_details_frame)
        self.task_id_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(record_details_frame, text=_("StatusNotes:")).grid(row=5, column=0, padx=5, pady=5, sticky=tk.NW)
        self.status_notes_text = tk.Text(record_details_frame, height=3, width=30)
        self.status_notes_text.grid(row=5, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(record_details_frame, text=_("Timestamp:")).grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
        self.timestamp_val_label = ttk.Label(record_details_frame, text="")
        self.timestamp_val_label.grid(row=6, column=1, padx=5, pady=5, sticky=tk.W)
        record_details_frame.columnconfigure(1, weight=1)

        record_action_frame = ttk.Frame(data_management_frame)
        record_action_frame.pack(pady=5, padx=10, fill=tk.X)
        self.add_record_button = ttk.Button(record_action_frame, text=_("Add Record"), command=self._add_record_handler)
        self.add_record_button.pack(side=tk.LEFT, padx=5)
        self.update_record_button = ttk.Button(record_action_frame, text=_("Update Selected Record"), command=self._update_record_handler, state=tk.DISABLED)
        self.update_record_button.pack(side=tk.LEFT, padx=5)
        self.clear_form_button = ttk.Button(record_action_frame, text=_("Clear Form"), command=self._clear_record_form_handler)
        self.clear_form_button.pack(side=tk.LEFT, padx=5)

        # Clear Location by Criteria Frame - now parented to manage_records_tab
        self.clear_by_criteria_frame = ttk.LabelFrame(self.manage_records_tab, text=_("Clear Location by Criteria"))
        self.clear_by_criteria_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5, expand=False) # This was already correct
        ttk.Label(self.clear_by_criteria_frame, text=_("MaterialID for Clear:")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.delete_material_id_entry = ttk.Entry(self.clear_by_criteria_frame)
        self.delete_material_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(clear_criteria_frame, text=_("TrayNumber for Clear:")).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.delete_tray_number_entry = ttk.Entry(self.clear_by_criteria_frame)
        self.delete_tray_number_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.clear_by_material_tray_button = ttk.Button(self.clear_by_criteria_frame, text=_("Clear by Mtrl+Tray"), command=self._clear_record_by_material_tray_handler)
        self.clear_by_material_tray_button.grid(row=2, column=0, columnspan=2, padx=5, pady=10)
        info_label_clear = _("Note: Clears record's MaterialID. Requires both MaterialID and TrayNumber.")
        ttk.Label(self.clear_by_criteria_frame, text=info_label_clear, font=("Arial", 8)).grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky=tk.W)
        self.clear_by_criteria_frame.columnconfigure(1, weight=1)

        # --- Tab 2: Search Locations ---
        self.search_locations_tab = ttk.Frame(self.data_notebook)
        self.data_notebook.add(self.search_locations_tab, text=_("Search Locations"))

        # Query Locations Frame - now parented to search_locations_tab
        self.query_locations_frame = ttk.LabelFrame(self.search_locations_tab, text=_("Query Locations"))
        self.query_locations_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5, expand=False)
        ttk.Label(self.query_locations_frame, text=_("Query by MaterialID:")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.query_material_id_entry = ttk.Entry(self.query_locations_frame)
        self.query_material_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(self.query_locations_frame, text=_("Query by TrayNumber:")).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.query_tray_number_entry = ttk.Entry(self.query_locations_frame)
        self.query_tray_number_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.EW)
        self.search_button = ttk.Button(self.query_locations_frame, text=_("Search"), command=self._search_records_handler)
        self.search_button.grid(row=0, column=4, padx=10, pady=5)
        self.query_locations_frame.columnconfigure(1, weight=1)
        self.query_locations_frame.columnconfigure(3, weight=1)

        # Query Results Frame - now parented to search_locations_tab
        self.query_results_frame = ttk.LabelFrame(self.search_locations_tab, text=_("Query Results"))
        self.query_results_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        columns = ("LocationID", "MaterialID", "TrayNumber", "Timestamp", "ProcessID", "TaskID", "StatusNotes")
        self.results_table = ttk.Treeview(self.query_results_frame, columns=columns, show="headings")
        col_defs = {
            "LocationID": {"text": _("Loc. ID"), "width": 60},
            "MaterialID": {"text": _("Material ID"), "width": 100},
            "TrayNumber": {"text": _("Tray No."), "width": 80},
            "Timestamp": {"text": _("Timestamp"), "width": 150},
            "ProcessID": {"text": _("Process ID"), "width": 100},
            "TaskID": {"text": _("Task ID"), "width": 100},
            "StatusNotes": {"text": _("Status Notes"), "width": 200}
        }
        for col_name in columns:
            self.results_table.heading(col_name, text=col_defs.get(col_name, {}).get("text", col_name))
            width = col_defs.get(col_name, {}).get("width", 100)
            self.results_table.column(col_name, width=width, anchor=tk.W)
        vsb = ttk.Scrollbar(self.query_results_frame, orient="vertical", command=self.results_table.yview) # Corrected parent
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb = ttk.Scrollbar(self.query_results_frame, orient="horizontal", command=self.results_table.xview) # Corrected parent
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.results_table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.results_table.pack(fill=tk.BOTH, expand=True) # This is correct for Treeview within its frame
        self.results_table.bind("<<TreeviewSelect>>", self._on_table_row_select)

    def _populate_language_combo(self):
        # Helper to populate language combo; called after UI is setup
        _ = builtins.__dict__.get('_', lambda s: s)
        # The values in the combobox should also be translatable if they are "English", "Chinese"
        # For now, using the display names from supported_languages which are already translated
        # if _ is working correctly during their definition.
        # However, supported_languages values are translated at the point of definition.
        # For the combobox, it's better to store codes and translate them for display.
        # Or, ensure supported_languages is defined *after* _ is set by gettext.
        # For simplicity, let's assume supported_languages values are fine as is for now.
        display_langs = [self.supported_languages.get(code, code) for code in self.supported_languages.keys()]
        self.language_combo['values'] = display_langs

        current_lang_code = self.service_config.get('language', 'en')
        display_value = self._get_display_language(current_lang_code)
        self.language_var.set(display_value)
        self.logger.info(f"Language dropdown populated. Current selection: {display_value} ({current_lang_code})")


    def _populate_config_ui_fields(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        if hasattr(self, 'host_ip_entry') and hasattr(self, 'port_number_entry'):
            self.host_ip_entry.delete(0, tk.END)
            self.host_ip_entry.insert(0, self.service_config.get('host', DEFAULT_HOST))
            self.port_number_entry.delete(0, tk.END)
            self.port_number_entry.insert(0, str(self.service_config.get('port', DEFAULT_PORT)))
            self.logger.info("Configuration UI fields populated from self.service_config.")
        else:
            self.logger.error("Attempted to populate config UI fields before they were fully created.")

    def _get_display_language(self, lang_code: str) -> str:
        _ = builtins.__dict__.get('_', lambda s: s) # Ensure _ is available
        # This translates the *display name* from the dict, not the code.
        return self.supported_languages.get(lang_code, _("English"))

    def _get_language_code(self, display_lang: str) -> str:
        _ = builtins.__dict__.get('_', lambda s: s)
        for code, display_name_func  in self.supported_languages.items():
            # Since display names are translated, we need to compare against translated display name
            # This is tricky if _ isn't the one used at definition time.
            # A better way: self.supported_languages = {"en": "English", "zh": "中文 (Chinese)"}
            # and then in _get_display_language, return _(self.supported_languages.get(lang_code, "English"))
            # For now, assume display_lang is the (potentially already translated) string from combobox
            if display_name_func == display_lang: # Compare with the value from the dict
                return code
        return "en" # Default to English if not found

    def _load_config(self) -> dict:
        _ = builtins.__dict__.get('_', lambda s: s) # Ensure _ is available for logs
        self.logger.info(f"Attempting to load configuration from: {self.config_file_path}")
        host = DEFAULT_HOST
        port = DEFAULT_PORT
        language = "en"
        try:
            with open(self.config_file_path, 'r') as f:
                config_data = json.load(f)
            loaded_host = config_data.get('host', DEFAULT_HOST)
            loaded_port_str = str(config_data.get('port', DEFAULT_PORT))
            language = config_data.get('language', "en")
            if not isinstance(language, str) or language not in self.supported_languages.keys(): # Validate against known codes
                self.logger.warning(f"Invalid language code '{language}' in config, defaulting to 'en'.")
                language = "en"
            if isinstance(loaded_host, str) and loaded_host.strip():
                host = loaded_host.strip()
            else:
                self.logger.warning(_("Invalid host '{host_val}' in config, using default: {default_host}").format(host_val=loaded_host, default_host=DEFAULT_HOST))
            try:
                parsed_port = int(loaded_port_str)
                if 1 <= parsed_port <= 65535:
                    port = parsed_port
                else:
                    self.logger.warning(_("Port {port_val} from config is outside valid range (1-65535), using default: {default_port}").format(port_val=parsed_port, default_port=DEFAULT_PORT))
            except ValueError:
                self.logger.warning(_("Invalid port value '{port_str}' in config, using default: {default_port}").format(port_str=loaded_port_str, default_port=DEFAULT_PORT))
        except FileNotFoundError:
            self.logger.info(_("Configuration file '{config_path}' not found. Using defaults. Will be created if config is saved.").format(config_path=self.config_file_path))
        except json.JSONDecodeError:
            self.logger.warning(_("Error decoding JSON from '{config_path}'. Using defaults.").format(config_path=self.config_file_path))
        except Exception as e:
            self.logger.error(_("Unexpected error loading config: {error}. Using defaults.").format(error=e))
        final_config = {'host': host, 'port': port, 'language': language}
        self.logger.info(_("Configuration loaded/initialised to: {config}").format(config=final_config))
        return final_config

    def _save_config_handler(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        self.logger.info(_("Save configuration button clicked."))
        host_val = self.host_ip_entry.get().strip()
        port_str_val = self.port_number_entry.get().strip()

        selected_display_language = self.language_var.get()
        lang_code = self._get_language_code(selected_display_language)

        if not host_val:
            messagebox.showerror(_("Validation Error"), _("Host IP address cannot be empty."))
            self.logger.warning("Save config validation failed: Host IP empty.")
            return
        try:
            port_val = int(port_str_val)
            if not (1 <= port_val <= 65535):
                messagebox.showerror(_("Validation Error"), _("Port number must be between 1 and 65535."))
                self.logger.warning(f"Save config validation failed: Port {port_val} out of range.")
                return
        except ValueError:
            messagebox.showerror(_("Validation Error"), _("Port number must be an integer."))
            self.logger.warning(f"Save config validation failed: Port '{port_str_val}' not an integer.")
            return

        save_successful = self._save_config(host_val, port_val, lang_code)

        if save_successful:
            self._populate_config_ui_fields()
            self._populate_language_combo() # Repopulate language combo to ensure it reflects saved state
            messagebox.showinfo(_("Configuration Saved"),
                                _("Configuration has been saved successfully.\n\n"
                                  "If the WMS service is currently running, "
                                  "you may need to restart it for changes to its "
                                  "listening address or port to take full effect.\n\n"
                                  "Language changes require an application restart to apply.")) # Added language restart note
            self.logger.info("Configuration save handler completed successfully.")
        else:
            messagebox.showerror(_("Save Error"), _("Failed to save configuration. Please check the logs for more details."))
            self.logger.error("Configuration save handler failed.")

    def _save_config(self, host: str, port: int, language: str) -> bool: # Added language param
        _ = builtins.__dict__.get('_', lambda s: s)
        self.logger.info(_("Attempting to save configuration: Host='{host}', Port={port}, Language='{lang}'").format(host=host, port=port, lang=language))

        if not isinstance(host, str) or not host.strip():
            self.logger.error(_("Invalid host value for saving: cannot be empty."))
            return False
        try:
            port_int = int(port)
            if not (1 <= port_int <= 65535):
                 self.logger.warning(_("Port {port_val} is outside typical valid range (1-65535). Saving anyway.").format(port_val=port_int))
        except ValueError:
            self.logger.error(_("Invalid port value '{port_val}' for saving. Must be an integer.").format(port_val=port))
            return False

        if not isinstance(language, str) or language not in self.supported_languages.keys(): # Validate language code
            self.logger.error(f"Invalid language code '{language}' provided for saving. Defaulting to 'en'.")
            language = "en"

        config_to_save = {'host': host.strip(), 'port': port_int, 'language': language} # Save language
        try:
            with open(self.config_file_path, 'w') as f:
                json.dump(config_to_save, f, indent=4)
            self.service_config = config_to_save
            self.current_api_base_url = f"http://{self.service_config['host']}:{self.service_config['port']}"
            if hasattr(self, 'api_service') and self.api_service is not None:
                self.api_service.update_base_url(self.current_api_base_url)
            else:
                self.logger.warning(_("ApiService not initialized when trying to update its base URL after saving config."))
            self.logger.info(_("Configuration saved successfully to '{config_path}': {config}").format(config_path=self.config_file_path, config=self.service_config))
            return True
        except IOError as e:
            self.logger.error(_("Error saving configuration to '{config_path}': {error}").format(config_path=self.config_file_path, error=e))
            return False
        except Exception as e:
            self.logger.error(_("Unexpected error saving config: {error}").format(error=e))
            return False

    def _clear_record_form_handler(self):
        _ = builtins.__dict__.get('_', lambda s: s)
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
        self.material_id_entry.focus()

    def _add_record_handler(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        self._log_action("Add record button clicked.")
        material_id = self.material_id_entry.get().strip()
        tray_number = self.tray_number_entry.get().strip()
        process_id = self.process_id_entry.get().strip()
        task_id = self.task_id_entry.get().strip()
        status_notes = self.status_notes_text.get("1.0", tk.END).strip()
        if not material_id:
            messagebox.showerror(_("Validation Error"), _("MaterialID cannot be empty."))
            self._log_action("Add record validation failed: MaterialID empty.", logging.WARNING)
            return
        payload = {
            "MaterialID": material_id, "TrayNumber": tray_number,
            "ProcessID": process_id, "TaskID": task_id, "StatusNotes": status_notes
        }
        success, response_data = self.api_service.create_location_record(payload)
        if success:
            loc_id = response_data.get('LocationID', 'N/A') if isinstance(response_data, dict) else 'N/A'
            messagebox.showinfo(_("Success"), _("Record added successfully. LocationID: {loc_id}").format(loc_id=loc_id))
            self._log_action(f"Record added via API: {response_data}")
            self._clear_record_form_handler()
        else:
            messagebox.showerror(_("API Error"), _("Failed to add record: {error}").format(error=response_data))
            self._log_action(f"API failed to add record: {response_data}", logging.ERROR)

    def _update_record_handler(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        self._log_action("Update record button clicked.")
        if self.selected_location_id_for_update is None:
            messagebox.showerror(_("Error"), _("No record selected for update. LocationID is missing."))
            self._log_action("Update record failed: No LocationID selected/available.", logging.WARNING)
            return
        location_id = self.selected_location_id_for_update
        material_id = self.material_id_entry.get().strip()
        payload = {
            "MaterialID": material_id,
            "TrayNumber": self.tray_number_entry.get().strip(),
            "ProcessID": self.process_id_entry.get().strip(),
            "TaskID": self.task_id_entry.get().strip(),
            "StatusNotes": self.status_notes_text.get("1.0", tk.END).strip()
        }
        success, response_data = self.api_service.update_location_record(location_id, payload)
        if success:
            messagebox.showinfo(_("Success"), _("Record {loc_id} updated successfully.").format(loc_id=location_id))
            self._log_action(f"Record {location_id} updated via API: {response_data}")
            self._clear_record_form_handler()
        else:
            messagebox.showerror(_("API Error"), _("Failed to update record {loc_id}: {error}").format(loc_id=location_id, error=response_data))
            self._log_action(f"API failed to update record {location_id}: {response_data}", logging.ERROR)

    def _populate_form_on_selection(self, selected_record_data: dict):
        self._log_action(f"Populating form with selected record: {selected_record_data.get('LocationID')}")
        self._clear_record_form_handler()
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
            self.update_record_button.config(state=tk.DISABLED)

    def _clear_results_table(self):
        self._log_action("Clearing results table.")
        for item in self.results_table.get_children():
            self.results_table.delete(item)

    def _populate_results_table(self, records: list):
        _ = builtins.__dict__.get('_', lambda s: s)
        self._log_action(f"Populating results table with {len(records)} records.")
        self._clear_results_table()
        for record in records:
            values = (
                record.get("LocationID", ""), record.get("MaterialID", ""),
                record.get("TrayNumber", ""), record.get("Timestamp", ""),
                record.get("ProcessID", ""), record.get("TaskID", ""),
                record.get("StatusNotes", "")
            )
            self.results_table.insert("", tk.END, values=values)

    def _search_records_handler(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        self._log_action("Search records button clicked.")
        query_material_id = self.query_material_id_entry.get().strip()
        query_tray_number = self.query_tray_number_entry.get().strip()
        params = {}
        if query_material_id: params["MaterialID"] = query_material_id
        if query_tray_number: params["TrayNumber"] = query_tray_number
        self._log_action(f"Searching records with params: {params}")
        success, data_or_error = self.api_service.get_location_records(params=params)
        if success:
            if isinstance(data_or_error, list):
                self._populate_results_table(data_or_error)
                messagebox.showinfo(_("Search Results"), _("Found {count} record(s).").format(count=len(data_or_error)))
                self._log_action(f"Search successful, {len(data_or_error)} record(s) displayed.")
            else:
                messagebox.showerror(_("API Error"), _("Received unexpected data format from API."))
                self._log_action(f"API search returned unexpected data format: {type(data_or_error)}", logging.ERROR)
                self._clear_results_table()
        else:
            messagebox.showerror(_("API Error"), _("Failed to search records: {error}").format(error=data_or_error))
            self._log_action(f"API search failed: {data_or_error}", logging.ERROR)
            self._clear_results_table()

    def _on_table_row_select(self, event):
        selected_items = self.results_table.selection()
        if not selected_items:
            return
        selected_item = selected_items[0]
        record_values = self.results_table.item(selected_item, "values")
        if not record_values:
            self._clear_record_form_handler()
            return
        column_names = self.results_table["columns"]
        selected_record_data = dict(zip(column_names, record_values))
        self._log_action(f"Table row selected. Data: {selected_record_data}")
        self._populate_form_on_selection(selected_record_data)

    def _clear_record_by_material_tray_handler(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        material_id = self.delete_material_id_entry.get().strip()
        tray_number = self.delete_tray_number_entry.get().strip()
        self._log_action(f"Clear by Mtrl+Tray button clicked for MaterialID: '{material_id}', TrayNumber: '{tray_number}'.")
        if not material_id or not tray_number:
            messagebox.showerror(_("Validation Error"), _("Both MaterialID and TrayNumber are required to clear a record."))
            self._log_action("Clear by Mtrl+Tray validation failed: MaterialID or TrayNumber empty.", logging.WARNING)
            return
        confirm_msg = _("Are you sure you want to clear the record for Material ID: '{mat_id}' and Tray Number: '{tray_num}'?\nThis will mark the location as empty.").format(mat_id=material_id, tray_num=tray_number)
        if not messagebox.askyesno(_("Confirm Clear"), confirm_msg):
            self._log_action("Clear operation cancelled by user.")
            return
        self._log_action(f"Attempting to clear record directly for MaterialID='{material_id}', TrayNumber='{tray_number}'.")
        clear_success, clear_response_data = self.api_service.clear_record_by_material_tray(material_id, tray_number)
        if clear_success:
            cleared_loc_id = clear_response_data.get("LocationID", "N/A") if isinstance(clear_response_data, dict) else "N/A"
            success_msg = _("Record for MaterialID '{mat_id}', TrayNumber '{tray_num}' (LocationID: {loc_id}) cleared successfully.").format(mat_id=material_id, tray_num=tray_number, loc_id=cleared_loc_id)
            self._log_action(f"Clear successful via API. Response: {clear_response_data}")
            messagebox.showinfo(_("Success"), success_msg)
            self.delete_material_id_entry.delete(0, tk.END)
            self.delete_tray_number_entry.delete(0, tk.END)
            self._search_records_handler()
        else:
            error_msg = _("Failed to clear record for MaterialID '{mat_id}', TrayNumber '{tray_num}': {error}").format(mat_id=material_id, tray_num=tray_number, error=clear_response_data)
            messagebox.showerror(_("API Error"), error_msg)
            self._log_action(error_msg, logging.ERROR)

    def _log_action(self, message, level=logging.INFO):
        logging.log(level, message)

    def _get_service_command(self):
        python_exe = sys.executable
        uvicorn_host = self.service_config.get('host', DEFAULT_HOST)
        uvicorn_port = str(self.service_config.get('port', DEFAULT_PORT))
        main_module_name = os.path.splitext(WMS_MAIN_PY)[0]
        return [python_exe, "-m", "uvicorn", f"{main_module_name}:app", f"--host={uvicorn_host}", f"--port={uvicorn_port}"]

    def initial_status_check(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        self._log_action("Performing initial WMS service status check.")
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, "r") as f:
                    pid_str = f.read().strip()
                    if not pid_str:
                        self._log_action("PID file is empty. Cleaning up.", level=logging.WARNING)
                        os.remove(PID_FILE)
                        raise FileNotFoundError
                    pid = int(pid_str)
                cmd = ["tasklist", "/FI", f"PID eq {pid}"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
                stdout, stderr = process.communicate()
                if str(pid) in stdout.decode(errors='ignore'):
                    self.service_pid = pid
                    self.status_var.set(_("Status: Running (PID: {pid_val})").format(pid_val=self.service_pid))
                    self._log_action(f"Service found running with PID: {pid} from PID file.")
                else:
                    self._log_action(f"PID {pid} from PID file not found in tasklist. Cleaning up stale PID file.")
                    os.remove(PID_FILE)
                    self.service_pid = None
                    self.status_var.set(_("Status: Stopped (Stale PID)"))
            except ValueError:
                self._log_action("Invalid PID in PID file. Cleaning up.", level=logging.WARNING)
                os.remove(PID_FILE)
                self.service_pid = None
                self.status_var.set(_("Status: Error (Invalid PID file)"))
            except FileNotFoundError:
                self.service_pid = None
                self.status_var.set(_("Status: Stopped (PID file was empty or removed)"))
            except Exception as e:
                self._log_action(f"Error checking PID file: {e}", level=logging.ERROR)
                if os.path.exists(PID_FILE):
                    os.remove(PID_FILE)
                self.service_pid = None
                self.status_var.set(_("Status: Error checking PID"))
        else:
            self.service_pid = None
            self.status_var.set(_("Status: Stopped"))
        self.logger.info(f"Initial status check complete. Status: {self.status_var.get()}")
        self.update_button_states()

    def update_button_states(self):
        if self.service_pid:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.restart_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.restart_button.config(state=tk.DISABLED)

    def start_service(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        self._log_action("Attempting to start WMS service...")
        if self.service_pid:
            messagebox.showwarning(_("Service Info"), _("Service is already running."))
            self._log_action("Start attempt failed: Service already running.")
            return
        if not os.path.exists(WMS_MAIN_PY):
            messagebox.showerror(_("Error"), _("{python_file} not found. Cannot start service.").format(python_file=WMS_MAIN_PY))
            self._log_action(f"Start attempt failed: {WMS_MAIN_PY} not found.", level=logging.ERROR)
            self.status_var.set(_("Status: Error - {python_file} not found").format(python_file=WMS_MAIN_PY))
            return
        try:
            command = self._get_service_command()
            self._log_action(f"Executing command: {' '.join(command)}")
            process = subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
            self.service_pid = process.pid
            with open(PID_FILE, "w") as f: f.write(str(self.service_pid))
            self.status_var.set(_("Status: Running (PID: {pid_val})").format(pid_val=self.service_pid))
            self._log_action(f"Service started successfully with PID: {self.service_pid}.")
            messagebox.showinfo(_("Service Control"), _("WMS Service started successfully."))
        except Exception as e:
            self.service_pid = None
            self.status_var.set(_("Status: Error starting"))
            self._log_action(f"Failed to start service: {e}", level=logging.ERROR)
            messagebox.showerror(_("Service Control Error"), _("Failed to start WMS service: {error}").format(error=e))
        self.update_button_states()

    def stop_service(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        self._log_action("Attempting to stop WMS service...")
        pid_to_stop = self.service_pid
        if not pid_to_stop:
            if os.path.exists(PID_FILE):
                try:
                    with open(PID_FILE, "r") as f:
                        pid_str = f.read().strip()
                        if pid_str:
                           pid_to_stop = int(pid_str)
                           self._log_action(f"Read PID {pid_to_stop} from file for stopping.")
                        else:
                            messagebox.showwarning(_("Service Info"), _("Service is not recorded as running (empty PID file)."))
                            self.initial_status_check()
                            return
                except Exception as e:
                    self._log_action(f"Could not read/parse PID from file during stop: {e}", level=logging.WARNING)
                    messagebox.showwarning(_("Service Info"), _("Service PID file is corrupt or unreadable."))
                    self.initial_status_check()
                    return
            else:
                messagebox.showwarning(_("Service Info"), _("Service is not recorded as running."))
                self._log_action("Stop attempt failed: Service not recorded as running.")
                self.initial_status_check()
                return
        if not pid_to_stop:
             messagebox.showwarning(_("Service Info"), _("No valid PID found to stop the service."))
             self.initial_status_check()
             return
        try:
            self._log_action(f"Stopping process with PID: {pid_to_stop} using taskkill.")
            subprocess.run(["taskkill", "/F", "/PID", str(pid_to_stop), "/T"], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self._log_action("Service stopped successfully via taskkill.")
            self.status_var.set(_("Status: Stopped"))
            messagebox.showinfo(_("Service Control"), _("WMS Service stopped successfully."))
        except subprocess.CalledProcessError as e:
            self._log_action(f"taskkill command failed for PID {pid_to_stop}: {e}. Output: {e.stdout} Stderr: {e.stderr}", level=logging.ERROR)
            cmd_check = ["tasklist", "/FI", f"PID eq {pid_to_stop}"]
            process_check = subprocess.Popen(cmd_check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            stdout_check, _ = process_check.communicate()
            if str(pid_to_stop) not in stdout_check.decode(errors='ignore'):
                self._log_action(f"Process PID {pid_to_stop} not found after taskkill failure, assuming stopped.", level=logging.INFO)
                self.status_var.set(_("Status: Stopped (taskkill error but process gone)"))
            else:
                self._log_action(f"Service with PID {pid_to_stop} might still be running after taskkill error.", level=logging.WARNING)
                messagebox.showerror(_("Service Control Error"), _("Failed to stop WMS service with taskkill: {error}. It might still be running.").format(error=e))
                self.update_button_states()
                return
        except Exception as e:
            self.status_var.set(_("Status: Error stopping"))
            self._log_action(f"An unexpected error occurred during stop for PID {pid_to_stop}: {e}", level=logging.ERROR)
            messagebox.showerror(_("Service Control Error"), _("An unexpected error occurred while stopping WMS service: {error}").format(error=e))
            self.update_button_states()
            return
        self.service_pid = None
        if os.path.exists(PID_FILE): os.remove(PID_FILE)
        self.update_button_states()

    def restart_service(self):
        self._log_action("Attempting to restart WMS service...")
        self.stop_service()
        self.root.after(1000, self.start_service)

    def _check_task_exists(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        try:
            result = subprocess.run(['schtasks', '/Query', '/TN', TASK_NAME], capture_output=True, text=True, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
            return result.returncode == 0 and TASK_NAME in result.stdout
        except FileNotFoundError:
            self._log_action("schtasks command not found. Cannot check auto-start status.", level=logging.ERROR)
            messagebox.showerror(_("Error"), _("Task Scheduler command (schtasks) not found. This feature may not work."))
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
        _ = builtins.__dict__.get('_', lambda s: s)
        self._log_action(f"Attempting to enable auto-start (Task: {TASK_NAME})...")
        python_exe = sys.executable
        script_dir = os.path.abspath(os.path.dirname(__file__))
        uvicorn_host_for_task = self.service_config.get('host', DEFAULT_HOST)
        uvicorn_port_for_task = str(self.service_config.get('port', DEFAULT_PORT))
        main_module_name_for_task = os.path.splitext(WMS_MAIN_PY)[0]
        uvicorn_command = f'"{python_exe}" -m uvicorn {main_module_name_for_task}:app --host {uvicorn_host_for_task} --port {uvicorn_port_for_task}'
        batch_script_name = "run_wms_service.bat"
        batch_script_path = os.path.join(script_dir, batch_script_name)
        try:
            with open(batch_script_path, "w") as bf:
                bf.write(f"@echo off\n")
                bf.write(f"cd /D \"{script_dir}\"\n")
                bf.write(f"echo Starting WMS Service...\n")
                bf.write(f"{uvicorn_command}\n")
            self._log_action(f"Created helper batch script: {batch_script_path}")
        except Exception as e:
            self._log_action(f"Failed to create batch script {batch_script_name}: {e}", level=logging.ERROR)
            messagebox.showerror(_("Auto-start Error"), _("Failed to create helper batch script: {error}").format(error=e))
            return
        schtasks_command = [
            'schtasks', '/Create', '/TN', TASK_NAME,
            '/TR', f'"{batch_script_path}"',
            '/SC', 'ONLOGON', '/RL', 'HIGHEST', '/F',
        ]
        try:
            self._log_action(f"Executing schtasks command: {' '.join(schtasks_command)}")
            result = subprocess.run(schtasks_command, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self._log_action(f"schtasks /Create output: {result.stdout}")
            messagebox.showinfo(_("Auto-start"), _("Auto-start enabled for WMS service via Task '{task_name}'.").format(task_name=TASK_NAME))
            self._log_action(f"Successfully enabled auto-start task '{TASK_NAME}'.")
        except subprocess.CalledProcessError as e:
            self._log_action(f"Failed to create scheduled task: {e}. Output: {e.stdout}, Stderr: {e.stderr}", level=logging.ERROR)
            messagebox.showerror(_("Auto-start Error"), _("Failed to enable auto-start (Task Scheduler error): {error}").format(error=e.stderr))
        except FileNotFoundError:
             self._log_action("schtasks command not found. Cannot enable auto-start.", level=logging.ERROR)
             messagebox.showerror(_("Error"), _("Task Scheduler command (schtasks) not found. This feature requires Windows and Task Scheduler."))
        except Exception as e:
            self._log_action(f"An unexpected error occurred enabling auto-start: {e}", level=logging.ERROR)
            messagebox.showerror(_("Auto-start Error"), _("An unexpected error occurred while enabling auto-start: {error}").format(error=e))
        self.update_auto_start_buttons_status()

    def disable_auto_start(self):
        _ = builtins.__dict__.get('_', lambda s: s)
        self._log_action(f"Attempting to disable auto-start (Task: {TASK_NAME})...")
        schtasks_command = ['schtasks', '/Delete', '/TN', TASK_NAME, '/F']
        try:
            self._log_action(f"Executing schtasks command: {' '.join(schtasks_command)}")
            result = subprocess.run(schtasks_command, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self._log_action(f"schtasks /Delete output: {result.stdout}")
            messagebox.showinfo(_("Auto-start"), _("Auto-start disabled for WMS service."))
            self._log_action(f"Successfully disabled auto-start task '{TASK_NAME}'.")
        except subprocess.CalledProcessError as e:
            if "ERROR: The specified task name" in e.stderr or "The system cannot find the file specified" in e.stderr or e.returncode == 1 :
                 self._log_action(f"Task '{TASK_NAME}' not found or already deleted. Output: {e.stderr}", level=logging.INFO)
                 messagebox.showinfo(_("Auto-start Info"), _("Auto-start task '{task_name}' was not found (already disabled).").format(task_name=TASK_NAME))
            else:
                self._log_action(f"Failed to delete scheduled task: {e}. Output: {e.stdout}, Stderr: {e.stderr}", level=logging.ERROR)
                messagebox.showerror(_("Auto-start Error"), _("Failed to disable auto-start (Task Scheduler error): {error}").format(error=e.stderr))
        except FileNotFoundError:
             self._log_action("schtasks command not found. Cannot disable auto-start.", level=logging.ERROR)
             messagebox.showerror(_("Error"), _("Task Scheduler command (schtasks) not found. This feature requires Windows and Task Scheduler."))
        except Exception as e:
            self._log_action(f"An unexpected error occurred disabling auto-start: {e}", level=logging.ERROR)
            messagebox.showerror(_("Auto-start Error"), _("An unexpected error occurred while disabling auto-start: {error}").format(error=e))
        self.update_auto_start_buttons_status()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServiceManagerApp(root)
    root.mainloop()

    if app.service_pid and os.path.exists(PID_FILE):
        app._log_action("Management app closing.")
        pass

[end of management_app.py]
