#!/usr/bin/env python3
"""
Quick Actions tab for BG3 Mac Toolkit
"""

import os

import tkinter as tk
from tkinter import ttk, messagebox

class QuickActionsWidget:
    """Quick action buttons for common modding tasks"""
    
    def __init__(self, parent, project_manager, bg3_tool=None):
        self.parent = parent
        self.project_manager = project_manager
        self.bg3_tool = bg3_tool
        self.setup_widget()
    
    def setup_widget(self):
        """Setup quick actions widget"""
        self.frame = ttk.LabelFrame(self.parent, text="Quick Actions", padding=10)
        
        # Single row of buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill='x')
        
        ttk.Button(button_frame, text="Build PAK", command=self.build_current_project).pack(side='left', padx=2)
        ttk.Button(button_frame, text="Open Project Folder", command=self.open_project_folder).pack(side='left', padx=2)
        ttk.Button(button_frame, text="Generate UUID", command=self.generate_uuid).pack(side='left', padx=2)
        ttk.Button(button_frame, text="New LSX File", command=self.new_lsx_file).pack(side='left', padx=2)
        ttk.Button(button_frame, text="Validate Meta.lsx", command=self.validate_meta).pack(side='left', padx=2)
        
        # Status on the right
        self.status_label = ttk.Label(self.frame, text="Ready")
        self.status_label.pack(side='right', padx=10)
    
    def build_current_project(self):
        """Build PAK for current project"""
        project = self.project_manager.get_current_project()
        if not project:
            messagebox.showwarning("No Project", "Please select a project first")
            return
        
        if not self.bg3_tool:
            messagebox.showerror("Error", "BG3 tool not available")
            return
        
        # Get build settings
        build_settings = project.get("build_settings", {})
        output_path = build_settings.get("output_path", os.path.join(project["path"], "build"))
        
        # Create output filename
        pak_name = f"{project['settings']['mod_name']}.pak"
        pak_file = os.path.join(output_path, pak_name)
        
        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        # Build the PAK
        try:
            success = self.bg3_tool.create_pak(project["path"], pak_file)
            if success:
                messagebox.showinfo("Success", f"PAK created successfully:\n{pak_file}")
                self.status_label.config(text=f"Built: {pak_name}")
            else:
                messagebox.showerror("Error", "Failed to create PAK")
                self.status_label.config(text="Build failed")
        except Exception as e:
            messagebox.showerror("Error", f"Build error: {e}")
            self.status_label.config(text="Build error")
    
    def open_project_folder(self):
        """Open project folder in Finder"""
        project = self.project_manager.get_current_project()
        if not project:
            messagebox.showwarning("No Project", "Please select a project first")
            return
        
        import subprocess
        try:
            subprocess.run(["open", project["path"]])
        except:
            pass
    
    def generate_uuid(self):
        """Generate a new UUID for the project"""
        import uuid
        new_uuid = str(uuid.uuid4())
        
        # Copy to clipboard
        self.parent.clipboard_clear()
        self.parent.clipboard_append(new_uuid)
        self.parent.update()
        
        messagebox.showinfo("UUID Generated", f"New UUID generated and copied to clipboard:\n{new_uuid}")
    
    def new_lsx_file(self):
        """Create a new LSX file template"""
        project = self.project_manager.get_current_project()
        if not project:
            messagebox.showwarning("No Project", "Please select a project first")
            return
        
        # Simple dialog for filename
        import tkinter.simpledialog
        filename = tkinter.simpledialog.askstring("New LSX File", "Enter filename (without .lsx):")
        if not filename:
            return
        
        if not filename.endswith('.lsx'):
            filename += '.lsx'
        
        file_path = os.path.join(project["path"], filename)
        
        # Basic LSX template
        template = '''<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="0" revision="9" build="331"/>
    <region id="Config">
        <node id="root">
            <children>
                <!-- Add your content here -->
            </children>
        </node>
    </region>
</save>'''
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(template)
            
            messagebox.showinfo("Success", f"Created new LSX file:\n{filename}")
            
            # Add to recent files
            self.project_manager.add_recent_file(file_path)
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not create file: {e}")
    
    def validate_meta(self):
        """Validate the project's meta.lsx file"""
        project = self.project_manager.get_current_project()
        if not project:
            messagebox.showwarning("No Project", "Please select a project first")
            return
        
        # Look for meta.lsx
        meta_path = None
        for root, dirs, files in os.walk(project["path"]):
            if "meta.lsx" in files:
                meta_path = os.path.join(root, "meta.lsx")
                break
        
        if not meta_path:
            messagebox.showwarning("Not Found", "meta.lsx file not found in project")
            return
        
        # Basic validation
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(meta_path)
            
            # Check for required elements
            required_attrs = ["Name", "UUID", "Version64", "Author", "Description"]
            found_attrs = []
            
            for attr in tree.findall('.//attribute'):
                attr_id = attr.get('id')
                if attr_id in required_attrs:
                    found_attrs.append(attr_id)
            
            missing = set(required_attrs) - set(found_attrs)
            
            if missing:
                messagebox.showwarning("Validation Issues", f"Missing required attributes:\n{', '.join(missing)}")
            else:
                messagebox.showinfo("Validation Success", "meta.lsx file is valid!")
            
        except ET.ParseError as e:
            messagebox.showerror("Parse Error", f"XML parsing error in meta.lsx:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Validation error: {e}")