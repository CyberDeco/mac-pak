#!/usr/bin/env python3
"""
BG3 LSX Tools - Simple LSX parsing and editing extensions
Phase 1-3: Parser -> Editor -> Browser
"""

import xml.etree.ElementTree as ET
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from collections import defaultdict

from larian_parser import *
        
# class LSXParser:
#     """Phase 1: Basic LSX file parsing and analysis"""
    
#     def __init__(self):
#         self.current_file = None
#         self.parsed_data = None
    
#     def parse_lsx_file(self, lsx_file):
#         """Parse LSX XML and return structured data"""
#         try:
#             tree = ET.parse(lsx_file)
#             root = tree.getroot()
            
#             self.current_file = lsx_file
#             self.parsed_data = {
#                 'file': lsx_file,
#                 'root_tag': root.tag,
#                 'version': root.get('version', 'unknown'),
#                 'regions': [],
#                 'nodes': [],
#                 'attributes': {},
#                 'raw_tree': tree
#             }
            
#             # Parse regions and nodes
#             for region in root.findall('.//region'):
#                 region_info = {
#                     'id': region.get('id'),
#                     'nodes': []
#                 }
                
#                 for node in region.findall('.//node'):
#                     node_info = {
#                         'id': node.get('id'),
#                         'attributes': []
#                     }
                    
#                     # Parse attributes
#                     for attr in node.findall('.//attribute'):
#                         attr_info = {
#                             'id': attr.get('id'),
#                             'type': attr.get('type'),
#                             'value': attr.get('value'),
#                             'handle': attr.get('handle')
#                         }
#                         node_info['attributes'].append(attr_info)
                    
#                     region_info['nodes'].append(node_info)
                
#                 self.parsed_data['regions'].append(region_info)
            
#             print(f"✅ Parsed {lsx_file}")
#             return self.parsed_data
            
#         except ET.ParseError as e:
#             print(f"❌ XML Parse Error: {e}")
#             return None
#         except Exception as e:
#             print(f"❌ Error parsing LSX: {e}")
#             return None
    
#     def get_lsx_schema_info(self, lsx_file=None):
#         """Analyze LSX structure and data types"""
#         if lsx_file:
#             self.parse_lsx_file(lsx_file)
        
#         if not self.parsed_data:
#             return None
        
#         schema_info = {
#             'file_type': self.parsed_data['root_tag'],
#             'regions': {},
#             'data_types': defaultdict(int),
#             'common_attributes': defaultdict(int),
#             'node_types': defaultdict(int)
#         }
        
#         for region in self.parsed_data['regions']:
#             region_id = region['id']
#             schema_info['regions'][region_id] = {
#                 'node_count': len(region['nodes']),
#                 'node_types': []
#             }
            
#             for node in region['nodes']:
#                 node_id = node['id']
#                 schema_info['node_types'][node_id] += 1
#                 schema_info['regions'][region_id]['node_types'].append(node_id)
                
#                 for attr in node['attributes']:
#                     attr_type = attr['type']
#                     attr_id = attr['id']
#                     schema_info['data_types'][attr_type] += 1
#                     schema_info['common_attributes'][attr_id] += 1
        
#         return schema_info

class LSXEditor:
    """ editor supporting LSX, LSJ, and LSF formats"""
    
    def __init__(self, parent=None, settings_manager=None, bg3_tool=None):
        self.parser = UniversalBG3Parser()
        self.bg3_tool = bg3_tool  # For LSF conversions
        self.current_file = None
        self.current_format = None
        self.modified = False
        self.settings_manager = settings_manager
        self.highlighter = None
        
        if parent:
            self.setup_editor_tab(parent)
    
    def setup_editor_tab(self, parent):
        """Setup  editor interface"""
        editor_frame = ttk.Frame(parent)
        
        #  toolbar
        toolbar = ttk.Frame(editor_frame)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        # File operations
        ttk.Button(toolbar, text="Open File", command=self.open_file).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_file).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Save As", command=self.save_as_file).pack(side='left', padx=2)
        
        ttk.Separator(toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        
        # Format conversions
        ttk.Button(toolbar, text="Convert to LSX", command=self.convert_to_lsx).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Convert to LSJ", command=self.convert_to_lsj).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Convert to LSF", command=self.convert_to_lsf).pack(side='left', padx=2)
        
        ttk.Separator(toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        
        # Tools
        ttk.Button(toolbar, text="Validate", command=self.validate_file).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Format", command=self.format_file).pack(side='left', padx=2)
        
        # Status
        self.format_label = ttk.Label(toolbar, text="Format: None")
        self.format_label.pack(side='right', padx=5)
        
        self.status_label = ttk.Label(toolbar, text="No file loaded")
        self.status_label.pack(side='right', padx=5)
        
        # Text editor with better configuration
        self.text_editor = scrolledtext.ScrolledText(
            editor_frame, 
            wrap=tk.NONE,
            font=('Monaco', 12) if os.name == 'posix' else ('Consolas', 12),
            tabs=('1c', '2c', '3c', '4c'),
            undo=True,
            maxundo=100
        )
        self.text_editor.pack(fill='both', expand=True, padx=5, pady=5)
        
        #  syntax highlighter
        self.highlighter = SyntaxHighlighter(self.text_editor)
        
        # Bind events
        self.text_editor.bind('<KeyPress>', self.on_text_change)
        self.text_editor.bind('<Button-1>', self.on_text_change)
        
        return editor_frame
    
    def open_file(self):
        """Open LSX, LSJ, or LSF files"""
        initial_dir = "/"
        if self.settings_manager:
            initial_dir = self.settings_manager.get("working_directory", "/")
        
        file_path = filedialog.askopenfilename(
            title="Open BG3 File",
            initialdir=initial_dir,
            filetypes=[
                ("All BG3 Files", "*.lsx;*.lsj;*.lsf"),
                ("LSX Files", "*.lsx"), 
                ("LSJ Files", "*.lsj"),
                ("LSF Files", "*.lsf"),
                ("XML Files", "*.xml"), 
                ("JSON Files", "*.json"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """Load and display any supported file format"""
        try:
            # Detect format
            file_format = self.parser.detect_file_format(file_path)
            self.current_format = file_format
            
            if file_format == 'lsf':
                # For LSF files, we need to convert to readable format first
                self._load_lsf_file(file_path)
            else:
                # Load LSX or LSJ directly
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.text_editor.delete(1.0, tk.END)
                self.text_editor.insert(1.0, content)
            
            self.current_file = file_path
            self.modified = False
            self.status_label.config(text=f"Loaded: {os.path.basename(file_path)}")
            self.format_label.config(text=f"Format: {file_format.upper()}")
            
            # Update working directory
            if self.settings_manager:
                self.settings_manager.set("working_directory", os.path.dirname(file_path))
            
            # Apply appropriate syntax highlighting
            self.highlighter.set_format(file_format)
            self.apply_highlighting()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")
    
    def _load_lsf_file(self, file_path):
        """Load LSF file by converting to LSX first"""
        if not self.bg3_tool:
            messagebox.showerror("Error", "LSF support requires divine.exe integration")
            return
        
        try:
            # Create temp LSX file
            temp_lsx = file_path + '.temp.lsx'
            
            # Convert using divine.exe
            success, output = self.bg3_tool.run_divine_command(
                action="convert-resource",
                source=self.bg3_tool.mac_to_wine_path(file_path),
                destination=self.bg3_tool.mac_to_wine_path(temp_lsx),
                input_format="lsf",
                output_format="lsx"
            )
            
            if success and os.path.exists(temp_lsx):
                with open(temp_lsx, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.text_editor.delete(1.0, tk.END)
                self.text_editor.insert(1.0, content)
                
                # Clean up
                os.remove(temp_lsx)
                
                # Add note about LSF conversion
                note = "<!-- This LSF file has been converted to LSX for editing -->\n"
                self.text_editor.insert(1.0, note)
                
            else:
                raise Exception(f"Conversion failed: {output}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Could not load LSF file: {e}")
    
    def convert_to_lsx(self):
        """Convert current file to LSX format"""
        if not self.current_file:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        if self.current_format == 'lsx':
            messagebox.showinfo("Info", "File is already in LSX format")
            return
        
        self._perform_conversion('lsx')
    
    def convert_to_lsj(self):
        """Convert current file to LSJ format"""
        if not self.current_file:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        if self.current_format == 'lsj':
            messagebox.showinfo("Info", "File is already in LSJ format")
            return
        
        # LSJ conversion is complex and may not be universally supported
        messagebox.showinfo("Info", "LSJ conversion not yet implemented")
    
    def convert_to_lsf(self):
        """Convert current file to LSF format"""
        if not self.current_file:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        if self.current_format == 'lsf':
            messagebox.showinfo("Info", "File is already in LSF format")
            return
        
        self._perform_conversion('lsf')
    
    def _perform_conversion(self, target_format):
        """Perform file format conversion"""
        if not self.bg3_tool:
            messagebox.showerror("Error", f"Conversion to {target_format.upper()} requires divine.exe")
            return
        
        # Save current content first if modified
        if self.modified:
            result = messagebox.askyesnocancel("Save Changes", 
                                             "Save current changes before conversion?")
            if result is True:
                self.save_file()
            elif result is None:
                return  # Cancelled
        
        # Choose output file
        output_file = filedialog.asksaveasfilename(
            title=f"Save as {target_format.upper()}",
            defaultextension=f".{target_format}",
            filetypes=[(f"{target_format.upper()} Files", f"*.{target_format}")]
        )
        
        if not output_file:
            return
        
        try:
            # Perform conversion using divine.exe
            success, output = self.bg3_tool.run_divine_command(
                action="convert-resource",
                source=self.bg3_tool.mac_to_wine_path(self.current_file),
                destination=self.bg3_tool.mac_to_wine_path(output_file),
                input_format=self.current_format,
                output_format=target_format
            )
            
            if success:
                messagebox.showinfo("Success", f"Converted to {target_format.upper()}: {output_file}")
                
                # Ask if user wants to open the converted file
                if messagebox.askyesno("Open Converted File", 
                                     "Would you like to open the converted file?"):
                    self.load_file(output_file)
            else:
                messagebox.showerror("Conversion Failed", f"Error: {output}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Conversion failed: {e}")
    
    def validate_file(self):
        """Validate current file based on format"""
        if not self.current_file:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        content = self.text_editor.get(1.0, tk.END + '-1c')
        
        try:
            if self.current_format == 'lsx':
                ET.fromstring(content)
                messagebox.showinfo("Validation", "Valid LSX/XML structure!")
            elif self.current_format == 'lsj':
                json.loads(content)
                messagebox.showinfo("Validation", "Valid LSJ/JSON structure!")
            elif self.current_format == 'lsf':
                messagebox.showinfo("Validation", "LSF files cannot be validated in text format")
            else:
                messagebox.showwarning("Validation", "Unknown file format")
                
        except (ET.ParseError, json.JSONDecodeError) as e:
            messagebox.showerror("Validation Error", f"Format Error:\n{e}")
    
    def format_file(self):
        """Format/prettify current file content"""
        if not self.current_file:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        content = self.text_editor.get(1.0, tk.END + '-1c')
        
        try:
            if self.current_format == 'lsx':
                # Format XML
                root = ET.fromstring(content)
                self._indent_xml(root)
                formatted = ET.tostring(root, encoding='unicode')
                formatted = '<?xml version="1.0" encoding="UTF-8"?>\n' + formatted
                
            elif self.current_format == 'lsj':
                # Format JSON
                data = json.loads(content)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
                
            else:
                messagebox.showinfo("Info", f"Formatting not supported for {self.current_format}")
                return
            
            # Replace content
            self.text_editor.delete(1.0, tk.END)
            self.text_editor.insert(1.0, formatted)
            self.apply_highlighting()
            
        except Exception as e:
            messagebox.showerror("Format Error", f"Could not format file: {e}")
    
    def _indent_xml(self, elem, level=0):
        """Helper to indent XML elements"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    def save_file(self):
        """Save file with format preservation"""
        if not self.current_file:
            self.save_as_file()
            return
        
        try:
            content = self.text_editor.get(1.0, tk.END + '-1c')
            
            # For LSF files, warn about saving as text
            if self.current_format == 'lsf':
                result = messagebox.askyesnocancel(
                    "LSF File Warning",
                    "This is an LSF file converted to text. Saving will create an LSX file.\n"
                    "Save as LSX instead?"
                )
                if result is True:
                    # Save as LSX
                    lsx_file = self.current_file.replace('.lsf', '.lsx')
                    with open(lsx_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    messagebox.showinfo("Saved", f"Saved as LSX: {lsx_file}")
                    return
                elif result is None:
                    return  # Cancelled
            
            # Normal save
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.modified = False
            self.status_label.config(text=f"Saved: {os.path.basename(self.current_file)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {e}")
    
    def save_as_file(self):
        """Save as new file with format selection"""
        initial_dir = "/"
        if self.settings_manager:
            initial_dir = self.settings_manager.get("working_directory", "/")
        
        # Determine default extension
        default_ext = ".lsx"
        if self.current_format:
            default_ext = f".{self.current_format}"
        
        file_path = filedialog.asksaveasfilename(
            title="Save BG3 File",
            initialdir=initial_dir,
            defaultextension=default_ext,
            filetypes=[
                ("LSX Files", "*.lsx"), 
                ("LSJ Files", "*.lsj"),
                ("XML Files", "*.xml"), 
                ("JSON Files", "*.json"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            self.current_file = file_path
            
            # Update format based on extension
            new_format = self.parser.detect_file_format(file_path)
            if new_format != 'unknown':
                self.current_format = new_format
                self.format_label.config(text=f"Format: {new_format.upper()}")
                self.highlighter.set_format(new_format)
            
            # Update working directory
            if self.settings_manager:
                self.settings_manager.set("working_directory", os.path.dirname(file_path))
            
            self.save_file()
    
    def apply_highlighting(self):
        """Apply syntax highlighting"""
        if self.highlighter:
            self.highlighter.highlight_text()
    
    def on_text_change(self, event=None):
        """Handle text changes"""
        if not self.modified:
            self.modified = True
            if self.current_file:
                self.status_label.config(text=f"Modified: {os.path.basename(self.current_file)}")

class SyntaxHighlighter:
    """ syntax highlighter supporting multiple formats"""
    
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.current_format = 'lsx'
        self.setup_tags()
    
    def setup_tags(self):
        """Configure text tags for different syntax elements"""
        # XML/LSX tags
        self.text_widget.tag_config("xml_tag", foreground="#0066CC", font=("Monaco", 12, "bold"))
        self.text_widget.tag_config("xml_attribute", foreground="#006600")
        self.text_widget.tag_config("xml_value", foreground="#CC0000")
        
        # JSON/LSJ tags
        self.text_widget.tag_config("json_key", foreground="#0066CC", font=("Monaco", 12, "bold"))
        self.text_widget.tag_config("json_string", foreground="#CC0000")
        self.text_widget.tag_config("json_number", foreground="#FF6600")
        self.text_widget.tag_config("json_bool", foreground="#9900CC", font=("Monaco", 12, "bold"))
        
        # Common elements
        self.text_widget.tag_config("bg3_important", foreground="#9900CC", font=("Monaco", 12, "bold"))
        self.text_widget.tag_config("uuid", foreground="#FF6600", font=("Monaco", 12, "bold"))
        self.text_widget.tag_config("comment", foreground="#666666", font=("Monaco", 12, "italic"))
    
    def set_format(self, file_format):
        """Set the current file format for appropriate highlighting"""
        self.current_format = file_format
    
    def highlight_text(self):
        """Apply syntax highlighting based on current format"""
        if self.current_format == 'lsx':
            self._highlight_xml()
        elif self.current_format == 'lsj':
            self._highlight_json()
        # LSF files are displayed as LSX after conversion
    
    def _highlight_xml(self):
        """Highlight XML/LSX syntax"""
        content = self.text_widget.get(1.0, tk.END)
        
        # Clear existing tags
        for tag in ["xml_tag", "xml_attribute", "xml_value", "bg3_important", "uuid", "comment"]:
            self.text_widget.tag_remove(tag, 1.0, tk.END)
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Comments
            if '<!--' in line and '-->' in line:
                comment_start = line.find('<!--')
                comment_end = line.find('-->') + 3
                start_pos = f"{line_num}.{comment_start}"
                end_pos = f"{line_num}.{comment_end}"
                self.text_widget.tag_add("comment", start_pos, end_pos)
                continue
            
            # XML tags
            self._highlight_xml_tags(line, line_num)
            
            # Attributes and values
            self._highlight_xml_attributes(line, line_num)
    
    def _highlight_json(self):
        """Highlight JSON/LSJ syntax"""
        content = self.text_widget.get(1.0, tk.END)
        
        # Clear existing tags
        for tag in ["json_key", "json_string", "json_number", "json_bool", "uuid", "comment"]:
            self.text_widget.tag_remove(tag, 1.0, tk.END)
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            self._highlight_json_elements(line, line_num)
    
    def _highlight_xml_tags(self, line, line_num):
        """Highlight XML tags in a line"""
        import re
        
        # Find all XML tags
        for match in re.finditer(r'<[^>]+>', line):
            start_pos = f"{line_num}.{match.start()}"
            end_pos = f"{line_num}.{match.end()}"
            self.text_widget.tag_add("xml_tag", start_pos, end_pos)
    
    def _highlight_xml_attributes(self, line, line_num):
        """Highlight XML attributes and values"""
        import re
        
        # Attribute patterns (id="value", type="value", etc.)
        attr_pattern = r'(\w+)="([^"]*)"'
        for match in re.finditer(attr_pattern, line):
            attr_name, attr_value = match.groups()
            
            # Attribute name
            name_start = f"{line_num}.{match.start(1)}"
            name_end = f"{line_num}.{match.end(1)}"
            
            # Check if it's a BG3-important attribute
            bg3_important_attrs = ["UUID", "Author", "Name", "Description", "Version64", "MD5", "Folder"]
            if attr_name in bg3_important_attrs:
                self.text_widget.tag_add("bg3_important", name_start, name_end)
            else:
                self.text_widget.tag_add("xml_attribute", name_start, name_end)
            
            # Attribute value
            value_start = f"{line_num}.{match.start(2)}"
            value_end = f"{line_num}.{match.end(2)}"
            
            # Check if it's a UUID
            #uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}
            uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        
            if re.match(uuid_pattern, attr_value):
                self.text_widget.tag_add("uuid", value_start, value_end)
            else:
                self.text_widget.tag_add("xml_value", value_start, value_end)
    
    def _highlight_json_elements(self, line, line_num):
        """Highlight JSON elements in a line"""
        import re
        
        # JSON string keys
        key_pattern = r'"([^"]+)"\s*:'
        for match in re.finditer(key_pattern, line):
            start_pos = f"{line_num}.{match.start(1)}"
            end_pos = f"{line_num}.{match.end(1)}"
            self.text_widget.tag_add("json_key", start_pos, end_pos)
        
        # JSON string values
        string_pattern = r':\s*"([^"]*)"'
        for match in re.finditer(string_pattern, line):
            value = match.group(1)
            start_pos = f"{line_num}.{match.start(1)}"
            end_pos = f"{line_num}.{match.end(1)}"
            
            # Check if it's a UUID
            uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        
            if re.match(uuid_pattern, value):
                self.text_widget.tag_add("uuid", start_pos, end_pos)
            else:
                self.text_widget.tag_add("json_string", start_pos, end_pos)
        
        # JSON numbers
        number_pattern = r':\s*(-?\d+\.?\d*)'
        for match in re.finditer(number_pattern, line):
            start_pos = f"{line_num}.{match.start(1)}"
            end_pos = f"{line_num}.{match.end(1)}"
            self.text_widget.tag_add("json_number", start_pos, end_pos)
        
        # JSON booleans and null
        bool_pattern = r':\s*(true|false|null)'
        for match in re.finditer(bool_pattern, line):
            start_pos = f"{line_num}.{match.start(1)}"
            end_pos = f"{line_num}.{match.end(1)}"
            self.text_widget.tag_add("json_bool", start_pos, end_pos)

class UniversalFileConverter:
    """Handles conversions between LSX, LSJ, and LSF formats using divine.exe"""
    
    def __init__(self, bg3_tool):
        self.bg3_tool = bg3_tool
    
    def convert_file(self, source_path, target_path, source_format=None, target_format=None):
        """Convert between any supported formats"""
        
        # Auto-detect formats if not provided
        if not source_format:
            source_format = self._detect_format(source_path)
        if not target_format:
            target_format = self._detect_format_from_extension(target_path)
        
        # Validate formats
        supported_formats = ['lsx', 'lsj', 'lsf']
        if source_format not in supported_formats or target_format not in supported_formats:
            raise ValueError(f"Unsupported format conversion: {source_format} -> {target_format}")
        
        # Direct conversions using divine.exe
        if source_format == target_format:
            # Just copy the file
            import shutil
            shutil.copy2(source_path, target_path)
            return True, "File copied (same format)"
        
        # Use divine.exe for conversions
        success, output = self.bg3_tool.run_divine_command(
            action="convert-resource",
            source=self.bg3_tool.mac_to_wine_path(source_path),
            destination=self.bg3_tool.mac_to_wine_path(target_path),
            input_format=source_format,
            output_format=target_format
        )
        
        return success, output
    
    def batch_convert(self, file_list, target_format, output_dir=None, progress_callback=None):
        """Convert multiple files to target format"""
        results = []
        total_files = len(file_list)
        
        for i, source_file in enumerate(file_list):
            if progress_callback:
                percentage = int((i / total_files) * 100)
                progress_callback(percentage, f"Converting {os.path.basename(source_file)}...")
            
            try:
                # Determine output path
                if output_dir:
                    basename = os.path.splitext(os.path.basename(source_file))[0]
                    target_file = os.path.join(output_dir, f"{basename}.{target_format}")
                else:
                    target_file = os.path.splitext(source_file)[0] + f".{target_format}"
                
                # Convert
                success, output = self.convert_file(source_file, target_file, target_format=target_format)
                
                results.append({
                    'source': source_file,
                    'target': target_file,
                    'success': success,
                    'output': output
                })
                
            except Exception as e:
                results.append({
                    'source': source_file,
                    'target': '',
                    'success': False,
                    'output': str(e)
                })
        
        if progress_callback:
            progress_callback(100, "Batch conversion complete!")
        
        return results
    
    def _detect_format(self, file_path):
        """Detect file format from extension and content"""
        ext = os.path.splitext(file_path)[1].lower()
        format_map = {'.lsx': 'lsx', '.lsj': 'lsj', '.lsf': 'lsf'}
        return format_map.get(ext, 'unknown')
    
    def _detect_format_from_extension(self, file_path):
        """Get format from file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        format_map = {'.lsx': 'lsx', '.lsj': 'lsj', '.lsf': 'lsf'}
        return format_map.get(ext, 'lsx')  # Default to lsx


class BatchFileProcessor:
    """Process multiple BG3 files with various operations"""
    
    def __init__(self, bg3_tool):
        self.bg3_tool = bg3_tool
        self.converter = UniversalFileConverter(bg3_tool)
    
    def setup_batch_tab(self, parent):
        """Setup batch processing interface"""
        frame = ttk.Frame(parent)
        
        # Title
        ttk.Label(frame, text="Batch File Processing", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # File selection
        file_frame = ttk.LabelFrame(frame, text="File Selection", padding=10)
        file_frame.pack(fill='x', padx=20, pady=10)
        
        # File list
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill='both', expand=True)
        
        self.file_listbox = tk.Listbox(list_frame, height=8)
        self.file_listbox.pack(side='left', fill='both', expand=True)
        
        list_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.file_listbox.yview)
        list_scrollbar.pack(side='right', fill='y')
        self.file_listbox.config(yscrollcommand=list_scrollbar.set)
        
        # File buttons
        file_btn_frame = ttk.Frame(file_frame)
        file_btn_frame.pack(fill='x', pady=5)
        
        ttk.Button(file_btn_frame, text="Add Files", command=self.add_files).pack(side='left', padx=2)
        ttk.Button(file_btn_frame, text="Add Directory", command=self.add_directory).pack(side='left', padx=2)
        ttk.Button(file_btn_frame, text="Remove Selected", command=self.remove_selected).pack(side='left', padx=2)
        ttk.Button(file_btn_frame, text="Clear All", command=self.clear_files).pack(side='left', padx=2)
        
        # Operations
        ops_frame = ttk.LabelFrame(frame, text="Batch Operations", padding=10)
        ops_frame.pack(fill='x', padx=20, pady=10)
        
        # Format conversion
        conv_frame = ttk.Frame(ops_frame)
        conv_frame.pack(fill='x', pady=5)
        
        ttk.Label(conv_frame, text="Convert to:").pack(side='left')
        self.target_format = tk.StringVar(value="lsx")
        format_combo = ttk.Combobox(conv_frame, textvariable=self.target_format, 
                                  values=["lsx", "lsj", "lsf"], state="readonly", width=10)
        format_combo.pack(side='left', padx=5)
        
        ttk.Button(conv_frame, text="Convert All", command=self.batch_convert).pack(side='left', padx=10)
        
        # Output directory
        output_frame = ttk.Frame(ops_frame)
        output_frame.pack(fill='x', pady=5)
        
        ttk.Label(output_frame, text="Output Directory:").pack(side='left')
        self.output_dir = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_dir, width=40).pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(output_frame, text="Browse", command=self.browse_output_dir).pack(side='left', padx=2)
        
        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(ops_frame, variable=self.progress_var, mode='determinate')
        self.progress_bar.pack(fill='x', pady=10)
        
        self.progress_label = ttk.Label(ops_frame, text="Ready")
        self.progress_label.pack()
        
        # Results
        results_frame = ttk.LabelFrame(frame, text="Results", padding=10)
        results_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=10)
        self.results_text.pack(fill='both', expand=True)
        
        self.file_list = []  # Store selected files
        
        return frame
    
    def add_files(self):
        """Add individual files to batch list"""
        files = filedialog.askopenfilenames(
            title="Select BG3 Files",
            filetypes=[
                ("All BG3 Files", "*.lsx;*.lsj;*.lsf"),
                ("LSX Files", "*.lsx"), 
                ("LSJ Files", "*.lsj"),
                ("LSF Files", "*.lsf"),
                ("All Files", "*.*")
            ]
        )
        
        for file_path in files:
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                self.file_listbox.insert(tk.END, os.path.basename(file_path))
    
    def add_directory(self):
        """Add all BG3 files from a directory"""
        directory = filedialog.askdirectory(title="Select Directory")
        
        if directory:
            # Find all BG3 files in directory
            extensions = ['.lsx', '.lsj', '.lsf']
            found_files = []
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        file_path = os.path.join(root, file)
                        if file_path not in self.file_list:
                            found_files.append(file_path)
            
            # Add to list
            for file_path in found_files:
                self.file_list.append(file_path)
                self.file_listbox.insert(tk.END, os.path.relpath(file_path, directory))
            
            if found_files:
                self.results_text.insert(tk.END, f"Added {len(found_files)} files from {directory}\n")
            else:
                self.results_text.insert(tk.END, f"No BG3 files found in {directory}\n")
    
    def remove_selected(self):
        """Remove selected files from list"""
        selected_indices = self.file_listbox.curselection()
        
        # Remove in reverse order to maintain indices
        for index in reversed(selected_indices):
            del self.file_list[index]
            self.file_listbox.delete(index)
    
    def clear_files(self):
        """Clear all files from list"""
        self.file_list.clear()
        self.file_listbox.delete(0, tk.END)
    
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir.set(directory)
    
    def batch_convert(self):
        """Perform batch conversion"""
        if not self.file_list:
            messagebox.showwarning("Warning", "No files selected for conversion")
            return
        
        target_format = self.target_format.get()
        output_dir = self.output_dir.get() or None
        
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create output directory: {e}")
                return
        
        # Clear previous results
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"Starting batch conversion to {target_format.upper()}...\n\n")
        
        # Progress callback
        def progress_update(percentage, message):
            self.progress_var.set(percentage)
            self.progress_label.config(text=message)
            self.progress_bar.update()
        
        # Run conversion in thread
        def conversion_worker():
            try:
                results = self.converter.batch_convert(
                    self.file_list, 
                    target_format, 
                    output_dir, 
                    progress_update
                )
                
                # Display results
                successful = sum(1 for r in results if r['success'])
                failed = len(results) - successful
                
                summary = f"Conversion complete!\n"
                summary += f"Successful: {successful}\n"
                summary += f"Failed: {failed}\n\n"
                
                self.results_text.insert(tk.END, summary)
                
                # Show detailed results
                for result in results:
                    status = "✅" if result['success'] else "❌"
                    source_name = os.path.basename(result['source'])
                    
                    if result['success']:
                        target_name = os.path.basename(result['target'])
                        self.results_text.insert(tk.END, f"{status} {source_name} -> {target_name}\n")
                    else:
                        self.results_text.insert(tk.END, f"{status} {source_name}: {result['output']}\n")
                
                self.progress_label.config(text="Conversion complete!")
                
            except Exception as e:
                self.results_text.insert(tk.END, f"❌ Batch conversion failed: {e}\n")
                self.progress_label.config(text="Conversion failed!")
        
        # Start conversion thread
        thread = threading.Thread(target=conversion_worker, daemon=True)
        thread.start()
