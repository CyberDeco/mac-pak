#!/usr/bin/env python3
"""
LSX Editor UI - Handles all UI element creation and layout
"""

from PyQt6.QtWidgets import (
    QHBoxLayout, QPushButton, QTextEdit, QLabel, QFrame
)
from PyQt6.QtGui import QFont
from ...editors.syntax_highlighter import LSXSyntaxHighlighter


class LSXEditorUI:
    """UI components for LSX Editor"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # Create toolbar
        self.toolbar_layout = self.create_toolbar()
        
        # Create text editor
        self.text_editor = self.create_text_editor()
    
    def create_toolbar(self):
        """Create the toolbar with all buttons"""
        toolbar = QHBoxLayout()
        
        # File operations
        self.open_btn = QPushButton("Open File")
        toolbar.addWidget(self.open_btn)
        
        self.save_btn = QPushButton("Save")
        toolbar.addWidget(self.save_btn)
        
        self.save_as_btn = QPushButton("Save As")
        toolbar.addWidget(self.save_as_btn)
        
        # Separator
        toolbar.addWidget(self._create_separator())
        
        # Format conversions
        self.convert_lsx_btn = QPushButton("Convert to LSX")
        toolbar.addWidget(self.convert_lsx_btn)
        
        self.convert_lsj_btn = QPushButton("Convert to LSJ")
        toolbar.addWidget(self.convert_lsj_btn)
        
        self.convert_lsf_btn = QPushButton("Convert to LSF")
        toolbar.addWidget(self.convert_lsf_btn)
        
        # Cancel button (hidden by default)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setVisible(False)
        toolbar.addWidget(self.cancel_btn)
        
        # Separator
        toolbar.addWidget(self._create_separator())
        
        # Tools
        self.validate_btn = QPushButton("Validate")
        toolbar.addWidget(self.validate_btn)
        
        self.format_btn = QPushButton("Format")
        toolbar.addWidget(self.format_btn)
        
        # Status labels
        toolbar.addStretch()
        
        self.format_label = QLabel("Format: None")
        toolbar.addWidget(self.format_label)
        
        self.status_label = QLabel("No file loaded")
        toolbar.addWidget(self.status_label)
        
        return toolbar
    
    def create_text_editor(self):
        """Create the text editor with syntax highlighting"""
        editor = QTextEdit()
        editor.setFont(QFont("Monaco", 12))
        
        # Setup syntax highlighter
        self.highlighter = LSXSyntaxHighlighter(editor.document())
        
        return editor
    
    def _create_separator(self):
        """Create a vertical separator"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        return separator
    
    def set_conversion_state(self, converting):
        """Enable/disable UI during conversion"""
        enabled = not converting
        
        # Disable most buttons during conversion
        self.open_btn.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)
        self.save_as_btn.setEnabled(enabled)
        self.convert_lsx_btn.setEnabled(enabled)
        self.convert_lsj_btn.setEnabled(enabled)
        self.convert_lsf_btn.setEnabled(enabled)
        self.validate_btn.setEnabled(enabled)
        self.format_btn.setEnabled(enabled)
        
        # Show/hide cancel button
        self.cancel_btn.setVisible(converting)