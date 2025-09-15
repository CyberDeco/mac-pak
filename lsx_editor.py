#!/usr/bin/env python3
"""
BG3 LSX Tools - PyQt6 Version
Universal editor supporting LSX, LSJ, and LSF formats with syntax highlighting
"""

import xml.etree.ElementTree as ET
import json
import os
import re
import threading
from pathlib import Path
from collections import defaultdict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QFileDialog, QMessageBox, QTabWidget, QListWidget,
    QSplitter, QFrame, QGroupBox, QComboBox, QProgressBar,
    QFormLayout, QLineEdit, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter, QTextDocument

# Import your existing backend
from larian_parser import UniversalBG3Parser

class LSXSyntaxHighlighter(QSyntaxHighlighter):
    """PyQt6 syntax highlighter for LSX/JSON files"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_format = 'lsx'
        self.setup_highlighting_rules()
    
    def setup_highlighting_rules(self):
        """Setup highlighting formats"""
        # XML/LSX formats
        self.xml_tag_format = QTextCharFormat()
        self.xml_tag_format.setForeground(QColor("#0066CC"))
        self.xml_tag_format.setFontWeight(QFont.Weight.Bold)
        
        self.xml_attribute_format = QTextCharFormat()
        self.xml_attribute_format.setForeground(QColor("#006600"))
        
        self.xml_value_format = QTextCharFormat()
        self.xml_value_format.setForeground(QColor("#CC0000"))
        
        # JSON/LSJ formats
        self.json_key_format = QTextCharFormat()
        self.json_key_format.setForeground(QColor("#0066CC"))
        self.json_key_format.setFontWeight(QFont.Weight.Bold)
        
        self.json_string_format = QTextCharFormat()
        self.json_string_format.setForeground(QColor("#CC0000"))
        
        self.json_number_format = QTextCharFormat()
        self.json_number_format.setForeground(QColor("#FF6600"))
        
        self.json_bool_format = QTextCharFormat()
        self.json_bool_format.setForeground(QColor("#9900CC"))
        self.json_bool_format.setFontWeight(QFont.Weight.Bold)
        
        # Common formats
        self.bg3_important_format = QTextCharFormat()
        self.bg3_important_format.setForeground(QColor("#9900CC"))
        self.bg3_important_format.setFontWeight(QFont.Weight.Bold)
        
        self.uuid_format = QTextCharFormat()
        self.uuid_format.setForeground(QColor("#FF6600"))
        self.uuid_format.setFontWeight(QFont.Weight.Bold)
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#666666"))
        self.comment_format.setFontItalic(True)
    
    def set_format(self, file_format):
        """Set the current file format"""
        self.current_format = file_format
        self.rehighlight()
    
    def highlightBlock(self, text):
        """Highlight a block of text"""
        if self.current_format == 'lsx':
            self.highlight_xml(text)
        elif self.current_format == 'lsj':
            self.highlight_json(text)
    
    def highlight_xml(self, text):
        """Highlight XML/LSX syntax"""
        # Comments
        comment_pattern = re.compile(r'<!--.*?-->')
        for match in comment_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.comment_format)
        
        # XML tags
        tag_pattern = re.compile(r'<[^>]+>')
        for match in tag_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.xml_tag_format)
        
        # Attributes and values
        attr_pattern = re.compile(r'(\w+)="([^"]*)"')
        for match in attr_pattern.finditer(text):
            attr_name, attr_value = match.groups()
            
            # Attribute name
            attr_start = match.start(1)
            attr_length = len(attr_name)
            
            # Check if it's BG3-important
            bg3_important_attrs = ["UUID", "Author", "Name", "Description", "Version64", "MD5", "Folder"]
            if attr_name in bg3_important_attrs:
                self.setFormat(attr_start, attr_length, self.bg3_important_format)
            else:
                self.setFormat(attr_start, attr_length, self.xml_attribute_format)
            
            # Attribute value
            value_start = match.start(2)
            value_length = len(attr_value)
            
            # Check if it's a UUID
            uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
            if re.match(uuid_pattern, attr_value):
                self.setFormat(value_start, value_length, self.uuid_format)
            else:
                self.setFormat(value_start, value_length, self.xml_value_format)
    
    def highlight_json(self, text):
        """Highlight JSON/LSJ syntax"""
        # JSON string keys
        key_pattern = re.compile(r'"([^"]+)"\s*:')
        for match in key_pattern.finditer(text):
            key_start = match.start(1)
            key_length = len(match.group(1))
            self.setFormat(key_start, key_length, self.json_key_format)
        
        # JSON string values
        string_pattern = re.compile(r':\s*"([^"]*)"')
        for match in string_pattern.finditer(text):
            value = match.group(1)
            value_start = match.start(1)
            value_length = len(value)
            
            # Check if it's a UUID
            uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
            if re.match(uuid_pattern, value):
                self.setFormat(value_start, value_length, self.uuid_format)
            else:
                self.setFormat(value_start, value_length, self.json_string_format)
        
        # JSON numbers
        number_pattern = re.compile(r':\s*(-?\d+\.?\d*)')
        for match in number_pattern.finditer(text):
            num_start = match.start(1)
            num_length = len(match.group(1))
            self.setFormat(num_start, num_length, self.json_number_format)
        
        # JSON booleans and null
        bool_pattern = re.compile(r':\s*(true|false|null)')
        for match in bool_pattern.finditer(text):
            bool_start = match.start(1)
            bool_length = len(match.group(1))
            self.setFormat(bool_start, bool_length, self.json_bool_format)


class FileConversionThread(QThread):
    """Thread for file conversions"""
    
    progress_updated = pyqtSignal(int, str)
    conversion_finished = pyqtSignal(bool, dict)
    
    def __init__(self, bg3_tool, source_path, target_path, source_format, target_format):
        super().__init__()
        self.bg3_tool = bg3_tool
        self.source_path = source_path
        self.target_path = target_path
        self.source_format = source_format
        self.target_format = target_format
    
    def run(self):
        """Run the conversion"""
        try:
            self.progress_updated.emit(20, "Starting conversion...")
            
            if self.source_format == self.target_format:
                # Just copy the file
                import shutil
                shutil.copy2(self.source_path, self.target_path)
                self.conversion_finished.emit(True, {"message": "File copied (same format)"})
                return
            
            self.progress_updated.emit(40, "Converting file...")
            
            # Use divine.exe for conversions
            success, output = self.bg3_tool.run_divine_command(
                action="convert-resource",
                source=self.bg3_tool.mac_to_wine_path(self.source_path),
                destination=self.bg3_tool.mac_to_wine_path(self.target_path),
                input_format=self.source_format,
                output_format=self.target_format
            )
            
            self.progress_updated.emit(100, "Conversion complete!")
            
            result_data = {
                "success": success,
                "output": output,
                "source_path": self.source_path,
                "target_path": self.target_path
            }
            
            self.conversion_finished.emit(success, result_data)
            
        except Exception as e:
            self.conversion_finished.emit(False, {"error": str(e)})


class BatchConversionThread(QThread):
    """Thread for batch conversions"""
    
    progress_updated = pyqtSignal(int, str)
    conversion_finished = pyqtSignal(list)
    
    def __init__(self, bg3_tool, file_list, target_format, output_dir=None):
        super().__init__()
        self.bg3_tool = bg3_tool
        self.file_list = file_list
        self.target_format = target_format
        self.output_dir = output_dir
    
    def run(self):
        """Run batch conversion"""
        results = []
        total_files = len(self.file_list)
        
        for i, source_file in enumerate(self.file_list):
            percentage = int((i / total_files) * 100)
            self.progress_updated.emit(percentage, f"Converting {os.path.basename(source_file)}...")
            
            try:
                # Determine output path
                if self.output_dir:
                    basename = os.path.splitext(os.path.basename(source_file))[0]
                    target_file = os.path.join(self.output_dir, f"{basename}.{self.target_format}")
                else:
                    target_file = os.path.splitext(source_file)[0] + f".{self.target_format}"
                
                # Detect source format
                source_format = self.detect_format(source_file)
                
                # Convert
                if source_format == self.target_format:
                    import shutil
                    shutil.copy2(source_file, target_file)
                    success, output = True, "File copied (same format)"
                else:
                    success, output = self.bg3_tool.run_divine_command(
                        action="convert-resource",
                        source=self.bg3_tool.mac_to_wine_path(source_file),
                        destination=self.bg3_tool.mac_to_wine_path(target_file),
                        input_format=source_format,
                        output_format=self.target_format
                    )
                
                results.append({
                    'source': source_file,
                    'target': target_file,
                    'success': success,
                    'output': output
                })
                
            except Exception as e:
                results.append({
                    'source': source_file,
                    'target': '',
                    'success': False,
                    'output': str(e)
                })
        
        self.progress_updated.emit(100, "Batch conversion complete!")
        self.conversion_finished.emit(results)
    
    def detect_format(self, file_path):
        """Detect file format from extension"""
        ext = os.path.splitext(file_path)[1].lower()
        format_map = {'.lsx': 'lsx', '.lsj': 'lsj', '.lsf': 'lsf'}
        return format_map.get(ext, 'lsx')


class LSXEditor(QWidget):
    """Universal BG3 file editor supporting LSX, LSJ, and LSF formats"""
    
    def __init__(self, parent=None, settings_manager=None, bg3_tool=None):
        super().__init__(parent)
        self.parser = UniversalBG3Parser()
        self.bg3_tool = bg3_tool
        self.current_file = None
        self.current_format = None
        self.modified = False
        self.settings_manager = settings_manager
        
        if self.bg3_tool:
            self.parser.set_bg3_tool(self.bg3_tool)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the editor interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        # File operations
        self.open_btn = QPushButton("Open File")
        self.open_btn.clicked.connect(self.open_file)
        toolbar_layout.addWidget(self.open_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_file)
        toolbar_layout.addWidget(self.save_btn)
        
        self.save_as_btn = QPushButton("Save As")
        self.save_as_btn.clicked.connect(self.save_as_file)
        toolbar_layout.addWidget(self.save_as_btn)
        
        # Separator
        toolbar_layout.addWidget(self.create_separator())
        
        # Format conversions
        self.convert_lsx_btn = QPushButton("Convert to LSX")
        self.convert_lsx_btn.clicked.connect(self.convert_to_lsx)
        toolbar_layout.addWidget(self.convert_lsx_btn)
        
        self.convert_lsj_btn = QPushButton("Convert to LSJ")
        self.convert_lsj_btn.clicked.connect(self.convert_to_lsj)
        toolbar_layout.addWidget(self.convert_lsj_btn)
        
        self.convert_lsf_btn = QPushButton("Convert to LSF")
        self.convert_lsf_btn.clicked.connect(self.convert_to_lsf)
        toolbar_layout.addWidget(self.convert_lsf_btn)
        
        # Separator
        toolbar_layout.addWidget(self.create_separator())
        
        # Tools
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.clicked.connect(self.validate_file)
        toolbar_layout.addWidget(self.validate_btn)
        
        self.format_btn = QPushButton("Format")
        self.format_btn.clicked.connect(self.format_file)
        toolbar_layout.addWidget(self.format_btn)
        
        # Status labels
        toolbar_layout.addStretch()
        self.format_label = QLabel("Format: None")
        toolbar_layout.addWidget(self.format_label)
        
        self.status_label = QLabel("No file loaded")
        toolbar_layout.addWidget(self.status_label)
        
        layout.addLayout(toolbar_layout)
        
        # Text editor
        self.text_editor = QTextEdit()
        self.text_editor.setFont(QFont("Monaco", 12))
        self.text_editor.textChanged.connect(self.on_text_change)
        
        # Setup syntax highlighter
        self.highlighter = LSXSyntaxHighlighter(self.text_editor.document())
        #self.highlighter = None
        
        layout.addWidget(self.text_editor)
        
        # Initially disable some buttons
        self.update_button_states()
    
    def create_separator(self):
        """Create a vertical separator"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        return separator
    
    def update_button_states(self):
        """Update button enabled states based on current file"""
        has_file = self.current_file is not None
        has_bg3_tool = self.bg3_tool is not None
        
        self.save_btn.setEnabled(has_file and self.modified)
        self.save_as_btn.setEnabled(has_file)
        self.validate_btn.setEnabled(has_file)
        self.format_btn.setEnabled(has_file)
        
        # Conversion buttons need divine.exe
        conversion_enabled = has_file and has_bg3_tool
        self.convert_lsx_btn.setEnabled(conversion_enabled)
        self.convert_lsj_btn.setEnabled(conversion_enabled)
        self.convert_lsf_btn.setEnabled(conversion_enabled)
    
    def open_file(self):
        """Open LSX, LSJ, or LSF files"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open BG3 File", initial_dir,
            "All BG3 Files (*.lsx *.lsj *.lsf);;LSX Files (*.lsx);;LSJ Files (*.lsj);;LSF Files (*.lsf);;XML Files (*.xml);;JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """Load and display any supported file format"""
        try:
            
            # Detect format first
            file_format = self.parser.detect_file_format(file_path)
            self.current_format = file_format
            
            # Handle LSF files differently
            if file_format == 'lsf':
                if not self.bg3_tool:
                    QMessageBox.critical(self, "Error", "LSF support requires divine.exe integration")
                    return
                
                content = f"<!-- LSF File: {os.path.basename(file_path)} -->\n"
                content += "<!-- LSF files must be converted to LSX for editing -->\n"
                content += "<!-- Use 'Convert to LSX' button to convert this file -->"
            else:
                # Read text files directly
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Set content on plain document
            self.text_editor.clear()
            self.text_editor.insertPlainText(content)
            
            # Set file info
            self.current_file = file_path
            self.current_format = self.parser.detect_file_format(file_path)
            self.modified = False
            self.status_label.setText(f"Loaded: {os.path.basename(file_path)}")
            self.format_label.setText(f"Format: {self.current_format.upper()}")
            
            if self.settings_manager:
                self.settings_manager.set("working_directory", os.path.dirname(file_path))
            
            self.update_button_states()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file: {e}")

    # def load_file(self, file_path):
    #     """Load and display any supported file format - minimal version"""
    #     try:
    #         # Just read the file normally - no fancy processing
    #         with open(file_path, 'r', encoding='utf-8') as f:
    #             content = f.read()
            
    #         # Set the content directly
    #         self.text_editor.clear()
    #         self.text_editor.insertPlainText(content)
            
    #         # Set basic info
    #         self.current_file = file_path
    #         self.current_format = self.parser.detect_file_format(file_path)
    #         self.modified = False
            
    #         # Update labels
    #         self.status_label.setText(f"Loaded: {os.path.basename(file_path)}")
    #         self.format_label.setText(f"Format: {self.current_format.upper()}")
            
    #         # Update buttons
    #         self.update_button_states()
            
    #     except Exception as e:
    #         QMessageBox.critical(self, "Error", f"Could not open file: {e}")
    
    def load_lsf_file(self, file_path):
        """Load LSF file by converting to LSX first"""
        if not self.bg3_tool:
            QMessageBox.critical(self, "Error", "LSF support requires divine.exe integration")
            return
        
        # Show a simple message and disable UI during conversion
        self.text_editor.setPlainText("Converting LSF file, please wait...")
        self.text_editor.setEnabled(False)
        
        # Create conversion thread
        temp_lsx = file_path + '.temp.lsx'
        self.lsf_conversion_thread = FileConversionThread(
            self.bg3_tool, file_path, temp_lsx, 'lsf', 'lsx'
        )
        self.lsf_conversion_thread.conversion_finished.connect(self.lsf_conversion_completed)
        self.lsf_conversion_thread.start()
    
    def lsf_conversion_completed(self, success, result_data):
        """Handle LSF conversion completion"""
        self.text_editor.setEnabled(True)
        
        if success:
            temp_lsx = result_data.get("target_path")
            try:
                if temp_lsx and os.path.exists(temp_lsx):
                    with open(temp_lsx, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Add note about LSF conversion
                    note = "<!-- This LSF file has been converted to LSX for editing -->\n"
                    self.text_editor.setPlainText(note + content)
                    
                    # Clean up
                    os.remove(temp_lsx)
                else:
                    raise Exception("Converted file not found")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load converted LSF file: {e}")
                self.text_editor.setPlainText("")
        else:
            error_msg = result_data.get("error", "Conversion failed")
            QMessageBox.critical(self, "Error", f"Could not convert LSF file: {error_msg}")
            self.text_editor.setPlainText("")
    
    def save_file(self):
        """Save file with format preservation"""
        if not self.current_file:
            self.save_as_file()
            return
        
        try:
            content = self.text_editor.toPlainText()
            
            # For LSF files, warn about saving as text
            if self.current_format == 'lsf':
                reply = QMessageBox.question(
                    self, "LSF File Warning",
                    "This is an LSF file converted to text. Saving will create an LSX file.\n"
                    "Save as LSX instead?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Save as LSX
                    lsx_file = self.current_file.replace('.lsf', '.lsx')
                    with open(lsx_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    QMessageBox.information(self, "Saved", f"Saved as LSX: {lsx_file}")
                    return
                elif reply == QMessageBox.StandardButton.Cancel:
                    return
            
            # Normal save
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.modified = False
            self.status_label.setText(f"Saved: {os.path.basename(self.current_file)}")
            self.update_button_states()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {e}")
    
    def save_as_file(self):
        """Save as new file with format selection"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        # Determine default extension
        default_ext = ".lsx"
        if self.current_format:
            default_ext = f".{self.current_format}"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save BG3 File", initial_dir,
            "LSX Files (*.lsx);;LSJ Files (*.lsj);;XML Files (*.xml);;JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            self.current_file = file_path
            
            # Update format based on extension
            new_format = self.parser.detect_file_format(file_path)
            if new_format != 'unknown':
                self.current_format = new_format
                self.format_label.setText(f"Format: {new_format.upper()}")
                self.highlighter.set_format(new_format)
            
            # Update working directory
            if self.settings_manager:
                self.settings_manager.set("working_directory", os.path.dirname(file_path))
            
            self.save_file()
    
    def convert_to_lsx(self):
        """Convert current file to LSX format"""
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "No file loaded")
            return
        
        if self.current_format == 'lsx':
            QMessageBox.information(self, "Info", "File is already in LSX format")
            return
        
        self.perform_conversion('lsx')
    
    def convert_to_lsj(self):
        """Convert current file to LSJ format"""
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "No file loaded")
            return
        
        if self.current_format == 'lsj':
            QMessageBox.information(self, "Info", "File is already in LSJ format")
            return
        
        # LSJ conversion is complex and may not be universally supported
        QMessageBox.information(self, "Info", "LSJ conversion not yet implemented")
    
    def convert_to_lsf(self):
        """Convert current file to LSF format"""
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "No file loaded")
            return
        
        if self.current_format == 'lsf':
            QMessageBox.information(self, "Info", "File is already in LSF format")
            return
        
        self.perform_conversion('lsf')
    
    def perform_conversion(self, target_format):
        """Perform file format conversion"""
        if not self.bg3_tool:
            QMessageBox.critical(self, "Error", f"Conversion to {target_format.upper()} requires divine.exe")
            return
        
        # Save current content first if modified
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
        
        # Choose output file
        output_file, _ = QFileDialog.getSaveFileName(
            self, f"Save as {target_format.upper()}",
            os.path.splitext(self.current_file)[0] + f".{target_format}",
            f"{target_format.upper()} Files (*.{target_format});;All Files (*.*)"
        )
        
        if not output_file:
            return
        
        # Start conversion thread
        self.conversion_thread = FileConversionThread(
            self.bg3_tool, self.current_file, output_file, 
            self.current_format, target_format
        )
        self.conversion_thread.conversion_finished.connect(self.conversion_completed)
        self.conversion_thread.start()
        
        # Show progress (simplified for now)
        QMessageBox.information(self, "Converting", f"Converting to {target_format.upper()}...")
    
    def conversion_completed(self, success, result_data):
        """Handle completed conversion"""
        if success:
            QMessageBox.information(self, "Success", f"Conversion completed successfully!")
            
            # Ask if user wants to open the converted file
            reply = QMessageBox.question(
                self, "Open Converted File",
                "Would you like to open the converted file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.load_file(result_data.get("target_path", ""))
        else:
            error_msg = result_data.get("error", result_data.get("output", "Unknown error"))
            QMessageBox.critical(self, "Conversion Failed", f"Error: {error_msg}")
    
    def validate_file(self):
        """Validate current file based on format"""
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "No file loaded")
            return
        
        content = self.text_editor.toPlainText()
        
        try:
            if self.current_format == 'lsx':
                ET.fromstring(content)
                QMessageBox.information(self, "Validation", "Valid LSX/XML structure!")
            elif self.current_format == 'lsj':
                json.loads(content)
                QMessageBox.information(self, "Validation", "Valid LSJ/JSON structure!")
            elif self.current_format == 'lsf':
                QMessageBox.information(self, "Validation", "LSF files cannot be validated in text format")
            else:
                QMessageBox.warning(self, "Validation", "Unknown file format")
                
        except (ET.ParseError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Validation Error", f"Format Error:\n{e}")
    
    def format_file(self):
        """Format/prettify current file content"""
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "No file loaded")
            return
        
        content = self.text_editor.toPlainText()
        
        try:
            if self.current_format == 'lsx':
                # Format XML
                root = ET.fromstring(content)
                self.indent_xml(root)
                formatted = ET.tostring(root, encoding='unicode')
                formatted = '<?xml version="1.0" encoding="UTF-8"?>\n' + formatted
                
            elif self.current_format == 'lsj':
                # Format JSON
                data = json.loads(content)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
                
            else:
                QMessageBox.information(self, "Info", f"Formatting not supported for {self.current_format}")
                return
            
            # Replace content
            self.text_editor.setPlainText(formatted)
            
        except Exception as e:
            QMessageBox.critical(self, "Format Error", f"Could not format file: {e}")
    
    def indent_xml(self, elem, level=0):
        """Helper to indent XML elements"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                self.indent_xml(child, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    def on_text_change(self):
        """Handle text changes"""
        if not self.modified:
            self.modified = True
            if self.current_file:
                self.status_label.setText(f"Modified: {os.path.basename(self.current_file)}")
            self.update_button_states()


class BatchProcessor(QWidget):
    """Batch file processing interface"""
    
    def __init__(self, parent=None, settings_manager=None, bg3_tool=None):
        super().__init__(parent)
        self.bg3_tool = bg3_tool
        self.settings_manager = settings_manager
        self.file_list = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup batch processing interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("Batch File Processing")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        
        # File list
        self.file_listbox = QListWidget()
        self.file_listbox.setMinimumHeight(150)
        file_layout.addWidget(self.file_listbox)
        
        # File buttons
        file_btn_layout = QHBoxLayout()
        
        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        file_btn_layout.addWidget(self.add_files_btn)
        
        self.add_dir_btn = QPushButton("Add Directory")
        self.add_dir_btn.clicked.connect(self.add_directory)
        file_btn_layout.addWidget(self.add_dir_btn)
        
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_selected)
        file_btn_layout.addWidget(self.remove_btn)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_files)
        file_btn_layout.addWidget(self.clear_btn)
        
        file_btn_layout.addStretch()
        file_layout.addLayout(file_btn_layout)
        
        layout.addWidget(file_group)
        
        # Operations group
        ops_group = QGroupBox("Batch Operations")
        ops_layout = QVBoxLayout(ops_group)
        
        # Format conversion
        conv_layout = QHBoxLayout()
        conv_layout.addWidget(QLabel("Convert to:"))
        
        self.target_format_combo = QComboBox()
        self.target_format_combo.addItems(["lsx", "lsj", "lsf"])
        conv_layout.addWidget(self.target_format_combo)
        
        self.convert_btn = QPushButton("Convert All")
        self.convert_btn.clicked.connect(self.batch_convert)
        conv_layout.addWidget(self.convert_btn)
        
        conv_layout.addStretch()
        ops_layout.addLayout(conv_layout)
        
        # Output directory
        output_layout = QFormLayout()
        
        self.output_dir_edit = QLineEdit()
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(self.output_dir_edit)
        
        self.browse_output_btn = QPushButton("Browse")
        self.browse_output_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout.addWidget(self.browse_output_btn)
        
        output_layout.addRow("Output Directory:", output_dir_layout)
        ops_layout.addLayout(output_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        ops_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready")
        ops_layout.addWidget(self.progress_label)
        
        layout.addWidget(ops_group)
        
        # Results
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
        self.update_button_states()
    
    def update_button_states(self):
        """Update button states based on current state"""
        has_files = len(self.file_list) > 0
        has_bg3_tool = self.bg3_tool is not None
        
        self.convert_btn.setEnabled(has_files and has_bg3_tool)
        self.remove_btn.setEnabled(has_files)
        self.clear_btn.setEnabled(has_files)
    
    def add_files(self):
        """Add individual files to batch list"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select BG3 Files", initial_dir,
            "All BG3 Files (*.lsx *.lsj *.lsf);;LSX Files (*.lsx);;LSJ Files (*.lsj);;LSF Files (*.lsf);;All Files (*)"
        )
        
        for file_path in files:
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                self.file_listbox.addItem(os.path.basename(file_path))
        
        self.update_button_states()
    
    def add_directory(self):
        """Add all BG3 files from a directory"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", initial_dir)
        
        if directory:
            # Find all BG3 files in directory
            extensions = ['.lsx', '.lsj', '.lsf']
            found_files = []
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        file_path = os.path.join(root, file)
                        if file_path not in self.file_list:
                            found_files.append(file_path)
            
            # Add to list
            for file_path in found_files:
                self.file_list.append(file_path)
                rel_path = os.path.relpath(file_path, directory)
                self.file_listbox.addItem(rel_path)
            
            if found_files:
                self.results_text.append(f"Added {len(found_files)} files from {directory}")
            else:
                self.results_text.append(f"No BG3 files found in {directory}")
            
            self.update_button_states()
    
    def remove_selected(self):
        """Remove selected files from list"""
        current_row = self.file_listbox.currentRow()
        if current_row >= 0:
            del self.file_list[current_row]
            self.file_listbox.takeItem(current_row)
            self.update_button_states()
    
    def clear_files(self):
        """Clear all files from list"""
        self.file_list.clear()
        self.file_listbox.clear()
        self.update_button_states()
    
    def browse_output_dir(self):
        """Browse for output directory"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", initial_dir)
        if directory:
            self.output_dir_edit.setText(directory)
    
    def batch_convert(self):
        """Perform batch conversion"""
        if not self.file_list:
            QMessageBox.warning(self, "Warning", "No files selected for conversion")
            return
        
        if not self.bg3_tool:
            QMessageBox.critical(self, "Error", "Batch conversion requires divine.exe integration")
            return
        
        target_format = self.target_format_combo.currentText()
        output_dir = self.output_dir_edit.text() or None
        
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create output directory: {e}")
                return
        
        # Clear previous results
        self.results_text.clear()
        self.results_text.append(f"Starting batch conversion to {target_format.upper()}...")
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start conversion thread
        self.conversion_thread = BatchConversionThread(
            self.bg3_tool, self.file_list, target_format, output_dir
        )
        self.conversion_thread.progress_updated.connect(self.update_progress)
        self.conversion_thread.conversion_finished.connect(self.batch_conversion_finished)
        self.conversion_thread.start()
        
        # Disable convert button during operation
        self.convert_btn.setEnabled(False)
    
    def update_progress(self, percentage, message):
        """Update progress display"""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
    
    def batch_conversion_finished(self, results):
        """Handle completed batch conversion"""
        # Hide progress bar
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Conversion complete!")
        
        # Display results
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        self.results_text.append(f"\nConversion complete!")
        self.results_text.append(f"Successful: {successful}")
        self.results_text.append(f"Failed: {failed}\n")
        
        # Show detailed results
        for result in results:
            status = "✅" if result['success'] else "❌"
            source_name = os.path.basename(result['source'])
            
            if result['success']:
                target_name = os.path.basename(result['target'])
                self.results_text.append(f"{status} {source_name} -> {target_name}")
            else:
                self.results_text.append(f"{status} {source_name}: {result['output']}")
        
        # Re-enable convert button
        self.convert_btn.setEnabled(True)


class UniversalEditorTab(QWidget):
    """Combined LSX Editor and Batch Processor in a tabbed interface"""
    
    def __init__(self, parent=None, settings_manager=None, bg3_tool=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.bg3_tool = bg3_tool
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the tabbed interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # LSX Editor tab
        self.editor = LSXEditor(
            parent=self,
            settings_manager=self.settings_manager,
            bg3_tool=self.bg3_tool
        )
        self.tab_widget.addTab(self.editor, "File Editor")
        
        # Batch Processor tab
        self.batch_processor = BatchProcessor(
            parent=self,
            settings_manager=self.settings_manager,
            bg3_tool=self.bg3_tool
        )
        self.tab_widget.addTab(self.batch_processor, "Batch Processing")
        
        layout.addWidget(self.tab_widget)