#!/usr/bin/env python3
"""
Projects Manager for BG3 Mac Toolkit
Recent files, favorites, project workspaces, and advanced file operations
"""

import json
import os
import time

from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class ProjectManager:
    """Manage BG3 modding projects with workspace support"""
    
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.projects_file = os.path.expanduser("~/.bg3_toolkit_projects.json")
        self.projects = self.load_projects()
        self.current_project = None
    
    def load_projects(self):
        """Load saved projects"""
        default_projects = {
            "projects": {},
            "current_project": None,
            "project_templates": self._get_default_templates()
        }
        
        try:
            if os.path.exists(self.projects_file):
                with open(self.projects_file, 'r') as f:
                    loaded = json.load(f)
                    default_projects.update(loaded)
        except Exception as e:
            print(f"Could not load projects: {e}")
        
        return default_projects
    
    def save_projects(self):
        """Save projects to file"""
        try:
            with open(self.projects_file, 'w') as f:
                json.dump(self.projects, f, indent=2)
        except Exception as e:
            print(f"Could not save projects: {e}")
    
    def create_project(self, name, path, template="basic_mod"):
        """Create a new modding project"""
        project_id = f"project_{int(time.time())}"
        
        project_data = {
            "name": name,
            "path": path,
            "template": template,
            "created": datetime.now().isoformat(),
            "last_opened": datetime.now().isoformat(),
            "settings": {
                "mod_name": name,
                "author": "",
                "version": "1.0.0",
                "description": "",
                "uuid": self._generate_uuid()
            },
            "recent_files": [],
            "favorites": [],
            "build_settings": {
                "output_path": os.path.join(path, "build"),
                "exclude_patterns": [".git", ".DS_Store", "*.tmp"]
            }
        }
        
        # Create project directory structure
        try:
            self._create_project_structure(path, template)
            
            self.projects["projects"][project_id] = project_data
            self.projects["current_project"] = project_id
            self.current_project = project_id
            self.save_projects()
            
            return True, project_id
            
        except Exception as e:
            return False, str(e)
    
    def _create_project_structure(self, path, template):
        """Create project directory structure based on template"""
        os.makedirs(path, exist_ok=True)
        
        template_data = self.projects["project_templates"].get(template, {})
        
        # Create directories
        for dir_path in template_data.get("directories", []):
            full_path = os.path.join(path, dir_path)
            os.makedirs(full_path, exist_ok=True)
        
        # Create files
        for file_info in template_data.get("files", []):
            file_path = os.path.join(path, file_info["path"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_info.get("content", ""))
    
    def _get_default_templates(self):
        """Get default project templates"""
        return {
            "basic_mod": {
                "name": "Basic Mod",
                "description": "Basic mod structure with meta.lsx",
                "directories": [
                    "Mods/ModName",
                    "Public/ModName/GUI",
                    "Public/ModName/Content",
                    "build"
                ],
                "files": [
                    {
                        "path": "Mods/ModName/meta.lsx",
                        "content": self._get_meta_template()
                    },
                    {
                        "path": "README.md",
                        "content": "# New BG3 Mod\n\nDescription of your mod goes here.\n"
                    }
                ]
            },
            "script_mod": {
                "name": "Script Mod",
                "description": "Mod with Osiris scripts",
                "directories": [
                    "Mods/ModName",
                    "Mods/ModName/Story/RawFiles/Goals",
                    "Public/ModName/Content",
                    "build"
                ],
                "files": [
                    {
                        "path": "Mods/ModName/meta.lsx",
                        "content": self._get_meta_template()
                    },
                    {
                        "path": "Mods/ModName/Story/RawFiles/Goals/ModName.txt",
                        "content": "// Osiris script for ModName\n\n"
                    }
                ]
            },
            "item_mod": {
                "name": "Item Mod",
                "description": "Mod that adds new items",
                "directories": [
                    "Mods/ModName",
                    "Public/ModName/Stats/Generated/Data",
                    "Public/ModName/Content/Assets",
                    "build"
                ],
                "files": [
                    {
                        "path": "Mods/ModName/meta.lsx",
                        "content": self._get_meta_template()
                    },
                    {
                        "path": "Public/ModName/Stats/Generated/Data/Armor.txt",
                        "content": "// New armor definitions\n\n"
                    }
                ]
            }
        }
    
    def _get_meta_template(self):
        """Get meta.lsx template"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="0" revision="9" build="331"/>
    <region id="Config">
        <node id="root">
            <children>
                <node id="Dependencies"/>
                <node id="ModuleInfo">
                    <attribute id="Author" type="LSString" value=""/>
                    <attribute id="CharacterCreationLevelName" type="FixedString" value=""/>
                    <attribute id="Description" type="LSString" value=""/>
                    <attribute id="Folder" type="LSString" value="ModName"/>
                    <attribute id="LobbyLevelName" type="FixedString" value=""/>
                    <attribute id="MD5" type="LSString" value=""/>
                    <attribute id="MainMenuBackgroundVideo" type="FixedString" value=""/>
                    <attribute id="MenuLevelName" type="FixedString" value=""/>
                    <attribute id="Name" type="LSString" value="ModName"/>
                    <attribute id="NumPlayers" type="uint8" value="4"/>
                    <attribute id="PhotoBooth" type="FixedString" value=""/>
                    <attribute id="StartupLevelName" type="FixedString" value=""/>
                    <attribute id="Tags" type="LSString" value=""/>
                    <attribute id="Type" type="FixedString" value="Add-on"/>
                    <attribute id="UUID" type="FixedString" value="GENERATE_UUID"/>
                    <attribute id="Version64" type="int64" value="36028797018963968"/>
                </node>
            </children>
        </node>
    </region>
</save>'''
    
    def _generate_uuid(self):
        """Generate a UUID for mod"""
        import uuid
        return str(uuid.uuid4())
    
    def get_current_project(self):
        """Get current project data"""
        if self.current_project and self.current_project in self.projects["projects"]:
            return self.projects["projects"][self.current_project]
        return None
    
    def set_current_project(self, project_id):
        """Set the current active project"""
        if project_id in self.projects["projects"]:
            self.current_project = project_id
            self.projects["current_project"] = project_id
            
            # Update last opened
            self.projects["projects"][project_id]["last_opened"] = datetime.now().isoformat()
            self.save_projects()
            return True
        return False
    
    def add_recent_file(self, file_path):
        """Add file to recent files for current project"""
        if not self.current_project:
            return
        
        project = self.projects["projects"][self.current_project]
        recent = project.get("recent_files", [])
        
        # Remove if already exists
        recent = [f for f in recent if f["path"] != file_path]
        
        # Add to front
        recent.insert(0, {
            "path": file_path,
            "accessed": datetime.now().isoformat()
        })
        
        # Keep only last 20
        project["recent_files"] = recent[:20]
        self.save_projects()
    
    def add_favorite(self, file_path):
        """Add file to favorites for current project"""
        if not self.current_project:
            return
        
        project = self.projects["projects"][self.current_project]
        favorites = project.get("favorites", [])
        
        if file_path not in favorites:
            favorites.append(file_path)
            project["favorites"] = favorites
            self.save_projects()


class ProjectCreationDialog:
    """Dialog for creating new projects"""
    
    def __init__(self, parent, project_manager):
        self.parent = parent
        self.project_manager = project_manager
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("New Project")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_dialog()
        self.dialog.wait_window()
    
    def setup_dialog(self):
        """Setup the project creation dialog"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Project name
        ttk.Label(main_frame, text="Project Name:").grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=40)
        name_entry.grid(row=0, column=1, sticky='ew', pady=(0, 5))
        
        # Project path
        ttk.Label(main_frame, text="Project Path:").grid(row=1, column=0, sticky='w', pady=(0, 5))
        
        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=1, column=1, sticky='ew', pady=(0, 5))
        
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        path_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(path_frame, text="Browse", command=self.browse_path).pack(side='right', padx=(5, 0))
        
        # Project template
        ttk.Label(main_frame, text="Template:").grid(row=2, column=0, sticky='nw', pady=(0, 5))
        
        template_frame = ttk.Frame(main_frame)
        template_frame.grid(row=2, column=1, sticky='ew', pady=(0, 5))
        
        self.template_var = tk.StringVar(value="basic_mod")
        
        templates = self.project_manager.projects["project_templates"]
        for template_id, template_info in templates.items():
            rb = ttk.Radiobutton(
                template_frame, 
                text=template_info["name"], 
                variable=self.template_var,
                value=template_id
            )
            rb.pack(anchor='w')
            
            # Description
            desc_label = ttk.Label(template_frame, text=f"  {template_info['description']}", foreground='gray')
            desc_label.pack(anchor='w')
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Create", command=self.create_project).pack(side='right')
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        
        # Focus name entry
        name_entry.focus_set()
    
    def browse_path(self):
        """Browse for project directory"""
        directory = filedialog.askdirectory(title="Select Project Directory")
        if directory:
            self.path_var.set(directory)
            
            # Auto-fill name if empty
            if not self.name_var.get():
                self.name_var.set(os.path.basename(directory))
    
    def create_project(self):
        """Create the project"""
        name = self.name_var.get().strip()
        path = self.path_var.get().strip()
        template = self.template_var.get()
        
        if not name:
            messagebox.showerror("Error", "Please enter a project name")
            return
        
        if not path:
            messagebox.showerror("Error", "Please select a project path")
            return
        
        # Create full project path
        project_path = os.path.join(path, name)
        
        success, result = self.project_manager.create_project(name, project_path, template)
        
        if success:
            self.result = result
            messagebox.showinfo("Success", f"Project '{name}' created successfully!")
            self.dialog.destroy()
        else:
            messagebox.showerror("Error", f"Could not create project: {result}")
    
    def cancel(self):
        """Cancel project creation"""
        self.dialog.destroy()
    
    def setup_recent_files_tab(self):
        """Setup recent files tab"""
        recent_frame = ttk.Frame(self.notebook)
        self.notebook.add(recent_frame, text="Recent Files")
        
        # Recent files list
        self.recent_listbox = tk.Listbox(recent_frame)
        self.recent_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Bind double-click to open file
        self.recent_listbox.bind('<Double-1>', self.on_recent_file_double_click)
        
        # Context menu
        self.recent_context_menu = tk.Menu(self.recent_listbox, tearoff=0)
        self.recent_context_menu.add_command(label="Open", command=self.open_selected_recent)
        self.recent_context_menu.add_command(label="Show in Finder", command=self.show_recent_in_finder)
        self.recent_context_menu.add_command(label="Add to Favorites", command=self.add_recent_to_favorites)
        
        self.recent_listbox.bind('<Button-2>', self.show_recent_context_menu)  # Right-click
        
        self.refresh_recent_files()

    # Complete the setup_projects_tab method (replace the broken one)
    def setup_projects_tab(self):
        """Setup projects management tab"""
        projects_frame = ttk.Frame(self.notebook)
        self.notebook.add(projects_frame, text="Projects")

        # Toolbar
        toolbar = ttk.Frame(projects_frame)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(toolbar, text="New Project", command=self.new_project_dialog).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Open Project", command=self.open_project_dialog).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Delete Project", command=self.delete_project).pack(side='left', padx=2)
        
        # Projects list
        list_frame = ttk.Frame(projects_frame)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create treeview for projects
        columns = ("name", "path", "last_opened")
        self.projects_tree = ttk.Treeview(list_frame, columns=columns, show='tree headings')
        
        # Configure columns
        self.projects_tree.heading("#0", text="Project")
        self.projects_tree.heading("name", text="Name")
        self.projects_tree.heading("path", text="Path")
        self.projects_tree.heading("last_opened", text="Last Opened")
        
        self.projects_tree.column("#0", width=200)
        self.projects_tree.column("name", width=150)
        self.projects_tree.column("path", width=300)
        self.projects_tree.column("last_opened", width=150)
        
        self.projects_tree.pack(fill='both', expand=True)
        
        # Bind double-click to open project
        self.projects_tree.bind('<Double-1>', self.on_project_double_click)
        
        # Refresh projects list
        self.refresh_projects_list()
    
    # Complete the setup_browser_tab method
    def setup_browser_tab(self):
        """Setup file browser tab"""
        browser_frame = ttk.Frame(self.notebook)
        self.notebook.add(browser_frame, text="Browse")
        
        # Path bar
        path_frame = ttk.Frame(browser_frame)
        path_frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(path_frame, text="Path:").pack(side='left')
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        path_entry.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(path_frame, text="Go", command=self.navigate_to_path).pack(side='right')
        
        # Toolbar
        toolbar = ttk.Frame(browser_frame)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(toolbar, text="Up", command=self.go_up_directory).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Home", command=self.go_home).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Project Root", command=self.go_project_root).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Refresh", command=self.refresh_browser).pack(side='left', padx=2)
        
        # File list
        browser_list_frame = ttk.Frame(browser_frame)
        browser_list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create treeview for files
        browser_columns = ("size", "modified", "type")
        self.browser_tree = ttk.Treeview(browser_list_frame, columns=browser_columns, show='tree headings')
        
        self.browser_tree.heading("#0", text="Name")
        self.browser_tree.heading("size", text="Size")
        self.browser_tree.heading("modified", text="Modified")
        self.browser_tree.heading("type", text="Type")
        
        self.browser_tree.column("#0", width=300)
        self.browser_tree.column("size", width=100)
        self.browser_tree.column("modified", width=150)
        self.browser_tree.column("type", width=100)
        
        self.browser_tree.pack(fill='both', expand=True)
        
        # Browser context menu
        self.browser_context_menu = tk.Menu(self.browser_tree, tearoff=0)
        self.browser_context_menu.add_command(label="Open", command=self.open_selected_browser_item)
        self.browser_context_menu.add_command(label="Add to Favorites", command=self.add_browser_to_favorites)
        self.browser_context_menu.add_separator()
        self.browser_context_menu.add_command(label="Show in Finder", command=self.show_browser_in_finder)
        self.browser_context_menu.add_command(label="Copy Path", command=self.copy_browser_path)
        
        self.browser_tree.bind('<Button-2>', self.show_browser_context_menu)
        self.browser_tree.bind('<Double-1>', self.on_browser_double_click)
        
        # Initialize to current working directory
        current_dir = self.settings_manager.get("working_directory", os.path.expanduser("~"))
        self.path_var.set(current_dir)
        self.refresh_browser()
    
    # Add all the missing event handler methods
    def on_recent_file_double_click(self, event):
        """Handle recent file double-click"""
        selection = self.recent_listbox.curselection()
        if selection:
            self.open_selected_recent()
    
    def on_favorite_double_click(self, event):
        """Handle favorite double-click"""
        selection = self.favorites_listbox.curselection()
        if selection:
            self.open_selected_favorite()
    
    def open_selected_recent(self):
        """Open selected recent file"""
        selection = self.recent_listbox.curselection()
        if not selection:
            return
        
        project = self.project_manager.get_current_project()
        if not project:
            return
        
        index = selection[0]
        recent_files = project.get("recent_files", [])
        if index < len(recent_files):
            file_path = recent_files[index]["path"]
            self.open_file(file_path)
    
    def open_selected_favorite(self):
        """Open selected favorite file"""
        selection = self.favorites_listbox.curselection()
        if not selection:
            return
        
        project = self.project_manager.get_current_project()
        if not project:
            return
        
        index = selection[0]
        favorites = project.get("favorites", [])
        if index < len(favorites):
            file_path = favorites[index]
            self.open_file(file_path)
    
    def open_selected_browser_item(self):
        """Open selected browser item"""
        selection = self.browser_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_text = self.browser_tree.item(item)['text']
        
        # Remove icon from name
        if ' ' in item_text:
            item_name = item_text.split(' ', 1)[1]
        else:
            item_name = item_text
        
        if item_name == "..":
            return
        
        current_path = self.path_var.get()
        full_path = os.path.join(current_path, item_name)
        
        if os.path.isfile(full_path):
            self.open_file(full_path)
    
    # Add other missing methods for context menus, file operations, etc.
    def show_recent_in_finder(self):
        """Show recent file in Finder"""
        selection = self.recent_listbox.curselection()
        if not selection:
            return
        
        project = self.project_manager.get_current_project()
        if not project:
            return
        
        index = selection[0]
        recent_files = project.get("recent_files", [])
        if index < len(recent_files):
            file_path = recent_files[index]["path"]
            self.show_in_finder(file_path)
    
    def show_in_finder(self, path):
        """Show file or directory in Finder (macOS)"""
        import subprocess
        try:
            subprocess.run(["open", "-R", path])
        except:
            pass
    
    def add_recent_to_favorites(self):
        """Add recent file to favorites"""
        selection = self.recent_listbox.curselection()
        if not selection:
            return
        
        project = self.project_manager.get_current_project()
        if not project:
            return
        
        index = selection[0]
        recent_files = project.get("recent_files", [])
        if index < len(recent_files):
            file_path = recent_files[index]["path"]
            self.project_manager.add_favorite(file_path)
            self.refresh_favorites()
    
    def remove_from_favorites(self):
        """Remove item from favorites"""
        selection = self.favorites_listbox.curselection()
        if not selection:
            return
        
        project = self.project_manager.get_current_project()
        if not project:
            return
        
        index = selection[0]
        favorites = project.get("favorites", [])
        if index < len(favorites):
            file_path = favorites[index]
            favorites.remove(file_path)
            project["favorites"] = favorites
            self.project_manager.save_projects()
            self.refresh_favorites()
    
    def show_favorite_in_finder(self):
        """Show favorite file in Finder"""
        selection = self.favorites_listbox.curselection()
        if not selection:
            return
        
        project = self.project_manager.get_current_project()
        if not project:
            return
        
        index = selection[0]
        favorites = project.get("favorites", [])
        if index < len(favorites):
            file_path = favorites[index]
            self.show_in_finder(file_path)
    
    def show_browser_in_finder(self):
        """Show browser item in Finder"""
        selection = self.browser_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_text = self.browser_tree.item(item)['text']
        
        if ' ' in item_text:
            item_name = item_text.split(' ', 1)[1]
        else:
            item_name = item_text
        
        current_path = self.path_var.get()
        full_path = os.path.join(current_path, item_name)
        self.show_in_finder(full_path)
    
    def add_browser_to_favorites(self):
        """Add browser item to favorites"""
        selection = self.browser_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_text = self.browser_tree.item(item)['text']
        
        if ' ' in item_text:
            item_name = item_text.split(' ', 1)[1]
        else:
            item_name = item_text
        
        current_path = self.path_var.get()
        full_path = os.path.join(current_path, item_name)
        
        if os.path.isfile(full_path):
            self.project_manager.add_favorite(full_path)
            self.refresh_favorites()
    
    def copy_browser_path(self):
        """Copy browser item path to clipboard"""
        selection = self.browser_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_text = self.browser_tree.item(item)['text']
        
        if ' ' in item_text:
            item_name = item_text.split(' ', 1)[1]
        else:
            item_name = item_text
        
        current_path = self.path_var.get()
        full_path = os.path.join(current_path, item_name)
        
        # Copy to clipboard
        self.parent.clipboard_clear()
        self.parent.clipboard_append(full_path)
        self.parent.update()
    
    def setup_favorites_tab(self):
        """Setup favorites tab"""
        favorites_frame = ttk.Frame(self.notebook)
        self.notebook.add(favorites_frame, text="Favorites")
        
        # Favorites list
        self.favorites_listbox = tk.Listbox(favorites_frame)
        self.favorites_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Bind double-click to open file
        self.favorites_listbox.bind('<Double-1>', self.on_favorite_double_click)
        
        # Context menu
        self.favorites_context_menu = tk.Menu(self.favorites_listbox, tearoff=0)
        self.favorites_context_menu.add_command(label="Open", command=self.open_selected_favorite)
        self.favorites_context_menu.add_command(label="Show in Finder", command=self.show_favorite_in_finder)
        self.favorites_context_menu.add_command(label="Remove from Favorites", command=self.remove_from_favorites)
        
        self.favorites_listbox.bind('<Button-2>', self.show_favorites_context_menu)
        
        self.refresh_favorites()