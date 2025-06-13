#!/usr/bin/env python3
"""
WMS Service Management Application with New I18n System
使用新的多语言资源管理系统的WMS服务管理应用
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import json
import os
import logging
import builtins
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import requests
from pathlib import Path

# 导入新的多语言管理器
from i18n_manager import I18nManager, get_i18n_manager, _, set_language

# 应用配置
APP_NAME = "WMS Service Management"
CONFIG_FILE_NAME = "service_config.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('management_app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ApiService:
    """API服务类，处理与WMS服务的通信"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
    
    def _handle_response(self, response: requests.Response) -> tuple[bool, dict | str]:
        """处理API响应"""
        try:
            if response.status_code == 200:
                return True, response.json()
            else:
                error_msg = _("HTTP Error {status}: {reason}").format(
                    status=response.status_code, 
                    reason=response.reason
                )
                self.logger.error(f"API error: {error_msg}")
                return False, error_msg
        except requests.exceptions.JSONDecodeError:
            error_msg = _("Invalid JSON response")
            self.logger.error(f"API error: {error_msg}")
            return False, error_msg
    
    def get_all_locations(self) -> tuple[bool, list | str]:
        """获取所有位置记录"""
        self.logger.info("API: Fetching all location records")
        try:
            response = requests.get(f"{self.base_url}/locations/", timeout=5)
            success, data = self._handle_response(response)
            if success:
                return True, data
            else:
                return False, data
        except requests.exceptions.RequestException as e:
            error_msg = _("Connection Error: {error}").format(error=str(e))
            self.logger.error(f"API get_all_locations failed: {e}")
            return False, error_msg
    
    def add_location_record(self, record_data: dict) -> tuple[bool, dict | str]:
        """添加位置记录"""
        self.logger.info(f"API: Adding location record: {record_data}")
        try:
            response = requests.post(f"{self.base_url}/locations/", json=record_data, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            error_msg = _("Connection Error: {error}").format(error=str(e))
            self.logger.error(f"API add_location_record failed: {e}")
            return False, error_msg
    
    def update_location_record(self, location_id: int, record_data: dict) -> tuple[bool, dict | str]:
        """更新位置记录"""
        self.logger.info(f"API: Updating location record ID {location_id}: {record_data}")
        try:
            response = requests.put(f"{self.base_url}/locations/{location_id}", json=record_data, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            error_msg = _("Connection Error: {error}").format(error=str(e))
            self.logger.error(f"API update_location_record failed for ID {location_id}: {e}")
            return False, error_msg
    
    def delete_location_record(self, location_id: int) -> tuple[bool, dict | str]:
        """删除位置记录"""
        self.logger.info(f"API: Deleting location record ID {location_id}")
        try:
            response = requests.delete(f"{self.base_url}/locations/{location_id}", timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            error_msg = _("Connection Error: {error}").format(error=str(e))
            self.logger.error(f"API delete_location_record failed for ID {location_id}: {e}")
            return False, error_msg
    
    def clear_location_record_by_id(self, location_id: int) -> tuple[bool, dict | str]:
        """按ID清除位置记录"""
        self.logger.info(f"API: Clearing location record ID {location_id} using clear-one.")
        try:
            response = requests.post(f"{self.base_url}/locations/clear-one/", json={"LocationID": location_id}, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            error_msg = _("Connection Error: {error}").format(error=str(e))
            self.logger.error(f"API clear_location_record_by_id failed for ID {location_id}: {e}")
            return False, error_msg
    
    def clear_record_by_material_tray(self, material_id: str, tray_number: str) -> tuple[bool, dict | str]:
        """按物料ID和托盘号清除记录"""
        self.logger.info(f"API: Clearing record by MaterialID='{material_id}', TrayNumber='{tray_number}'")
        try:
            payload = {"MaterialID": material_id, "TrayNumber": tray_number}
            response = requests.post(f"{self.base_url}/locations/clear-by-material-tray/", json=payload, timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            error_msg = _("Connection Error: {error}").format(error=str(e))
            self.logger.error(f"API clear_record_by_material_tray failed for MaterialID='{material_id}', TrayNumber='{tray_number}': {e}")
            return False, error_msg

class ServiceManagerApp:
    """服务管理应用主类"""
    
    def __init__(self, root):
        self.root = root
        self.logger = logging.getLogger(__name__)
        self.config_file_path = os.path.abspath(CONFIG_FILE_NAME)
        
        # 初始化多语言管理器
        self.i18n = get_i18n_manager()
        
        # 加载配置
        self.service_config = self._load_config()
        
        # 设置语言
        self.setup_language()
        
        # 设置UI
        self.root.title(_(APP_NAME))
        self.root.geometry("600x800")
        
        self.service_pid = None
        self.current_api_base_url = f"http://{self.service_config['host']}:{self.service_config['port']}"
        self.api_service = ApiService(base_url=self.current_api_base_url)
        self.selected_location_id_for_update = None
        
        self._setup_ui(root)
        
        self.initial_status_check()
        self.update_auto_start_buttons_status()
        self._clear_record_form_handler()
        self._populate_config_ui_fields()
        self._populate_language_combo()
    
    def setup_language(self):
        """设置应用语言"""
        lang_code = self.service_config.get('language', 'en')
        self.logger.info(f"设置应用语言为: {lang_code}")
        
        success = self.i18n.set_language(lang_code)
        if success:
            self.logger.info(f"语言设置成功: {lang_code}")
        else:
            self.logger.warning(f"语言设置失败，使用默认语言: {self.i18n.default_language}")
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        self.logger.info(f"尝试加载配置文件: {self.config_file_path}")
        host = DEFAULT_HOST
        port = DEFAULT_PORT
        language = "en"
        
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            loaded_host = config_data.get('host', DEFAULT_HOST)
            loaded_port_str = str(config_data.get('port', DEFAULT_PORT))
            language = config_data.get('language', "en")
            
            # 验证语言代码
            supported_languages = self.i18n.get_supported_languages() if hasattr(self, 'i18n') else {'en': 'English', 'zh': '中文'}
            if not isinstance(language, str) or language not in supported_languages.keys():
                self.logger.warning(f"无效的语言代码 '{language}'，使用默认值 'en'")
                language = "en"
            
            if isinstance(loaded_host, str) and loaded_host.strip():
                host = loaded_host.strip()
            else:
                self.logger.warning(f"配置中的主机 '{loaded_host}' 无效，使用默认值: {DEFAULT_HOST}")
            
            try:
                parsed_port = int(loaded_port_str)
                if 1 <= parsed_port <= 65535:
                    port = parsed_port
                else:
                    self.logger.warning(f"配置中的端口 {parsed_port} 超出有效范围 (1-65535)，使用默认值: {DEFAULT_PORT}")
            except ValueError:
                self.logger.warning(f"配置中的端口值 '{loaded_port_str}' 无效，使用默认值: {DEFAULT_PORT}")
                
        except FileNotFoundError:
            self.logger.info(f"配置文件 '{self.config_file_path}' 未找到，使用默认值")
        except json.JSONDecodeError:
            self.logger.warning(f"配置文件 '{self.config_file_path}' JSON 解析错误，使用默认值")
        except Exception as e:
            self.logger.error(f"加载配置时发生意外错误: {e}，使用默认值")
        
        final_config = {'host': host, 'port': port, 'language': language}
        self.logger.info(f"配置加载完成: {final_config}")
        return final_config
    
    def _setup_ui(self, root):
        """设置用户界面"""
        main_paned_window = ttk.PanedWindow(root, orient=tk.VERTICAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 服务控制区域
        service_control_frame = ttk.LabelFrame(main_paned_window, text=_("Service Control"))
        main_paned_window.add(service_control_frame, weight=0)
        
        self.status_var = tk.StringVar(value=_("Status: Unknown"))
        self.status_label = ttk.Label(service_control_frame, textvariable=self.status_var, font=("Arial", 12))
        self.status_label.pack(pady=5)
        
        service_buttons_frame = ttk.Frame(service_control_frame)
        service_buttons_frame.pack(pady=5)
        
        self.start_button = ttk.Button(service_buttons_frame, text=_("Start Service"), command=self._start_service_handler)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(service_buttons_frame, text=_("Stop Service"), command=self._stop_service_handler)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.restart_button = ttk.Button(service_buttons_frame, text=_("Restart Service"), command=self._restart_service_handler)
        self.restart_button.pack(side=tk.LEFT, padx=5)
        
        # 配置区域
        config_frame = ttk.LabelFrame(main_paned_window, text=_("Configuration"))
        main_paned_window.add(config_frame, weight=0)
        
        # 主机IP
        ttk.Label(config_frame, text=_("Host IP") + ":").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.host_ip_entry = ttk.Entry(config_frame, width=20)
        self.host_ip_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 端口号
        ttk.Label(config_frame, text=_("Port Number") + ":").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_number_entry = ttk.Entry(config_frame, width=20)
        self.port_number_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 语言选择
        ttk.Label(config_frame, text=_("Language") + ":").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.language_var = tk.StringVar()
        self.language_combo = ttk.Combobox(config_frame, textvariable=self.language_var, state="readonly", width=27)
        self.language_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 保存配置按钮
        self.save_config_button = ttk.Button(config_frame, text=_("Save Configuration"), command=self._save_config_handler)
        self.save_config_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        config_frame.columnconfigure(1, weight=1)
        
        # 数据管理区域
        data_management_frame = ttk.LabelFrame(main_paned_window, text=_("Data Management"))
        main_paned_window.add(data_management_frame, weight=1)
        
        # 记录详情
        self.record_details_frame = ttk.LabelFrame(data_management_frame, text=_("Record Details"))
        self.record_details_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5, expand=False)
        
        # 创建记录表单字段
        self._create_record_form()
        
        # 操作按钮
        self._create_action_buttons(data_management_frame)
        
        # 数据表格
        self._create_data_table(data_management_frame)
    
    def _create_record_form(self):
        """创建记录表单"""
        ttk.Label(self.record_details_frame, text=_("LocationID") + ":").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.location_id_entry = ttk.Entry(self.record_details_frame, state="readonly")
        self.location_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(self.record_details_frame, text=_("MaterialID") + ":").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.material_id_entry = ttk.Entry(self.record_details_frame)
        self.material_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(self.record_details_frame, text=_("TrayNumber") + ":").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.tray_number_entry = ttk.Entry(self.record_details_frame)
        self.tray_number_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(self.record_details_frame, text=_("ProcessID") + ":").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.process_id_entry = ttk.Entry(self.record_details_frame)
        self.process_id_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(self.record_details_frame, text=_("TaskID") + ":").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.task_id_entry = ttk.Entry(self.record_details_frame)
        self.task_id_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(self.record_details_frame, text=_("StatusNotes") + ":").grid(row=5, column=0, padx=5, pady=5, sticky=tk.NW)
        self.status_notes_text = tk.Text(self.record_details_frame, height=3, width=30)
        self.status_notes_text.grid(row=5, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(self.record_details_frame, text=_("Timestamp") + ":").grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
        self.timestamp_val_label = ttk.Label(self.record_details_frame, text="")
        self.timestamp_val_label.grid(row=6, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.record_details_frame.columnconfigure(1, weight=1)
    
    def _create_action_buttons(self, parent):
        """创建操作按钮"""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        self.add_button = ttk.Button(buttons_frame, text=_("Add Record"), command=self._add_record_handler)
        self.add_button.pack(side=tk.LEFT, padx=5)
        
        self.update_button = ttk.Button(buttons_frame, text=_("Update Record"), command=self._update_record_handler)
        self.update_button.pack(side=tk.LEFT, padx=5)
        
        self.delete_button = ttk.Button(buttons_frame, text=_("Delete Record"), command=self._delete_record_handler)
        self.delete_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_by_mtrl_tray_button = ttk.Button(buttons_frame, text=_("Clear by Mtrl+Tray"), command=self._clear_by_material_tray_handler)
        self.clear_by_mtrl_tray_button.pack(side=tk.LEFT, padx=5)
        
        self.refresh_button = ttk.Button(buttons_frame, text=_("Refresh"), command=self._refresh_data_handler)
        self.refresh_button.pack(side=tk.RIGHT, padx=5)
    
    def _create_data_table(self, parent):
        """创建数据表格"""
        table_frame = ttk.Frame(parent)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建表格
        columns = ("LocationID", "MaterialID", "TrayNumber", "ProcessID", "TaskID", "StatusNotes", "Timestamp")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)
        
        # 设置列标题
        for col in columns:
            self.tree.heading(col, text=_(col))
            self.tree.column(col, width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
    
    def _populate_language_combo(self):
        """填充语言下拉框"""
        supported_languages = self.i18n.get_supported_languages()
        display_names = []
        
        for code, name in supported_languages.items():
            # 获取翻译后的语言名称
            translated_name = _(name)
            display_names.append(f"{translated_name} ({code})")
        
        self.language_combo['values'] = display_names
        
        # 设置当前选择
        current_lang = self.service_config.get('language', 'en')
        current_display = f"{_(supported_languages.get(current_lang, 'English'))} ({current_lang})"
        self.language_var.set(current_display)
        
        self.logger.info(f"语言下拉框已填充，当前选择: {current_display}")
    
    def _get_language_code(self, display_text: str) -> str:
        """从显示文本中提取语言代码"""
        import re
        match = re.search(r'\(([^)]+)\)$', display_text)
        return match.group(1) if match else 'en'
    
    def _save_config_handler(self):
        """保存配置处理器"""
        self.logger.info(_("Save configuration button clicked."))
        host_val = self.host_ip_entry.get().strip()
        port_str_val = self.port_number_entry.get().strip()
        
        selected_display_language = self.language_var.get()
        lang_code = self._get_language_code(selected_display_language)
        
        # 验证输入
        if not host_val:
            messagebox.showerror(_("Error"), _("Host IP cannot be empty"))
            return
        
        try:
            port_val = int(port_str_val)
            if not (1 <= port_val <= 65535):
                raise ValueError()
        except ValueError:
            messagebox.showerror(_("Error"), _("Port must be a number between 1 and 65535"))
            return
        
        self.logger.info(f"尝试保存配置: Host='{host_val}', Port={port_val}, Language='{lang_code}'")
        
        # 更新配置
        self.service_config['host'] = host_val
        self.service_config['port'] = port_val
        self.service_config['language'] = lang_code
        
        # 保存到文件
        try:
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.service_config, f, indent=2)
            
            self.logger.info(f"配置保存成功: {self.service_config}")
            
            # 更新API服务URL
            self.current_api_base_url = f"http://{host_val}:{port_val}"
            self.api_service = ApiService(base_url=self.current_api_base_url)
            self.logger.info(f"API服务URL已更新: {self.current_api_base_url}")
            
            # 更新语言设置
            if self.i18n.set_language(lang_code):
                self.logger.info(f"语言已切换到: {lang_code}")
                # 重新填充UI元素
                self._populate_config_ui_fields()
                self._populate_language_combo()
                messagebox.showinfo(_("Success"), _("Configuration saved successfully. Please restart the application to see language changes."))
            else:
                self.logger.warning(f"语言切换失败: {lang_code}")
                messagebox.showwarning(_("Warning"), _("Configuration saved but language change failed"))
            
        except Exception as e:
            error_msg = f"保存配置失败: {e}"
            self.logger.error(error_msg)
            messagebox.showerror(_("Error"), _("Failed to save configuration: {error}").format(error=str(e)))
    
    def _populate_config_ui_fields(self):
        """填充配置UI字段"""
        self.host_ip_entry.delete(0, tk.END)
        self.host_ip_entry.insert(0, self.service_config['host'])
        
        self.port_number_entry.delete(0, tk.END)
        self.port_number_entry.insert(0, str(self.service_config['port']))
        
        self.logger.info("配置UI字段已从配置中填充")
    
    # 其他方法的实现...
    def initial_status_check(self):
        """初始状态检查"""
        self.logger.info(_("Performing initial WMS service status check."))
        # 这里可以添加实际的状态检查逻辑
        self.status_var.set(_("Status: Stopped"))
        self.logger.info(_("Initial status check complete. Status: Stopped"))
    
    def update_auto_start_buttons_status(self):
        """更新自动启动按钮状态"""
        self.logger.info(_("Auto-start task status check completed."))
    
    def _clear_record_form_handler(self):
        """清除记录表单"""
        self.logger.info(_("Clearing record form."))
        # 清除表单字段的实现
    
    def _start_service_handler(self):
        """启动服务处理器"""
        self.logger.info(_("Start service button clicked."))
        messagebox.showinfo(_("Info"), _("Service start functionality not implemented yet."))
    
    def _stop_service_handler(self):
        """停止服务处理器"""
        self.logger.info(_("Stop service button clicked."))
        messagebox.showinfo(_("Info"), _("Service stop functionality not implemented yet."))
    
    def _restart_service_handler(self):
        """重启服务处理器"""
        self.logger.info(_("Restart service button clicked."))
        messagebox.showinfo(_("Info"), _("Service restart functionality not implemented yet."))
    
    def _add_record_handler(self):
        """添加记录处理器"""
        self.logger.info(_("Add record button clicked."))
        messagebox.showinfo(_("Info"), _("Add record functionality not implemented yet."))
    
    def _update_record_handler(self):
        """更新记录处理器"""
        self.logger.info(_("Update record button clicked."))
        messagebox.showinfo(_("Info"), _("Update record functionality not implemented yet."))
    
    def _delete_record_handler(self):
        """删除记录处理器"""
        self.logger.info(_("Delete record button clicked."))
        messagebox.showinfo(_("Info"), _("Delete record functionality not implemented yet."))
    
    def _clear_by_material_tray_handler(self):
        """按物料+托盘清除处理器"""
        self.logger.info(_("Clear by Mtrl+Tray button clicked."))
        messagebox.showinfo(_("Info"), _("Clear by material+tray functionality not implemented yet."))
    
    def _refresh_data_handler(self):
        """刷新数据处理器"""
        self.logger.info(_("Refresh button clicked."))
        messagebox.showinfo(_("Info"), _("Refresh functionality not implemented yet."))
    
    def _on_tree_select(self, event):
        """树形视图选择事件处理器"""
        selection = self.tree.selection()
        if selection:
            self.logger.info(f"Record selected: {selection[0]}")

def main():
    """主函数"""
    root = tk.Tk()
    app = ServiceManagerApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()