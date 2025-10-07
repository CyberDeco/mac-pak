#!/usr/bin/env python3
"""
LSX Editor UI - Handles all UI element creation and layout
Updated with reorganized toolbar and search functionality

Replace: mac_pak/ui/widgets/universal_editor/lsx_editor_ui.py
"""

from PyQt6.QtWidgets import (
    QHBoxLayout, QPushButton, QTextEdit, QLabel, QFrame, QVBoxLayout, QComboBox
)
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtCore import Qt
from ...editors.syntax_highlighter import LSXSyntaxHighlighter
from .lsx_search_widget import LSXSearchWidget


class LSXEditorUI:
    """UI components for LSX Editor"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # Create text editor first (needed for search widget)
        self.text_editor = self.create_text_editor()
        
        # Create search widget
        self.search_widget = LSXSearchWidget(self.text_editor, parent)
        
        # Create toolbar
        self.toolbar_layout = self.create_toolbar()
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
    
    def create_toolbar(self):
        """Create the reorganized toolbar with logical grouping"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(3)
        
        # === FILE OPERATIONS GROUP ===
        self.open_btn = QPushButton("📂 Open")
        self.open_btn.setToolTip("Open file (Cmd+O)")
        toolbar.addWidget(self.open_btn)
        
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setToolTip("Save file (Cmd+S)")
        toolbar.addWidget(self.save_btn)
        
        self.save_as_btn = QPushButton("Save As...")
        self.save_as_btn.setToolTip("Save as new file (Cmd+Shift+S)")
        toolbar.addWidget(self.save_as_btn)
        
        # Separator
        toolbar.addWidget(self._create_separator())
        
        # === EDIT TOOLS GROUP ===
        self.search_btn = QPushButton("🔍 Find")
        self.search_btn.setToolTip("Find and Replace (Cmd+F)")
        toolbar.addWidget(self.search_btn)
        
        self.format_btn = QPushButton("✨ Format")
        self.format_btn.setToolTip("Prettify/format code")
        toolbar.addWidget(self.format_btn)
        
        self.validate_btn = QPushButton("✓ Validate")
        self.validate_btn.setToolTip("Validate file structure")
        toolbar.addWidget(self.validate_btn)
        
        # Separator
        toolbar.addWidget(self._create_separator())
        
        # === CONVERSION GROUP ===
        convert_label = QLabel("Convert:")
        convert_label.setStyleSheet("font-weight: 600; color: #666;")
        toolbar.addWidget(convert_label)
        
        self.convert_lsx_btn = QPushButton("LSX")
        self.convert_lsx_btn.setToolTip("Convert to LSX (XML) format")
        self.convert_lsx_btn.setMaximumWidth(60)
        toolbar.addWidget(self.convert_lsx_btn)
        
        self.convert_lsj_btn = QPushButton("LSJ")
        self.convert_lsj_btn.setToolTip("Convert to LSJ (JSON) format")
        self.convert_lsj_btn.setMaximumWidth(60)
        toolbar.addWidget(self.convert_lsj_btn)
        
        self.convert_lsf_btn = QPushButton("LSF")
        self.convert_lsf_btn.setToolTip("Convert to LSF (Binary) format")
        self.convert_lsf_btn.setMaximumWidth(60)
        toolbar.addWidget(self.convert_lsf_btn)
        
        # Cancel button (hidden by default)
        self.cancel_btn = QPushButton("✕ Cancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setStyleSheet("QPushButton { background-color: #ff3b30; color: white; font-weight: bold; }")
        toolbar.addWidget(self.cancel_btn)
        
        # === STATUS GROUP (Right side) ===
        toolbar.addStretch()
        
        # Format indicator
        self.format_label = QLabel("Format: None")
        self.format_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 600;
                color: #333;
            }
        """)
        toolbar.addWidget(self.format_label)
        
        # Status message
        self.status_label = QLabel("No file loaded")
        self.status_label.setStyleSheet("color: #666; padding: 0 10px;")
        toolbar.addWidget(self.status_label)
        
        return toolbar
    
    def create_text_editor(self):
        """Create the text editor with syntax highlighting"""
        editor = QTextEdit()
        editor.setFont(QFont("Monaco", 12))
        editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        # Remove border from text editor since container has the border
        editor.setStyleSheet("QTextEdit { border: none; background-color: white; }")
        
        # Setup syntax highlighter
        self.highlighter = LSXSyntaxHighlighter(editor.document())
        
        return editor
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # File operations
        self.open_shortcut = QShortcut(QKeySequence.StandardKey.Open, self.parent)
        self.open_shortcut.activated.connect(self.parent.open_file)
        
        self.save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self.parent)
        self.save_shortcut.activated.connect(self.parent.save_file)
        
        self.save_as_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self.parent)
        self.save_as_shortcut.activated.connect(self.parent.save_as_file)
        
        # Find shortcuts
        self.find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self.parent)
        self.find_shortcut.activated.connect(self.show_search)
        
        self.find_next_shortcut = QShortcut(QKeySequence.StandardKey.FindNext, self.parent)
        self.find_next_shortcut.activated.connect(self.search_widget.find_next)
        
        self.find_prev_shortcut = QShortcut(QKeySequence.StandardKey.FindPrevious, self.parent)
        self.find_prev_shortcut.activated.connect(self.search_widget.find_previous)
        
        self.replace_shortcut = QShortcut(QKeySequence.StandardKey.Replace, self.parent)
        self.replace_shortcut.activated.connect(self.show_search_with_replace)
    
    def show_search(self):
        """Show search widget"""
        cursor = self.text_editor.textCursor()
        selected_text = cursor.selectedText() if cursor.hasSelection() else ""
        self.search_widget.show_search(selected_text)
    
    def show_search_with_replace(self):
        """Show search widget with focus on replace field"""
        cursor = self.text_editor.textCursor()
        selected_text = cursor.selectedText() if cursor.hasSelection() else ""
        self.search_widget.show_search(selected_text)
        self.search_widget.replace_edit.setFocus()
    
    def _create_separator(self):
        """Create a vertical separator"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("QFrame { color: #d0d0d0; margin: 2px 5px; }")
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
        self.search_btn.setEnabled(enabled)
        
        # Show/hide cancel button
        self.cancel_btn.setVisible(converting)
        
        # Update status
        if converting:
            self.status_label.setText("Converting...")
            self.status_label.setStyleSheet("color: #007aff; font-weight: 600;")
        else:
            self.status_label.setStyleSheet("color: #666;")
    
    def update_format_badge(self, format_type):
        """Update the format badge with color coding"""
        if not format_type or format_type == 'unknown':
            self.format_label.setText("Format: None")
            self.format_label.setStyleSheet("""
                QLabel {
                    background-color: #f0f0f0;
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: 600;
                    color: #333;
                }
            """)
        else:
            format_upper = format_type.upper()
            self.format_label.setText(f"Format: {format_upper}")
            
            # Color code by format
            if format_type == 'lsx':
                bg_color = "#e3f2fd"  # Light blue
                border_color = "#2196f3"
                text_color = "#1976d2"
            elif format_type == 'lsj':
                bg_color = "#f3e5f5"  # Light purple
                border_color = "#9c27b0"
                text_color = "#7b1fa2"
            elif format_type == 'lsf':
                bg_color = "#fff3e0"  # Light orange
                border_color = "#ff9800"
                text_color = "#f57c00"
            else:
                bg_color = "#f0f0f0"
                border_color = "#d0d0d0"
                text_color = "#333"
            
            self.format_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: 600;
                    color: {text_color};
                }}
            """)