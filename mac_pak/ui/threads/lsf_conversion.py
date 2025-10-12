#!/usr/bin/env python3
"""
LSF/LSX/LSJ Conversion Thread
Handles background conversion operations for the Universal Editor using synchronous calls
"""

import os
import tempfile
import shutil
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from PyQt6.QtCore import QThread, pyqtSignal

class LSFConversionThread(QThread):
    """Thread for LSF/LSX/LSJ conversions without blocking UI - uses synchronous calls"""
    
    # Signals
    conversion_complete = pyqtSignal(bool, dict)  # success, result_data
    progress_updated = pyqtSignal(int, str)  # percentage, message
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, wine_wrapper, operation, source_path, dest_path=None, 
                 source_format=None, target_format=None, converter=None, parent=None):
        super().__init__(parent)
        self.wine_wrapper = wine_wrapper
        self.operation = operation
        self.source_path = source_path
        self.dest_path = dest_path
        self.source_format = source_format
        self.target_format = target_format
        self.converter = converter  # Add this
        self._cancelled = False
        self.setTerminationEnabled(True)
    
    def run(self):
        try:
            if self._cancelled:
                return
            
            if self.operation == 'load_lsf':
                self._handle_load_lsf()
            elif self.operation == 'convert':
                self._handle_convert()
            elif self.operation == 'save':
                self._handle_save()
            else:
                self.error_occurred.emit(f"Unknown operation: {self.operation}")
                
        except Exception as e:
            if not self._cancelled:
                self.error_occurred.emit(f"Conversion failed: {e}")
                self.conversion_complete.emit(False, {"error": str(e)})
        finally:
            self.finished.emit()
    
    def _handle_load_lsf(self):
        temp_lsx = None
        try:
            self.progress_updated.emit(10, "Preparing LSF file...")
            if self._cancelled:
                return
            
            temp_lsx = self.source_path + '.temp.lsx'
            self.progress_updated.emit(30, "Converting LSF to LSX...")
            
            if self._cancelled:
                return
            
            success = self.wine_wrapper.convert_lsf_to_lsx(self.source_path, temp_lsx)
            
            if self._cancelled:
                return
            
            if success and os.path.exists(temp_lsx):
                self.progress_updated.emit(80, "Reading converted file...")
                
                with open(temp_lsx, 'rb') as f:
                    content = f.read().decode('utf-8')
                
                self.progress_updated.emit(100, "Load complete!")
                
                result_data = {
                    "success": True,
                    "content": content,
                    "original_file": self.source_path,
                    "format": "lsx"
                }
                
                self.conversion_complete.emit(True, result_data)
            else:
                self.error_occurred.emit("LSF to LSX conversion failed")
                self.conversion_complete.emit(False, {"error": "Conversion failed"})
                
        except Exception as e:
            self.error_occurred.emit(f"Error loading LSF: {e}")
            self.conversion_complete.emit(False, {"error": str(e)})
        finally:
            if temp_lsx and os.path.exists(temp_lsx):
                try:
                    os.remove(temp_lsx)
                except:
                    pass
    
    def _handle_convert(self):
        try:
            self.progress_updated.emit(10, f"Preparing {self.source_format.upper()} file...")
            
            if self._cancelled:
                return
            
            needs_wine = (self.source_format == 'lsf' or self.target_format == 'lsf')
            
            if needs_wine:
                self._handle_wine_conversion()
            else:
                self._handle_text_conversion()
                
        except Exception as e:
            self.error_occurred.emit(f"Conversion failed: {e}")
            self.conversion_complete.emit(False, {"error": str(e)})
    
    def _handle_wine_conversion(self):
        try:
            self.progress_updated.emit(30, f"Converting {self.source_format.upper()} to {self.target_format.upper()}...")
            
            if self._cancelled:
                return
            
            if self.target_format == 'lsf':
                success = self.wine_wrapper.convert_lsx_to_lsf(self.source_path, self.dest_path)
            elif self.source_format == 'lsf':
                success = self.wine_wrapper.convert_lsf_to_lsx(self.source_path, self.dest_path)
            else:
                success = False
            
            if self._cancelled:
                return
            
            if success and os.path.exists(self.dest_path):
                self.progress_updated.emit(90, "Reading result...")
                
                content = None
                if self.target_format != 'lsf':
                    with open(self.dest_path, 'rb') as f:
                        content = f.read().decode('utf-8')
                else:
                    content = f"<!-- LSF File: {os.path.basename(self.dest_path)} -->"
                
                self.progress_updated.emit(100, "Conversion complete!")
                
                result_data = {
                    "success": True,
                    "content": content,
                    "source_path": self.source_path,
                    "target_path": self.dest_path,
                    "source_format": self.source_format,
                    "target_format": self.target_format
                }
                
                self.conversion_complete.emit(True, result_data)
            else:
                self.error_occurred.emit("Conversion failed - output file not created")
                self.conversion_complete.emit(False, {"error": "Output file not created"})
                
        except Exception as e:
            self.error_occurred.emit(f"Wine conversion failed: {e}")
            self.conversion_complete.emit(False, {"error": str(e)})
    
    def _handle_text_conversion(self):
        try:
            self.progress_updated.emit(30, f"Converting {self.source_format.upper()} to {self.target_format.upper()}...")
            
            if self._cancelled:
                return
            
            with open(self.source_path, 'rb') as f:
                content = f.read().decode('utf-8')
            
            if self._cancelled:
                return
            
            self.progress_updated.emit(60, "Processing conversion...")
            
            if self.source_format == 'lsx' and self.target_format == 'lsj':
                converted_content = self.converter.lsx_to_lsj(content)
            elif self.source_format == 'lsj' and self.target_format == 'lsx':
                converted_content = self.converter.lsj_to_lsx(content)
            else:
                converted_content = content
            
            if self._cancelled:
                return
            
            with open(self.dest_path, 'wb') as f:
                f.write(converted_content.encode('utf-8'))
            
            self.progress_updated.emit(100, "Conversion complete!")
            
            result_data = {
                "success": True,
                "content": converted_content,
                "source_path": self.source_path,
                "target_path": self.dest_path,
                "source_format": self.source_format,
                "target_format": self.target_format
            }
            
            self.conversion_complete.emit(True, result_data)
            
        except Exception as e:
            self.error_occurred.emit(f"Text conversion failed: {e}")
            self.conversion_complete.emit(False, {"error": str(e)})
    
    def _handle_save(self):
        try:
            self.progress_updated.emit(20, "Preparing to save...")
            
            if self._cancelled:
                return
            
            if self.source_path and os.path.exists(self.source_path):
                shutil.copy2(self.source_path, self.dest_path)
                
                self.progress_updated.emit(100, "Save complete!")
                
                result_data = {
                    "success": True,
                    "saved_path": self.dest_path
                }
                
                self.conversion_complete.emit(True, result_data)
            else:
                self.error_occurred.emit("Source file not found")
                self.conversion_complete.emit(False, {"error": "Source file not found"})
                
        except Exception as e:
            self.error_occurred.emit(f"Save failed: {e}")
            self.conversion_complete.emit(False, {"error": str(e)})
    
    def cancel(self):
        self._cancelled = True
        self.requestInterruption()
    
    def is_cancelled(self):
        return self._cancelled or self.isInterruptionRequested()


class BatchConversionThread(QThread):
    """Thread for batch converting multiple files"""
    
    batch_progress = pyqtSignal(int, int, str)
    file_converted = pyqtSignal(str, bool, str)
    batch_complete = pyqtSignal(int, int)
    
    def __init__(self, wine_wrapper, file_list, source_format, target_format, 
                 output_dir=None, converter=None, parent=None):
        super().__init__(parent)
        self.wine_wrapper = wine_wrapper
        self.file_list = file_list
        self.source_format = source_format
        self.target_format = target_format
        self.output_dir = output_dir
        self.converter = converter
        self._cancelled = False
        self.setTerminationEnabled(True)
    
    def run(self):
        successful = 0
        total = len(self.file_list)
        
        try:
            for i, file_path in enumerate(self.file_list):
                if self._cancelled:
                    break
                
                filename = os.path.basename(file_path)
                self.batch_progress.emit(i + 1, total, filename)
                
                if self._cancelled:
                    break
                
                if self.output_dir:
                    base_name = os.path.splitext(filename)[0]
                    output_path = os.path.join(self.output_dir, f"{base_name}.{self.target_format}")
                else:
                    output_path = os.path.splitext(file_path)[0] + f".{self.target_format}"
                
                try:
                    success = self._convert_single_file(file_path, output_path)
                    
                    if success:
                        successful += 1
                        self.file_converted.emit(file_path, True, "")
                    else:
                        self.file_converted.emit(file_path, False, "Conversion failed")
                        
                except Exception as e:
                    self.file_converted.emit(file_path, False, str(e))
            
            if not self._cancelled:
                self.batch_complete.emit(successful, total)
                
        except Exception as e:
            print(f"Batch conversion error: {e}")
        finally:
            self.finished.emit()
    
    def _convert_single_file(self, source_path, dest_path):
        needs_wine = (self.source_format == 'lsf' or self.target_format == 'lsf')
        
        if needs_wine:
            if self.target_format == 'lsf':
                return self.wine_wrapper.convert_lsx_to_lsf(source_path, dest_path)
            elif self.source_format == 'lsf':
                return self.wine_wrapper.convert_lsf_to_lsx(source_path, dest_path)
        else:
            with open(source_path, 'rb') as f:
                content = f.read().decode('utf-8')
            
            # Use the passed converter
            if self.source_format == 'lsx' and self.target_format == 'lsj':
                converted = self.converter.lsx_to_lsj(content)
            elif self.source_format == 'lsj' and self.target_format == 'lsx':
                converted = self.converter.lsj_to_lsx(content)
            else:
                return False
    
    def cancel(self):
        self._cancelled = True
        self.requestInterruption()
    
    def is_cancelled(self):
        return self._cancelled or self.isInterruptionRequested()
