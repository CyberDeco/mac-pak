#!/usr/bin/env python3
"""
LSF/LSX/LSJ Conversion Thread
Handles background conversion operations for the Universal Editor using synchronous calls
"""

import os
import tempfile
import shutil
from PyQt6.QtCore import QThread, pyqtSignal


class LSFConversionThread(QThread):
    """Thread for LSF/LSX/LSJ conversions without blocking UI - uses synchronous calls"""
    
    # Signals
    conversion_complete = pyqtSignal(bool, dict)  # success, result_data
    progress_updated = pyqtSignal(int, str)  # percentage, message
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, wine_wrapper, operation, source_path, dest_path=None, source_format=None, target_format=None, parent=None):
        """
        Initialize conversion thread
        
        Args:
            wine_wrapper: WineWrapper instance for conversions
            operation: Operation type ('load_lsf', 'convert', 'save')
            source_path: Source file path
            dest_path: Destination file path (optional, for conversions)
            source_format: Source format ('lsx', 'lsj', 'lsf')
            target_format: Target format ('lsx', 'lsj', 'lsf')
            parent: Parent QObject
        """
        super().__init__(parent)
        self.wine_wrapper = wine_wrapper
        self.operation = operation
        self.source_path = source_path
        self.dest_path = dest_path
        self.source_format = source_format
        self.target_format = target_format
        self._cancelled = False
        self.setTerminationEnabled(True)
    
    def run(self):
        """Execute conversion operation in background thread"""
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
        """Load LSF file by converting to LSX"""
        temp_lsx = None
        try:
            self.progress_updated.emit(10, "Preparing LSF file...")
            
            if self._cancelled:
                return
            
            # Create temp file for conversion
            temp_lsx = self.source_path + '.temp.lsx'
            
            self.progress_updated.emit(30, "Converting LSF to LSX...")
            
            if self._cancelled:
                return
            
            # SYNCHRONOUS conversion (blocking is fine in a thread)
            success = self.wine_wrapper.convert_lsf_to_lsx(
                self.source_path,
                temp_lsx
            )
            
            if self._cancelled:
                return
            
            if success and os.path.exists(temp_lsx):
                self.progress_updated.emit(80, "Reading converted file...")
                
                # Read the converted content
                with open(temp_lsx, 'r', encoding='utf-8') as f:
                    content = f.read()
                
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
            # Clean up temp file
            if temp_lsx and os.path.exists(temp_lsx):
                try:
                    os.remove(temp_lsx)
                except:
                    pass
    
    def _handle_convert(self):
        """Convert between LSX/LSJ/LSF formats"""
        try:
            self.progress_updated.emit(10, f"Preparing {self.source_format.upper()} file...")
            
            if self._cancelled:
                return
            
            # Determine conversion type
            needs_wine = (self.source_format == 'lsf' or self.target_format == 'lsf')
            
            if needs_wine:
                self._handle_wine_conversion()
            else:
                self._handle_text_conversion()
                
        except Exception as e:
            self.error_occurred.emit(f"Conversion failed: {e}")
            self.conversion_complete.emit(False, {"error": str(e)})
    
    def _handle_wine_conversion(self):
        """Handle conversions involving LSF (requires divine.exe)"""
        try:
            self.progress_updated.emit(30, f"Converting {self.source_format.upper()} to {self.target_format.upper()}...")
            
            if self._cancelled:
                return
            
            # SYNCHRONOUS conversion (blocking is fine in a thread)
            if self.target_format == 'lsf':
                success = self.wine_wrapper.convert_lsx_to_lsf(
                    self.source_path,
                    self.dest_path
                )
            elif self.source_format == 'lsf':
                success = self.wine_wrapper.convert_lsf_to_lsx(
                    self.source_path,
                    self.dest_path
                )
            else:
                success = False
            
            if self._cancelled:
                return
            
            if success and os.path.exists(self.dest_path):
                self.progress_updated.emit(90, "Reading result...")
                
                # For text formats, read the content
                content = None
                if self.target_format != 'lsf':
                    with open(self.dest_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                else:
                    # For binary LSF, just note the file path
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
        """Handle LSX <-> LSJ conversions (no divine.exe needed)"""
        try:
            self.progress_updated.emit(30, f"Converting {self.source_format.upper()} to {self.target_format.upper()}...")
            
            if self._cancelled:
                return
            
            # Read source content
            with open(self.source_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if self._cancelled:
                return
            
            self.progress_updated.emit(60, "Processing conversion...")
            
            # Perform text-based conversion
            if self.source_format == 'lsx' and self.target_format == 'lsj':
                converted_content = self._convert_lsx_to_lsj(content)
            elif self.source_format == 'lsj' and self.target_format == 'lsx':
                converted_content = self._convert_lsj_to_lsx(content)
            else:
                # Same format, just copy
                converted_content = content
            
            if self._cancelled:
                return
            
            # Write result
            with open(self.dest_path, 'w', encoding='utf-8') as f:
                f.write(converted_content)
            
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
    
    def _convert_lsx_to_lsj(self, lsx_content):
        """Convert LSX (XML) to LSJ (JSON)"""
        import xml.etree.ElementTree as ET
        import json
        
        try:
            root = ET.fromstring(lsx_content)
            data = self._xml_to_dict(root)
            return json.dumps(data, indent=2)
        except Exception as e:
            raise Exception(f"LSX to LSJ conversion failed: {e}")
    
    def _convert_lsj_to_lsx(self, lsj_content):
        """Convert LSJ (JSON) to LSX (XML)"""
        import xml.etree.ElementTree as ET
        import json
        
        try:
            data = json.loads(lsj_content)
            root = self._dict_to_xml(data)
            
            # Format and return as string
            ET.indent(root, space="  ")
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode')
        except Exception as e:
            raise Exception(f"LSJ to LSX conversion failed: {e}")
    
    def _xml_to_dict(self, element):
        """Convert XML element to dictionary"""
        result = {"tag": element.tag}
        
        if element.attrib:
            result["attributes"] = element.attrib
        
        if element.text and element.text.strip():
            result["text"] = element.text.strip()
        
        children = list(element)
        if children:
            result["children"] = [self._xml_to_dict(child) for child in children]
        
        return result
    
    def _dict_to_xml(self, data):
        """Convert dictionary to XML element"""
        import xml.etree.ElementTree as ET
        
        element = ET.Element(data.get("tag", "root"))
        
        if "attributes" in data:
            for key, value in data["attributes"].items():
                element.set(key, str(value))
        
        if "text" in data:
            element.text = data["text"]
        
        if "children" in data:
            for child_data in data["children"]:
                child = self._dict_to_xml(child_data)
                element.append(child)
        
        return element
    
    def _handle_save(self):
        """Handle save operation (potentially with conversion)"""
        try:
            self.progress_updated.emit(20, "Preparing to save...")
            
            if self._cancelled:
                return
            
            # For save, source_path is the content/temp file, dest_path is final location
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
        """Cancel the conversion operation"""
        self._cancelled = True
        self.requestInterruption()
    
    def is_cancelled(self):
        """Check if operation was cancelled"""
        return self._cancelled or self.isInterruptionRequested()


class BatchConversionThread(QThread):
    """Thread for batch converting multiple files"""
    
    # Signals
    batch_progress = pyqtSignal(int, int, str)  # current, total, filename
    file_converted = pyqtSignal(str, bool, str)  # file_path, success, error_message
    batch_complete = pyqtSignal(int, int)  # successful, total
    
    def __init__(self, wine_wrapper, file_list, source_format, target_format, output_dir=None, parent=None):
        """
        Initialize batch conversion thread
        
        Args:
            wine_wrapper: WineWrapper instance
            file_list: List of file paths to convert
            source_format: Source format ('lsx', 'lsj', 'lsf')
            target_format: Target format ('lsx', 'lsj', 'lsf')
            output_dir: Optional output directory (defaults to same dir as source)
            parent: Parent QObject
        """
        super().__init__(parent)
        self.wine_wrapper = wine_wrapper
        self.file_list = file_list
        self.source_format = source_format
        self.target_format = target_format
        self.output_dir = output_dir
        self._cancelled = False
        self.setTerminationEnabled(True)
    
    def run(self):
        """Execute batch conversion"""
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
                
                # Determine output path
                if self.output_dir:
                    base_name = os.path.splitext(filename)[0]
                    output_path = os.path.join(self.output_dir, f"{base_name}.{self.target_format}")
                else:
                    output_path = os.path.splitext(file_path)[0] + f".{self.target_format}"
                
                # Perform conversion
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
        """Convert a single file"""
        needs_wine = (self.source_format == 'lsf' or self.target_format == 'lsf')
        
        if needs_wine:
            # Use wine for LSF conversions
            if self.target_format == 'lsf':
                return self.wine_wrapper.convert_lsx_to_lsf(source_path, dest_path)
            elif self.source_format == 'lsf':
                return self.wine_wrapper.convert_lsf_to_lsx(source_path, dest_path)
        else:
            # Text conversion
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            converter = LSXTextConverter()
            
            if self.source_format == 'lsx' and self.target_format == 'lsj':
                converted = converter.lsx_to_lsj(content)
            elif self.source_format == 'lsj' and self.target_format == 'lsx':
                converted = converter.lsj_to_lsx(content)
            else:
                return False
            
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(converted)
            
            return True
        
        return False
    
    def cancel(self):
        """Cancel batch conversion"""
        self._cancelled = True
        self.requestInterruption()
    
    def is_cancelled(self):
        """Check if cancelled"""
        return self._cancelled or self.isInterruptionRequested()


class LSXTextConverter:
    """Simple text converter for LSX<->LSJ (used by batch conversion)"""
    
    def lsx_to_lsj(self, lsx_content):
        """Convert LSX to LSJ"""
        import json
        import xml.etree.ElementTree as ET
        
        root = ET.fromstring(lsx_content)
        data = self._xml_to_dict(root)
        return json.dumps(data, indent=2)
    
    def lsj_to_lsx(self, lsj_content):
        """Convert LSJ to LSX"""
        import json
        import xml.etree.ElementTree as ET
        
        data = json.loads(lsj_content)
        root = self._dict_to_xml(data)
        ET.indent(root, space="  ")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode')
    
    def _xml_to_dict(self, element):
        """Convert XML to dict"""
        result = {"tag": element.tag}
        if element.attrib:
            result["attributes"] = element.attrib
        if element.text and element.text.strip():
            result["text"] = element.text.strip()
        children = list(element)
        if children:
            result["children"] = [self._xml_to_dict(child) for child in children]
        return result
    
    def _dict_to_xml(self, data):
        """Convert dict to XML"""
        import xml.etree.ElementTree as ET
        
        element = ET.Element(data.get("tag", "root"))
        if "attributes" in data:
            for key, value in data["attributes"].items():
                element.set(key, str(value))
        if "text" in data:
            element.text = data["text"]
        if "children" in data:
            for child_data in data["children"]:
                element.append(self._dict_to_xml(child_data))
        return element