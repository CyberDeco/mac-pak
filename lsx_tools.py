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
        
class LSXParser:
    """Phase 1: Basic LSX file parsing and analysis"""
    
    def __init__(self):
        self.current_file = None
        self.parsed_data = None
    
    def parse_lsx_file(self, lsx_file):
        """Parse LSX XML and return structured data"""
        try:
            tree = ET.parse(lsx_file)
            root = tree.getroot()
            
            self.current_file = lsx_file
            self.parsed_data = {
                'file': lsx_file,
                'root_tag': root.tag,
                'version': root.get('version', 'unknown'),
                'regions': [],
                'nodes': [],
                'attributes': {},
                'raw_tree': tree
            }
            
            # Parse regions and nodes
            for region in root.findall('.//region'):
                region_info = {
                    'id': region.get('id'),
                    'nodes': []
                }
                
                for node in region.findall('.//node'):
                    node_info = {
                        'id': node.get('id'),
                        'attributes': []
                    }
                    
                    # Parse attributes
                    for attr in node.findall('.//attribute'):
                        attr_info = {
                            'id': attr.get('id'),
                            'type': attr.get('type'),
                            'value': attr.get('value'),
                            'handle': attr.get('handle')
                        }
                        node_info['attributes'].append(attr_info)
                    
                    region_info['nodes'].append(node_info)
                
                self.parsed_data['regions'].append(region_info)
            
            print(f"✅ Parsed {lsx_file}")
            return self.parsed_data
            
        except ET.ParseError as e:
            print(f"❌ XML Parse Error: {e}")
            return None
        except Exception as e:
            print(f"❌ Error parsing LSX: {e}")
            return None
    
    def get_lsx_schema_info(self, lsx_file=None):
        """Analyze LSX structure and data types"""
        if lsx_file:
            self.parse_lsx_file(lsx_file)
        
        if not self.parsed_data:
            return None
        
        schema_info = {
            'file_type': self.parsed_data['root_tag'],
            'regions': {},
            'data_types': defaultdict(int),
            'common_attributes': defaultdict(int),
            'node_types': defaultdict(int)
        }
        
        for region in self.parsed_data['regions']:
            region_id = region['id']
            schema_info['regions'][region_id] = {
                'node_count': len(region['nodes']),
                'node_types': []
            }
            
            for node in region['nodes']:
                node_id = node['id']
                schema_info['node_types'][node_id] += 1
                schema_info['regions'][region_id]['node_types'].append(node_id)
                
                for attr in node['attributes']:
                    attr_type = attr['type']
                    attr_id = attr['id']
                    schema_info['data_types'][attr_type] += 1
                    schema_info['common_attributes'][attr_id] += 1
        
        return schema_info

class LSXEditor:
    """LSX Editor with syntax highlighting and better UX"""
    
    def __init__(self, parent=None, settings_manager=None):
        self.parser = LSXParser()  # Assuming this exists from your original code
        self.current_file = None
        self.modified = False
        self.settings_manager = settings_manager
        self.highlighter = None
        
        # Tracking variables for highlighting
        self.highlight_timer = None
        self.last_change_time = 0
        self.highlight_delay = 1000  # 1 second delay
        
        if parent:
            self.setup_editor_tab(parent)
    
    def setup_editor_tab(self, parent):
        """Setup the editor interface"""
        editor_frame = ttk.Frame(parent)
        
        # Toolbar
        toolbar = ttk.Frame(editor_frame)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(toolbar, text="Open LSX", command=self.open_file).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_file).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Save As", command=self.save_as_file).pack(side='left', padx=2)
        
        ttk.Separator(toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        
        ttk.Button(toolbar, text="Validate", command=self.validate_xml).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Highlight", command=self.apply_highlighting).pack(side='left', padx=2)
        
        self.status_label = ttk.Label(toolbar, text="No file loaded")
        self.status_label.pack(side='right', padx=5)
        
        # Text editor
        self.text_editor = scrolledtext.ScrolledText(
            editor_frame, 
            wrap=tk.NONE,
            font=('Courier', 12),
            tabs=('1c', '2c', '3c', '4c'),
            undo=True
        )
        self.text_editor.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Setup syntax highlighter
        self.highlighter = LSXSyntaxHighlighter(self.text_editor)
        
        # Bind events
        self.text_editor.bind('<KeyPress>', self.on_text_change)
        self.text_editor.bind('<Button-1>', self.on_text_change)
        
        # Auto-highlight after typing pause
        self.highlight_timer = None
        
        return editor_frame
    
    def open_file(self):
        """Open and display an LSX file with working directory support"""
        initial_dir = "/"
        if self.settings_manager:
            initial_dir = self.settings_manager.get("working_directory", "/")
        
        file_path = filedialog.askopenfilename(
            title="Open LSX File",
            initialdir=initial_dir,
            filetypes=[("LSX Files", "*.lsx"), ("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.text_editor.delete(1.0, tk.END)
                self.text_editor.insert(1.0, content)
                
                self.current_file = file_path
                self.modified = False
                self.status_label.config(text=f"Loaded: {os.path.basename(file_path)}")
                
                # Update working directory
                if self.settings_manager:
                    self.settings_manager.set("working_directory", os.path.dirname(file_path))
                
                # Apply syntax highlighting
                self.apply_highlighting()
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
    
    def save_file(self):
        """Save the current LSX file"""
        if not self.current_file:
            self.save_as_file()
            return
        
        try:
            content = self.text_editor.get(1.0, tk.END + '-1c')
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.modified = False
            self.status_label.config(text=f"Saved: {os.path.basename(self.current_file)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {e}")
    
    def save_as_file(self):
        """Save as new file"""
        initial_dir = "/"
        if self.settings_manager:
            initial_dir = self.settings_manager.get("working_directory", "/")
        
        file_path = filedialog.asksaveasfilename(
            title="Save LSX File",
            initialdir=initial_dir,
            defaultextension=".lsx",
            filetypes=[("LSX Files", "*.lsx"), ("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.current_file = file_path
            
            # Update working directory
            if self.settings_manager:
                self.settings_manager.set("working_directory", os.path.dirname(file_path))
            
            self.save_file()
    
    def validate_xml(self):
        """Validate XML structure"""
        content = self.text_editor.get(1.0, tk.END + '-1c')
        
        try:
            ET.fromstring(content)
            messagebox.showinfo("Validation", "Valid XML structure!")
            self.status_label.config(text="Valid XML")
        except ET.ParseError as e:
            messagebox.showerror("Validation Error", f"XML Parse Error:\n{e}")
            self.status_label.config(text="Invalid XML")
    
    def apply_highlighting(self):
        """Apply syntax highlighting to the text"""
        if self.highlighter:
            self.highlighter.highlight_text()
    
    def on_text_change(self, event=None):
        """Handle text changes with delayed highlighting"""
        if not self.modified:
            self.modified = True
            if self.current_file:
                self.status_label.config(text=f"Modified: {os.path.basename(self.current_file)}")
        
        # Cancel previous timer
        if self.highlight_timer:
            self.text_editor.after_cancel(self.highlight_timer)
        
        # Set new timer for highlighting (500ms delay)
        self.highlight_timer = self.text_editor.after(500, self.apply_highlighting)


class LSXSyntaxHighlighter:
    """Simple syntax highlighting for LSX files"""
    
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.setup_tags()
    
    def setup_tags(self):
        """Configure text tags for different syntax elements"""
        # XML tags
        self.text_widget.tag_config("xml_tag", foreground="#0066CC", font=("Courier", 12, "bold"))
        
        # Attribute names
        self.text_widget.tag_config("attribute_name", foreground="#006600", font=("Courier", 12))
        
        # Attribute values
        self.text_widget.tag_config("attribute_value", foreground="#CC0000", font=("Courier", 12))
        
        # BG3-specific important attributes
        self.text_widget.tag_config("bg3_important", foreground="#9900CC", font=("Courier", 12, "bold"))
        
        # UUIDs
        self.text_widget.tag_config("uuid", foreground="#FF6600", font=("Courier", 12, "bold"))
        
        # Comments
        self.text_widget.tag_config("comment", foreground="#666666", font=("Courier", 12, "italic"))
    
    def highlight_text(self):
        """Apply syntax highlighting to current text"""
        content = self.text_widget.get(1.0, tk.END)
        
        # Clear existing tags
        for tag in ["xml_tag", "attribute_name", "attribute_value", "bg3_important", "uuid", "comment"]:
            self.text_widget.tag_remove(tag, 1.0, tk.END)
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_start = f"{line_num}.0"
            
            # Highlight XML comments
            if '<!--' in line and '-->' in line:
                comment_start = line.find('<!--')
                comment_end = line.find('-->') + 3
                start_pos = f"{line_num}.{comment_start}"
                end_pos = f"{line_num}.{comment_end}"
                self.text_widget.tag_add("comment", start_pos, end_pos)
                continue
            
            # Highlight XML tags
            tag_start = 0
            while True:
                tag_start = line.find('<', tag_start)
                if tag_start == -1:
                    break
                    
                tag_end = line.find('>', tag_start)
                if tag_end == -1:
                    break
                
                start_pos = f"{line_num}.{tag_start}"
                end_pos = f"{line_num}.{tag_end + 1}"
                self.text_widget.tag_add("xml_tag", start_pos, end_pos)
                tag_start = tag_end + 1
            
            # Highlight attribute patterns
            import re
            
            # Attribute names (id="value", type="value", etc.)
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
                    self.text_widget.tag_add("attribute_name", name_start, name_end)
                
                # Attribute value
                value_start = f"{line_num}.{match.start(2)}"
                value_end = f"{line_num}.{match.end(2)}"
                
                # Check if it's a UUID
                uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
                if re.match(uuid_pattern, attr_value):
                    self.text_widget.tag_add("uuid", value_start, value_end)
                else:
                    self.text_widget.tag_add("attribute_value", value_start, value_end)

class FileConversionOperations:
    """Handle LSX/LSF/LOCA conversions"""
    
    def __init__(self, bg3_tool):
        self.bg3_tool = bg3_tool
    
    def convert_lsx_to_lsf_threaded(self, lsx_file, lsf_file=None, progress_callback=None, completion_callback=None):
        """Convert LSX to LSF with progress tracking"""
        
        def conversion_worker():
            try:
                if progress_callback:
                    progress_callback(20, "Starting LSX to LSF conversion...")
                
                if not lsf_file:
                    lsf_file_path = lsx_file.replace('.lsx', '.lsf')
                else:
                    lsf_file_path = lsf_file
                
                if progress_callback:
                    progress_callback(50, "Converting file...")
                
                success, output = self.bg3_tool.run_divine_command(
                    action="convert-resource",
                    source=self.bg3_tool.mac_to_wine_path(lsx_file),
                    destination=self.bg3_tool.mac_to_wine_path(lsf_file_path),
                    input_format="lsx",
                    output_format="lsf"
                )
                
                if progress_callback:
                    progress_callback(100, "Conversion complete!" if success else "Conversion failed")
                
                result_data = {
                    'success': success,
                    'source': lsx_file,
                    'destination': lsf_file_path,
                    'output': output
                }
                
                if completion_callback:
                    completion_callback(result_data)
                
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Error: {e}")
                if completion_callback:
                    completion_callback({
                        'success': False,
                        'error': str(e),
                        'source': lsx_file
                    })
        
        # Start in background thread
        thread = threading.Thread(target=conversion_worker, daemon=True)
        thread.start()
        return thread
    
    def convert_lsf_to_lsx_threaded(self, lsf_file, lsx_file=None, progress_callback=None, completion_callback=None):
        """Convert LSF to LSX with progress tracking"""
        
        def conversion_worker():
            try:
                if progress_callback:
                    progress_callback(20, "Starting LSF to LSX conversion...")
                
                if not lsx_file:
                    lsx_file_path = lsf_file.replace('.lsf', '.lsx')
                else:
                    lsx_file_path = lsx_file
                
                if progress_callback:
                    progress_callback(50, "Converting file...")
                
                success, output = self.bg3_tool.run_divine_command(
                    action="convert-resource",
                    source=self.bg3_tool.mac_to_wine_path(lsf_file),
                    destination=self.bg3_tool.mac_to_wine_path(lsx_file_path),
                    input_format="lsf",
                    output_format="lsx"
                )
                
                if progress_callback:
                    progress_callback(100, "Conversion complete!" if success else "Conversion failed")
                
                result_data = {
                    'success': success,
                    'source': lsf_file,
                    'destination': lsx_file_path,
                    'output': output
                }
                
                if completion_callback:
                    completion_callback(result_data)
                
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Error: {e}")
                if completion_callback:
                    completion_callback({
                        'success': False,
                        'error': str(e),
                        'source': lsf_file
                    })
        
        # Start in background thread
        thread = threading.Thread(target=conversion_worker, daemon=True)
        thread.start()
        return thread
    
    def batch_convert_threaded(self, file_list, conversion_type="lsx_to_lsf", progress_callback=None, completion_callback=None):
        """Batch convert multiple files"""
        
        def batch_worker():
            try:
                total_files = len(file_list)
                results = []
                
                for i, file_path in enumerate(file_list):
                    if progress_callback:
                        percentage = int((i / total_files) * 90)  # Leave 10% for final processing
                        progress_callback(percentage, f"Converting {os.path.basename(file_path)}...")
                    
                    if conversion_type == "lsx_to_lsf":
                        success, output = self.bg3_tool.run_divine_command(
                            action="convert-resource",
                            source=self.bg3_tool.mac_to_wine_path(file_path),
                            destination=self.bg3_tool.mac_to_wine_path(file_path.replace('.lsx', '.lsf')),
                            input_format="lsx",
                            output_format="lsf"
                        )
                    else:  # lsf_to_lsx
                        success, output = self.bg3_tool.run_divine_command(
                            action="convert-resource",
                            source=self.bg3_tool.mac_to_wine_path(file_path),
                            destination=self.bg3_tool.mac_to_wine_path(file_path.replace('.lsf', '.lsx')),
                            input_format="lsf",
                            output_format="lsx"
                        )
                    
                    results.append({
                        'file': file_path,
                        'success': success,
                        'output': output
                    })
                
                if progress_callback:
                    progress_callback(100, "Batch conversion complete!")
                
                if completion_callback:
                    completion_callback({
                        'success': True,
                        'results': results,
                        'total_files': total_files,
                        'successful': len([r for r in results if r['success']]),
                        'failed': len([r for r in results if not r['success']])
                    })
                
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Error: {e}")
                if completion_callback:
                    completion_callback({
                        'success': False,
                        'error': str(e)
                    })
        
        # Start in background thread
        thread = threading.Thread(target=batch_worker, daemon=True)
        thread.start()
        return thread
