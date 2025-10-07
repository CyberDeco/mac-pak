#!/usr/bin/env python3
"""
Navigation bar widget for the asset browser - handles path navigation and recent folders
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLineEdit, QComboBox, QLabel, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal


class NavigationBar(QWidget):
    """Navigation toolbar for browsing directories"""
    
    # Signals
    directory_changed = pyqtSignal(str)  # Emits when directory changes
    refresh_requested = pyqtSignal()  # Emits when refresh is clicked
    clear_cache_requested = pyqtSignal()  # Emits when clear cache is clicked
    
    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        
        self.settings_manager = settings_manager
        self.current_directory = None
        
        self.setup_ui()
        self.connect_signals()
        
        # Load recent folders if available
        if settings_manager:
            self.update_recent_folders()
    
    def setup_ui(self):
        """Setup navigation bar UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Up button
        self.up_btn = QPushButton("↑ Up")
        self.up_btn.setEnabled(False)
        layout.addWidget(self.up_btn)
        
        # Path edit field
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Enter path or browse...")
        layout.addWidget(self.path_edit, 1)
        
        # Browse button
        self.browse_btn = QPushButton("Browse")
        layout.addWidget(self.browse_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        layout.addWidget(self.refresh_btn)
        
        # Clear cache button
        self.clear_cache_btn = QPushButton("Clear Cache")
        layout.addWidget(self.clear_cache_btn)
        
        # Recent folders dropdown
        recent_label = QLabel("Recent:")
        layout.addWidget(recent_label)
        
        self.recent_combo = QComboBox()
        self.recent_combo.setMinimumWidth(200)
        self.recent_combo.setMaximumWidth(250)
        self.recent_combo.addItem("Select recent folder...")
        layout.addWidget(self.recent_combo)
    
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
        self.path_edit.setToolTip(directory)
        
        # Update up button state
        parent_dir = os.path.dirname(directory)
        can_go_up = parent_dir and parent_dir != directory
        self.up_btn.setEnabled(can_go_up)
        
        # Save to settings and update recent
        if self.settings_manager:
            self.settings_manager.set("working_directory", directory)
            self.add_to_recent(directory)
    
    def go_up(self):
        """Navigate up one directory level"""
        if not self.current_directory:
            return
        
        parent_dir = os.path.dirname(self.current_directory)
        
        if parent_dir and parent_dir != self.current_directory:
            self.directory_changed.emit(parent_dir)
    
    def navigate_to_path(self):
        """Navigate to the path entered in the path field"""
        path = self.path_edit.text().strip()
        
        if not path:
            return
        
        # Expand user home directory
        path = os.path.expanduser(path)
        
        if os.path.exists(path) and os.path.isdir(path):
            self.directory_changed.emit(path)
        else:
            QMessageBox.warning(
                self, 
                "Invalid Path", 
                f"The path '{path}' does not exist or is not a directory."
            )
    
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