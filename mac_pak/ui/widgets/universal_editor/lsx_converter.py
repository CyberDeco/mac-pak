#!/usr/bin/env python3
"""
LSX Converter - Handles format conversions using LSFConversionThread
Updated to properly handle LSF conversions and Save button states
"""

import os
import tempfile
from PyQt6.QtWidgets import QMessageBox
from .lsx_lsj_converter import LSXLSJConverter
from ...threads.lsf_conversion import LSFConversionThread
from ...dialogs.progress_dialog import ProgressDialog

class LSXConverter:
    """Handles file format conversions for LSX Editor"""
    
    def __init__(self, editor, wine_wrapper, parser, settings_manager):
        self.editor = editor
        self.wine_wrapper = wine_wrapper
        self.parser = parser
        self.settings_manager = settings_manager
        
        # Conversion state
        self.conversion_thread = None
        self.progress_dialog = None
        self.converted_binary_file = None
        self.temp_output_file = None
    
    def convert_to_format(self, source_format, target_format, source_file, ui):
        """Convert file to target format"""
        # Check if wine needed
        needs_wine = (source_format == 'lsf' or target_format == 'lsf')
        
        if needs_wine and not self.wine_wrapper:
            QMessageBox.critical(self.editor, "Error", "Conversion involving LSF requires divine.exe")
            return
        
        # Create temp output file
        temp_fd, self.temp_output_file = tempfile.mkstemp(suffix=f".{target_format}")
        os.close(temp_fd)
        
        try:
            if needs_wine:
                self._convert_with_wine(source_format, target_format, source_file, ui)
            else:
                self._convert_text_formats(source_format, target_format, source_file, ui)
        except Exception as e:
            self._conversion_failed(f"Conversion error: {e}", ui)
    
    def _convert_with_wine(self, source_format, target_format, source_file, ui):
        """Convert using divine.exe via LSFConversionThread"""
        # Create progress dialog
        self.progress_dialog = ProgressDialog(
            self.editor,
            f"Converting to {target_format.upper()}",
            cancel_text="Cancel",
            min_val=0,
            max_val=100
        )
        
        if source_file:
            self.progress_dialog.set_file_info(source_file)
        else:
            self.progress_dialog.file_info_label.setText("Converting editor content...")
        
        self.progress_dialog.show()
        
        # Prepare source file
        if source_file and source_format == 'lsf':
            # LSF files: use directly
            temp_source = source_file
        elif source_file:
            # Text files: copy to temp
            temp_source = self._create_temp_source(source_file, source_format)
        else:
            # Editor content: create temp file
            temp_source = self._create_temp_from_content(ui, source_format)
        
        # Disable UI
        ui.set_conversion_state(True)

        converter = LSXLSJConverter()
        
        # Create and start conversion thread with CORRECT parameter order
        self.conversion_thread = LSFConversionThread(
            self.wine_wrapper,           # 1st: wine_wrapper
            'convert',                   # 2nd: operation
            temp_source,                 # 3rd: source_path
            self.temp_output_file,       # 4th: dest_path
            source_format,               # 5th: source_format
            target_format,               # 6th: target_format
            converter,                   # 7th: converter
            self.editor                  # 7th: parent
        )
        
        # Connect signals
        self.conversion_thread.progress_updated.connect(
            lambda pct, msg: self.progress_dialog.update_progress(pct, msg)
        )
        self.conversion_thread.conversion_complete.connect(
            lambda success, data: self._on_conversion_complete(success, data, target_format, ui)
        )
        self.conversion_thread.error_occurred.connect(
            lambda error: self._conversion_failed(error, ui)
        )
        
        # Connect cancel
        self.progress_dialog.canceled.connect(self.cancel_conversion)
        
        # Start thread
        self.conversion_thread.start()
    
    def _convert_text_formats(self, source_format, target_format, source_file, ui):
        """Convert between LSX and LSJ (no wine needed)"""
        try:
            
            converter = LSXLSJConverter()
            content = ui.text_editor.toPlainText()
            
            if source_format == 'lsx' and target_format == 'lsj':
                converted = converter.lsx_to_lsj(content)
            elif source_format == 'lsj' and target_format == 'lsx':
                converted = converter.lsj_to_lsx(content)
            else:
                raise Exception(f"Unsupported conversion: {source_format} to {target_format}")
            
            # Write to temp file
            with open(self.temp_output_file, 'wb') as f:
                f.write(converted.encode('utf-8'))
            
            # Show result immediately (no thread needed)
            result_data = {
                'success': True,
                'content': converted,
                'target_path': self.temp_output_file
            }
            self._on_conversion_complete(True, result_data, target_format, ui)
            
        except Exception as e:
            self._conversion_failed(f"Text conversion failed: {e}", ui)
    
    def _on_conversion_complete(self, success, result_data, target_format, ui):
        """Handle conversion completion"""
        try:
            # Close progress dialog
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            
            # Re-enable UI
            ui.set_conversion_state(False)
            
            if not success:
                error = result_data.get('error', 'Unknown error')
                self._conversion_failed(error, ui)
                return
            
            # Store the original file path if converting FROM LSF
            if self.editor.current_format == 'lsf' and self.editor.current_file:
                # This is a conversion from an LSF file
                self.editor.original_file_for_conversion = self.editor.current_file
            
            # Load converted content
            if target_format == 'lsf':
                # Binary file - show placeholder
                content = self._create_lsf_result_placeholder()
                self.converted_binary_file = self.temp_output_file
            else:
                # Text file - load content
                content = result_data.get('content', '')
                if not content and os.path.exists(self.temp_output_file):
                    with open(self.temp_output_file, 'rb') as f:
                        content = f.read().decode('utf-8')
            
            # Update editor
            ui.text_editor.clear()
            ui.text_editor.insertPlainText(content)
            
            # Update state
            self.editor.current_format = target_format
            self.editor.current_file = None  # Now a preview, no destination file
            self.editor.modified = True
            
            # Update UI labels
            if hasattr(ui, 'update_format_badge'):
                ui.update_format_badge(target_format)
            else:
                ui.format_label.setText(f"Format: {target_format.upper()}")
            
            if target_format == 'lsf':
                ui.status_label.setText(f"Converted to {target_format.upper()} - use Save As to save")
            else:
                # Check if converted from LSF
                if (hasattr(self.editor, 'original_file_for_conversion') and 
                    self.editor.original_file_for_conversion and 
                    self.editor.original_file_for_conversion.lower().endswith('.lsf')):
                    ui.status_label.setText(f"Converted from LSF - use Save As to save")
                else:
                    ui.status_label.setText(f"Converted to {target_format.upper()} - use Save/Save As")
            
            # Update syntax highlighter
            if hasattr(ui, 'highlighter') and target_format != 'lsf':
                ui.highlighter.current_format = target_format
            
            self.editor.update_button_states()
            
            # Cleanup temp files (except binary LSF)
            if target_format != 'lsf' and os.path.exists(self.temp_output_file):
                try:
                    os.remove(self.temp_output_file)
                except:
                    pass
            
        except Exception as e:
            self._conversion_failed(f"Error displaying result: {e}", ui)
    
    def cancel_conversion(self):
        """Cancel ongoing conversion"""
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.cancel()
            self.conversion_thread.quit()
            self.conversion_thread.wait(2000)
        
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        # Re-enable UI
        if hasattr(self.editor, 'ui'):
            self.editor.ui.set_conversion_state(False)
        
        self.editor.ui.status_label.setText("Conversion cancelled")
    
    def _conversion_failed(self, error_message, ui):
        """Handle conversion failure"""
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        # Re-enable UI
        ui.set_conversion_state(False)
        
        # Show error
        QMessageBox.critical(self.editor, "Conversion Failed", f"Error: {error_message}")
        ui.status_label.setText("Conversion failed")
        
        # Cleanup
        if self.temp_output_file and os.path.exists(self.temp_output_file):
            try:
                os.remove(self.temp_output_file)
            except:
                pass
    
    def _create_temp_source(self, source_file, source_format):
        """Create temp copy of source file"""
        temp_fd, temp_path = tempfile.mkstemp(suffix=f".{source_format}")
        try:
            with open(source_file, 'rb') as src:
                content = src.read().decode('utf-8')
            with os.fdopen(temp_fd, 'wb') as dst:
                dst.write(content.encode('utf-8'))
            return temp_path
        except:
            os.close(temp_fd)
            raise
    
    def _create_temp_from_content(self, ui, source_format):
        """Create temp file from editor content"""
        temp_fd, temp_path = tempfile.mkstemp(suffix=f".{source_format}")
        try:
            content = ui.text_editor.toPlainText()
            with os.fdopen(temp_fd, 'wb') as f:
                f.write(content.encode('utf-8'))
            return temp_path
        except:
            os.close(temp_fd)
            raise
    
    def _create_lsf_result_placeholder(self):
        """Create placeholder for LSF conversion result"""
        file_size = os.path.getsize(self.temp_output_file) if self.temp_output_file else 0
        return (
            "<!-- LSF File: Converted Successfully -->\n"
            f"<!-- File Size: {file_size:,} bytes -->\n"
            "<!-- LSF files are binary and cannot be previewed as text -->\n"
            "<!-- Use 'Save As' to save this LSF file -->\n"
            "<!-- Or convert back to LSX to view content -->"
        )