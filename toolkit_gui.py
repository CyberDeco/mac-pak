from lsx_tools import *

import json
import threading
import time
from tkinter import scrolledtext
from file_manager import *

class ResponsiveButton:
    """Wrapper to make buttons more responsive and prevent double-clicks"""
    
    def __init__(self, parent, text, command, **kwargs):
        self.command = command
        self.button = ttk.Button(parent, text=text, command=self.handle_click, **kwargs)
        self.last_click_time = 0
        self.click_delay = 0.1  # Minimum time between clicks
    
    def handle_click(self):
        """Handle button click with debouncing"""
        import time
        current_time = time.time()
        
        if current_time - self.last_click_time < self.click_delay:
            return  # Ignore rapid clicks
        
        self.last_click_time = current_time
        
        # Temporarily disable button to prevent double-clicks
        self.button.config(state='disabled')
        
        try:
            # Execute the command
            if callable(self.command):
                self.command()
        except Exception as e:
            print(f"Button command error: {e}")
        finally:
            # Re-enable button after a short delay
            self.button.after(50, lambda: self.button.config(state='normal'))
    
    def pack(self, **kwargs):
        return self.button.pack(**kwargs)
    
    def grid(self, **kwargs):
        return self.button.grid(**kwargs)

class AssetBrowser:
    """Phase 3: Browse extracted PAK contents and preview LSX files"""
    
    def __init__(self, parent=None, bg3_tool=None, settings_manager=None):  # Add settings_manager here
        self.bg3_tool = bg3_tool
        self.settings_manager = settings_manager
        self.parser = LSXParser()
        self.current_directory = None
        
        if parent:
            self.setup_browser_tab(parent)
    
    def browse_folder(self):
        """Browse for extracted PAK folder"""
        initial_dir = "/"
        if self.settings_manager:
            initial_dir = self.settings_manager.get("working_directory", "/")
        
        folder_path = filedialog.askdirectory(
            title="Select Extracted PAK Folder",
            initialdir=initial_dir
        )
        
        if folder_path:
            self.current_directory = folder_path
            
            # Update working directory
            if self.settings_manager:
                self.settings_manager.set("working_directory", folder_path)
                
            self.refresh_view()
    
    def setup_browser_tab(self, parent):
        """Setup the asset browser interface"""
        browser_frame = ttk.Frame(parent)
        
        # Top toolbar
        toolbar = ttk.Frame(browser_frame)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(toolbar, text="Browse Folder", command=self.browse_folder).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Refresh", command=self.refresh_view).pack(side='left', padx=2)
        
        # Search
        ttk.Label(toolbar, text="Filter:").pack(side='left', padx=(10,2))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_files)
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=20)
        search_entry.pack(side='left', padx=2)
        
        # Main layout - split pane
        main_pane = ttk.PanedWindow(browser_frame, orient='horizontal')
        main_pane.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left: File tree
        tree_frame = ttk.Frame(main_pane)
        main_pane.add(tree_frame, weight=1)
        
        ttk.Label(tree_frame, text="Files").pack(anchor='w')
        
        self.file_tree = ttk.Treeview(tree_frame, selectmode='browse')
        self.file_tree.heading('#0', text='File Name')
        self.file_tree.pack(fill='both', expand=True)

        # Add this binding for tree expansion
        self.file_tree.bind('<<TreeviewOpen>>', self.on_tree_expand)
        
        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.file_tree.yview)
        tree_scroll.pack(side='right', fill='y')
        self.file_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Bind selection
        self.file_tree.bind('<<TreeviewSelect>>', self.on_file_select)
        
        # Right: Preview pane
        preview_frame = ttk.Frame(main_pane)
        main_pane.add(preview_frame, weight=2)
        
        ttk.Label(preview_frame, text="Preview").pack(anchor='w')
        
        self.preview_text = scrolledtext.ScrolledText(
            preview_frame,
            font=('Courier', 10),
            state='disabled'
        )
        self.preview_text.pack(fill='both', expand=True)

        # Auto-load working directory at startup
        if self.settings_manager:
            working_dir = self.settings_manager.get("working_directory")
            if working_dir and os.path.exists(working_dir):
                self.current_directory = working_dir
                self.refresh_view()
        
        return browser_frame
    
    def refresh_view(self):
        """Refresh the file tree view"""
        if not self.current_directory:
            return
        
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Populate tree
        self.populate_tree(self.current_directory, '')

    def on_tree_expand(self, event):
        """Handle expanding tree nodes"""
        item = self.file_tree.selection()[0] if self.file_tree.selection() else None
        if not item:
            item = self.file_tree.focus()
        
        if item:
            # Check if this item has the "Loading..." placeholder
            children = self.file_tree.get_children(item)
            if children and self.file_tree.item(children[0])['text'] == "Loading...":
                # Remove the placeholder
                self.file_tree.delete(children[0])
                
                # Get the directory path for this item
                values = self.file_tree.item(item)['values']
                if values and os.path.isdir(values[0]):
                    # Populate the actual contents
                    self.populate_tree(values[0], item)
    
    def populate_tree(self, directory, parent):
        """Recursively populate the file tree"""
        try:
            items = []
            for item in os.listdir(directory):
                if item.startswith('.'):  # Skip hidden files
                    continue
                    
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    # Add folder
                    folder_id = self.file_tree.insert(parent, 'end', text=f"📁 {item}", 
                                                    values=(item_path,), tags=('folder',))
                    
                    # Check if this folder has contents to decide if it should be expandable
                    try:
                        if any(not f.startswith('.') for f in os.listdir(item_path)):
                            # Add placeholder to make it expandable
                            self.file_tree.insert(folder_id, 'end', text="Loading...")
                    except (PermissionError, OSError):
                        pass  # No placeholder if we can't read the directory
                else:
                    # Add file with appropriate icon
                    icon = self.get_file_icon(item)
                    self.file_tree.insert(parent, 'end', text=f"{icon} {item}", 
                                        values=(item_path,), tags=('file',))
            
        except PermissionError:
            self.file_tree.insert(parent, 'end', text="❌ Permission Denied")
    
    # def populate_tree(self, directory, parent):
    #     """Recursively populate the file tree"""
    #     try:
    #         items = []
    #         for item in os.listdir(directory):
    #             item_path = os.path.join(directory, item)
    #             if os.path.isdir(item_path):
    #                 # Add folder
    #                 folder_id = self.file_tree.insert(parent, 'end', text=f"📁 {item}", 
    #                                                 values=(item_path,), tags=('folder',))
    #                 # Add placeholder to make it expandable
    #                 self.file_tree.insert(folder_id, 'end', text="Loading...")
    #             else:
    #                 # Add file with appropriate icon
    #                 icon = self.get_file_icon(item)
    #                 self.file_tree.insert(parent, 'end', text=f"{icon} {item}", 
    #                                     values=(item_path,), tags=('file',))
            
    #     except PermissionError:
    #         self.file_tree.insert(parent, 'end', text="❌ Permission Denied")
    
    def get_file_icon(self, filename):
        """Get appropriate icon for file type"""
        ext = os.path.splitext(filename)[1].lower()
        
        icons = {
            '.lsx': '📄',
            '.lsf': '🔒',
            '.xml': '📄',
            '.txt': '📝',
            '.dds': '🖼️',
            '.gr2': '🎭',
            '.json': '📋'
        }
        
        return icons.get(ext, '📄')
    
    def filter_files(self, *args):
        """Filter files based on search term"""
        # Simple implementation - would need enhancement for real filtering
        pass
    
    def on_file_select(self, event):
        """Handle file selection"""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.file_tree.item(item)['values']
        
        if values:
            file_path = values[0]
            if os.path.isfile(file_path):
                self.preview_file(file_path)
    
    def preview_file(self, file_path):
        """Preview selected file"""
        self.preview_text.config(state='normal')
        self.preview_text.delete(1.0, tk.END)
        
        try:
            # Get file info
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            preview_content = f"File: {os.path.basename(file_path)}\n"
            preview_content += f"Size: {file_size:,} bytes\n"
            preview_content += f"Type: {file_ext}\n"
            preview_content += "-" * 50 + "\n\n"
            
            if file_ext in ['.lsx', '.xml', '.txt', '.json']:
                # Text-based files
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(2000)  # First 2KB
                    preview_content += content
                    if file_size > 2000:
                        preview_content += f"\n\n... ({file_size-2000:,} more bytes)"
                
                # If it's LSX, add structure info
                if file_ext == '.lsx':
                    schema_info = self.parser.get_lsx_schema_info(file_path)
                    if schema_info:
                        preview_content += f"\n\n{'='*30}\nLSX STRUCTURE INFO:\n{'='*30}\n"
                        preview_content += f"File Type: {schema_info['file_type']}\n"
                        preview_content += f"Regions: {len(schema_info['regions'])}\n"
                        preview_content += f"Node Types: {dict(list(schema_info['node_types'].items())[:5])}\n"
                        if len(schema_info['node_types']) > 5:
                            preview_content += "... and more\n"
            
            else:
                preview_content += f"Binary file - cannot preview\n"
                preview_content += f"Extension: {file_ext}"
            
            self.preview_text.insert(1.0, preview_content)
            
        except Exception as e:
            self.preview_text.insert(1.0, f"Error previewing file: {e}")
        
        finally:
            self.preview_text.config(state='disabled')

# PAK Operations with Progress Bars
class PAKOperations:
    """PAK operations with progress feedback"""
    
    def __init__(self, bg3_tool, parent_window):
        self.bg3_tool = bg3_tool
        self.parent_window = parent_window
    
    def extract_pak_with_progress(self, pak_file, destination_dir, progress_callback=None):
        """Extract PAK with progress tracking"""
        
        def extraction_worker():
            try:
                if progress_callback:
                    progress_callback(10, "Starting extraction...")
                
                # Your existing extraction code here, but with progress updates
                success = self.bg3_tool.extract_pak(pak_file, destination_dir)
                
                if progress_callback:
                    progress_callback(100, "Extraction complete!")
                
                return success
                
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Error: {e}")
                return False
        
        return extraction_worker()
    
    def create_pak_with_progress(self, source_dir, pak_file, progress_callback=None):
        """Create PAK with progress tracking"""
        
        def creation_worker():
            try:
                if progress_callback:
                    progress_callback(10, "Validating mod structure...")
                
                # Validate first
                validation = self.bg3_tool.validate_mod_structure(source_dir)
                
                if progress_callback:
                    progress_callback(30, "Creating PAK file...")
                
                # Create PAK
                success = self.bg3_tool.create_pak(source_dir, pak_file)
                
                if progress_callback:
                    progress_callback(100, "PAK creation complete!")
                
                return success
                
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Error: {e}")
                return False
        
        return creation_worker()

class SettingsManager:
    """Manage user settings including working directory"""
    
    def __init__(self):
        self.settings_file = os.path.expanduser("~/.bg3_toolkit_settings.json")
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        default_settings = {
            "working_directory": os.path.expanduser("~/Desktop"),
            "wine_path": "/opt/homebrew/bin/wine",
            "lslib_path": "",
            "window_geometry": "1000x700",
            "recent_files": []
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    default_settings.update(loaded_settings)
        except Exception as e:
            print(f"Could not load settings: {e}")
        
        return default_settings
    
    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Could not save settings: {e}")
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
        self.save_settings()

class SettingsDialog:
    """Settings configuration dialog"""
    
    def __init__(self, parent, settings_manager):
        self.parent = parent
        self.settings_manager = settings_manager
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("BG3 Toolkit Settings")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        """Setup the settings dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Working Directory
        ttk.Label(main_frame, text="Working Directory:").pack(anchor='w', pady=(0, 5))
        
        dir_frame = ttk.Frame(main_frame)
        dir_frame.pack(fill='x', pady=(0, 15))
        
        self.working_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_frame, textvariable=self.working_dir_var)
        dir_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(dir_frame, text="Browse", command=self.browse_working_dir).pack(side='right')
        
        # Wine Path
        ttk.Label(main_frame, text="Wine Executable Path:").pack(anchor='w', pady=(0, 5))
        
        wine_frame = ttk.Frame(main_frame)
        wine_frame.pack(fill='x', pady=(0, 15))
        
        self.wine_path_var = tk.StringVar()
        wine_entry = ttk.Entry(wine_frame, textvariable=self.wine_path_var)
        wine_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(wine_frame, text="Browse", command=self.browse_wine_path).pack(side='right')
        
        # LSLib Path
        ttk.Label(main_frame, text="Divine.exe Path:").pack(anchor='w', pady=(0, 5))
        
        lslib_frame = ttk.Frame(main_frame)
        lslib_frame.pack(fill='x', pady=(0, 20))
        
        self.lslib_path_var = tk.StringVar()
        lslib_entry = ttk.Entry(lslib_frame, textvariable=self.lslib_path_var)
        lslib_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(lslib_frame, text="Browse", command=self.browse_lslib_path).pack(side='right')
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', side='bottom')
        
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side='right')
    
    def load_current_settings(self):
        """Load current settings into the dialog"""
        self.working_dir_var.set(self.settings_manager.get("working_directory", ""))
        self.wine_path_var.set(self.settings_manager.get("wine_path", ""))
        self.lslib_path_var.set(self.settings_manager.get("lslib_path", ""))
    
    def browse_working_dir(self):
        """Browse for working directory"""
        directory = filedialog.askdirectory(
            title="Select Working Directory",
            initialdir=self.working_dir_var.get()
        )
        if directory:
            self.working_dir_var.set(directory)
    
    def browse_wine_path(self):
        """Browse for Wine executable"""
        file_path = filedialog.askopenfilename(
            title="Select Wine Executable",
            filetypes=[("Executable files", "*"), ("All files", "*.*")]
        )
        if file_path:
            self.wine_path_var.set(file_path)
    
    def browse_lslib_path(self):
        """Browse for Divine.exe"""
        file_path = filedialog.askopenfilename(
            title="Select Divine.exe",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if file_path:
            self.lslib_path_var.set(file_path)
    
    def save_settings(self):
        """Save settings and close dialog"""
        self.settings_manager.set("working_directory", self.working_dir_var.get())
        self.settings_manager.set("wine_path", self.wine_path_var.get())
        self.settings_manager.set("lslib_path", self.lslib_path_var.get())
        
        messagebox.showinfo("Settings", "Settings saved successfully!")
        self.dialog.destroy()

class ProgressDialog:
    """Progress dialog with better UI responsiveness"""
    
    def __init__(self, parent, title="Processing..."):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Make it modal and prevent closing during operation
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        self.setup_ui()
        self.cancelled = False
        self.last_update_time = 0
        self.update_frequency = 0.1  # Update at most 10 times per second
    
    def setup_ui(self):
        """Setup the progress dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Initializing...")
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            mode='determinate',
            variable=self.progress_var,
            length=350
        )
        self.progress_bar.pack(pady=(0, 10))
        
        # Percentage label
        self.percent_label = ttk.Label(main_frame, text="0%")
        self.percent_label.pack(pady=(0, 10))
        
        # Cancel button
        self.cancel_button = ttk.Button(main_frame, text="Cancel", command=self.on_cancel)
        self.cancel_button.pack()
        
        # Center the dialog on parent
        self.center_dialog()
    
    def center_dialog(self):
        """Center the dialog on the parent window"""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def update_progress(self, percentage, status_text=""):
        """Update progress with throttling to prevent UI lag"""
        if self.cancelled:
            return False
        
        import time
        current_time = time.time()
        
        # Throttle updates to prevent UI lag
        if current_time - self.last_update_time < self.update_frequency and percentage != 100:
            return True
        
        self.last_update_time = current_time
        
        try:
            self.progress_var.set(min(100, max(0, percentage)))
            self.percent_label.config(text=f"{int(percentage)}%")
            
            if status_text:
                # Truncate very long status text
                if len(status_text) > 50:
                    status_text = status_text[:47] + "..."
                self.status_label.config(text=status_text)
            
            # Force update but limit frequency
            self.dialog.update_idletasks()
            
        except tk.TclError:
            # Dialog might be closed
            return False
        
        return True
    
    def on_cancel(self):
        """Handle cancel button with confirmation"""
        if not self.cancelled:
            result = messagebox.askyesno("Cancel Operation", 
                                       "Are you sure you want to cancel this operation?",
                                       parent=self.dialog)
            if result:
                self.cancelled = True
                self.status_label.config(text="Cancelling...")
                self.cancel_button.config(state='disabled')
    
    def is_cancelled(self):
        """Check if operation was cancelled"""
        return self.cancelled
    
    def close(self):
        """Close the dialog safely"""
        try:
            if not self.cancelled:
                self.dialog.destroy()
        except tk.TclError:
            pass  # Dialog already closed

class BG3ModToolkitGUI:
    """Main GUI application with progress bars and better UX"""
    
    def __init__(self, bg3_tool):
        self.bg3_tool = bg3_tool
        self.root = tk.Tk()
        self.root.title("BG3 Mac Modding Toolkit")
        self.root.geometry("1000x700")
        
        # Initialize settings manager
        self.settings_manager = SettingsManager()

        # Get project manager
        self.project_manager = ProjectManager(self.settings_manager)
        
        # Setup menu bar
        self.setup_menubar()
        
        # Setup main GUI
        self.setup_gui()
    
    def setup_menubar(self):
        """Setup the application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Preferences", command=self.open_settings)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_gui(self):
        """Setup the main GUI"""
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Asset Browser
        browser = AssetBrowser(bg3_tool=self.bg3_tool, settings_manager=self.settings_manager)
        browser_tab = browser.setup_browser_tab(notebook)
        notebook.add(browser_tab, text="Asset Browser")
        
        # Tab 2: LSX Editor with syntax highlighting
        editor = LSXEditor(settings_manager=self.settings_manager)
        editor_tab = editor.setup_editor_tab(notebook)
        notebook.add(editor_tab, text="LSX Editor")
        
        # Tab 3: PAK Tools with progress bars
        pak_tab = self.setup_pak_tools_tab(notebook)
        notebook.add(pak_tab, text="PAK Tools")

        # Tab 4: File Manager
        file_manager = FileManagerWidget(notebook, self.settings_manager, self.project_manager)
        notebook.add(file_manager.frame, text="Projects")

        # Quick actions above status bar
        quick_actions = QuickActionsWidget(self.root, self.project_manager, self.bg3_tool)
        quick_actions.frame.pack(side='bottom', fill='x', padx=10, pady=2)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief='sunken')
        self.status_bar.pack(side='bottom', fill='x')
    
    def setup_pak_tools_tab(self, parent):
        """PAK tools with responsive buttons"""
        frame = ttk.Frame(parent)
        
        ttk.Label(frame, text="PAK Operations", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Create two columns
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        # Left column - Extraction
        left_frame = ttk.LabelFrame(button_frame, text="Extract PAKs", padding=10)
        left_frame.grid(row=0, column=0, padx=10, sticky="ew")
        
        # Use responsive buttons
        extract_btn = ResponsiveButton(left_frame, "Extract PAK File", self.extract_pak_with_progress)
        extract_btn.pack(pady=5, fill='x')
        
        list_btn = ResponsiveButton(left_frame, "List PAK Contents", self.list_pak_with_progress)
        list_btn.pack(pady=5, fill='x')
        
        # Right column - Creation
        right_frame = ttk.LabelFrame(button_frame, text="Create PAKs", padding=10)
        right_frame.grid(row=0, column=1, padx=10, sticky="ew")
        
        create_btn = ResponsiveButton(right_frame, "Create PAK from Folder", self.create_pak_with_progress)
        create_btn.pack(pady=5, fill='x')
        
        rebuild_btn = ResponsiveButton(right_frame, "Rebuild Modified PAK", self.rebuild_pak_with_progress)
        rebuild_btn.pack(pady=5, fill='x')
        
        validate_btn = ResponsiveButton(right_frame, "Validate Mod Structure", self.validate_mod_gui)
        validate_btn.pack(pady=5, fill='x')
        
        # Configure grid weights
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        
        # Results area
        self.results_text = scrolledtext.ScrolledText(frame, height=20)
        self.results_text.pack(fill='both', expand=True, padx=20, pady=20)
        
        return frame
    
    def extract_pak_with_progress(self):
        """Extract PAK with progress dialog"""
        initial_dir = self.settings_manager.get("working_directory", "/")
        
        pak_file = filedialog.askopenfilename(
            title="Select PAK file",
            initialdir=initial_dir,
            filetypes=[("PAK files", "*.pak"), ("All files", "*.*")]
        )
        
        if pak_file:
            # Update working directory
            self.settings_manager.set("working_directory", os.path.dirname(pak_file))
            
            dest_dir = filedialog.askdirectory(
                title="Select extraction destination",
                initialdir=initial_dir
            )
            
            if dest_dir:
                # Update working directory
                self.settings_manager.set("working_directory", dest_dir)
                
                # Start progress dialog
                progress_dialog = ProgressDialog(self.root, "Extracting PAK File")
                
                def extraction_worker():
                    try:
                        # Update progress
                        self.root.after(0, lambda: progress_dialog.update_progress(10, "Starting extraction..."))
                        
                        # Add result to UI thread-safely
                        self.root.after(0, lambda: self.results_text.insert(tk.END, f"Extracting {os.path.basename(pak_file)}...\n"))
                        
                        # Simulate progress updates (in real implementation, you'd hook into Divine.exe output)
                        self.root.after(0, lambda: progress_dialog.update_progress(30, "Extracting files..."))
                        
                        # Perform extraction
                        success = self.bg3_tool.extract_pak(pak_file, dest_dir)
                        
                        # Update progress
                        if success:
                            self.root.after(0, lambda: progress_dialog.update_progress(100, "Extraction complete!"))
                            self.root.after(0, lambda: self.results_text.insert(tk.END, "✅ Extraction completed!\n\n"))
                        else:
                            self.root.after(0, lambda: progress_dialog.update_progress(0, "Extraction failed"))
                            self.root.after(0, lambda: self.results_text.insert(tk.END, "❌ Extraction failed!\n\n"))
                        
                        # Close progress dialog
                        time.sleep(0.5)  # Brief pause to show completion
                        self.root.after(0, progress_dialog.close)
                        
                    except Exception as e:
                        self.root.after(0, lambda: self.results_text.insert(tk.END, f"❌ Error: {e}\n\n"))
                        self.root.after(0, progress_dialog.close)
                
                # Start extraction in background thread
                threading.Thread(target=extraction_worker, daemon=True).start()
    
    def list_pak_with_progress(self):
        """List PAK contents with progress dialog"""
        initial_dir = self.settings_manager.get("working_directory", "/")
        
        pak_file = filedialog.askopenfilename(
            title="Select PAK file",
            initialdir=initial_dir,
            filetypes=[("PAK files", "*.pak"), ("All files", "*.*")]
        )
        
        if pak_file:
            # Update working directory
            self.settings_manager.set("working_directory", os.path.dirname(pak_file))
            
            progress_dialog = ProgressDialog(self.root, "Listing PAK Contents")
            
            def listing_worker():
                try:
                    self.root.after(0, lambda: progress_dialog.update_progress(20, "Reading PAK file..."))
                    self.root.after(0, lambda: self.results_text.insert(tk.END, f"Listing contents of {os.path.basename(pak_file)}...\n"))
                    
                    self.root.after(0, lambda: progress_dialog.update_progress(50, "Parsing file list..."))
                    
                    files = self.bg3_tool.list_pak_contents(pak_file)
                    
                    self.root.after(0, lambda: progress_dialog.update_progress(80, "Formatting results..."))
                    
                    # Format results
                    result_text = f"Found {len(files)} files:\n"
                    
                    for file_info in files[:50]:  # Show first 50
                        result_text += f"  {file_info['name']}\n"
                    
                    if len(files) > 50:
                        result_text += f"  ... and {len(files) - 50} more files\n"
                    
                    result_text += "\n"
                    
                    self.root.after(0, lambda: progress_dialog.update_progress(100, "Complete!"))
                    self.root.after(0, lambda: self.results_text.insert(tk.END, result_text))
                    
                    time.sleep(0.5)
                    self.root.after(0, progress_dialog.close)
                    
                except Exception as e:
                    self.root.after(0, lambda: self.results_text.insert(tk.END, f"❌ Error: {e}\n\n"))
                    self.root.after(0, progress_dialog.close)
            
            threading.Thread(target=listing_worker, daemon=True).start()
    
    def create_pak_with_progress(self):
        """Create PAK with progress dialog"""
        initial_dir = self.settings_manager.get("working_directory", "/")
        
        source_dir = filedialog.askdirectory(
            title="Select folder to pack into PAK",
            initialdir=initial_dir
        )
        
        if source_dir:
            # Update working directory
            self.settings_manager.set("working_directory", source_dir)
            
            # Suggest PAK filename based on folder name
            suggested_name = f"{os.path.basename(source_dir)}.pak"
            
            pak_file = filedialog.asksaveasfilename(
                title="Save PAK file as",
                initialdir=os.path.dirname(source_dir),
                defaultextension=".pak",
                initialfile=suggested_name,
                filetypes=[("PAK files", "*.pak"), ("All files", "*.*")]
            )
            
            if pak_file:
                progress_dialog = ProgressDialog(self.root, "Creating PAK File")
                
                def creation_worker():
                    try:
                        self.root.after(0, lambda: progress_dialog.update_progress(10, "Validating mod structure..."))
                        self.root.after(0, lambda: self.results_text.insert(tk.END, f"Creating PAK from: {os.path.basename(source_dir)}\n"))
                        self.root.after(0, lambda: self.results_text.insert(tk.END, f"Output: {os.path.basename(pak_file)}\n"))
                        
                        # Validate mod structure
                        validation = self.bg3_tool.validate_mod_structure(source_dir)
                        
                        self.root.after(0, lambda: progress_dialog.update_progress(30, "Structure validation complete"))
                        
                        # Add validation results
                        validation_text = "\nMod Structure Validation:\n"
                        for item in validation['structure']:
                            validation_text += f"  {item}\n"
                        for warning in validation['warnings']:
                            validation_text += f"  {warning}\n"
                        validation_text += "\n"
                        
                        self.root.after(0, lambda: self.results_text.insert(tk.END, validation_text))
                        
                        self.root.after(0, lambda: progress_dialog.update_progress(50, "Creating PAK file..."))
                        
                        # Create the PAK
                        success = self.bg3_tool.create_pak(source_dir, pak_file)
                        
                        if success:
                            self.root.after(0, lambda: progress_dialog.update_progress(100, "PAK creation complete!"))
                            self.root.after(0, lambda: self.results_text.insert(tk.END, "✅ PAK creation completed!\n"))
                            self.root.after(0, lambda: self.results_text.insert(tk.END, f"Ready to install: {os.path.basename(pak_file)}\n\n"))
                        else:
                            self.root.after(0, lambda: progress_dialog.update_progress(0, "PAK creation failed"))
                            self.root.after(0, lambda: self.results_text.insert(tk.END, "❌ PAK creation failed!\n\n"))
                        
                        time.sleep(0.5)
                        self.root.after(0, progress_dialog.close)
                        
                    except Exception as e:
                        self.root.after(0, lambda: self.results_text.insert(tk.END, f"❌ Error: {e}\n\n"))
                        self.root.after(0, progress_dialog.close)
                
                threading.Thread(target=creation_worker, daemon=True).start()
    
    def rebuild_pak_with_progress(self):
        """Rebuild PAK with progress dialog"""
        initial_dir = self.settings_manager.get("working_directory", "/")
        
        extracted_dir = filedialog.askdirectory(
            title="Select extracted/modified PAK folder",
            initialdir=initial_dir
        )
        
        if extracted_dir:
            # Update working directory
            self.settings_manager.set("working_directory", extracted_dir)
            
            # Suggest output filename
            suggested_name = f"{os.path.basename(extracted_dir)}_modified.pak"
            
            pak_file = filedialog.asksaveasfilename(
                title="Save rebuilt PAK as",
                initialdir=os.path.dirname(extracted_dir),
                defaultextension=".pak",
                initialfile=suggested_name,
                filetypes=[("PAK files", "*.pak"), ("All files", "*.*")]
            )
            
            if pak_file:
                progress_dialog = ProgressDialog(self.root, "Rebuilding PAK")
                
                def rebuild_worker():
                    try:
                        self.root.after(0, lambda: progress_dialog.update_progress(20, "Starting rebuild..."))
                        self.root.after(0, lambda: self.results_text.insert(tk.END, f"Rebuilding PAK from: {os.path.basename(extracted_dir)}\n"))
                        
                        self.root.after(0, lambda: progress_dialog.update_progress(60, "Creating PAK file..."))
                        
                        success = self.bg3_tool.create_pak(extracted_dir, pak_file)
                        
                        if success:
                            self.root.after(0, lambda: progress_dialog.update_progress(100, "Rebuild complete!"))
                            self.root.after(0, lambda: self.results_text.insert(tk.END, "✅ PAK rebuild completed!\n\n"))
                        else:
                            self.root.after(0, lambda: progress_dialog.update_progress(0, "Rebuild failed"))
                            self.root.after(0, lambda: self.results_text.insert(tk.END, "❌ PAK rebuild failed!\n\n"))
                        
                        time.sleep(0.5)
                        self.root.after(0, progress_dialog.close)
                        
                    except Exception as e:
                        self.root.after(0, lambda: self.results_text.insert(tk.END, f"❌ Error: {e}\n\n"))
                        self.root.after(0, progress_dialog.close)
                
                threading.Thread(target=rebuild_worker, daemon=True).start()
    
    def validate_mod_gui(self):
        """Validate mod structure (this one can stay synchronous since it's fast)"""
        initial_dir = self.settings_manager.get("working_directory", "/")
        
        mod_dir = filedialog.askdirectory(
            title="Select mod folder to validate",
            initialdir=initial_dir
        )
        
        if mod_dir:
            # Update working directory
            self.settings_manager.set("working_directory", mod_dir)
            
            self.results_text.insert(tk.END, f"Validating mod structure: {os.path.basename(mod_dir)}\n")
            
            validation = self.bg3_tool.validate_mod_structure(mod_dir)
            
            self.results_text.insert(tk.END, f"\nValidation Results:\n")
            self.results_text.insert(tk.END, f"Valid: {'✅ Yes' if validation['valid'] else '❌ No'}\n\n")
            
            self.results_text.insert(tk.END, "Structure Found:\n")
            for item in validation['structure']:
                self.results_text.insert(tk.END, f"  {item}\n")
            
            if validation['warnings']:
                self.results_text.insert(tk.END, "\nWarnings:\n")
                for warning in validation['warnings']:
                    self.results_text.insert(tk.END, f"  {warning}\n")
            
            self.results_text.insert(tk.END, "\n")
    
    def open_settings(self):
        """Open settings dialog"""
        SettingsDialog(self.root, self.settings_manager)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """BG3 Mac Modding Toolkit
        
                    A native Mac application for modding Baldur's Gate 3.
                    
                    Features:
                    • Extract and create PAK files
                    • Browse game assets
                    • Edit LSX files with syntax highlighting
                    • Validate mod structures
                    
                    Built with Python, tkinter, and lslib via Wine."""
        
        messagebox.showinfo("About BG3 Mac Modding Toolkit", about_text)
    
    def run(self):
        """Start the GUI application"""
        # Restore window geometry
        geometry = self.settings_manager.get("window_geometry", "1000x700")
        self.root.geometry(geometry)
        
        # Save geometry on close
        def on_closing():
            self.settings_manager.set("window_geometry", self.root.geometry())
            self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        self.root.mainloop()
        