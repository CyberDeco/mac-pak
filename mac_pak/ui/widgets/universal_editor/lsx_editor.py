import os
import json
import xml.etree.ElementTree as ET
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
    QLabel, QFrame, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ....data.parsers.larian_parser import UniversalBG3Parser
from ...editors.syntax_highlighter import LSXSyntaxHighlighter
from ...dialogs.progress_dialog import ProgressDialog

class LSXEditor(QWidget):
    """Universal BG3 file editor supporting LSX, LSJ, and LSF formats"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        self.parser = UniversalBG3Parser()
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.current_file = None
        self.current_format = None
        self.modified = False
        self.original_file_for_conversion = None
        self.converted_binary_file = None
        
        # Conversion state tracking
        self.conversion_thread = None
        
        if self.wine_wrapper:
            self.parser.set_wine_wrapper(self.wine_wrapper)
        
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
        
        # Cancel button (hidden by default)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        self.cancel_btn.setVisible(False)
        toolbar_layout.addWidget(self.cancel_btn)
        
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
        
        layout.addWidget(self.text_editor)
        
        # Initially disable some buttons
        self.update_button_states()

    def set_conversion_ui_state(self, enabled):
        """Enable/disable UI during conversion with cancel button"""
        # Disable conversion buttons and file operations during conversion
        self.convert_lsx_btn.setEnabled(enabled)
        self.convert_lsj_btn.setEnabled(enabled)
        self.convert_lsf_btn.setEnabled(enabled)
        self.open_btn.setEnabled(enabled)
        self.save_btn.setEnabled(enabled and self.modified)
        self.save_as_btn.setEnabled(enabled and (self.current_file or self.modified))
        
        # Show/hide cancel button
        self.cancel_btn.setVisible(not enabled)
        
        if enabled:
            # Restore normal button states
            self.update_button_states()
    
    def create_separator(self):
        """Create a vertical separator"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        return separator

    def has_content(self):
        """Check if editor has meaningful content"""
        content = self.text_editor.toPlainText().strip()

        # Consider LSF preview content as valid content
        if content.startswith("<!-- LSF File:") and "Converted Successfully" in content:
            return True
        
        return bool(content) and not content.startswith("<!-- LSF File:")
    
    def update_button_states(self):
        """Update button enabled states based on current file"""
        has_file = self.current_file is not None
        has_content = self.has_content()
        has_wine_wrapper = self.wine_wrapper is not None
        
        # Save becomes enabled when modified, even if no current_file (preview mode)
        self.save_btn.setEnabled(self.modified)
        self.save_as_btn.setEnabled(has_file or self.modified)
        self.validate_btn.setEnabled(has_file or self.modified)
        self.format_btn.setEnabled(has_file or self.modified)
        
        # Conversion buttons need divine.exe and a file loaded
        conversion_enabled = (has_file or has_content) and has_wine_wrapper

        # Disable conversion to current format
        self.convert_lsx_btn.setEnabled(conversion_enabled and self.current_format != 'lsx')
        self.convert_lsj_btn.setEnabled(conversion_enabled and self.current_format != 'lsj')
        self.convert_lsf_btn.setEnabled(conversion_enabled and self.current_format != 'lsf')

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
            # Store original file path for conversion reference
            self.original_file_for_conversion = file_path
            
            # Detect format first
            file_format = self.parser.detect_file_format(file_path)
            self.current_format = file_format
            
            # Handle LSF files differently
            if file_format == 'lsf':
                if not self.wine_wrapper:
                    QMessageBox.critical(self, "Error", "LSF support requires divine.exe integration")
                    return
                
                content = f"<!-- LSF File: {os.path.basename(file_path)} -->\n"
                content += "<!-- LSF files are binary and cannot be previewed -->\n" 
                content += "<!-- Use the 'Convert to LSX' button to convert this file -->"
                content += "<!-- It will not be saved until you click 'Save As' -->"
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
        """Load LSF file by converting to LSX first - ASYNC VERSION"""
        if not self.wine_wrapper:
            QMessageBox.critical(self, "Error", "LSF support requires divine.exe integration")
            return
        
        # Show a simple message and disable UI during conversion
        self.text_editor.setPlainText("Converting LSF file, please wait...")
        self.text_editor.setEnabled(False)
        
        # Create temp file for conversion
        temp_lsx = file_path + '.temp.lsx'
        
        # Start ASYNC conversion
        self.lsf_load_monitor = self.wine_wrapper.binary_converter.convert_resource_async(
            file_path, 
            temp_lsx
        )
        
        # Store temp path for cleanup
        self.lsf_temp_file = temp_lsx
        
        # Connect signals
        self.lsf_load_monitor.process_finished.connect(
            lambda success, output: self.lsf_load_completed(success, output, temp_lsx)
        )
    
    def lsf_load_completed(self, success, output, temp_lsx):
        """Handle LSF load conversion completion"""
        self.text_editor.setEnabled(True)
        
        try:
            if success and os.path.exists(temp_lsx):
                with open(temp_lsx, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add note about LSF conversion
                note = "<!-- This LSF file has been converted to LSX for editing -->\n"
                self.text_editor.setPlainText(note + content)
                
                self.status_label.setText(f"Loaded LSF file (converted to LSX for editing)")
            else:
                error_msg = output if output else "Conversion failed"
                QMessageBox.critical(self, "Error", f"Could not convert LSF file: {error_msg}")
                self.text_editor.setPlainText("")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load converted LSF file: {e}")
            self.text_editor.setPlainText("")
        
        finally:
            # Cleanup temp file
            try:
                if os.path.exists(temp_lsx):
                    os.remove(temp_lsx)
            except:
                pass
            
            # Cleanup monitor
            if hasattr(self, 'lsf_load_monitor'):
                try:
                    self.lsf_load_monitor.deleteLater()
                except:
                    pass
                self.lsf_load_monitor = None
    
    def save_file(self):
        """Save file with format preservation and game file protection"""
        if not self.current_file:
            # No current file means this is converted content - force Save As
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
        """Save as new file with format selection - enhanced for binary files"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        # Determine default extension based on current format
        default_ext = ".lsx"
        if self.current_format:
            default_ext = f".{self.current_format}"
        
        # Suggest a filename based on the original file if available
        if hasattr(self, 'original_file_for_conversion') and self.original_file_for_conversion:
            base_name = os.path.splitext(os.path.basename(self.original_file_for_conversion))[0]
            suggested_name = f"{base_name}_converted{default_ext}"
            initial_path = os.path.join(initial_dir, suggested_name)
        else:
            initial_path = initial_dir
        
        # Adjust file filter based on format
        if self.current_format == 'lsf':
            file_filter = "LSF Files (*.lsf);;All Files (*.*)"
        else:
            file_filter = "LSX Files (*.lsx);;LSJ Files (*.lsj);;XML Files (*.xml);;JSON Files (*.json);;All Files (*.*)"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save BG3 File", initial_path, file_filter
        )
        
        if file_path:
            try:
                # Handle binary files (LSF) differently
                if self.current_format == 'lsf' and hasattr(self, 'converted_binary_file') and self.converted_binary_file:
                    # Copy the binary file
                    import shutil
                    shutil.copy2(self.converted_binary_file, file_path)
                    
                    # Clean up the temp binary file
                    try:
                        os.remove(self.converted_binary_file)
                        self.converted_binary_file = None
                    except:
                        pass
                    
                    success_msg = f"LSF file saved: {os.path.basename(file_path)}"
                    QMessageBox.information(self, "Saved", success_msg)
                else:
                    # Handle text files normally
                    content = self.text_editor.toPlainText()
                    
                    # Write the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                # Update current file and state
                self.current_file = file_path
                
                # Update format based on extension
                new_format = self.parser.detect_file_format(file_path)
                if new_format != 'unknown':
                    self.current_format = new_format
                    self.format_label.setText(f"Format: {new_format.upper()}")
                    if hasattr(self, 'highlighter') and self.highlighter and new_format != 'lsf':
                        self.highlighter.set_format(new_format)
                
                # Update working directory
                if self.settings_manager:
                    self.settings_manager.set("working_directory", os.path.dirname(file_path))
                
                self.modified = False
                self.status_label.setText(f"Saved: {os.path.basename(file_path)}")
                self.update_button_states()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")

    def perform_lsf_conversion(self, target_format, temp_output_file):
        
        # Determine source: file path or content
        if self.current_file:
            # Use file path
            success = getattr(self.wine_wrapper, f"convert_{self.current_format}_to_{target_format}")(
                self.current_file, temp_output_file
            )
        else:
            # Use text content from editor
            content = self.text_editor.toPlainText()
            success = getattr(self.wine_wrapper, f"convert_{self.current_format}_to_{target_format}")(
                content, temp_output_file, is_content=True
            )
        return success
    
    def convert_to_lsx(self):
        print("DEBUG: convert_to_lsx() called")
        """Convert current file to LSX format"""
        if not self.current_file and not self.has_content():
            QMessageBox.warning(self, "Warning", "No file or content loaded")
            return
        
        if self.current_format == 'lsx':
            QMessageBox.information(self, "Info", "File is already in LSX format")
            return
        
        self.perform_conversion('lsx')
    
    def convert_to_lsj(self):
        """Convert current file to LSJ format"""
        if not self.current_file and not self.has_content():
            QMessageBox.warning(self, "Warning", "No file or content loaded")
            return
        
        if self.current_format == 'lsj':
            QMessageBox.information(self, "Info", "File is already in LSJ format")
            return
        
        self.perform_conversion('lsj')
    
    def convert_to_lsf(self):
        """Convert current file to LSX format"""
        if not self.current_file and not self.has_content():
            QMessageBox.warning(self, "Warning", "No file or content loaded")
            return
        
        if self.current_format == 'lsf':
            QMessageBox.information(self, "Info", "File is already in LSF format")
            return
        
        self.perform_conversion('lsf')

    def perform_conversion(self, target_format):
        """Perform file format conversion for preview using progress dialog"""
        
        # Only LSX/LSJ conversions that involve LSF need wine_wrapper
        needs_wine = (self.current_format == 'lsf' or target_format == 'lsf')
        
        if needs_wine and not self.wine_wrapper:
            QMessageBox.critical(self, "Error", f"Conversion involving LSF requires divine.exe")
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
        
        # Create temporary file for conversion output
        temp_fd, temp_output_file = tempfile.mkstemp(suffix=f".{target_format}")
        os.close(temp_fd)
        
        try:
            if needs_wine:
                # Use threaded wine conversion with progress dialog
                self.perform_threaded_wine_conversion(target_format, temp_output_file)
            else:
                # Handle LSX <-> LSJ conversions (immediate, no dialog needed)
                success = self.perform_text_conversion(target_format, temp_output_file)
                if success:
                    self.preview_conversion_completed(True, {"target_path": temp_output_file}, target_format, temp_output_file)
                else:
                    self.preview_conversion_completed(False, {"error": "Conversion failed"}, target_format, temp_output_file)
        
        except Exception as e:
            self.preview_conversion_completed(False, {"error": str(e)}, target_format, temp_output_file)
    
    def perform_threaded_wine_conversion(self, target_format, temp_output_file):
        """Perform conversion using ASYNC WineProcessMonitor - NO THREADS"""
        try:
            # Create and show progress dialog
            self.progress_dialog = ProgressDialog(
                self, 
                f"Converting to {target_format.upper()}",
                cancel_text="Cancel",
                min_val=0,
                max_val=100
            )
            
            # Set file info if available
            if self.current_file:
                self.progress_dialog.set_file_info(self.current_file)
            else:
                self.progress_dialog.file_info_label.setText("Converting editor content...")
            
            # Connect cancellation
            self.progress_dialog.canceled.connect(self.cancel_conversion)
            
            # Show dialog
            self.progress_dialog.show()
            
            # Determine source file
            # CRITICAL: For LSF files, use the actual file directly!
            if self.current_file and self.current_format == 'lsf':
                source_file = self.current_file
                source_format = self.current_format
                self.progress_dialog.update_progress(15, "Preparing LSF file...")
                
            elif self.current_file:
                # For text formats, copy to temp
                temp_source_fd, source_file = tempfile.mkstemp(suffix=f".{self.current_format}")
                
                try:
                    with open(self.current_file, 'r', encoding='utf-8') as src:
                        content = src.read()
                    
                    with os.fdopen(temp_source_fd, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.temp_source_file = source_file
                except Exception as e:
                    os.close(temp_source_fd)
                    raise e
                
                source_format = self.current_format
                self.progress_dialog.update_progress(15, "Preparing source file...")
                
            else:
                # No file - use editor content (text formats only)
                if self.current_format == 'lsf':
                    self.progress_dialog.close()
                    self.conversion_error("Cannot convert LSF from editor content - load a file first")
                    return
                
                temp_source_fd, source_file = tempfile.mkstemp(suffix=f".{self.current_format}")
                content = self.text_editor.toPlainText()
                
                try:
                    with os.fdopen(temp_source_fd, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.temp_source_file = source_file
                except Exception as e:
                    os.close(temp_source_fd)
                    raise e
                
                source_format = self.current_format
                self.progress_dialog.update_progress(15, "Preparing conversion...")
            
            # Handle LSJ to LSF conversion (needs intermediate LSX)
            if self.current_format == 'lsj' and target_format == 'lsf':
                self.progress_dialog.update_progress(10, "Converting LSJ to intermediate LSX...")
                
                temp_lsx = temp_output_file + '.temp.lsx'
                
                if self.current_file:
                    success = self.convert_lsj_to_lsx_content(temp_lsx)
                else:
                    success = self.convert_lsj_to_lsx_content(temp_lsx, content)
                
                if success:
                    source_file = temp_lsx
                    source_format = 'lsx'
                    self.temp_intermediate_file = temp_lsx
                    self.progress_dialog.update_progress(25, "Starting LSF conversion...")
                else:
                    self.progress_dialog.close()
                    self.conversion_error("Failed to convert LSJ to intermediate LSX")
                    return
            
            # Start ASYNC conversion - NO THREAD!
            self.progress_dialog.update_progress(30, "Starting conversion...")
            
            # Use the async method from binary_converter
            self.conversion_monitor = self.wine_wrapper.binary_converter.convert_resource_async(
                source_file, 
                temp_output_file
            )
            
            # Store for later reference
            self.conversion_source_file = source_file
            self.conversion_target_file = temp_output_file
            self.conversion_target_format = target_format
            
            # Connect signals - the monitor will emit when done
            self.conversion_monitor.progress_updated.connect(self.on_conversion_progress)
            self.conversion_monitor.process_finished.connect(self.on_conversion_finished)
            
        except Exception as e:
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            self.conversion_error(f"Failed to start conversion: {e}")
    
    def on_conversion_progress(self, percentage, message):
        """Handle progress updates from async conversion"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            # Map to dialog progress (30-90% range)
            dialog_progress = 30 + int((percentage / 100) * 60)
            self.progress_dialog.update_progress(dialog_progress, message)
    
    def on_conversion_finished(self, success, output):
        """Handle async conversion completion"""
        try:
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                if success:
                    self.progress_dialog.update_progress(95, "Conversion complete!")
                else:
                    self.progress_dialog.update_progress(100, f"Conversion failed")
            
            # Prepare result data
            result_data = {
                "success": success,
                "output": output,
                "source_path": self.conversion_source_file,
                "target_path": self.conversion_target_file
            }
            
            # Call the existing completion handler
            self.threaded_conversion_completed(
                success, 
                result_data, 
                self.conversion_target_format, 
                self.conversion_target_file
            )
            
        except Exception as e:
            self.conversion_error(f"Error handling conversion result: {e}")
    
    def threaded_conversion_completed(self, success, result_data, target_format, temp_output_file):
        """Handle conversion completion - name kept for compatibility"""
        try:
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                if success:
                    self.progress_dialog.update_progress(95, "Conversion complete, preparing preview...")
                else:
                    error_msg = result_data.get("error", result_data.get("output", "Unknown error"))
                    self.progress_dialog.update_progress(100, f"Conversion failed: {error_msg}")
            
            if success:
                # Check if the output file actually exists and has content
                if os.path.exists(temp_output_file):
                    file_size = os.path.getsize(temp_output_file)
                    
                    if file_size > 0:
                        if hasattr(self, 'progress_dialog') and self.progress_dialog:
                            self.progress_dialog.update_progress(100, "Loading converted file...")
                        
                        self.preview_conversion_completed(True, result_data, target_format, temp_output_file)
                    else:
                        self.preview_conversion_completed(False, {"error": "Output file is empty"}, target_format, temp_output_file)
                else:
                    self.preview_conversion_completed(False, {"error": "Output file was not created"}, target_format, temp_output_file)
            else:
                error_msg = result_data.get("error", result_data.get("output", "Unknown error"))
                self.preview_conversion_completed(False, {"error": error_msg}, target_format, temp_output_file)
                
        except Exception as e:
            self.preview_conversion_completed(False, {"error": f"Exception: {str(e)}"}, target_format, temp_output_file)
        finally:
            # Cleanup
            self._cleanup_conversion_dialog_and_monitor()
    
    def cancel_conversion(self):
        """Cancel ongoing conversion - ASYNC version"""
        if hasattr(self, 'conversion_monitor') and self.conversion_monitor:
            self.conversion_monitor.cancel()
            self.status_label.setText("Conversion cancelled")
        
        # Cleanup
        self._cleanup_conversion_dialog_and_monitor()
    
    def _cleanup_conversion_dialog_and_monitor(self):
        """Cleanup for async conversion"""
        # Disconnect signals
        if hasattr(self, 'conversion_monitor') and self.conversion_monitor:
            try:
                self.conversion_monitor.progress_updated.disconnect(self.on_conversion_progress)
            except TypeError:
                pass
            
            try:
                self.conversion_monitor.process_finished.disconnect(self.on_conversion_finished)
            except TypeError:
                pass
            
            try:
                self.conversion_monitor.deleteLater()
            except:
                pass
            self.conversion_monitor = None
        
        # Close progress dialog
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            try:
                self.progress_dialog.canceled.disconnect(self.cancel_conversion)
            except TypeError:
                pass
            
            try:
                self.progress_dialog.close()
            except RuntimeError:
                pass
            finally:
                self.progress_dialog = None
        
        # Cleanup temp files
        self.cleanup_conversion_temps()
    
    def conversion_error(self, error_message):
        """Handle conversion errors - UPDATED for async"""
        QMessageBox.critical(self, "Conversion Failed", f"Error: {error_message}")
        self.status_label.setText("Conversion failed")
        
        # Use cleanup
        self._cleanup_conversion_dialog_and_monitor()
    
    def cleanup_conversion_temps(self):
        """Clean up temporary files created during conversion"""
        # Clean up temporary source file (from editor content)
        if hasattr(self, 'temp_source_file'):
            try:
                os.remove(self.temp_source_file)
            except:
                pass
            delattr(self, 'temp_source_file')
        
        # Clean up intermediate conversion file (LSJ->LSX->LSF)
        if hasattr(self, 'temp_intermediate_file'):
            try:
                os.remove(self.temp_intermediate_file)
            except:
                pass
            delattr(self, 'temp_intermediate_file')
        
    def perform_text_conversion(self, target_format, temp_output_file):
        """Perform conversion between text formats (LSX <-> LSJ)"""
        try:
            content = self.text_editor.toPlainText()
            
            if self.current_format == 'lsx' and target_format == 'lsj':
                return self.convert_lsx_to_lsj_content(content, temp_output_file)
            elif self.current_format == 'lsj' and target_format == 'lsx':
                return self.convert_lsj_to_lsx_content(temp_output_file, content)
            else:
                return False
        
        except Exception as e:
            print(f"Text conversion error: {e}")
            return False
    
    def convert_lsx_to_lsj_content(self, lsx_content, output_file):
        """Convert LSX content to LSJ format"""
        try:
            import xml.etree.ElementTree as ET
            import json
            
            # Parse XML
            root = ET.fromstring(lsx_content)
            
            # Convert to JSON structure (simplified conversion)
            json_data = {
                "save": {
                    "header": {
                        "version": root.get("version", "unknown")
                    },
                    "regions": {}
                }
            }
            
            # Convert regions
            for region in root.findall('.//region'):
                region_id = region.get('id', 'unknown')
                region_data = {}
                
                # Convert nodes
                for node in region.findall('.//node'):
                    node_id = node.get('id', 'unknown')
                    node_data = {}
                    
                    # Convert attributes
                    for attr in node.findall('.//attribute'):
                        attr_id = attr.get('id')
                        attr_value = attr.get('value')
                        attr_type = attr.get('type', 'string')
                        
                        if attr_id:
                            node_data[attr_id] = {
                                "type": attr_type,
                                "value": attr_value
                            }
                    
                    if node_data:
                        region_data[node_id] = node_data
                
                if region_data:
                    json_data["save"]["regions"][region_id] = region_data
            
            # Write JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            return True
        
        except Exception as e:
            print(f"LSX to LSJ conversion error: {e}")
            return False
    
    def convert_lsj_to_lsx_content(self, output_file, lsj_content=None):
        """Convert LSJ content to LSX format"""
        try:
            import json
            import xml.etree.ElementTree as ET
            
            if lsj_content:
                json_data = json.loads(lsj_content)
            else:
                # Read from current file
                with open(self.current_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
            
            # Create XML structure
            root = ET.Element("save")
            
            # Set version
            if "save" in json_data and "header" in json_data["save"]:
                version = json_data["save"]["header"].get("version", "4.0.0.0")
            else:
                version = "4.0.0.0"
            
            root.set("version", version)
            
            # Convert regions
            if "save" in json_data and "regions" in json_data["save"]:
                regions_data = json_data["save"]["regions"]
                
                for region_id, region_content in regions_data.items():
                    region_elem = ET.SubElement(root, "region")
                    region_elem.set("id", region_id)
                    
                    for node_id, node_content in region_content.items():
                        node_elem = ET.SubElement(region_elem, "node")
                        node_elem.set("id", node_id)
                        
                        for attr_id, attr_data in node_content.items():
                            attr_elem = ET.SubElement(node_elem, "attribute")
                            attr_elem.set("id", attr_id)
                            
                            if isinstance(attr_data, dict):
                                attr_elem.set("type", attr_data.get("type", "string"))
                                attr_elem.set("value", str(attr_data.get("value", "")))
                            else:
                                attr_elem.set("type", "string")
                                attr_elem.set("value", str(attr_data))
            
            # Format and write XML
            self.indent_xml(root)
            tree = ET.ElementTree(root)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                tree.write(f, encoding='unicode', xml_declaration=False)
            
            return True
        
        except Exception as e:
            print(f"LSJ to LSX conversion error: {e}")
            return False

    def preview_conversion_completed(self, success, result_data, target_format, temp_file_path):
        """Handle completed conversion for preview"""
        try:
            if success:
                # Handle binary vs text files differently
                if target_format == 'lsf':
                    # LSF files are binary - show a placeholder instead of content
                    file_size = os.path.getsize(temp_file_path)
                    converted_content = f"<!-- LSF File: Converted Successfully -->\n"
                    converted_content += f"<!-- File Size: {file_size:,} bytes -->\n"
                    converted_content += f"<!-- LSF files are binary and cannot be previewed as text -->\n"
                    converted_content += f"<!-- Use 'Save As' to save this LSF file -->\n"
                    converted_content += f"<!-- Or convert back to LSX to view content -->"
                else:
                    # Text files (LSX, LSJ) - load content normally
                    with open(temp_file_path, 'r', encoding='utf-8') as f:
                        converted_content = f.read()
                
                # Update editor with converted content
                self.text_editor.setPlainText(converted_content)
                
                # Update UI to reflect the new format
                self.current_format = target_format
                self.format_label.setText(f"Format: {target_format.upper()} (Preview)")
                
                if target_format == 'lsf':
                    self.status_label.setText(f"Converted to {target_format.upper()} - binary file ready to save")
                else:
                    self.status_label.setText(f"Converted to {target_format.upper()} - use Save/Save As to keep changes")
                
                # Mark as modified so save buttons become available
                self.modified = True
                
                # Update syntax highlighter for new format (skip for binary files)
                if hasattr(self, 'highlighter') and self.highlighter and target_format != 'lsf':
                    self.highlighter.set_format(target_format)
                
                # Clear the current_file since this is now a preview of converted content
                # User will need to Save As to choose where to save it
                self.current_file = None
                
                # Store the binary file path for LSF files so we can save it later
                if target_format == 'lsf':
                    self.converted_binary_file = temp_file_path
                else:
                    self.converted_binary_file = None
                
                self.update_button_states()
                
            else:
                error_msg = result_data.get("error", result_data.get("output", "Unknown error"))
                QMessageBox.critical(self, "Conversion Failed", f"Error: {error_msg}")
                self.status_label.setText("Conversion failed")
        
        except Exception as e:
            QMessageBox.critical(self, "Preview Error", f"Could not preview converted file: {e}")
            self.status_label.setText("Preview failed")
        
        finally:
            # Clean up temporary file (except for LSF files that we need to keep for saving)
            if target_format != 'lsf':
                try:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                except Exception as e:
                    print(f"Warning: Could not remove temp file {temp_file_path}: {e}")
    
    def conversion_completed(self, success, result_data):
        """Handle completed conversion (legacy method, kept for compatibility)"""
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
        if not self.current_file and not self.modified:
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
        if not self.current_file and not self.modified:
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
            else:
                self.status_label.setText("Modified: Converted content (use Save As)")
            self.update_button_states()