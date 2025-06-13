#!/usr/bin/env python3
"""
Script to compile .po translation files to .mo files for the WMS Management App.
"""

import os
import struct
import array
from pathlib import Path

def compile_po_to_mo(po_file_path, mo_file_path):
    """
    Compile a .po file to .mo file format.
    This is a simplified implementation that handles basic msgid/msgstr pairs.
    """
    
    # Read and parse the .po file
    translations = {}
    
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple parser for msgid/msgstr pairs
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('msgid '):
            # Extract msgid
            msgid = line[6:].strip('"')
            i += 1
            
            # Handle multiline msgid
            while i < len(lines) and lines[i].strip().startswith('"'):
                msgid += lines[i].strip().strip('"')
                i += 1
            
            # Look for msgstr
            if i < len(lines) and lines[i].strip().startswith('msgstr'):
                msgstr_line = lines[i].strip()
                msgstr = msgstr_line[6:].strip().strip('"')
                i += 1
                
                # Handle multiline msgstr
                while i < len(lines) and lines[i].strip().startswith('"'):
                    msgstr += lines[i].strip().strip('"')
                    i += 1
                
                # Only add non-empty translations
                if msgid and msgstr and msgid != msgstr:
                    translations[msgid] = msgstr
        else:
            i += 1
    
    # Create .mo file
    create_mo_file(translations, mo_file_path)
    print(f"Compiled {len(translations)} translations from {po_file_path} to {mo_file_path}")

def create_mo_file(translations, mo_file_path):
    """
    Create a .mo file from translations dictionary.
    """
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(mo_file_path), exist_ok=True)
    
    # Prepare data
    keys = sorted(translations.keys())
    values = [translations[k] for k in keys]
    
    # Calculate offsets
    koffsets = []
    voffsets = []
    kencoded = []
    vencoded = []
    
    for k, v in zip(keys, values):
        kencoded.append(k.encode('utf-8'))
        vencoded.append(v.encode('utf-8'))
    
    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart
    for k in kencoded:
        valuestart += len(k) + 1
    
    koffsets = []
    voffsets = []
    
    offset = keystart
    for k in kencoded:
        koffsets.append((len(k), offset))
        offset += len(k) + 1
    
    offset = valuestart
    for v in vencoded:
        voffsets.append((len(v), offset))
        offset += len(v) + 1
    
    # Write .mo file
    with open(mo_file_path, 'wb') as f:
        # Magic number
        f.write(struct.pack('<I', 0x950412de))
        # Version
        f.write(struct.pack('<I', 0))
        # Number of entries
        f.write(struct.pack('<I', len(keys)))
        # Offset of key table
        f.write(struct.pack('<I', 7 * 4))
        # Offset of value table
        f.write(struct.pack('<I', 7 * 4 + 8 * len(keys)))
        # Hash table size (0 = no hash table)
        f.write(struct.pack('<I', 0))
        # Offset of hash table
        f.write(struct.pack('<I', 0))
        
        # Key table
        for length, offset in koffsets:
            f.write(struct.pack('<I', length))
            f.write(struct.pack('<I', offset))
        
        # Value table
        for length, offset in voffsets:
            f.write(struct.pack('<I', length))
            f.write(struct.pack('<I', offset))
        
        # Keys
        for k in kencoded:
            f.write(k)
            f.write(b'\x00')
        
        # Values
        for v in vencoded:
            f.write(v)
            f.write(b'\x00')

def main():
    """Main function to compile all .po files in the project."""
    
    base_dir = Path(__file__).parent
    locale_dir = base_dir / 'locale'
    
    # Compile English translations
    en_po = locale_dir / 'en' / 'LC_MESSAGES' / 'management_app.po'
    en_mo = locale_dir / 'en' / 'LC_MESSAGES' / 'management_app.mo'
    
    if en_po.exists():
        compile_po_to_mo(str(en_po), str(en_mo))
    else:
        print(f"Warning: {en_po} not found")
    
    # Compile Chinese translations
    zh_po = locale_dir / 'zh' / 'LC_MESSAGES' / 'management_app.po'
    zh_mo = locale_dir / 'zh' / 'LC_MESSAGES' / 'management_app.mo'
    
    if zh_po.exists():
        compile_po_to_mo(str(zh_po), str(zh_mo))
    else:
        print(f"Warning: {zh_po} not found")
    
    print("\nTranslation compilation completed!")
    print("The management application can now use the compiled translations.")

if __name__ == '__main__':
    main()