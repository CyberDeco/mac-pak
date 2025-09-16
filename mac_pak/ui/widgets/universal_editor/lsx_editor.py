import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
    QLabel, QFrame, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ....data.parsers.larian_parser import UniversalBG3Parser
from ...threads.lsx_lsf_lsj_conversion import FileConversionThread
from ...editors.syntax_highlighter import LSXSyntaxHighlighter

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

    def is_game_file(self, file_path):
        """Check if file is from game directory (should not be modified directly)"""
        if not file_path:
            return False
        
        # Common BG3 game directory indicators
        game_indicators = [
            '/steamapps/common/baldurs gate 3',
            '/baldur\'s gate 3', 
            '/Contents/Data', 'Gustav']
        
        file_path_lower = file_path.lower()
        
        # Check if path contains game directory indicators
        for indicator in game_indicators:
            if indicator in file_path_lower:
                return True
        
        # Check if it's in a PAK extraction directory (temporary files)
        if 'extracted' in file_path_lower or 'temp' in file_path_lower:
            return True
        
        return False
    
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
        """Save file with format preservation and game file protection"""
        if not self.current_file:
            self.save_as_file()
            return
        
        # Check if this is a game file that shouldn't be modified directly
        if self.is_game_file(self.current_file):
            reply = QMessageBox.warning(
                self, "Game File Warning",
                "This appears to be a file from the game directory or extracted PAK.\n\n"
                "Modifying game files directly can cause issues and your changes may be lost.\n"
                "It's recommended to save this as a new file in your mod directory instead.\n\n"
                "Save as new file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.save_as_file()
            return
        
        # Rest of the existing save_file() method...
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