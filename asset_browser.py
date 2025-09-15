#!/usr/bin/env python3
"""
BG3 Asset Browser - PyQt6 Version
Native Mac file browser with preview system
"""

import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QLabel, QPushButton, QLineEdit, QGroupBox, QScrollArea,
    QMessageBox, QFileDialog, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QPixmap, QPainter, QIcon

# Import your existing backend classes
from larian_parser import UniversalBG3Parser
from preview_manager import FilePreviewManager, get_file_icon

class FilePreviewThread(QThread):
    """Thread for handling file previews that might take time"""
    
    preview_ready = pyqtSignal(dict)  # preview_data
    progress_updated = pyqtSignal(int, str)  # percentage, message
    
    def __init__(self, preview_manager, file_path):
        super().__init__()
        self.preview_manager = preview_manager
        self.file_path = file_path
        self.cancelled = False
    
    def run(self):
        """Run preview generation in background"""
        try:
            file_ext = os.path.splitext(self.file_path)[1].lower()
            
            def progress_callback(percent, message):
                if not self.cancelled:
                    self.progress_updated.emit(percent, message)
            
            # Use the full preview system with progress
            preview_data = self.preview_manager.get_preview(
                self.file_path, use_cache=True, progress_callback=progress_callback
            )
            
            if not self.cancelled:
                self.preview_ready.emit(preview_data)
                
        except Exception as e:
            if not self.cancelled:
                error_data = {
                    'content': f"Error previewing file: {e}",
                    'thumbnail': None
                }
                self.preview_ready.emit(error_data)
    
    def cancel(self):
        """Cancel the preview operation"""
        self.cancelled = True

class PreviewWidget(QWidget):
    """Widget for displaying file previews with Mac styling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.preview_thread = None
    
    def setup_ui(self):
        """Setup preview widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setFont(QFont("SF Pro Text", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.file_label)
        
        header_layout.addStretch()
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(4)  # Thin Mac-style progress
        header_layout.addWidget(self.progress_bar)
        
        layout.addLayout(header_layout)
        
        # Thumbnail area
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setMinimumHeight(200)
        self.thumbnail_label.setMaximumHeight(200)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: #f8f8f8;
            }
        """)
        layout.addWidget(self.thumbnail_label)
        
        # Content area
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setFont(QFont("SF Mono", 11))  # Mac monospace
        self.content_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: white;
                padding: 8px;
            }
        """)
        layout.addWidget(self.content_text)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
    
    def preview_file(self, file_path, preview_manager):
        """Preview a file with progress indication"""
        if not file_path or not os.path.isfile(file_path):
            self.clear_preview()
            return
        
        # Cancel any existing preview
        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.cancel()
            self.preview_thread.quit()
            self.preview_thread.wait(1000)
        
        # Update header
        self.file_label.setText(os.path.basename(file_path))
        
        # Check if file is supported
        if not preview_manager.is_supported(file_path):
            self.show_unsupported_file(file_path, preview_manager)
            return
        
        # Check if this file might need progress indication
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.lsf', '.lsbs', '.lsbc', '.lsfx']:
            self.show_progress(True)
        
        # Start preview thread
        self.preview_thread = FilePreviewThread(preview_manager, file_path)
        self.preview_thread.preview_ready.connect(self.display_preview)
        self.preview_thread.progress_updated.connect(self.update_progress)
        self.preview_thread.start()
    
    def show_unsupported_file(self, file_path, preview_manager):
        """Show info for unsupported file types"""
        file_size = os.path.getsize(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        content = f"File: {os.path.basename(file_path)}\n"
        content += f"Size: {file_size:,} bytes\n"
        content += f"Type: {file_ext}\n"
        content += "-" * 50 + "\n\n"
        content += f"Unsupported file type: {file_ext}\n"
        content += "Supported types: " + ", ".join(preview_manager.get_supported_extensions())
        
        self.content_text.setPlainText(content)
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("📄\nUnsupported File")
        self.show_progress(False)
    
    def display_preview(self, preview_data):
        """Display preview data from thread"""
        self.show_progress(False)
        
        # Display content
        self.content_text.setPlainText(preview_data.get('content', ''))
        
        # Display thumbnail if available (for DDS files)
        if preview_data.get('thumbnail'):
            thumbnail = preview_data['thumbnail']
            # The thumbnail from preview_manager is already a PhotoImage/QPixmap
            if hasattr(thumbnail, 'width'):  # PhotoImage
                try:
                    # Convert PhotoImage to QPixmap if needed
                    # For now, just show text indicator
                    self.thumbnail_label.setText("🖼️\nThumbnail Available")
                except:
                    self.thumbnail_label.setText("🖼️\nPreview Available")
            else:
                self.thumbnail_label.setText("🖼️\nThumbnail Available")
        else:
            self.thumbnail_label.clear()
            self.thumbnail_label.setText("📄\nText Preview")
    
    def show_progress(self, show):
        """Show or hide progress indicators"""
        self.progress_bar.setVisible(show)
        self.progress_label.setVisible(show)
        
        if not show:
            self.progress_bar.setValue(0)
            self.progress_label.setText("")
    
    def update_progress(self, percentage, message):
        """Update progress display"""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
    
    def clear_preview(self):
        """Clear the preview display"""
        self.file_label.setText("No file selected")
        self.content_text.clear()
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("Select a file to preview")
        self.show_progress(False)

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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Asset Browser")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.browse_btn = QPushButton("Browse Folder")
        self.browse_btn.clicked.connect(self.browse_folder)
        toolbar_layout.addWidget(self.browse_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_view)
        toolbar_layout.addWidget(self.refresh_btn)
        
        self.clear_cache_btn = QPushButton("Clear Cache")
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        toolbar_layout.addWidget(self.clear_cache_btn)
        
        toolbar_layout.addStretch()
        
        # Search
        search_label = QLabel("Filter:")
        toolbar_layout.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search files...")
        self.search_edit.textChanged.connect(self.filter_files)
        self.search_edit.setMaximumWidth(200)
        toolbar_layout.addWidget(self.search_edit)
        
        layout.addLayout(toolbar_layout)
        
        # Main content - horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: File tree
        tree_frame = QFrame()
        tree_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(10, 10, 10, 10)
        
        tree_label = QLabel("Files")
        tree_label.setFont(QFont("SF Pro Text", 12, QFont.Weight.Bold))
        tree_layout.addWidget(tree_label)
        
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabel("Name")
        self.file_tree.setRootIsDecorated(True)
        self.file_tree.setUniformRowHeights(True)
        self.file_tree.setAnimated(True)  # Mac-style animations
        self.file_tree.itemSelectionChanged.connect(self.on_file_select)
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
        
        # Set splitter sizes (1/3 for tree, 2/3 for preview)
        splitter.setSizes([300, 600])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
    
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
            
            self.refresh_view()
    
    def refresh_view(self):
        """Refresh the file tree view"""
        if not self.current_directory:
            return
        
        self.file_tree.clear()
        self.populate_tree(self.current_directory, None)
        
        # Clear preview
        self.preview_widget.clear_preview()
    
    def populate_tree(self, directory, parent_item):
        """Populate tree with directory contents"""
        try:
            items = []
            
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
                    # Directory
                    tree_item.setText(0, f"📁 {item_name}")
                    tree_item.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                    )
                    # Add placeholder for lazy loading
                    placeholder = QTreeWidgetItem(tree_item)
                    placeholder.setText(0, "Loading...")
                    placeholder.setData(0, Qt.ItemDataRole.UserRole, "placeholder")
                else:
                    # File
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
        
        if file_path and os.path.isfile(file_path):
            self.preview_widget.preview_file(file_path, self.preview_manager)
        else:
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