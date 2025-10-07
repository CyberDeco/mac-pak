#!/usr/bin/env python3
"""
PAK Tools Tab - Main UI
Coordinates extract, create, and list operations
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, 
    QTextEdit, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .drop_label import DropLabel
from .extract_operations import ExtractOperations
from .create_operations import CreateOperations
from .list_operations import ListOperations


class PakToolsTab(QWidget):
    """Main PAK tools UI - delegates to operation modules"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__()
        self.parent_window = parent
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        
        # Initialize operation modules
        self.extract_ops = ExtractOperations(self, wine_wrapper, settings_manager)
        self.create_ops = CreateOperations(self, wine_wrapper, settings_manager)
        self.list_ops = ListOperations(self, wine_wrapper, settings_manager)
        
        # UI state
        self.progress_dialog = None
        
        self.setup_ui()
    
    def create_styled_group(self, title):
        """Create a styled QGroupBox"""
        group = QGroupBox(title)
        group.setProperty("header", "h2")
        return group
    
    def setup_ui(self):
        """Setup main UI layout"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("PAK Operations", self)
        title_label.setProperty("header", "h1")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Operation groups
        operations_layout = QHBoxLayout()
        operations_layout.setSpacing(20)
        
        # Extract group
        extract_group = self.create_styled_group("")
        extract_layout = QVBoxLayout(extract_group)
        
        self.extract_btn = QPushButton("📦 Extract PAK File")
        self.extract_btn.clicked.connect(self.extract_ops.extract_pak_file)
        extract_layout.addWidget(self.extract_btn)
        
        self.list_btn = QPushButton("📋 List PAK Contents")
        self.list_btn.clicked.connect(self.list_ops.list_pak_contents)
        extract_layout.addWidget(self.list_btn)
        
        self.individual_extract_btn = QPushButton("📄 Extract Individual Files")
        self.individual_extract_btn.clicked.connect(self.extract_ops.show_individual_extraction_dialog)
        extract_layout.addWidget(self.individual_extract_btn)
        
        operations_layout.addWidget(extract_group)
        
        # Create group
        create_group = self.create_styled_group("")
        create_layout = QVBoxLayout(create_group)
        
        self.create_btn = QPushButton("🔧 Create PAK from Folder")
        self.create_btn.clicked.connect(self.create_ops.create_pak_file)
        create_layout.addWidget(self.create_btn)
        
        self.rebuild_btn = QPushButton("🔧 Rebuild Modified PAK")
        self.rebuild_btn.clicked.connect(self.create_ops.rebuild_pak_file)
        create_layout.addWidget(self.rebuild_btn)
        
        self.validate_btn = QPushButton("✓ Validate Mod Structure")
        self.validate_btn.clicked.connect(self.create_ops.validate_mod_structure)
        create_layout.addWidget(self.validate_btn)
        
        operations_layout.addWidget(create_group)
        
        drop_group = self.create_styled_group("")
        drop_layout = QVBoxLayout(drop_group)
        self.drop_label = DropLabel(self)
        self.drop_label.file_dropped.connect(self.handle_dropped_pak)
        drop_layout.addWidget(self.drop_label)
        operations_layout.addWidget(drop_group)
        
        layout.addLayout(operations_layout)
        
        # Results area
        results_group = self.create_styled_group("Operation Results")
        results_layout = QVBoxLayout(results_group)
        
        clear_results_layout = QHBoxLayout()
        clear_results_layout.addStretch()
        clear_results_btn = QPushButton("Clear Results")
        clear_results_btn.clicked.connect(self.clear_results)
        clear_results_layout.addWidget(clear_results_btn)
        results_layout.addLayout(clear_results_layout)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Monaco", 10))
        self.results_text.setPlaceholderText("Operation results will appear here...")
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
    
    def set_pak_buttons_enabled(self, enabled):
        """Enable/disable all operation buttons"""
        self.extract_btn.setEnabled(enabled)
        self.create_btn.setEnabled(enabled)
        self.rebuild_btn.setEnabled(enabled)
        self.list_btn.setEnabled(enabled)
        self.validate_btn.setEnabled(enabled)
        self.individual_extract_btn.setEnabled(enabled)
    
    def add_result_text(self, text):
        """Add text to results area (thread-safe)"""
        self.results_text.append(text.rstrip())
        cursor = self.results_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.results_text.setTextCursor(cursor)
    
    def clear_results(self):
        """Clear results text area"""
        self.results_text.clear()
    
    def handle_dropped_pak(self, pak_file):
        """Handle dropped PAK files"""
        self.add_result_text(f"Dropped file: {os.path.basename(pak_file)}")
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("PAK File Dropped")
        msg.setText(f"What would you like to do with {os.path.basename(pak_file)}?")
        
        extract_btn = msg.addButton("Extract", QMessageBox.ButtonRole.ActionRole)
        list_btn = msg.addButton("List Contents", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.exec()
        
        if msg.clickedButton() == extract_btn:
            pak_dir = os.path.dirname(pak_file)
            pak_name = os.path.splitext(os.path.basename(pak_file))[0]
            dest_dir = os.path.join(pak_dir, f"{pak_name}_extracted")
            self.extract_ops._start_extract_pak_async(pak_file, dest_dir)
        elif msg.clickedButton() == list_btn:
            self.list_ops._start_list_pak_async(pak_file)