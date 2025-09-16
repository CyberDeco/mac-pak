#!/usr/bin/env python3
"""
Assets Browser tab UI funcs
"""

import os
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QTreeWidget, QFileDialog,
                            QTextEdit, QLabel, QLineEdit, QComboBox, QCheckBox, QSplitter, QFrame, QTreeWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..widgets.asset_browser.preview_manager import FilePreviewManager, PreviewWidget, get_file_icon
from ..widgets.pak_tools.drop_label import DropLabel
from ..widgets.settings_dialog import SettingsDialog

from ..threads.pak_operations_thread import DivineOperationThread, ConversionPAKThread
from ...data.parsers.larian_parser import UniversalBG3Parser


class AssetBrowserTab(QWidget):
    """Asset Browser tab for the main application"""
    
    def __init__(self, parent=None, bg3_tool=None, settings_manager=None):
        super().__init__(parent)
        
        self.bg3_tool = bg3_tool
        self.settings_manager = settings_manager
        self.parser = UniversalBG3Parser()
        
        if bg3_tool:
            self.parser.set_bg3_tool(bg3_tool)
        
        # Initialize preview system
        self.preview_manager = FilePreviewManager(bg3_tool, self.parser)
        
        self.current_directory = None
        self.setup_ui()
        
        # Load initial directory if available
        if settings_manager:
            working_dir = settings_manager.get("working_directory")
            if working_dir and os.path.exists(working_dir):
                self.current_directory = working_dir
                self.refresh_view()
                
    def setup_ui(self):
        """Setup the asset browser interface with Mac styling"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Asset Browser")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Main toolbar - Navigation and actions
        toolbar_layout = QHBoxLayout()
        
        # Navigation section
        self.up_btn = QPushButton("↑ Up")
        self.up_btn.clicked.connect(self.go_up_directory)
        self.up_btn.setEnabled(False)
        toolbar_layout.addWidget(self.up_btn)
        
        # Editable path field (much longer)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Enter path or browse...")
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        self.path_edit.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        toolbar_layout.addWidget(self.path_edit, 1)  # Take up most space
        
        # Main action buttons
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_folder)
        toolbar_layout.addWidget(self.browse_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_view)
        toolbar_layout.addWidget(self.refresh_btn)
        
        self.clear_cache_btn = QPushButton("Clear Cache")
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        toolbar_layout.addWidget(self.clear_cache_btn)
        
        # Recent files dropdown in the space
        recent_label = QLabel("Recent:")
        toolbar_layout.addWidget(recent_label)
        
        self.recent_files_combo = QComboBox()
        self.recent_files_combo.setMinimumWidth(200)
        self.recent_files_combo.setMaximumWidth(250)
        self.recent_files_combo.currentTextChanged.connect(self.load_recent_folder)
        toolbar_layout.addWidget(self.recent_files_combo)
        
        layout.addLayout(toolbar_layout)
        
        # Update recent files on startup
        self.update_recent_files_combo()
        
        # File type filters (moved underneath)
        filter_group = QGroupBox("File Type Filters")
        filter_layout = QHBoxLayout(filter_group)
        
        # Common BG3 file types
        self.filter_checkboxes = {}
        file_types = [
            ("LSX Files", [".lsx"]),
            ("LSF Files", [".lsf"]),
            ("DDS Images", [".dds"]),
            ("Textures", [".dds", ".png", ".jpg"]),
            ("Audio", [".wem", ".wav"]),
            ("Scripts", [".lua", ".script"]),
            ("Localization", [".loca"]),
            ("All Files", [])
        ]
        
        for label, extensions in file_types:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.update_file_filter)
            self.filter_checkboxes[label] = (checkbox, extensions)
            filter_layout.addWidget(checkbox)
        
        filter_layout.addStretch()
        layout.addWidget(filter_group)
        
        # Main content - horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: File tree with integrated filter
        tree_frame = QFrame()
        tree_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(10, 10, 10, 10)
        
        # Files header with integrated search
        files_header_layout = QHBoxLayout()
        
        tree_label = QLabel("Files")
        tree_label.setFont(QFont("SF Pro Text", 16, QFont.Weight.Bold))
        files_header_layout.addWidget(tree_label)
        
        files_header_layout.addStretch()
        
        # Search filter in the Files header
        filter_label = QLabel("Filter:")
        files_header_layout.addWidget(filter_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search files...")
        self.search_edit.textChanged.connect(self.filter_files)
        self.search_edit.setMaximumWidth(150)
        files_header_layout.addWidget(self.search_edit)
        
        tree_layout.addLayout(files_header_layout)
        
        # File tree
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabel("Name")
        self.file_tree.setRootIsDecorated(True)
        self.file_tree.setUniformRowHeights(True)
        self.file_tree.setAnimated(True)
        self.file_tree.itemSelectionChanged.connect(self.on_file_select)
        self.file_tree.itemClicked.connect(self.on_file_select)
        self.file_tree.itemExpanded.connect(self.on_item_expanded)
        self.file_tree.itemDoubleClicked.connect(self.on_item_double_click)

        # Make sure this line exists in setup_ui():
        self.file_tree.itemSelectionChanged.connect(self.on_file_select)
        
        # You might also want to try using itemClicked as an alternative:
        self.file_tree.itemClicked.connect(self.on_file_select)
        self.file_tree.itemExpanded.connect(self.on_item_expanded)
        
        # Apply Mac-style tree styling
        self.file_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: white;
                alternate-background-color: #f8f8f8;
                selection-background-color: #007AFF;
                outline: none;
            }
            QTreeWidget::item {
                height: 24px;
                padding: 2px;
            }
            QTreeWidget::item:selected {
                background-color: #007AFF;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #e3f2fd;
            }
        """)
        
        tree_layout.addWidget(self.file_tree)
        splitter.addWidget(tree_frame)
        
        # Right: Preview pane
        self.preview_widget = PreviewWidget()
        splitter.addWidget(self.preview_widget)
        
        splitter.setSizes([500, 500])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter, 1)

    def navigate_to_path(self):
        """Navigate to the path entered in the path field"""
        path = self.path_edit.text().strip()
        
        if not path:
            return
        
        # Expand user home directory
        path = os.path.expanduser(path)
        
        if os.path.exists(path) and os.path.isdir(path):
            self.current_directory = path
            
            if self.settings_manager:
                self.settings_manager.set("working_directory", path)
            
            self.add_to_recent_folders(path)
            self.refresh_view()
            self.update_navigation_state()
        else:
            QMessageBox.warning(self, "Invalid Path", f"The path '{path}' does not exist or is not a directory.")
            # Reset to current directory
            self.update_navigation_state()
    
    def update_navigation_state(self):
        """Update navigation button states and path display"""
        if self.current_directory:
            # Update path field with current directory
            self.path_edit.setText(self.current_directory)
            
            # Enable/disable up button
            parent_dir = os.path.dirname(self.current_directory)
            can_go_up = parent_dir and parent_dir != self.current_directory
            self.up_btn.setEnabled(can_go_up)
        else:
            self.path_edit.setText("")
            self.up_btn.setEnabled(False)

    def on_item_double_click(self, item):
        """Handle double-click to navigate into directories"""
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if item_path and item_path != "placeholder" and os.path.isdir(item_path):
            self.current_directory = item_path
            
            if self.settings_manager:
                self.settings_manager.set("working_directory", item_path)
            
            self.refresh_view()
            self.update_navigation_state()

    def go_up_directory(self):
        """Navigate up one directory level"""
        if not self.current_directory:
            return
        
        parent_dir = os.path.dirname(self.current_directory)
        
        # Don't go above root directory
        if parent_dir and parent_dir != self.current_directory:
            self.current_directory = parent_dir
            
            # Update working directory
            if self.settings_manager:
                self.settings_manager.set("working_directory", parent_dir)
            
            self.refresh_view()
            self.update_navigation_state()
    
    def update_navigation_state(self):
        """Update navigation button states and path display"""
        if self.current_directory:
            # Update path display with better truncation
            display_path = self.current_directory
            
            # Truncate from the middle for better readability
            if len(display_path) > 50:
                parts = display_path.split('/')
                if len(parts) > 3:
                    display_path = f"{parts[0]}/.../{parts[-2]}/{parts[-1]}"
                else:
                    display_path = "..." + display_path[-47:]
            
            self.path_edit.setText(display_path)
            self.path_edit.setToolTip(self.current_directory)  # Full path on hover
            
            # Enable/disable up button
            parent_dir = os.path.dirname(self.current_directory)
            can_go_up = parent_dir and parent_dir != self.current_directory
            self.up_btn.setEnabled(can_go_up)
        else:
            self.path_edit.setText("No folder selected")
            self.path_edit.setToolTip("")
            self.up_btn.setEnabled(False)

    def load_recent_folder(self, combo_text):
        """Load a folder from the recent files dropdown"""
        if not combo_text or combo_text.startswith("Select recent"):
            return
        
        # Extract the path from "FolderName - /full/path" format
        if " - " in combo_text:
            folder_path = combo_text.split(" - ", 1)[1]
        else:
            folder_path = combo_text
        
        if folder_path and os.path.exists(folder_path):
            self.current_directory = folder_path
            if self.settings_manager:
                self.settings_manager.set("working_directory", folder_path)
            self.refresh_view()
            self.update_navigation_state()
    
    def update_recent_files_combo(self):
        """Update the recent files dropdown"""
        if not self.settings_manager:
            return
        
        recent_folders = self.settings_manager.get("recent_asset_folders", [])
        
        self.recent_files_combo.clear()
        self.recent_files_combo.addItem("Select recent folder...")
        
        for folder in recent_folders:
            if os.path.exists(folder):
                folder_name = os.path.basename(folder) or folder
                self.recent_files_combo.addItem(f"{folder_name} - {folder}")
    
    def add_to_recent_folders(self, folder_path):
        """Add folder to recent files list"""
        if not self.settings_manager:
            return
        
        recent_folders = self.settings_manager.get("recent_asset_folders", [])
        
        # Remove if already exists
        if folder_path in recent_folders:
            recent_folders.remove(folder_path)
        
        # Add to beginning
        recent_folders.insert(0, folder_path)
        
        # Keep only last 10
        recent_folders = recent_folders[:10]
        
        self.settings_manager.set("recent_asset_folders", recent_folders)
        self.update_recent_files_combo()
    
    def browse_folder(self):
        """Browse for extracted PAK folder using native Mac dialog"""
        initial_dir = str(Path.home())
        if self.settings_manager:
            initial_dir = self.settings_manager.get("working_directory", initial_dir)
        
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Extracted PAK Folder", initial_dir
        )
        
        if folder_path:
            self.current_directory = folder_path
            
            # Update working directory
            if self.settings_manager:
                self.settings_manager.set("working_directory", folder_path)
            
            # Add to recent folders
            self.add_to_recent_folders(folder_path)
            
            self.refresh_view()
            self.update_navigation_state()  # Add this line
    
    def refresh_view(self):
        """Refresh the file tree view"""
        if not self.current_directory:
            return
        
        self.file_tree.clear()
        self.populate_tree(self.current_directory, None)
        
        # Clear preview
        self.preview_widget.clear_preview()
        
        # Update navigation state
        self.update_navigation_state()  # Add this line

    def update_file_filter(self):
        """Update file visibility based on type filters"""
        # Get enabled file types
        enabled_extensions = set()
        show_all = False
        
        for label, (checkbox, extensions) in self.filter_checkboxes.items():
            if checkbox.isChecked():
                if not extensions:  # "All Files" option
                    show_all = True
                    break
                enabled_extensions.update(extensions)
        
        # Apply filter to tree
        def filter_tree_item(item):
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            
            if not item_path or item_path == "placeholder":
                return True
            
            if os.path.isdir(item_path):
                # Always show directories
                return True
            
            if show_all:
                return True
            
            # Check file extension
            file_ext = os.path.splitext(item_path)[1].lower()
            return file_ext in enabled_extensions
        
        # Apply to all items
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            self.apply_filter_recursive(item, filter_tree_item)
    
    def apply_filter_recursive(self, item, filter_func):
        """Recursively apply filter to tree items"""
        # Check children first
        visible_children = 0
        for i in range(item.childCount()):
            child = item.child(i)
            self.apply_filter_recursive(child, filter_func)
            if not child.isHidden():
                visible_children += 1
        
        # Item is visible if it matches filter or has visible children
        item_visible = filter_func(item) or visible_children > 0
        item.setHidden(not item_visible)
    
    def populate_tree(self, directory, parent_item):
        """Populate tree with directory contents including file sizes"""
        try:
            # Get directory contents
            for item_name in sorted(os.listdir(directory)):
                if item_name.startswith('.'):  # Skip hidden files
                    continue
                
                item_path = os.path.join(directory, item_name)
                
                # Create tree item
                if parent_item:
                    tree_item = QTreeWidgetItem(parent_item)
                else:
                    tree_item = QTreeWidgetItem(self.file_tree)
                
                # Set item data
                tree_item.setData(0, Qt.ItemDataRole.UserRole, item_path)
                
                if os.path.isdir(item_path):
                    # Directory - count items
                    try:
                        item_count = len([f for f in os.listdir(item_path) if not f.startswith('.')])
                        tree_item.setText(0, f"📁 {item_name} ({item_count} items)")
                    except:
                        tree_item.setText(0, f"📁 {item_name}")
                    
                    tree_item.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                    )
                    # Add placeholder for lazy loading
                    placeholder = QTreeWidgetItem(tree_item)
                    placeholder.setText(0, "Loading...")
                    placeholder.setData(0, Qt.ItemDataRole.UserRole, "placeholder")
                else:
                    # File - show size
                    try:
                        file_size = os.path.getsize(item_path)
                        size_str = self.format_file_size(file_size)
                        icon = get_file_icon(item_name)
                        tree_item.setText(0, f"{icon} {item_name} ({size_str})")
                    except:
                        icon = get_file_icon(item_name)
                        tree_item.setText(0, f"{icon} {item_name}")
                    
                    tree_item.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
                    )
        
        except PermissionError:
            if parent_item:
                error_item = QTreeWidgetItem(parent_item)
            else:
                error_item = QTreeWidgetItem(self.file_tree)
            error_item.setText(0, "⚠️ Permission Denied")
    
    def format_file_size(self, size_bytes):
        """Format file size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def on_item_expanded(self, item):
        """Handle tree item expansion for lazy loading"""
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_path or not os.path.isdir(item_path):
            return
        
        # Check if this has the loading placeholder
        if item.childCount() == 1:
            child = item.child(0)
            if child.data(0, Qt.ItemDataRole.UserRole) == "placeholder":
                # Remove placeholder and populate real contents
                item.removeChild(child)
                self.populate_tree(item_path, item)
    
    def on_file_select(self):
        """Handle file selection"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            self.preview_widget.clear_preview()
            return
        
        item = selected_items[0]
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if file_path and file_path != "placeholder" and os.path.isfile(file_path):
            self.preview_widget.preview_file(file_path, self.preview_manager)
        else:
            print(f"Debug: Not a valid file or is placeholder")
            self.preview_widget.clear_preview()
    
    def filter_files(self):
        """Filter files based on search term"""
        search_term = self.search_edit.text().lower()
        
        def filter_item(item):
            """Recursively filter tree items"""
            item_text = item.text(0).lower()
            
            # Check if item matches search
            matches = search_term in item_text
            
            # Check children
            visible_children = 0
            for i in range(item.childCount()):
                child = item.child(i)
                if filter_item(child):
                    visible_children += 1
            
            # Item is visible if it matches or has visible children
            visible = matches or visible_children > 0 or not search_term
            item.setHidden(not visible)
            
            return visible
        
        # Apply filter to all top-level items
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            filter_item(item)
    
    def clear_cache(self):
        """Clear the preview cache"""
        self.preview_manager.clear_cache()
        QMessageBox.information(self, "Cache Cleared", "Preview cache has been cleared.")