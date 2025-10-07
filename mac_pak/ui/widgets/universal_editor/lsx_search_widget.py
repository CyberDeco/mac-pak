#!/usr/bin/env python3
"""
LSX Search Widget - Find and Replace functionality for text editor
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, 
    QLabel, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor, QTextDocument, QColor, QPalette


class LSXSearchWidget(QWidget):
    """Search and replace widget for LSX editor"""
    
    # Signals
    closed = pyqtSignal()
    
    def __init__(self, text_editor, parent=None):
        super().__init__(parent)
        self.text_editor = text_editor
        self.last_search_pos = 0
        self.search_results_count = 0
        self.current_result_index = 0
        
        self.setup_ui()
        self.setVisible(False)
        
        # Style the widget
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#f0f0f0"))
        self.setPalette(palette)
        self.setMaximumHeight(120)
    
    def setup_ui(self):
        """Setup the search UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(5)
        
        # First row - Find
        find_layout = QHBoxLayout()
        
        find_label = QLabel("Find:")
        find_label.setMinimumWidth(50)
        find_layout.addWidget(find_label)
        
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Search text...")
        self.find_edit.returnPressed.connect(self.find_next)
        self.find_edit.textChanged.connect(self.on_search_text_changed)
        find_layout.addWidget(self.find_edit)
        
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self.find_previous)
        find_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.find_next)
        self.next_btn.setDefault(True)
        find_layout.addWidget(self.next_btn)

        # First close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setMaximumWidth(30)
        self.close_btn.clicked.connect(self.hide_search)
        find_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(find_layout)
        
        # Second row - Replace
        replace_layout = QHBoxLayout()
        
        replace_label = QLabel("Replace:")
        replace_label.setMinimumWidth(50)
        replace_layout.addWidget(replace_label)
        
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("Replacement text...")
        self.replace_edit.returnPressed.connect(self.replace_current)
        replace_layout.addWidget(self.replace_edit)
        
        self.replace_btn = QPushButton("Replace")
        self.replace_btn.clicked.connect(self.replace_current)
        replace_layout.addWidget(self.replace_btn)
        
        self.replace_all_btn = QPushButton("Replace All")
        self.replace_all_btn.clicked.connect(self.replace_all)
        replace_layout.addWidget(self.replace_all_btn)
        
        main_layout.addLayout(replace_layout)
        
        # Third row - Options and status
        options_layout = QHBoxLayout()
        
        self.case_sensitive_cb = QCheckBox("Case sensitive")
        self.case_sensitive_cb.stateChanged.connect(self.on_options_changed)
        options_layout.addWidget(self.case_sensitive_cb)
        
        self.whole_words_cb = QCheckBox("Whole words")
        self.whole_words_cb.stateChanged.connect(self.on_options_changed)
        options_layout.addWidget(self.whole_words_cb)
        
        self.regex_cb = QCheckBox("Regex")
        self.regex_cb.stateChanged.connect(self.on_options_changed)
        options_layout.addWidget(self.regex_cb)
        
        options_layout.addStretch()
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        options_layout.addWidget(self.status_label)
        
        main_layout.addLayout(options_layout)
    
    def show_search(self, find_text=""):
        """Show the search widget"""
        self.setVisible(True)
        if find_text:
            self.find_edit.setText(find_text)
        self.find_edit.setFocus()
        self.find_edit.selectAll()
        self.update_search_status()
    
    def hide_search(self):
        """Hide the search widget"""
        self.setVisible(False)
        self.clear_highlights()
        self.closed.emit()
    
    def on_search_text_changed(self):
        """Handle search text changes"""
        self.last_search_pos = 0
        self.update_search_status()
        
        # Highlight all matches
        if self.find_edit.text():
            self.highlight_all_matches()
    
    def on_options_changed(self):
        """Handle search option changes"""
        self.last_search_pos = 0
        self.update_search_status()
        if self.find_edit.text():
            self.highlight_all_matches()
    
    def get_search_flags(self):
        """Get QTextDocument search flags based on options"""
        flags = QTextDocument.FindFlag(0)
        
        if self.case_sensitive_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        
        if self.whole_words_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        
        return flags
    
    def find_next(self):
        """Find next occurrence"""
        search_text = self.find_edit.text()
        if not search_text:
            return
        
        flags = self.get_search_flags()
        
        # Start from current cursor position
        cursor = self.text_editor.textCursor()
        
        if self.regex_cb.isChecked():
            import re
            pattern_flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE
            pattern = re.compile(search_text, pattern_flags)
            
            # Search in text from current position
            text = self.text_editor.toPlainText()
            start_pos = cursor.position()
            
            match = pattern.search(text, start_pos)
            if match:
                # Found match
                cursor.setPosition(match.start())
                cursor.setPosition(match.end(), QTextCursor.MoveMode.KeepAnchor)
                self.text_editor.setTextCursor(cursor)
                self.text_editor.ensureCursorVisible()
                self.update_current_result_index()
                return True
            else:
                # Wrap around to beginning
                match = pattern.search(text, 0)
                if match:
                    cursor.setPosition(match.start())
                    cursor.setPosition(match.end(), QTextCursor.MoveMode.KeepAnchor)
                    self.text_editor.setTextCursor(cursor)
                    self.text_editor.ensureCursorVisible()
                    self.update_current_result_index()
                    return True
        else:
            # Standard text search
            found = self.text_editor.find(search_text, flags)
            
            if not found:
                # Wrap around to beginning
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.text_editor.setTextCursor(cursor)
                found = self.text_editor.find(search_text, flags)
            
            if found:
                self.update_current_result_index()
                return True
        
        # Not found
        self.status_label.setText("Not found")
        self.status_label.setStyleSheet("color: red;")
        return False
    
    def find_previous(self):
        """Find previous occurrence"""
        search_text = self.find_edit.text()
        if not search_text:
            return
        
        flags = self.get_search_flags()
        flags |= QTextDocument.FindFlag.FindBackward
        
        cursor = self.text_editor.textCursor()
        
        if self.regex_cb.isChecked():
            import re
            pattern_flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE
            pattern = re.compile(search_text, pattern_flags)
            
            text = self.text_editor.toPlainText()
            end_pos = cursor.position()
            
            # Find all matches before current position
            matches = list(pattern.finditer(text[:end_pos]))
            if matches:
                match = matches[-1]
                cursor.setPosition(match.start())
                cursor.setPosition(match.end(), QTextCursor.MoveMode.KeepAnchor)
                self.text_editor.setTextCursor(cursor)
                self.text_editor.ensureCursorVisible()
                self.update_current_result_index()
                return True
            else:
                # Wrap around to end
                matches = list(pattern.finditer(text))
                if matches:
                    match = matches[-1]
                    cursor.setPosition(match.start())
                    cursor.setPosition(match.end(), QTextCursor.MoveMode.KeepAnchor)
                    self.text_editor.setTextCursor(cursor)
                    self.text_editor.ensureCursorVisible()
                    self.update_current_result_index()
                    return True
        else:
            found = self.text_editor.find(search_text, flags)
            
            if not found:
                # Wrap around to end
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.text_editor.setTextCursor(cursor)
                found = self.text_editor.find(search_text, flags)
            
            if found:
                self.update_current_result_index()
                return True
        
        self.status_label.setText("Not found")
        self.status_label.setStyleSheet("color: red;")
        return False
    
    def replace_current(self):
        """Replace current selection"""
        cursor = self.text_editor.textCursor()
        
        if not cursor.hasSelection():
            # Find next first
            if not self.find_next():
                return
            cursor = self.text_editor.textCursor()
        
        # Check if selection matches search text
        search_text = self.find_edit.text()
        selected_text = cursor.selectedText()
        
        matches = False
        if self.case_sensitive_cb.isChecked():
            matches = (selected_text == search_text)
        else:
            matches = (selected_text.lower() == search_text.lower())
        
        if matches or self.regex_cb.isChecked():
            replacement_text = self.replace_edit.text()
            cursor.insertText(replacement_text)
            self.find_next()  # Move to next occurrence
            self.update_search_status()
    
    def replace_all(self):
        """Replace all occurrences"""
        search_text = self.find_edit.text()
        if not search_text:
            return
        
        replacement_text = self.replace_edit.text()
        
        # Move to beginning
        cursor = self.text_editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.text_editor.setTextCursor(cursor)
        
        replaced_count = 0
        
        if self.regex_cb.isChecked():
            import re
            pattern_flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE
            pattern = re.compile(search_text, pattern_flags)
            
            text = self.text_editor.toPlainText()
            new_text = pattern.sub(replacement_text, text)
            replaced_count = len(pattern.findall(text))
            
            if replaced_count > 0:
                cursor.select(QTextCursor.SelectionType.Document)
                cursor.insertText(new_text)
        else:
            flags = self.get_search_flags()
            
            while self.text_editor.find(search_text, flags):
                cursor = self.text_editor.textCursor()
                cursor.insertText(replacement_text)
                replaced_count += 1
        
        self.status_label.setText(f"Replaced {replaced_count} occurrence(s)")
        self.status_label.setStyleSheet("color: green;")
        self.update_search_status()
    
    def highlight_all_matches(self):
        """Highlight all matching occurrences"""
        self.clear_highlights()
        
        search_text = self.find_edit.text()
        if not search_text:
            return
        
        # Create extra selections for highlights
        extra_selections = []
        
        # Move to beginning
        cursor = self.text_editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        if self.regex_cb.isChecked():
            import re
            pattern_flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE
            pattern = re.compile(search_text, pattern_flags)
            
            text = self.text_editor.toPlainText()
            for match in pattern.finditer(text):
                selection = self.text_editor.ExtraSelection()
                selection.cursor = self.text_editor.textCursor()
                selection.cursor.setPosition(match.start())
                selection.cursor.setPosition(match.end(), QTextCursor.MoveMode.KeepAnchor)
                selection.format.setBackground(QColor("#FFFF00"))
                extra_selections.append(selection)
        else:
            flags = self.get_search_flags()
            self.text_editor.setTextCursor(cursor)
            
            while self.text_editor.find(search_text, flags):
                selection = self.text_editor.ExtraSelection()
                selection.cursor = self.text_editor.textCursor()
                selection.format.setBackground(QColor("#FFFF00"))
                extra_selections.append(selection)
        
        self.text_editor.setExtraSelections(extra_selections)
        self.search_results_count = len(extra_selections)
    
    def clear_highlights(self):
        """Clear all search highlights"""
        self.text_editor.setExtraSelections([])
        self.search_results_count = 0
        self.current_result_index = 0
    
    def update_search_status(self):
        """Update the status label with search results count"""
        search_text = self.find_edit.text()
        if not search_text:
            self.status_label.setText("")
            return
        
        # Count occurrences
        text = self.text_editor.toPlainText()
        
        if self.regex_cb.isChecked():
            import re
            try:
                pattern_flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE
                pattern = re.compile(search_text, pattern_flags)
                count = len(pattern.findall(text))
            except re.error:
                self.status_label.setText("Invalid regex")
                self.status_label.setStyleSheet("color: red;")
                return
        else:
            if self.case_sensitive_cb.isChecked():
                count = text.count(search_text)
            else:
                count = text.lower().count(search_text.lower())
        
        if count > 0:
            self.status_label.setText(f"{count} match(es)")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("No matches")
            self.status_label.setStyleSheet("color: red;")
    
    def update_current_result_index(self):
        """Update which result is currently selected"""
        if self.search_results_count == 0:
            return
        
        cursor = self.text_editor.textCursor()
        current_pos = cursor.position()
        
        # Simple estimation - could be more accurate
        self.current_result_index = (self.current_result_index % self.search_results_count) + 1
    
    def keyPressEvent(self, event):
        """Handle key presses"""
        if event.key() == Qt.Key.Key_Escape:
            self.hide_search()
        else:
            super().keyPressEvent(event)