import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import os
import logging
import sys

# --- Configuration ---
APP_NAME = "WMS Service Management"
PID_FILE = "wms_service.pid"
LOG_FILE = "management_app.log"
WMS_MAIN_PY = "main.py" # Assumes main.py is in the same directory
WMS_HOST = "0.0.0.0"
WMS_PORT = 8000
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

class ServiceManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("450x300")

        self.service_pid = None

        # --- UI Elements ---
        # Status Label
        self.status_var = tk.StringVar(value="Status: Unknown")
        self.status_label = ttk.Label(root, textvariable=self.status_var, font=("Arial", 12))
        self.status_label.pack(pady=10)

        # Control Buttons Frame
        button_frame = ttk.Frame(root)
        button_frame.pack(pady=10)

        self.start_button = ttk.Button(button_frame, text="Start Service", command=self.start_service)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)

        self.stop_button = ttk.Button(button_frame, text="Stop Service", command=self.stop_service, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)

        self.restart_button = ttk.Button(button_frame, text="Restart Service", command=self.restart_service)
        self.restart_button.grid(row=0, column=2, padx=5, pady=5)

        # Auto-start Buttons Frame
        auto_start_frame = ttk.Frame(root)
        auto_start_frame.pack(pady=10)

        self.enable_auto_start_button = ttk.Button(auto_start_frame, text="Enable Auto-start", command=self.enable_auto_start)
        self.enable_auto_start_button.grid(row=0, column=0, padx=5, pady=5)

        self.disable_auto_start_button = ttk.Button(auto_start_frame, text="Disable Auto-start", command=self.disable_auto_start)
        self.disable_auto_start_button.grid(row=0, column=1, padx=5, pady=5)

        # Log Text Area (Optional - for basic in-app log viewing)
        # self.log_text = tk.Text(root, height=5, state=tk.DISABLED)
        # self.log_text.pack(pady=10, fill=tk.X, padx=10)

        self.initial_status_check()
        self.update_auto_start_buttons_status()

    def _log_action(self, message, level=logging.INFO):
        logging.log(level, message)
        # Could also update self.log_text here if it was enabled

    def _get_service_command(self):
        # Resolve the absolute path to python executable and main.py
        python_exe = sys.executable
        script_path = os.path.abspath(WMS_MAIN_PY)
        return [python_exe, "-m", "uvicorn", f"{os.path.splitext(WMS_MAIN_PY)[0]}:app", f"--host={WMS_HOST}", f"--port={WMS_PORT}"]

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
        wms_script_path = os.path.join(script_dir, WMS_MAIN_PY)

        # Construct the command Task Scheduler will run.
        # Option 1: Direct python execution (can be tricky with paths and environments in schtasks)
        # command_to_run = f'"{python_exe}" -m uvicorn "{os.path.splitext(wms_script_path)[0]}:app" --host {WMS_HOST} --port {WMS_PORT}'

        # Option 2: Create a simple batch script wrapper for robustness (recommended)
        batch_script_name = "run_wms_service.bat"
        batch_script_path = os.path.join(script_dir, batch_script_name)
        uvicorn_command = f'"{python_exe}" -m uvicorn {os.path.splitext(WMS_MAIN_PY)[0]}:app --host {WMS_HOST} --port {WMS_PORT}'

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
