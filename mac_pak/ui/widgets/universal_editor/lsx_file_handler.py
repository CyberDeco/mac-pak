#!/usr/bin/env python3
"""
LSX File Handler - Handles file loading, saving, validation, and formatting
"""

import os
import json
import xml.etree.ElementTree as ET
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer
from ...dialogs.progress_dialog import ProgressDialog


class LSXFileHandler:
    """Handles file I/O operations for LSX Editor"""
    
    def __init__(self, editor, wine_wrapper, parser, settings_manager):
        self.editor = editor
        self.wine_wrapper = wine_wrapper
        self.parser = parser
        self.settings_manager = settings_manager
    
    def load_file(self, file_path, ui):
        """Load and display any supported file format"""
        try:
            # Store original file
            self.editor.original_file_for_conversion = file_path
            
            # Detect format
            file_format = self.parser.detect_file_format(file_path)
            
            # Handle LSF files
            if file_format == 'lsf':
                if not self.wine_wrapper:
                    QMessageBox.critical(self.editor, "Error", "LSF support requires divine.exe integration")
                    return
                
                content = self._create_lsf_placeholder(file_path)
            else:
                # Read text files
                with open(file_path, 'rb') as f:
                    content = f.read().decode('utf-8')
            
            # Update editor - revert to original approach
            ui.text_editor.clear()
            
            # Show progress dialog for large files
            show_progress = len(content) > 50000  # Show for files > 50KB
            progress_dialog = None
            
            if show_progress:
                progress_dialog = ProgressDialog(
                    self.editor,
                    "Loading File",
                    cancel_text=None,  # Can't cancel
                    min_val=0,
                    max_val=100
                )
                progress_dialog.update_progress(30, "Loading content...")
                progress_dialog.show()
                # Force UI update
                progress_dialog.repaint()
            
            ui.text_editor.insertPlainText(content)
            
            if show_progress and progress_dialog:
                progress_dialog.update_progress(100, "Complete")
                QTimer.singleShot(100, progress_dialog.close)  # Close after brief delay
            
            # Update state
            self.editor.current_file = file_path
            self.editor.current_format = file_format
            self.editor.modified = False
            
            # Update UI
            ui.status_label.setText(f"Loaded: {os.path.basename(file_path)}")
            ui.format_label.setText(f"Format: {file_format.upper()}")
            
            # Update settings
            if self.settings_manager:
                self.settings_manager.set("working_directory", os.path.dirname(file_path))
            
            self.editor.update_button_states()
            
        except Exception as e:
            QMessageBox.critical(self.editor, "Error", f"Could not open file: {e}")
    
    def save_file(self, file_path, ui):
        """Save file with validation"""
        # Check if game file
        if self._is_game_file(file_path):
            reply = QMessageBox.warning(
                self.editor, "Game File Warning",
                "This appears to be a file from the game directory or extracted PAK.\n\n"
                "Modifying game files directly can cause issues.\n"
                "Save as new file instead?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Trigger save as from main editor
                self.editor.save_as_file()
            return
        
        try:
            content = ui.text_editor.toPlainText()
            
            # Handle LSF warning
            if self.editor.current_format == 'lsf':
                reply = QMessageBox.question(
                    self.editor, "LSF File Warning",
                    "This is an LSF file converted to text. Save as LSX instead?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    lsx_file = file_path.replace('.lsf', '.lsx')
                    with open(lsx_file, 'wb') as f:
                        f.write(content.encode('utf-8'))
                    QMessageBox.information(self.editor, "Saved", f"Saved as LSX: {lsx_file}")
                    return
                elif reply == QMessageBox.StandardButton.Cancel:
                    return
            
            # Normal save
            with open(file_path, 'wb') as f:
                f.write(content.encode('utf-8'))
            
            self.editor.modified = False
            ui.status_label.setText(f"Saved: {os.path.basename(file_path)}")
            self.editor.update_button_states()
            
        except Exception as e:
            QMessageBox.critical(self.editor, "Error", f"Could not save file: {e}")
    
    def save_as_file(self, file_path, ui):
        """Save file to new location"""
        try:
            # Handle binary LSF files
            if self.editor.current_format == 'lsf' and hasattr(self.editor.converter, 'converted_binary_file'):
                import shutil
                binary_file = self.editor.converter.converted_binary_file
                if binary_file and os.path.exists(binary_file):
                    shutil.copy2(binary_file, file_path)
                    
                    # Cleanup
                    try:
                        os.remove(binary_file)
                        self.editor.converter.converted_binary_file = None
                    except:
                        pass
                    
                    QMessageBox.information(self.editor, "Saved", f"LSF file saved: {os.path.basename(file_path)}")
                else:
                    raise Exception("Binary LSF file not found")
            else:
                # Save text content
                content = ui.text_editor.toPlainText()
                with open(file_path, 'wb') as f:
                    f.write(content.encode('utf-8'))
            
            # Update state
            self.editor.current_file = file_path
            
            # Update format based on extension
            new_format = self.parser.detect_file_format(file_path)
            if new_format != 'unknown':
                self.editor.current_format = new_format
                ui.format_label.setText(f"Format: {new_format.upper()}")
                if hasattr(ui, 'highlighter') and new_format != 'lsf':
                    ui.highlighter.current_format = new_format
            
            # Update settings
            if self.settings_manager:
                self.settings_manager.set("working_directory", os.path.dirname(file_path))
            
            self.editor.modified = False
            ui.status_label.setText(f"Saved: {os.path.basename(file_path)}")
            self.editor.update_button_states()
            
        except Exception as e:
            QMessageBox.critical(self.editor, "Error", f"Could not save file: {e}")
    
    def validate_file(self, ui):
        """Validate current file based on format"""
        if not self.editor.current_file and not self.editor.modified:
            QMessageBox.warning(self.editor, "Warning", "No file loaded")
            return
        
        content = ui.text_editor.toPlainText()
        
        try:
            if self.editor.current_format == 'lsx':
                ET.fromstring(content)
                QMessageBox.information(self.editor, "Validation", "Valid LSX/XML structure!")
            elif self.editor.current_format == 'lsj':
                json.loads(content)
                QMessageBox.information(self.editor, "Validation", "Valid LSJ/JSON structure!")
            elif self.editor.current_format == 'lsf':
                QMessageBox.information(self.editor, "Validation", "LSF files cannot be validated in text format")
            else:
                QMessageBox.warning(self.editor, "Validation", "Unknown file format")
                
        except (ET.ParseError, json.JSONDecodeError) as e:
            QMessageBox.critical(self.editor, "Validation Error", f"Format Error:\n{e}")
    
    def format_file(self, ui):
        """Format/prettify current file content"""
        if not self.editor.current_file and not self.editor.modified:
            QMessageBox.warning(self.editor, "Warning", "No file loaded")
            return
        
        content = ui.text_editor.toPlainText()
        
        try:
            if self.editor.current_format == 'lsx':
                formatted = self._format_xml(content)
            elif self.editor.current_format == 'lsj':
                formatted = self._format_json(content)
            else:
                QMessageBox.information(self.editor, "Info", f"Formatting not supported for {self.editor.current_format}")
                return
            
            # Replace content
            ui.text_editor.setPlainText(formatted)
            
        except Exception as e:
            QMessageBox.critical(self.editor, "Format Error", f"Could not format file: {e}")
    
    def _format_xml(self, content):
        """Format XML content"""
        root = ET.fromstring(content)
        self._indent_xml(root)
        formatted = ET.tostring(root, encoding='unicode')
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + formatted
    
    def _format_json(self, content):
        """Format JSON content"""
        data = json.loads(content)
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _indent_xml(self, elem, level=0):
        """Helper to indent XML elements"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                self._indent_xml(child, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    def _create_lsf_placeholder(self, file_path):
        """Create placeholder text for LSF files"""
        return (
            f"<!-- LSF File: {os.path.basename(file_path)} -->\n"
            "<!-- LSF files are binary and cannot be previewed -->\n"
            "<!-- Use the 'Convert to LSX' button to convert this file -->\n"
            "<!-- It will not be saved until you click 'Save As' -->"
        )
    
    def _is_game_file(self, file_path):
        """Check if file is from game directory"""
        if not file_path:
            return False
        
        game_indicators = [
            '/steamapps/common/baldurs gate 3',
            '/baldur\'s gate 3',
            '/Contents/Data',
            'Gustav',
            'extracted',
            'temp'
        ]
        
        file_path_lower = file_path.lower()
        return any(indicator in file_path_lower for indicator in game_indicators)