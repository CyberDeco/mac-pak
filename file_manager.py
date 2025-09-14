#!/usr/bin/env python3
"""
File Management System for BG3 Mac Toolkit
Recent files, favorites, project workspaces, and advanced file operations
"""

import os

from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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