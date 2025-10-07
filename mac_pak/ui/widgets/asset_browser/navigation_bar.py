#!/usr/bin/env python3
"""
Enhanced navigation bar with breadcrumb navigation
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QLineEdit, QComboBox, QLabel, QFileDialog, 
                            QMessageBox, QScrollArea, QFrame, QStyle)
from PyQt6.QtCore import pyqtSignal, Qt

class BreadcrumbButton(QPushButton):
    """Custom button for breadcrumb navigation"""
    
    clicked_with_path = pyqtSignal(str)
    
    def __init__(self, text, path, parent=None, icon=None):
        super().__init__(text, parent)
        self.path = path
        if icon:
            self.setIcon(icon)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #3478f6;
                font-weight: 400;
                font-size: 12px;
                padding: 2px 4px;
                text-align: left;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(52, 120, 246, 0.1);
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: rgba(52, 120, 246, 0.15);
            }
        """)
        self.clicked.connect(lambda: self.clicked_with_path.emit(self.path))


class NavigationBar(QWidget):
    """Enhanced navigation toolbar with breadcrumb navigation"""
    
    # Signals
    directory_changed = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    clear_cache_requested = pyqtSignal()
    
    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        
        self.settings_manager = settings_manager
        self.current_directory = None
        self.breadcrumb_buttons = []
        
        self.setup_ui()
        self.connect_signals()
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Load recent folders if available
        if settings_manager:
            self.update_recent_folders()
    
    def setup_ui(self):
        """Setup enhanced navigation bar UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        
        # Top row: Main controls
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        # Up button with icon
        self.up_btn = QPushButton("Up")
        self.up_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent))

        self.up_btn.setEnabled(False)
        self.up_btn.setToolTip("Go to parent directory")
        top_layout.addWidget(self.up_btn)
        
        # Path edit field
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Enter path, drag folder here, or browse...")
        top_layout.addWidget(self.path_edit, 1)
        
        # Browse button with icon
        self.browse_btn = QPushButton(" Browse")
        self.browse_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.browse_btn.setToolTip("Browse for a folder")
        top_layout.addWidget(self.browse_btn)
        
        # Refresh button with icon
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setToolTip("Refresh current view")
        top_layout.addWidget(self.refresh_btn)
        
        # Clear cache button
        self.clear_cache_btn = QPushButton("🗑️ Clear Cache")
        self.clear_cache_btn.setToolTip("Clear preview cache")
        top_layout.addWidget(self.clear_cache_btn)
        
        # Recent folders dropdown
        recent_label = QLabel("Recent:")
        top_layout.addWidget(recent_label)
        
        self.recent_combo = QComboBox()
        self.recent_combo.setMinimumWidth(200)
        self.recent_combo.setMaximumWidth(250)
        self.recent_combo.addItem("Select recent folder...")
        top_layout.addWidget(self.recent_combo)
        
        main_layout.addLayout(top_layout)
        
        # Bottom row: Breadcrumb navigation
        breadcrumb_frame = QFrame()
        breadcrumb_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #d1d1d6;
                border-radius: 6px;
                padding: 0px;
            }
        """)
        breadcrumb_layout = QHBoxLayout(breadcrumb_frame)
        breadcrumb_layout.setContentsMargins(4, 0, 4, 0)
        breadcrumb_layout.setSpacing(0)
        
        # Scrollable breadcrumb area
        self.breadcrumb_scroll = QScrollArea()
        self.breadcrumb_scroll.setWidgetResizable(True)
        self.breadcrumb_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.breadcrumb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.breadcrumb_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.breadcrumb_scroll.setMaximumHeight(30)
        self.breadcrumb_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                height: 6px;
                background-color: transparent;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #c0c0c0;
                border-radius: 3px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        self.breadcrumb_container = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_container)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(0)
        self.breadcrumb_layout.addStretch()
        
        self.breadcrumb_scroll.setWidget(self.breadcrumb_container)
        breadcrumb_layout.addWidget(self.breadcrumb_scroll)
        
        main_layout.addWidget(breadcrumb_frame)
    
    def connect_signals(self):
        """Connect widget signals"""
        self.up_btn.clicked.connect(self.go_up)
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        self.browse_btn.clicked.connect(self.browse_folder)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.clear_cache_btn.clicked.connect(self.clear_cache_requested.emit)
        self.recent_combo.currentTextChanged.connect(self.load_recent_folder)
    
    def set_directory(self, directory):
        """Set the current directory and update UI"""
        if not directory or not os.path.exists(directory):
            return
        
        self.current_directory = directory
        self.path_edit.setText(directory)
        
        # Enable up button if not at root
        parent = str(Path(directory).parent)
        self.up_btn.setEnabled(parent != directory)
        
        # Update breadcrumbs
        self.update_breadcrumbs(directory)
        
        # Add to recent folders
        self.add_to_recent(directory)
    
    def update_breadcrumbs(self, directory):
        """Update breadcrumb navigation trail"""
        # Clear existing breadcrumbs
        for btn in self.breadcrumb_buttons:
            btn.deleteLater()
        self.breadcrumb_buttons.clear()
        
        # Properly clear all widgets from layout
        while self.breadcrumb_layout.count() > 0:
            item = self.breadcrumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Remove stretch
        while self.breadcrumb_layout.count() > 0:
            self.breadcrumb_layout.takeAt(0)
        
        # Build breadcrumb path
        path = Path(directory)
        parts = []
        
        # Build path parts
        current = path
        while current != current.parent:
            parts.insert(0, (current.name or str(current), str(current)))
            current = current.parent
        
        # Add root with home icon
        hd_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DriveHDIcon)
        parts.insert(0, ("", str(current), hd_icon))
        
        # Create breadcrumb buttons
        for i, part_data in enumerate(parts):
            # Unpack with optional icon
            if len(part_data) == 3:
                name, full_path, icon = part_data
            else:
                name, full_path = part_data
                if name == 'Desktop':
                    icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)
                else:
                    icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            
            # Add separator (skip for first item)
            # Add separator (skip for first item)
            if i > 0:
                separator_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                separator = QLabel()
                separator.setPixmap(separator_icon.pixmap(12, 12))  # Adjust size as needed
                separator.setStyleSheet("""
                    padding: 2px 4px;
                    margin-top: 0px;
                    background-color: transparent;
                    border: none;
                """)
                self.breadcrumb_layout.addWidget(separator)
            
            # Add breadcrumb button
            if i == 0:
                # First item is root with icon
                display_name = name if name else ""
            else:
                display_name = name if name else "Root"
                # Truncate long folder names
                if len(display_name) > 25:
                    display_name = display_name[:22] + "..."
            
            btn = BreadcrumbButton(display_name, full_path, self, icon)
            btn.clicked_with_path.connect(self.directory_changed.emit)
            self.breadcrumb_layout.addWidget(btn)
            self.breadcrumb_buttons.append(btn)
            
            # Make last button bold and darker
            if i == len(parts) - 1:
                btn.setStyleSheet(btn.styleSheet().replace("color: #3478f6;", "color: #1d1d1f;") + """
                    QPushButton {
                        font-weight: 500;
                    }
                """)
        
        self.breadcrumb_layout.addStretch()
    
    def go_up(self):
        """Navigate to parent directory"""
        if self.current_directory:
            parent = str(Path(self.current_directory).parent)
            if parent != self.current_directory:
                self.directory_changed.emit(parent)
    
    def navigate_to_path(self):
        """Navigate to the path in the edit field"""
        path = self.path_edit.text().strip()
        if path and os.path.exists(path) and os.path.isdir(path):
            self.directory_changed.emit(path)
        else:
            QMessageBox.warning(self, "Invalid Path", "The specified path does not exist or is not a directory.")
    
    def browse_folder(self):
        """Browse for a folder using native dialog"""
        initial_dir = str(Path.home())
        if self.settings_manager:
            initial_dir = self.settings_manager.get("working_directory", initial_dir)
        
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Extracted PAK Folder", 
            initial_dir
        )
        
        if folder_path:
            self.directory_changed.emit(folder_path)
    
    def load_recent_folder(self, combo_text):
        """Load a folder from the recent files dropdown"""
        if not combo_text or combo_text.startswith("Select recent"):
            return
        
        # Extract path from "Name - Path" format
        if " - " in combo_text:
            folder_path = combo_text.split(" - ", 1)[1]
        else:
            folder_path = combo_text
        
        if folder_path and os.path.exists(folder_path):
            self.directory_changed.emit(folder_path)
    
    def add_to_recent(self, folder_path):
        """Add folder to recent files list"""
        if not self.settings_manager:
            return
        
        recent_folders = self.settings_manager.get("recent_asset_folders", [])
        
        if folder_path in recent_folders:
            recent_folders.remove(folder_path)
        
        recent_folders.insert(0, folder_path)
        recent_folders = recent_folders[:10]  # Keep only 10 most recent
        
        self.settings_manager.set("recent_asset_folders", recent_folders)
        self.update_recent_folders()
    
    def update_recent_folders(self):
        """Update the recent folders dropdown"""
        if not self.settings_manager:
            return
        
        recent_folders = self.settings_manager.get("recent_asset_folders", [])
        
        self.recent_combo.clear()
        self.recent_combo.addItem("Select recent folder...")
        
        for folder in recent_folders:
            if os.path.exists(folder):
                folder_name = os.path.basename(folder) or folder
                self.recent_combo.addItem(f"{folder_name} - {folder}")
    
    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drop event"""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.directory_changed.emit(path)
                event.acceptProposedAction()