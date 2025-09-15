#!/usr/bin/env python3
"""
BG3 Asset Browser - Simple file dropdown and parser preview
Refactored to use standalone preview system
"""

import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from collections import defaultdict
import threading
import tempfile

from larian_parser import UniversalBG3Parser
from progress_dialog import ProgressDialog
from preview_manager import FilePreviewManager, get_file_icon

class AssetBrowser:
    """Phase 3: Browse extracted PAK contents and preview LSX files"""
    
    def __init__(self, parent=None, bg3_tool=None, settings_manager=None):
        self.bg3_tool = bg3_tool
        self.settings_manager = settings_manager
        self.parser = UniversalBG3Parser()
        if bg3_tool:
            self.parser.set_bg3_tool(bg3_tool)
        
        # Initialize the preview system
        self.preview_manager = FilePreviewManager(bg3_tool, self.parser)
        
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

    def preview_file_with_progress(self, file_path):
        """Preview file with progress dialog for slow operations"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Check if this file type needs progress dialog
        if file_ext in ['.lsf', '.lsbs', '.lsbc', '.lsfx']:
            self.preview_file_with_conversion_progress(file_path)
        else:
            self.preview_file(file_path)
    
    def preview_file_with_conversion_progress(self, file_path):
        """Preview file with progress dialog for conversion operations"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Create progress dialog
        progress_dialog = ProgressDialog(
            parent=self.preview_text.winfo_toplevel(),
            title=f"Converting {file_ext.upper()} File"
        )
        
        def conversion_worker():
            """Worker thread for file conversion"""
            try:
                progress_dialog.update_progress(10, f"Preparing {file_ext.upper()} conversion...")
                
                if progress_dialog.is_cancelled():
                    return
                
                # Clear preview first
                self.preview_text.after(0, lambda: self.clear_preview())
                
                # Use the preview manager with progress callback
                def progress_callback(percent, message):
                    if not progress_dialog.is_cancelled():
                        progress_dialog.update_progress(percent, message)
                
                preview_data = self.preview_manager.preview_system.preview_file_with_progress(
                    file_path, progress_callback
                )
                
                if progress_dialog.is_cancelled():
                    return
                
                # Update preview with results
                self.preview_text.after(0, lambda: self.display_preview_data(preview_data))
                
            except Exception as e:
                error_msg = f"Error converting {file_ext.upper()}: {e}"
                self.preview_text.after(0, lambda: self.display_error_content(error_msg))
            finally:
                # Close progress dialog
                self.preview_text.after(100, progress_dialog.close)
        
        # Start conversion in background thread
        thread = threading.Thread(target=conversion_worker, daemon=True)
        thread.start()
    
    def clear_preview(self):
        """Clear the preview pane"""
        if hasattr(self, 'thumbnail_canvas'):
            self.thumbnail_canvas.delete("all")
            if hasattr(self.thumbnail_canvas, 'image'):
                self.thumbnail_canvas.image = None
        
        self.preview_text.config(state='normal')
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.config(state='disabled')
    
    def display_preview_data(self, preview_data):
        """Display preview data from the preview system"""
        self.preview_text.config(state='normal')
        self.preview_text.delete(1.0, tk.END)
        
        # Handle thumbnail if present
        if hasattr(self, 'thumbnail_canvas') and preview_data.get('thumbnail'):
            self.thumbnail_canvas.delete("all")
            
            canvas_width = self.thumbnail_canvas.winfo_width()
            canvas_height = self.thumbnail_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                center_x = canvas_width // 2
                center_y = canvas_height // 2
                
                self.thumbnail_canvas.create_image(center_x, center_y, image=preview_data['thumbnail'])
                self.thumbnail_canvas.image = preview_data['thumbnail']
        
        # Display content
        self.preview_text.insert(1.0, preview_data['content'])
        self.preview_text.config(state='disabled')
    
    def display_error_content(self, error_msg):
        """Display error message in preview"""
        self.preview_text.config(state='normal')
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, error_msg)
        self.preview_text.config(state='disabled')
    
    def setup_browser_tab(self, parent):
        """Setup the asset browser interface"""
        browser_frame = ttk.Frame(parent)
        
        # Top toolbar
        toolbar = ttk.Frame(browser_frame)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(toolbar, text="Browse Folder", command=self.browse_folder).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Refresh", command=self.refresh_view).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Clear Cache", command=self.clear_cache).pack(side='left', padx=2)
        
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
        
        # Add thumbnail canvas
        self.thumbnail_canvas = tk.Canvas(preview_frame, height=200, bg='white')
        self.thumbnail_canvas.pack(fill='x', pady=5)
        
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
    
    def clear_cache(self):
        """Clear the preview cache"""
        self.preview_manager.clear_cache()
        messagebox.showinfo("Cache Cleared", "Preview cache has been cleared.")
    
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
                    icon = get_file_icon(item)
                    self.file_tree.insert(parent, 'end', text=f"{icon} {item}", 
                                        values=(item_path,), tags=('file',))
            
        except PermissionError:
            self.file_tree.insert(parent, 'end', text="⚠ Permission Denied")
    
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
                self.preview_file_with_progress(file_path)

    def preview_file(self, file_path):
        """Preview selected file using the preview manager"""
        try:
            # Clear any existing thumbnail
            if hasattr(self, 'thumbnail_canvas'):
                self.thumbnail_canvas.delete("all")
                if hasattr(self.thumbnail_canvas, 'image'):
                    self.thumbnail_canvas.image = None

            # Check if file is supported
            if not self.preview_manager.is_supported(file_path):
                # Handle unsupported files
                file_size = os.path.getsize(file_path)
                file_ext = os.path.splitext(file_path)[1].lower()
                
                preview_content = f"File: {os.path.basename(file_path)}\n"
                preview_content += f"Size: {file_size:,} bytes\n"
                preview_content += f"Type: {file_ext}\n"
                preview_content += "-" * 50 + "\n\n"
                preview_content += f"Unsupported file type: {file_ext}\n"
                preview_content += "Supported types: " + ", ".join(self.preview_manager.get_supported_extensions())
                
                self.preview_text.config(state='normal')
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.insert(1.0, preview_content)
                self.preview_text.config(state='disabled')
                return
            
            # Get preview using the manager
            preview_data = self.preview_manager.get_preview(file_path, use_cache=True)
            
            # Display the preview
            self.display_preview_data(preview_data)
            
        except Exception as e:
            self.display_error_content(f"Error previewing file: {e}")


class GameAssetOperations:
    """Operations for working with game assets"""
    
    def __init__(self, bg3_tool):
        self.bg3_tool = bg3_tool
        self.asset_index = {}
    
    def extract_specific_asset_threaded(self, pak_file, asset_path, destination, progress_callback=None, completion_callback=None):
        """Extract a specific asset from a PAK file"""
        
        def extraction_worker():
            try:
                if progress_callback:
                    progress_callback(10, "Extracting specific asset...")
                
                import tempfile
                import shutil
                
                # Create temporary extraction directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    if progress_callback:
                        progress_callback(30, "Extracting PAK to temporary location...")
                    
                    # Extract entire PAK to temp
                    success, output = self.bg3_tool.extract_pak_with_monitoring(
                        pak_file, temp_dir, 
                        lambda pct, msg: progress_callback(30 + (pct * 0.5), msg) if progress_callback else None
                    )
                    
                    if not success:
                        raise Exception(f"Failed to extract PAK: {output}")
                    
                    if progress_callback:
                        progress_callback(80, "Locating target asset...")
                    
                    # Find the specific asset
                    source_asset = os.path.join(temp_dir, asset_path.replace('/', os.sep))
                    
                    if os.path.exists(source_asset):
                        if progress_callback:
                            progress_callback(90, "Copying asset to destination...")
                        
                        # Create destination directory if needed
                        os.makedirs(os.path.dirname(destination), exist_ok=True)
                        
                        # Copy the asset
                        shutil.copy2(source_asset, destination)
                        
                        if progress_callback:
                            progress_callback(100, "Asset extracted successfully!")
                        
                        if completion_callback:
                            completion_callback({
                                'success': True,
                                'source_pak': pak_file,
                                'asset_path': asset_path,
                                'destination': destination
                            })
                    else:
                        raise Exception(f"Asset not found in PAK: {asset_path}")
                
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Error: {e}")
                if completion_callback:
                    completion_callback({
                        'success': False,
                        'error': str(e),
                        'source_pak': pak_file,
                        'asset_path': asset_path
                    })
        
        # Start in background thread
        thread = threading.Thread(target=extraction_worker, daemon=True)
        thread.start()
        return thread