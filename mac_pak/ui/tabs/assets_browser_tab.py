#!/usr/bin/env python3
"""
Assets Browser tab UI funcs
"""

import os
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QTreeWidget, QFileDialog,
                            QTextEdit, QLabel, QLineEdit, QComboBox, QCheckBox, QSplitter, QFrame, QTreeWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...data.file_preview import get_file_icon
from ...data.file_preview import FilePreviewManager

from ..widgets.asset_browser.preview_widget import PreviewWidget
from ...data.parsers.larian_parser import UniversalBG3Parser
from ...core.combo_box import CheckableComboBox

class AssetBrowserTab(QWidget):
    """Asset Browser tab for the main application"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.parser = UniversalBG3Parser()
        
        # Initialize filter state
        self.show_all_types = True
        self.enabled_extensions = set()
        
        if wine_wrapper:
            self.parser.set_wine_wrapper(wine_wrapper)

        # Initialize preview system
        self.preview_widget = PreviewWidget(parent, self.wine_wrapper, self.parser)
        self.preview_manager = FilePreviewManager(self.wine_wrapper, self.parser)
        
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
        title_label.setProperty("header", "h1")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Main toolbar - Navigation and actions
        toolbar_layout = QHBoxLayout()
        
        # Navigation section
        self.up_btn = QPushButton("↑ Up")
        self.up_btn.clicked.connect(self.go_up_directory)
        self.up_btn.setEnabled(False)
        toolbar_layout.addWidget(self.up_btn)
        
        # Editable path field
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Enter path or browse...")
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        toolbar_layout.addWidget(self.path_edit, 1)
        
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
        
        # Recent files dropdown
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
        
        # File type filters and search on same line
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        # File type filter combo (removed label)
        self.filter_combo = CheckableComboBox(self)
        self.filter_combo.setMinimumWidth(200)
        
        # Common BG3 file types
        file_types = [
            ("All Files", []),
            ("PAK Files", [".pak"]),
            ("LSF Files", [".lsf"]),
            ("LSX Files", [".lsx"]),
            ("LSJ Files", [".lsj"]),
            ("DDS Images", [".dds"]),
            ("Models", [".gr2"]),
            ("Textures", [".dds", ".png", ".jpg"]),
            ("Audio", [".wem", ".wav"]),
            ("Scripts", [".lua", ".script"]),
            ("Localization", [".loca"]),
        ]
        
        for label, extensions in file_types:
            self.filter_combo.add_item(label, extensions, checked=True)
        
        self.filter_combo.itemsChanged.connect(self.update_file_filter)
        
        filter_layout.addWidget(self.filter_combo)
        
        # Search filter (removed label)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search files...")
        self.search_edit.textChanged.connect(self.filter_files)
        self.search_edit.setMinimumWidth(200)
        filter_layout.addWidget(self.search_edit)
        
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Main content - horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: File tree (removed header)
        tree_frame = QFrame()
        tree_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(10, 10, 10, 10)
        
        # File tree
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["Name", "Type"])  # Changed from setHeaderLabel
        self.file_tree.setRootIsDecorated(True)
        self.file_tree.setUniformRowHeights(True)
        self.file_tree.setAnimated(True)
        self.file_tree.setSortingEnabled(True)  # Enable sorting
        self.file_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)  # Sort by name column

        # Remove grid lines between columns
        self.file_tree.setFrameShape(QFrame.Shape.NoFrame)
        self.file_tree.header().setHighlightSections(False)
        
        self.file_tree.itemSelectionChanged.connect(self.on_file_select)
        self.file_tree.itemClicked.connect(self.on_file_select)
        self.file_tree.itemExpanded.connect(self.on_item_expanded)
        self.file_tree.itemDoubleClicked.connect(self.on_item_double_click)
        
        # Set column widths
        self.file_tree.setColumnWidth(0, 650)  # Name column
        self.file_tree.setColumnWidth(1, 50)  # Type column
        
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
                border: none;
            }
            QTreeWidget::item:selected {
                background-color: #007AFF;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #e3f2fd;
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
            /* Remove column separators */
            QHeaderView::section {
                background-color: #f8f8f8;
                padding: 4px;
                border: none;
                border-right: 1px solid #d0d0d0;
                border-bottom: 1px solid #d0d0d0;
            }
            QHeaderView::section:last {
                border-right: none;
            }
        """)
        
        tree_layout.addWidget(self.file_tree)
        splitter.addWidget(tree_frame)
        
        # Right: Preview pane
        splitter.addWidget(self.preview_widget)
        
        splitter.setSizes([750, 250])
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
            self.update_navigation_state()

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
        
        if parent_dir and parent_dir != self.current_directory:
            self.current_directory = parent_dir
            
            if self.settings_manager:
                self.settings_manager.set("working_directory", parent_dir)
            
            self.refresh_view()
            self.update_navigation_state()
    
    def update_navigation_state(self):
        """Update navigation button states and path display"""
        if self.current_directory:
            self.path_edit.setText(self.current_directory)
            self.path_edit.setToolTip(self.current_directory)
            
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
        
        if folder_path in recent_folders:
            recent_folders.remove(folder_path)
        
        recent_folders.insert(0, folder_path)
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
            
            if self.settings_manager:
                self.settings_manager.set("working_directory", folder_path)
            
            self.add_to_recent_folders(folder_path)
            self.refresh_view()
            self.update_navigation_state()
    
    def refresh_view(self):
        """Refresh the file tree view"""
        if not self.current_directory:
            return
        
        self.file_tree.clear()
        self.populate_tree(self.current_directory, None)
        
        # Apply filters to newly populated tree
        self.apply_all_filters()
        
        self.preview_widget.clear_preview()
        self.update_navigation_state()

    def update_file_filter(self):
        """Update file visibility based on type filters"""
        enabled_extensions = set()
        show_all = False
        
        checked_items = self.filter_combo.get_checked_items()
        
        # If nothing is checked, hide everything
        if not checked_items:
            self.show_all_types = False
            self.enabled_extensions = set()
            self.apply_all_filters()
            return
        
        # Process all checked items
        for label, extensions in checked_items.items():
            if not extensions:  # "All Files" option
                show_all = True
            else:
                enabled_extensions.update(extensions)
        
        # If "All Files" is checked, show everything regardless of other selections
        self.show_all_types = show_all
        self.enabled_extensions = enabled_extensions
        
        self.apply_all_filters()
    
    def get_current_filter_func(self):
        """Get the current filter function based on current filter state"""
        search_term = self.search_edit.text().lower()
        
        def filter_tree_item(item):
            """Check if item matches both type and search filters"""
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            item_text = item.text(0).lower()
            
            if not item_path or item_path == "placeholder":
                return True
            
            search_matches = not search_term or search_term in item_text
            
            if os.path.isdir(item_path):
                return search_matches
            
            if self.show_all_types:
                type_matches = True
            else:
                file_ext = os.path.splitext(item_path)[1].lower()
                type_matches = file_ext in self.enabled_extensions
            
            return search_matches and type_matches
        
        return filter_tree_item
    
    def apply_all_filters(self):
        """Apply both type filters and search filters"""
        filter_func = self.get_current_filter_func()
        
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            self.apply_filter_recursive(item, filter_func)
    
    def filter_files(self):
        """Filter files based on search term"""
        self.apply_all_filters()
    
    def apply_filter_recursive(self, item, filter_func):
        """Recursively apply filter to tree items"""
        visible_children = 0
        for i in range(item.childCount()):
            child = item.child(i)
            self.apply_filter_recursive(child, filter_func)
            if not child.isHidden():
                visible_children += 1
        
        item_visible = filter_func(item) or visible_children > 0
        item.setHidden(not item_visible)
    
    def populate_tree(self, directory, parent_item):
        """Populate tree with directory contents including file sizes"""
        try:
            # Temporarily disable sorting while populating
            sorting_enabled = self.file_tree.isSortingEnabled()
            self.file_tree.setSortingEnabled(False)
            
            for item_name in sorted(os.listdir(directory)):
                if item_name.startswith('.'):
                    continue
                
                item_path = os.path.join(directory, item_name)
                
                if parent_item:
                    tree_item = QTreeWidgetItem(parent_item)
                else:
                    tree_item = QTreeWidgetItem(self.file_tree)
                
                tree_item.setData(0, Qt.ItemDataRole.UserRole, item_path)
                
                if os.path.isdir(item_path):
                    try:
                        item_count = len([f for f in os.listdir(item_path) if not f.startswith('.')])
                        tree_item.setText(0, f"📁 {item_name} ({item_count} items)")
                    except:
                        tree_item.setText(0, f"📁 {item_name}")
                    
                    tree_item.setText(1, "Folder")  # Type column
                    
                    tree_item.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                    )
                    placeholder = QTreeWidgetItem(tree_item)
                    placeholder.setText(0, "Loading...")
                    placeholder.setData(0, Qt.ItemDataRole.UserRole, "placeholder")
                else:
                    try:
                        file_size = os.path.getsize(item_path)
                        size_str = self.format_file_size(file_size)
                        icon = get_file_icon(item_name)
                        tree_item.setText(0, f"{icon} {item_name} ({size_str})")
                    except:
                        icon = get_file_icon(item_name)
                        tree_item.setText(0, f"{icon} {item_name}")
                    
                    # Set file type in Type column
                    file_ext = os.path.splitext(item_path)[1].lower()
                    if file_ext:
                        tree_item.setText(1, file_ext[1:].upper())  # Remove dot and capitalize
                    else:
                        tree_item.setText(1, "File")
                    
                    tree_item.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
                    )
            
            # Re-enable sorting
            self.file_tree.setSortingEnabled(sorting_enabled)
        
        except PermissionError:
            if parent_item:
                error_item = QTreeWidgetItem(parent_item)
            else:
                error_item = QTreeWidgetItem(self.file_tree)
            error_item.setText(0, "⚠️ Permission Denied")
            error_item.setText(1, "Error")
    
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
        
        if item.childCount() == 1:
            child = item.child(0)
            if child.data(0, Qt.ItemDataRole.UserRole) == "placeholder":
                item.removeChild(child)
                self.populate_tree(item_path, item)
                
                # Apply filters to the newly expanded items
                filter_func = self.get_current_filter_func()
                self.apply_filter_recursive(item, filter_func)
    
    def on_file_select(self):
        """Handle file selection"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            self.preview_widget.clear_preview()
            return
        
        item = selected_items[0]
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if file_path and file_path != "placeholder" and os.path.isfile(file_path):
            self.preview_widget.preview_file(file_path)
        else:
            self.preview_widget.clear_preview()
    
    def clear_cache(self):
        """Clear the preview cache"""
        self.preview_manager.clear_cache()
        QMessageBox.information(self, "Cache Cleared", "Preview cache has been cleared.")