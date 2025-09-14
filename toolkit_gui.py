#from lsx_tools import *

import json
import threading
import time
from tkinter import scrolledtext

from wine_wrapper import WineWrapper
from asset_browser import AssetBrowser
from quick_actions import QuickActionsWidget
from file_manager import FileManagerWidget
from pak_utils import PAKOperations
from lsx_tools import *
from projects import *

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
            "divine_path": "",
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
        
        # divine Path
        ttk.Label(main_frame, text="Divine.exe Path:").pack(anchor='w', pady=(0, 5))
        
        divine_frame = ttk.Frame(main_frame)
        divine_frame.pack(fill='x', pady=(0, 20))
        
        self.divine_path_var = tk.StringVar()
        divine_entry = ttk.Entry(divine_frame, textvariable=self.divine_path_var)
        divine_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(divine_frame, text="Browse", command=self.browse_divine_path).pack(side='right')
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', side='bottom')
        
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side='right')
    
    def load_current_settings(self):
        """Load current settings into the dialog"""
        self.working_dir_var.set(self.settings_manager.get("working_directory", ""))
        self.wine_path_var.set(self.settings_manager.get("wine_path", ""))
        self.divine_path_var.set(self.settings_manager.get("divine_path", ""))
    
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
    
    def browse_divine_path(self):
        """Browse for Divine.exe"""
        file_path = filedialog.askopenfilename(
            title="Select Divine.exe",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if file_path:
            self.divine_path_var.set(file_path)
    
    def save_settings(self):
        """Save settings and close dialog"""
        self.settings_manager.set("working_directory", self.working_dir_var.get())
        self.settings_manager.set("wine_path", self.wine_path_var.get())
        self.settings_manager.set("divine_path", self.divine_path_var.get())
        
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
    """Main GUI application - now focused only on UI logic"""
    
    def __init__(self, wine_path=None, divine_path=None):

        if not wine_path:
            wine_path = SettingsDialog.wine_path_var
            if not wine_path:
                raise ValueError("Must set wine_path when launching tool or in settings")
        if not divine_path:
            divine_path = SettingsDialog.divine_path_var
            if not divine_path:
                raise ValueError("Must set divine_path when launching tool or in settings")
        
        self.bg3_tool = WineWrapper(wine_path, divine_path)
        
        # Initialize operations modules
        self.pak_ops = PAKOperations(self.bg3_tool)
        
        self.root = tk.Tk()
        self.root.title("BG3 Mac Modding Toolkit")
        self.root.geometry("1000x700")
        
        # Initialize settings and project managers
        self.settings_manager = SettingsManager()
        self.project_manager = ProjectManager(self.settings_manager)
        
        # Setup GUI
        self.setup_menubar()
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

        # Tab 2: Enhanced Universal Editor with LSX, LSJ, LSF support
        editor = LSXEditor(settings_manager=self.settings_manager, bg3_tool=self.bg3_tool)
        editor_tab = editor.setup_editor_tab(notebook)
        notebook.add(editor_tab, text="Universal Editor")
        
        # Tab 3: Batch File Processing
        batch_processor = BatchFileProcessor(self.bg3_tool)
        batch_tab = batch_processor.setup_batch_tab(notebook)
        notebook.add(batch_tab, text="Batch Processing")
        
        # Tab 4: PAK Tools with progress bars
        pak_tab = self.setup_pak_tools_tab(notebook)
        notebook.add(pak_tab, text="PAK Tools")

        # Tab 5: File Manager
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

        """Extract PAK - now just handles UI logic"""
        initial_dir = self.settings_manager.get("working_directory", "/")
        
        pak_file = filedialog.askopenfilename(
            title="Select PAK file",
            initialdir=initial_dir,
            filetypes=[("PAK files", "*.pak"), ("All files", "*.*")]
        )
        
        if not pak_file:
            return
        
        self.settings_manager.set("working_directory", os.path.dirname(pak_file))
        
        dest_dir = filedialog.askdirectory(
            title="Select extraction destination",
            initialdir=initial_dir
        )
        
        if not dest_dir:
            return
            
        self.settings_manager.set("working_directory", dest_dir)
        
        # Create progress dialog
        progress_dialog = ProgressDialog(self.root, "Extracting PAK File")
        
        # Progress callback - updates the dialog
        def progress_update(percentage, message):
            self.root.after(0, lambda: progress_dialog.update_progress(percentage, message))
        
        # Completion callback - handles the results
        def extraction_complete(success, output):
            self.root.after(0, lambda: self._add_result_text(
                f"Extracting {os.path.basename(pak_file)}...\n"
            ))
            
            if success:
                self.root.after(0, lambda: self._add_result_text(
                    f"✅ Extraction completed!\n{output}\n\n"
                ))
            else:
                self.root.after(0, lambda: self._add_result_text(
                    f"❌ Extraction failed!\n{output}\n\n"
                ))
            
            self.root.after(0, progress_dialog.close)
        
        # Start the operation (all logic moved to pak_operations)
        self.pak_ops.extract_pak_threaded(pak_file, dest_dir, progress_update, extraction_complete)
    
    def create_pak_with_progress(self):
        """Create PAK - now just handles UI logic"""
        initial_dir = self.settings_manager.get("working_directory", "/")
        
        source_dir = filedialog.askdirectory(
            title="Select folder to pack into PAK",
            initialdir=initial_dir
        )
        
        if not source_dir:
            return
            
        self.settings_manager.set("working_directory", source_dir)
        suggested_name = f"{os.path.basename(source_dir)}.pak"
        
        pak_file = filedialog.asksaveasfilename(
            title="Save PAK file as",
            initialdir=os.path.dirname(source_dir),
            defaultextension=".pak",
            initialfile=suggested_name,
            filetypes=[("PAK files", "*.pak"), ("All files", "*.*")]
        )
        
        if not pak_file:
            return
        
        # Create progress dialog
        progress_dialog = ProgressDialog(self.root, "Creating PAK File")
        
        def progress_update(percentage, message):
            self.root.after(0, lambda: progress_dialog.update_progress(percentage, message))
        
        def creation_complete(result_data):
            self.root.after(0, lambda: self._add_result_text(
                f"Creating PAK from: {os.path.basename(source_dir)}\n"
                f"Output: {os.path.basename(pak_file)}\n"
            ))
            
            # Show validation results if available
            if result_data.get('validation'):
                validation_text = self._format_validation_results(result_data['validation'])
                self.root.after(0, lambda: self._add_result_text(validation_text))
            
            # Show final result
            if result_data['success']:
                self.root.after(0, lambda: self._add_result_text(
                    f"✅ PAK creation completed!\n{result_data['output']}\n\n"
                ))
            else:
                self.root.after(0, lambda: self._add_result_text(
                    f"❌ PAK creation failed!\n{result_data['output']}\n\n"
                ))
            
            self.root.after(0, progress_dialog.close)
        
        # Start the operation with validation
        self.pak_ops.create_pak_threaded(source_dir, pak_file, progress_update, creation_complete, validate=True)
    
    def list_pak_with_progress(self):
        """List PAK contents - now just handles UI logic"""
        initial_dir = self.settings_manager.get("working_directory", "/")
        
        pak_file = filedialog.askopenfilename(
            title="Select PAK file",
            initialdir=initial_dir,
            filetypes=[("PAK files", "*.pak"), ("All files", "*.*")]
        )
        
        if not pak_file:
            return
            
        self.settings_manager.set("working_directory", os.path.dirname(pak_file))
        
        progress_dialog = ProgressDialog(self.root, "Listing PAK Contents")
        
        def progress_update(percentage, message):
            self.root.after(0, lambda: progress_dialog.update_progress(percentage, message))
        
        def listing_complete(result_data):
            if result_data['success']:
                result_text = self._format_file_list(result_data, pak_file)
                self.root.after(0, lambda: self._add_result_text(result_text))
            else:
                self.root.after(0, lambda: self._add_result_text(
                    f"❌ Failed to list PAK contents: {result_data.get('error', 'Unknown error')}\n\n"
                ))
            
            self.root.after(0, progress_dialog.close)
        
        # Start the operation
        self.pak_ops.list_pak_contents_threaded(pak_file, progress_update, listing_complete)
    
    def rebuild_pak_with_progress(self):
        """Rebuild PAK - now just calls create_pak_threaded without validation"""
        initial_dir = self.settings_manager.get("working_directory", "/")
        
        extracted_dir = filedialog.askdirectory(
            title="Select extracted/modified PAK folder",
            initialdir=initial_dir
        )
        
        if not extracted_dir:
            return
            
        self.settings_manager.set("working_directory", extracted_dir)
        suggested_name = f"{os.path.basename(extracted_dir)}_modified.pak"
        
        pak_file = filedialog.asksaveasfilename(
            title="Save rebuilt PAK as",
            initialdir=os.path.dirname(extracted_dir),
            defaultextension=".pak",
            initialfile=suggested_name,
            filetypes=[("PAK files", "*.pak"), ("All files", "*.*")]
        )
        
        if not pak_file:
            return
        
        progress_dialog = ProgressDialog(self.root, "Rebuilding PAK")
        
        def progress_update(percentage, message):
            self.root.after(0, lambda: progress_dialog.update_progress(percentage, message))
        
        def rebuild_complete(result_data):
            self.root.after(0, lambda: self._add_result_text(
                f"Rebuilding PAK from: {os.path.basename(extracted_dir)}\n"
            ))
            
            if result_data['success']:
                self.root.after(0, lambda: self._add_result_text("✅ PAK rebuild completed!\n\n"))
            else:
                self.root.after(0, lambda: self._add_result_text(
                    f"❌ PAK rebuild failed!\n{result_data['output']}\n\n"
                ))
            
            self.root.after(0, progress_dialog.close)
        
        # Rebuilding is just creating a PAK from an extracted folder (no validation needed)
        self.pak_ops.create_pak_threaded(extracted_dir, pak_file, progress_update, rebuild_complete, validate=False)
    
    def validate_mod_gui(self):
        """Validate mod structure - now uses pak_operations"""
        initial_dir = self.settings_manager.get("working_directory", "/")
        
        mod_dir = filedialog.askdirectory(
            title="Select mod folder to validate",
            initialdir=initial_dir
        )
        
        if not mod_dir:
            return
            
        self.settings_manager.set("working_directory", mod_dir)
        
        self._add_result_text(f"Validating mod structure: {os.path.basename(mod_dir)}\n")
        
        # Use the validation from pak_operations
        validation = self.pak_ops.validate_mod_structure(mod_dir)
        
        # Format and display results
        result_text = f"\nValidation Results:\n"
        result_text += f"Valid: {'✅ Yes' if validation['valid'] else '❌ No'}\n\n"
        
        result_text += "Structure Found:\n"
        for item in validation['structure']:
            result_text += f"  ✅ {item}\n"
        
        if validation['warnings']:
            result_text += "\nWarnings:\n"
            for warning in validation['warnings']:
                result_text += f"  ⚠️ {warning}\n"
        
        result_text += "\n"
        self._add_result_text(result_text)
    
    # Helper methods to keep the main methods clean
    def _add_result_text(self, text):
        """Thread-safe way to add text to results area"""
        self.results_text.insert(tk.END, text)
        self.results_text.see(tk.END)  # Auto-scroll to bottom
    
    def _format_validation_results(self, validation):
        """Format validation results for display"""
        result_text = "\nMod Structure Validation:\n"
        for item in validation['structure']:
            result_text += f"  ✅ {item}\n"
        for warning in validation['warnings']:
            result_text += f"  ⚠️ {warning}\n"
        result_text += "\n"
        return result_text
    
    def _format_file_list(self, result_data, pak_file):
        """Format file list for display"""
        files = result_data['files']
        result_text = f"Found {result_data['file_count']} files in {os.path.basename(pak_file)}:\n"
        
        # Show first 50 files
        for file_info in files[:50]:
            icon = "📁" if file_info['type'] == 'folder' else "📄"
            result_text += f"  {icon} {file_info['name']}\n"
        
        if len(files) > 50:
            result_text += f"  ... and {len(files) - 50} more files\n"
        
        result_text += "\n"
        return result_text
    
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
                    
                    Built with Python, tkinter, and divine via Wine."""
        
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
        