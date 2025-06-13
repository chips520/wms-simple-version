#!/usr/bin/env python3
"""
多语言资源管理器
替代传统的gettext方式，使用JSON格式管理翻译资源
解决编码问题并提供更灵活的多语言支持
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Any
import logging

class I18nManager:
    """多语言资源管理器"""
    
    def __init__(self, base_dir: Optional[str] = None, default_language: str = 'en'):
        """
        初始化多语言管理器
        
        Args:
            base_dir: 基础目录，默认为当前脚本目录
            default_language: 默认语言代码
        """
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.default_language = default_language
        self.current_language = default_language
        self.translations: Dict[str, Dict[str, str]] = {}
        self.logger = logging.getLogger(__name__)
        
        # 支持的语言配置
        self.supported_languages = {
            'en': 'English',
            'zh': '中文 (Chinese)'
        }
        
        # 加载所有翻译资源
        self._load_all_translations()
    
    def _load_all_translations(self):
        """加载所有语言的翻译资源"""
        translations_dir = self.base_dir / 'translations'
        
        # 如果翻译目录不存在，创建它
        if not translations_dir.exists():
            translations_dir.mkdir(exist_ok=True)
            self._create_default_translations()
        
        # 加载每种语言的翻译文件
        for lang_code in self.supported_languages.keys():
            translation_file = translations_dir / f'{lang_code}.json'
            if translation_file.exists():
                try:
                    with open(translation_file, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                    self.logger.info(f"已加载 {lang_code} 翻译资源，共 {len(self.translations[lang_code])} 条")
                except Exception as e:
                    self.logger.error(f"加载 {lang_code} 翻译文件失败: {e}")
                    self.translations[lang_code] = {}
            else:
                self.logger.warning(f"翻译文件 {translation_file} 不存在")
                self.translations[lang_code] = {}
    
    def _create_default_translations(self):
        """创建默认的翻译文件"""
        translations_dir = self.base_dir / 'translations'
        
        # 英文翻译（作为基础）
        en_translations = {
            "WMS Service Management": "WMS Service Management",
            "Service Control": "Service Control",
            "Status: Unknown": "Status: Unknown",
            "Start Service": "Start Service",
            "Stop Service": "Stop Service",
            "Restart Service": "Restart Service",
            "Configuration": "Configuration",
            "Host IP": "Host IP",
            "Port Number": "Port Number",
            "Language": "Language",
            "Save Configuration": "Save Configuration",
            "Data Management": "Data Management",
            "Record Details": "Record Details",
            "LocationID": "LocationID",
            "MaterialID": "MaterialID",
            "TrayNumber": "TrayNumber",
            "ProcessID": "ProcessID",
            "TaskID": "TaskID",
            "StatusNotes": "StatusNotes",
            "Timestamp": "Timestamp",
            "Add Record": "Add Record",
            "Update Record": "Update Record",
            "Delete Record": "Delete Record",
            "Clear by Mtrl+Tray": "Clear by Mtrl+Tray",
            "Refresh": "Refresh",
            "English": "English",
            "中文 (Chinese)": "中文 (Chinese)"
        }
        
        # 中文翻译
        zh_translations = {
            "WMS Service Management": "WMS服务管理",
            "Service Control": "服务控制",
            "Status: Unknown": "状态：未知",
            "Start Service": "启动服务",
            "Stop Service": "停止服务",
            "Restart Service": "重启服务",
            "Configuration": "配置",
            "Host IP": "主机IP",
            "Port Number": "端口号",
            "Language": "语言",
            "Save Configuration": "保存配置",
            "Data Management": "数据管理",
            "Record Details": "记录详情",
            "LocationID": "位置ID",
            "MaterialID": "物料ID",
            "TrayNumber": "托盘号",
            "ProcessID": "工艺ID",
            "TaskID": "任务ID",
            "StatusNotes": "状态备注",
            "Timestamp": "时间戳",
            "Add Record": "添加记录",
            "Update Record": "更新记录",
            "Delete Record": "删除记录",
            "Clear by Mtrl+Tray": "按物料+托盘清除",
            "Refresh": "刷新",
            "English": "英语",
            "中文 (Chinese)": "中文"
        }
        
        # 保存翻译文件
        self._save_translation_file('en', en_translations)
        self._save_translation_file('zh', zh_translations)
        
        self.logger.info("已创建默认翻译文件")
    
    def _save_translation_file(self, lang_code: str, translations: Dict[str, str]):
        """保存翻译文件"""
        translations_dir = self.base_dir / 'translations'
        translation_file = translations_dir / f'{lang_code}.json'
        
        try:
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已保存 {lang_code} 翻译文件: {translation_file}")
        except Exception as e:
            self.logger.error(f"保存 {lang_code} 翻译文件失败: {e}")
    
    def set_language(self, lang_code: str) -> bool:
        """
        设置当前语言
        
        Args:
            lang_code: 语言代码
            
        Returns:
            bool: 设置是否成功
        """
        if lang_code not in self.supported_languages:
            self.logger.warning(f"不支持的语言代码: {lang_code}")
            return False
        
        self.current_language = lang_code
        self.logger.info(f"语言已切换到: {lang_code} ({self.supported_languages[lang_code]})")
        return True
    
    def get_text(self, key: str, **kwargs) -> str:
        """
        获取翻译文本
        
        Args:
            key: 翻译键
            **kwargs: 格式化参数
            
        Returns:
            str: 翻译后的文本
        """
        # 尝试获取当前语言的翻译
        if self.current_language in self.translations:
            text = self.translations[self.current_language].get(key)
            if text:
                try:
                    return text.format(**kwargs) if kwargs else text
                except KeyError as e:
                    self.logger.warning(f"翻译文本格式化失败: {e}")
                    return text
        
        # 回退到默认语言
        if self.default_language in self.translations:
            text = self.translations[self.default_language].get(key)
            if text:
                try:
                    return text.format(**kwargs) if kwargs else text
                except KeyError as e:
                    self.logger.warning(f"默认翻译文本格式化失败: {e}")
                    return text
        
        # 如果都没有找到，返回原始键
        self.logger.warning(f"未找到翻译: {key}")
        return key
    
    def add_translation(self, lang_code: str, key: str, value: str):
        """
        添加翻译
        
        Args:
            lang_code: 语言代码
            key: 翻译键
            value: 翻译值
        """
        if lang_code not in self.translations:
            self.translations[lang_code] = {}
        
        self.translations[lang_code][key] = value
        self.logger.info(f"已添加翻译 [{lang_code}] {key}: {value}")
    
    def save_translations(self):
        """保存所有翻译到文件"""
        for lang_code, translations in self.translations.items():
            self._save_translation_file(lang_code, translations)
    
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.supported_languages.copy()
    
    def get_current_language(self) -> str:
        """获取当前语言代码"""
        return self.current_language
    
    def get_language_display_name(self, lang_code: str) -> str:
        """获取语言显示名称"""
        return self.supported_languages.get(lang_code, lang_code)

# 全局实例
_i18n_manager = None

def get_i18n_manager() -> I18nManager:
    """获取全局多语言管理器实例"""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager

def _(key: str, **kwargs) -> str:
    """翻译函数的简化版本"""
    return get_i18n_manager().get_text(key, **kwargs)

def set_language(lang_code: str) -> bool:
    """设置语言的简化函数"""
    return get_i18n_manager().set_language(lang_code)

if __name__ == '__main__':
    # 测试代码
    manager = I18nManager()
    
    print("=== 多语言资源管理器测试 ===")
    print(f"支持的语言: {manager.get_supported_languages()}")
    
    # 测试英文
    manager.set_language('en')
    print(f"\n英文测试:")
    print(f"Service Control: {manager.get_text('Service Control')}")
    print(f"Start Service: {manager.get_text('Start Service')}")
    
    # 测试中文
    manager.set_language('zh')
    print(f"\n中文测试:")
    print(f"Service Control: {manager.get_text('Service Control')}")
    print(f"Start Service: {manager.get_text('Start Service')}")
    
    # 测试格式化
    manager.add_translation('zh', 'Hello {name}', '你好 {name}')
    print(f"\n格式化测试: {manager.get_text('Hello {name}', name='张三')}")
    
    print("\n测试完成！")