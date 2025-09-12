#!/usr/bin/env python3
"""
File Management System for BG3 Mac Toolkit
Recent files, favorites, project workspaces, and advanced file operations
"""

import json
import os
import shutil
import time
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import defaultdict

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

class FileManagerWidget:
    """File manager widget with projects, recent files, and favorites"""
    
    def __init__(self, parent, settings_manager, project_manager):
        self.parent = parent
        self.settings_manager = settings_manager
        self.project_manager = project_manager
        self.setup_widget()
    
    def setup_widget(self):
        """Setup the file manager widget"""
        self.frame = ttk.Frame(self.parent)
        
        # Notebook for different views
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Projects tab
        self.setup_projects_tab()
        
        # Recent files tab
        self.setup_recent_files_tab()
        
        # Favorites tab
        self.setup_favorites_tab()
        
        # File browser tab
        self.setup_browser_tab()
    
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
    
    def new_project_dialog(self):
        """Show new project creation dialog"""
        dialog = ProjectCreationDialog(self.parent, self.project_manager)
        if dialog.result:
            self.refresh_projects_list()
    
    def open_project_dialog(self):
        """Open project selection dialog"""
        directory = filedialog.askdirectory(
            title="Select Project Directory",
            initialdir=self.settings_manager.get("working_directory", os.path.expanduser("~"))
        )
        
        if directory:
            # Check if this is already a project
            project_id = self.find_project_by_path(directory)
            if project_id:
                self.project_manager.set_current_project(project_id)
            else:
                # Create new project from existing directory
                name = os.path.basename(directory)
                success, project_id = self.project_manager.create_project(name, directory, "basic_mod")
                if not success:
                    messagebox.showerror("Error", f"Could not create project: {project_id}")
                    return
            
            self.refresh_projects_list()
            self.refresh_recent_files()
    
    def delete_project(self):
        """Delete selected project"""
        selection = self.projects_tree.selection()
        if not selection:
            return
        
        project_id = selection[0]
        project = self.project_manager.projects["projects"].get(project_id)
        if not project:
            return
        
        result = messagebox.askyesno(
            "Delete Project",
            f"Are you sure you want to delete project '{project['name']}'?\n\nThis will only remove it from the project list, not delete the files."
        )
        
        if result:
            del self.project_manager.projects["projects"][project_id]
            if self.project_manager.current_project == project_id:
                self.project_manager.current_project = None
                self.project_manager.projects["current_project"] = None
            
            self.project_manager.save_projects()
            self.refresh_projects_list()
    
    def find_project_by_path(self, path):
        """Find project by directory path"""
        for project_id, project in self.project_manager.projects["projects"].items():
            if os.path.samefile(project["path"], path):
                return project_id
        return None
    
    def refresh_projects_list(self):
        """Refresh the projects list"""
        # Clear existing items
        for item in self.projects_tree.get_children():
            self.projects_tree.delete(item)
        
        # Add projects
        for project_id, project in self.project_manager.projects["projects"].items():
            last_opened = project.get("last_opened", "Never")
            if last_opened != "Never":
                try:
                    dt = datetime.fromisoformat(last_opened)
                    last_opened = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
            
            # Mark current project
            name = project["name"]
            if project_id == self.project_manager.current_project:
                name += " (Current)"
            
            self.projects_tree.insert(
                "", "end", project_id,
                text=name,
                values=(project["name"], project["path"], last_opened)
            )
    
    def on_project_double_click(self, event):
        """Handle project double-click"""
        selection = self.projects_tree.selection()
        if selection:
            project_id = selection[0]
            self.project_manager.set_current_project(project_id)
            self.refresh_projects_list()
            self.refresh_recent_files()
            
            # Switch to project directory
            project = self.project_manager.get_current_project()
            if project:
                self.path_var.set(project["path"])
                self.refresh_browser()
    
    def refresh_recent_files(self):
        """Refresh recent files list"""
        self.recent_listbox.delete(0, tk.END)
        
        project = self.project_manager.get_current_project()
        if not project:
            self.recent_listbox.insert(0, "No project selected")
            return
        
        recent_files = project.get("recent_files", [])
        if not recent_files:
            self.recent_listbox.insert(0, "No recent files")
            return
        
        for file_info in recent_files:
            file_path = file_info["path"]
            file_name = os.path.basename(file_path)
            
            # Show relative path if in project
            if file_path.startswith(project["path"]):
                rel_path = os.path.relpath(file_path, project["path"])
                display_name = f"{file_name} ({rel_path})"
            else:
                display_name = f"{file_name} ({file_path})"
            
            self.recent_listbox.insert(tk.END, display_name)
    
    def refresh_favorites(self):
        """Refresh favorites list"""
        self.favorites_listbox.delete(0, tk.END)
        
        project = self.project_manager.get_current_project()
        if not project:
            self.favorites_listbox.insert(0, "No project selected")
            return
        
        favorites = project.get("favorites", [])
        if not favorites:
            self.favorites_listbox.insert(0, "No favorites")
            return
        
        for file_path in favorites:
            file_name = os.path.basename(file_path)
            
            # Show relative path if in project
            if file_path.startswith(project["path"]):
                rel_path = os.path.relpath(file_path, project["path"])
                display_name = f"{file_name} ({rel_path})"
            else:
                display_name = f"{file_name} ({file_path})"
            
            self.favorites_listbox.insert(tk.END, display_name)
    
    def refresh_browser(self):
        """Refresh the file browser"""
        current_path = self.path_var.get()
        
        if not os.path.exists(current_path):
            return
        
        # Clear existing items
        for item in self.browser_tree.get_children():
            self.browser_tree.delete(item)
        
        try:
            # Add parent directory link if not at root
            if current_path != "/" and os.path.dirname(current_path) != current_path:
                self.browser_tree.insert("", "end", text="..", values=("", "", "Directory"))
            
            # Add directories first
            items = []
            for item in os.listdir(current_path):
                if item.startswith('.'):
                    continue
                
                item_path = os.path.join(current_path, item)
                
                try:
                    stat = os.stat(item_path)
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    
                    if os.path.isdir(item_path):
                        items.append((item, "", modified, "Directory", True))
                    else:
                        size = self.format_file_size(stat.st_size)
                        ext = os.path.splitext(item)[1].lower()
                        file_type = ext[1:] if ext else "File"
                        items.append((item, size, modified, file_type, False))
                        
                except (OSError, PermissionError):
                    items.append((item, "N/A", "N/A", "Unknown", False))
            
            # Sort: directories first, then by name
            items.sort(key=lambda x: (not x[4], x[0].lower()))
            
            for item_name, size, modified, file_type, is_dir in items:
                icon = "📁" if is_dir else self.get_file_icon(item_name)
                self.browser_tree.insert(
                    "", "end", 
                    text=f"{icon} {item_name}",
                    values=(size, modified, file_type)
                )
        
        except PermissionError:
            self.browser_tree.insert("", "end", text="Permission Denied", values=("", "", ""))
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def get_file_icon(self, filename):
        """Get file icon based on extension"""
        ext = os.path.splitext(filename)[1].lower()
        icons = {
            '.lsx': '📄', '.lsf': '🔒', '.xml': '📄', '.txt': '📝',
            '.dds': '🖼️', '.gr2': '🎭', '.json': '📋', '.py': '🐍',
            '.pak': '📦', '.zip': '📦', '.exe': '⚙️'
        }
        return icons.get(ext, '📄')
    
    def navigate_to_path(self):
        """Navigate to the path in the entry"""
        path = self.path_var.get()
        if os.path.exists(path) and os.path.isdir(path):
            self.settings_manager.set("working_directory", path)
            self.refresh_browser()
    
    def go_up_directory(self):
        """Go up one directory"""
        current_path = self.path_var.get()
        parent_path = os.path.dirname(current_path)
        if parent_path != current_path:
            self.path_var.set(parent_path)
            self.refresh_browser()
    
    def go_home(self):
        """Go to home directory"""
        home_path = os.path.expanduser("~")
        self.path_var.set(home_path)
        self.refresh_browser()
    
    def go_project_root(self):
        """Go to current project root"""
        project = self.project_manager.get_current_project()
        if project:
            self.path_var.set(project["path"])
            self.refresh_browser()
    
    def on_browser_double_click(self, event):
        """Handle browser double-click"""
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
            self.go_up_directory()
            return
        
        current_path = self.path_var.get()
        full_path = os.path.join(current_path, item_name)
        
        if os.path.isdir(full_path):
            self.path_var.set(full_path)
            self.refresh_browser()
        else:
            # Open file - this would integrate with your LSX editor
            self.open_file(full_path)
    
    def open_file(self, file_path):
        """Open a file (placeholder for integration with LSX editor)"""
        print(f"Would open file: {file_path}")
        # Add to recent files
        self.project_manager.add_recent_file(file_path)
        self.refresh_recent_files()
    
    # Context menu handlers
    def show_recent_context_menu(self, event):
        """Show context menu for recent files"""
        self.recent_context_menu.post(event.x_root, event.y_root)
    
    def show_favorites_context_menu(self, event):
        """Show context menu for favorites"""
        self.favorites_context_menu.post(event.x_root, event.y_root)
    
    def show_browser_context_menu(self, event):
        """Show context menu for browser"""
        self.browser_context_menu.post(event.x_root, event.y_root)

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
        
        self.recent_listbox.bind('<Button-2>', self.show_recent_context_menu)
        
        self.refresh_recent_files()

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

    def show_recent_context_menu(self, event):
        """Show context menu for recent files"""
        try:
            self.recent_context_menu.post(event.x_root, event.y_root)
        except:
            pass
    
    def show_favorites_context_menu(self, event):
        """Show context menu for favorites"""
        try:
            self.favorites_context_menu.post(event.x_root, event.y_root)
        except:
            pass
    
    def show_recent_in_finder(self):
        """Show recent file in Finder - placeholder"""
        messagebox.showinfo("Feature", "Show in Finder - Coming soon")
    
    def add_recent_to_favorites(self):
        """Add recent to favorites - placeholder"""
        messagebox.showinfo("Feature", "Add to Favorites - Coming soon")
    
    def remove_from_favorites(self):
        """Remove from favorites - placeholder"""
        messagebox.showinfo("Feature", "Remove from Favorites - Coming soon")
    
    def show_favorite_in_finder(self):
        """Show favorite in Finder - placeholder"""
        messagebox.showinfo("Feature", "Show in Finder - Coming soon")
    
    def open_file(self, file_path):
        """Open a file - placeholder"""
        messagebox.showinfo("File Open", f"Would open: {os.path.basename(file_path)}")
    
    def refresh_recent_files(self):
        """Refresh recent files list"""
        self.recent_listbox.delete(0, tk.END)
        self.recent_listbox.insert(0, "No recent files")
    
    def refresh_favorites(self):
        """Refresh favorites list"""
        self.favorites_listbox.delete(0, tk.END)  
        self.favorites_listbox.insert(0, "No favorites")

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
        
        # Initialize to current working directory
        current_dir = self.settings_manager.get("working_directory", os.path.expanduser("~"))
        self.path_var.set(current_dir)

    def navigate_to_path(self):
        """Navigate to path - placeholder"""
        messagebox.showinfo("Feature", "Navigate to path - Coming soon")
    
    def go_up_directory(self):
        """Go up directory - placeholder"""
        messagebox.showinfo("Feature", "Go up directory - Coming soon")
    
    def go_home(self):
        """Go home - placeholder"""
        messagebox.showinfo("Feature", "Go home - Coming soon")
    
    def go_project_root(self):
        """Go to project root - placeholder"""
        messagebox.showinfo("Feature", "Go to project root - Coming soon")
    
    def refresh_browser(self):
        """Refresh browser - placeholder"""
        messagebox.showinfo("Feature", "Refresh browser - Coming soon")

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