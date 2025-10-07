#!/usr/bin/env python3
"""
LSX Editor - Main widget (refactored)
Orchestrates file operations, conversions, and UI updates
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt

from .lsx_editor_ui import LSXEditorUI
from .lsx_file_handler import LSXFileHandler
from .lsx_converter import LSXConverter
from ....data.parsers.larian_parser import UniversalBG3Parser


class LSXEditor(QWidget):
    """Universal BG3 file editor supporting LSX, LSJ, and LSF formats"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        self.parser = UniversalBG3Parser()
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        
        # File state
        self.current_file = None
        self.current_format = None
        self.modified = False
        self.original_file_for_conversion = None
        
        # Initialize parser
        if self.wine_wrapper:
            self.parser.set_wine_wrapper(self.wine_wrapper)
        
        # Create UI
        self.ui = LSXEditorUI(self)
        self.setup_layout()
        
        # Create handlers
        self.file_handler = LSXFileHandler(self, self.wine_wrapper, self.parser, self.settings_manager)
        self.converter = LSXConverter(self, self.wine_wrapper, self.parser, self.settings_manager)
        
        # Connect signals
        self.connect_signals()
        
        # Initial state
        self.update_button_states()
    
    def setup_layout(self):
        """Setup main layout"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Add toolbar
        layout.addLayout(self.ui.toolbar_layout)
        
        # Add text editor
        layout.addWidget(self.ui.text_editor)
    
    def connect_signals(self):
        """Connect UI signals to handlers"""
        # File operations
        self.ui.open_btn.clicked.connect(self.open_file)
        self.ui.save_btn.clicked.connect(self.save_file)
        self.ui.save_as_btn.clicked.connect(self.save_as_file)
        
        # Conversions
        self.ui.convert_lsx_btn.clicked.connect(lambda: self.convert_to_format('lsx'))
        self.ui.convert_lsj_btn.clicked.connect(lambda: self.convert_to_format('lsj'))
        self.ui.convert_lsf_btn.clicked.connect(lambda: self.convert_to_format('lsf'))
        self.ui.cancel_btn.clicked.connect(self.cancel_conversion)
        
        # Tools
        self.ui.validate_btn.clicked.connect(self.validate_file)
        self.ui.format_btn.clicked.connect(self.format_file)
        
        # Text changes
        self.ui.text_editor.textChanged.connect(self.on_text_change)
    
    def open_file(self):
        """Open file dialog and load selected file"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open BG3 File", initial_dir,
            "All BG3 Files (*.lsx *.lsj *.lsf);;LSX Files (*.lsx);;LSJ Files (*.lsj);;LSF Files (*.lsf);;XML Files (*.xml);;JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.file_handler.load_file(file_path, self.ui)
    
    def save_file(self):
        """Save current file"""
        if not self.current_file:
            self.save_as_file()
            return
        
        self.file_handler.save_file(self.current_file, self.ui)
    
    def save_as_file(self):
        """Save as new file"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        # Determine default extension and filter
        default_ext = f".{self.current_format}" if self.current_format else ".lsx"
        
        # Suggest filename
        if hasattr(self, 'original_file_for_conversion') and self.original_file_for_conversion:
            base_name = os.path.splitext(os.path.basename(self.original_file_for_conversion))[0]
            suggested_name = f"{base_name}_converted{default_ext}"
            initial_path = os.path.join(initial_dir, suggested_name)
        else:
            initial_path = initial_dir
        
        # File filter
        if self.current_format == 'lsf':
            file_filter = "LSF Files (*.lsf);;All Files (*.*)"
        else:
            file_filter = "LSX Files (*.lsx);;LSJ Files (*.lsj);;XML Files (*.xml);;JSON Files (*.json);;All Files (*.*)"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save BG3 File", initial_path, file_filter
        )
        
        if file_path:
            self.file_handler.save_as_file(file_path, self.ui)
    
    def convert_to_format(self, target_format):
        """Convert current file to specified format"""
        # Validation
        if not self.current_file and not self.has_content():
            QMessageBox.warning(self, "Warning", "No file or content loaded")
            return
        
        if self.current_format == target_format:
            QMessageBox.information(self, "Info", f"File is already in {target_format.upper()} format")
            return
        
        # Check if save needed
        if self.modified:
            reply = QMessageBox.question(
                self, "Save Changes",
                "Save current changes before conversion?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        # Start conversion
        self.converter.convert_to_format(
            self.current_format,
            target_format,
            self.current_file,
            self.ui
        )
    
    def cancel_conversion(self):
        """Cancel ongoing conversion"""
        self.converter.cancel_conversion()
    
    def validate_file(self):
        """Validate current file"""
        self.file_handler.validate_file(self.ui)
    
    def format_file(self):
        """Format/prettify current file"""
        self.file_handler.format_file(self.ui)
    
    def has_content(self):
        """Check if editor has meaningful content"""
        content = self.ui.text_editor.toPlainText().strip()
        
        # Consider LSF preview content as valid
        if content.startswith("<!-- LSF File:") and "Converted Successfully" in content:
            return True
        
        return bool(content) and not content.startswith("<!-- LSF File:")
    
    def update_button_states(self):
        """Update button enabled states"""
        has_file = self.current_file is not None
        has_content = self.has_content()
        has_wine = self.wine_wrapper is not None
        
        # File operations
        self.ui.save_btn.setEnabled(self.modified)
        self.ui.save_as_btn.setEnabled(has_file or self.modified)
        self.ui.validate_btn.setEnabled(has_file or self.modified)
        self.ui.format_btn.setEnabled(has_file or self.modified)
        
        # Conversions (need wine for LSF)
        conversion_enabled = (has_file or has_content) and has_wine
        self.ui.convert_lsx_btn.setEnabled(conversion_enabled and self.current_format != 'lsx')
        self.ui.convert_lsj_btn.setEnabled(conversion_enabled and self.current_format != 'lsj')
        self.ui.convert_lsf_btn.setEnabled(conversion_enabled and self.current_format != 'lsf')
    
    def on_text_change(self):
        """Handle text changes"""
        if not self.modified:
            self.modified = True
            if self.current_file:
                self.ui.status_label.setText(f"Modified: {os.path.basename(self.current_file)}")
            else:
                self.ui.status_label.setText("Modified: Converted content (use Save As)")
            self.update_button_states()