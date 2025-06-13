#!/usr/bin/env python3
"""
翻译迁移工具
将现有的 .po 文件转换为新的 JSON 格式
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

def parse_po_file(po_file_path: str) -> Dict[str, str]:
    """解析.po文件并返回翻译字典"""
    translations = {}
    
    # 尝试不同的编码方式
    encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']
    content = None
    
    for encoding in encodings:
        try:
            with open(po_file_path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"成功使用编码 {encoding} 读取文件 {po_file_path}")
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        print(f"无法读取文件 {po_file_path}，尝试了所有编码方式")
        return translations
    
    # 使用正则表达式匹配 msgid 和 msgstr 对
    # 支持多行字符串
    pattern = r'msgid\s+"([^"]*(?:\\.[^"]*)*)"|msgid\s+""\s*\n((?:\s*"[^"]*(?:\\.[^"]*)*"\s*\n)*)|msgstr\s+"([^"]*(?:\\.[^"]*)*)"|msgstr\s+""\s*\n((?:\s*"[^"]*(?:\\.[^"]*)*"\s*\n)*)'
    
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('msgid '):
            # 提取 msgid
            msgid_match = re.match(r'msgid\s+"(.*)"', line)
            if msgid_match:
                msgid = msgid_match.group(1)
            else:
                msgid = ""
            
            i += 1
            
            # 处理多行 msgid
            while i < len(lines) and lines[i].strip().startswith('"'):
                line_content = re.match(r'"(.*)"', lines[i].strip())
                if line_content:
                    msgid += line_content.group(1)
                i += 1
            
            # 查找对应的 msgstr
            if i < len(lines) and lines[i].strip().startswith('msgstr'):
                msgstr_line = lines[i].strip()
                msgstr_match = re.match(r'msgstr\s+"(.*)"', msgstr_line)
                if msgstr_match:
                    msgstr = msgstr_match.group(1)
                else:
                    msgstr = ""
                
                i += 1
                
                # 处理多行 msgstr
                while i < len(lines) and lines[i].strip().startswith('"'):
                    line_content = re.match(r'"(.*)"', lines[i].strip())
                    if line_content:
                        msgstr += line_content.group(1)
                    i += 1
                
                # 解码转义字符
                msgid = msgid.encode().decode('unicode_escape') if msgid else msgid
                msgstr = msgstr.encode().decode('unicode_escape') if msgstr else msgstr
                
                # 只添加非空的翻译
                if msgid and msgstr and msgid != msgstr:
                    translations[msgid] = msgstr
        else:
            i += 1
    
    return translations

def convert_po_to_json(po_file_path: str, json_file_path: str) -> bool:
    """
    将 .po 文件转换为 JSON 格式
    
    Args:
        po_file_path: 源 .po 文件路径
        json_file_path: 目标 JSON 文件路径
        
    Returns:
        bool: 转换是否成功
    """
    try:
        translations = parse_po_file(po_file_path)
        
        if not translations:
            print(f"警告: {po_file_path} 中没有找到有效的翻译")
            return False
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
        
        # 保存为 JSON 格式
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2, sort_keys=True)
        
        print(f"成功转换: {po_file_path} -> {json_file_path}")
        print(f"  转换了 {len(translations)} 条翻译")
        return True
        
    except Exception as e:
        print(f"转换失败 {po_file_path}: {e}")
        return False

def migrate_all_translations():
    """
    迁移所有翻译文件
    """
    base_dir = Path(__file__).parent
    locale_dir = base_dir / 'locale'
    translations_dir = base_dir / 'translations'
    
    # 创建新的翻译目录
    translations_dir.mkdir(exist_ok=True)
    
    print("=== 开始迁移翻译文件 ===")
    
    # 支持的语言
    languages = ['en', 'zh']
    
    success_count = 0
    total_count = 0
    
    for lang in languages:
        po_file = locale_dir / lang / 'LC_MESSAGES' / 'management_app.po'
        json_file = translations_dir / f'{lang}.json'
        
        total_count += 1
        
        if po_file.exists():
            if convert_po_to_json(str(po_file), str(json_file)):
                success_count += 1
        else:
            print(f"警告: 找不到 .po 文件: {po_file}")
    
    print(f"\n=== 迁移完成 ===")
    print(f"成功: {success_count}/{total_count}")
    
    # 验证迁移结果
    print("\n=== 验证迁移结果 ===")
    for lang in languages:
        json_file = translations_dir / f'{lang}.json'
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"{lang}.json: {len(data)} 条翻译")
                
                # 显示几个示例
                if data:
                    print(f"  示例翻译:")
                    for i, (key, value) in enumerate(list(data.items())[:3]):
                        print(f"    {key} -> {value}")
                    if len(data) > 3:
                        print(f"    ... 还有 {len(data) - 3} 条")
            except Exception as e:
                print(f"验证 {json_file} 失败: {e}")
        else:
            print(f"未找到: {json_file}")

def create_backup():
    """
    创建原始文件的备份
    """
    base_dir = Path(__file__).parent
    locale_dir = base_dir / 'locale'
    backup_dir = base_dir / 'locale_backup'
    
    if locale_dir.exists():
        import shutil
        try:
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(locale_dir, backup_dir)
            print(f"已创建备份: {backup_dir}")
        except Exception as e:
            print(f"创建备份失败: {e}")

if __name__ == '__main__':
    print("翻译迁移工具")
    print("将 .po 文件转换为 JSON 格式")
    print()
    
    # 创建备份
    create_backup()
    
    # 执行迁移
    migrate_all_translations()
    
    print("\n迁移完成！")
    print("新的 JSON 翻译文件位于 'translations' 目录中")
    print("原始文件的备份位于 'locale_backup' 目录中")