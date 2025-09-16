#!/usr/bin/env python3
"""
Threaded file parse operators
"""

import os
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ...data.parsers.larian_parser import AutoConversionProcessor, AutoConversionDialog

class ConversionPAKThread(QThread):
    """Enhanced PAK operation thread with auto-conversion support"""
    
    # Signals for communicating with main thread
    progress_updated = pyqtSignal(int, str)  # percentage, message
    operation_finished = pyqtSignal(bool, dict)  # success, result_data
    
    def __init__(self, wine_wrapper, operation_type, **kwargs):
        super().__init__()
        self.wine_wrapper = wine_wrapper
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.cancelled = False
    
    def run(self):
        """Run the PAK operation with auto-conversion support"""
        try:
            if self.operation_type == "create_pak":
                self._create_pak_with_conversion()
            else:
                # Fall back to regular operation
                self.operation_finished.emit(False, {"error": f"Unsupported operation with conversion: {self.operation_type}"})
        except Exception as e:
            self.operation_finished.emit(False, {"error": str(e)})
    
    def _create_pak_with_conversion(self):
        """Create PAK with auto-conversion of source files"""
        source_dir = self.kwargs.get("source_dir")
        pak_file = self.kwargs.get("pak_file")
        validate = self.kwargs.get("validate", True)
        
        def progress_callback(percentage, message):
            if not self.cancelled:
                self.progress_updated.emit(percentage, message)
        
        # # Import conversion classes
        # try:
        #     from larian_parser import AutoConversionProcessor
        # except ImportError:
        #     # Fall back to regular PAK creation if conversion not available
        #     self._create_pak_regular()
        #     return
        
        # Step 1: Find files needing conversion
        self.progress_updated.emit(5, "Scanning for files needing conversion...")
        processor = AutoConversionProcessor(self.wine_wrapper)
        conversion_files = processor.find_conversion_files(source_dir)
        
        conversions = []
        conversion_errors = []
        
        # Step 2: Perform conversions if needed
        total_conversions = sum(len(files) for files in conversion_files.values())
        if total_conversions > 0:
            self.progress_updated.emit(10, f"Converting {total_conversions} files...")
            
            current_conversion = 0
            for conv_type, files in conversion_files.items():
                for file_info in files:
                    if self.cancelled:
                        return
                    
                    current_conversion += 1
                    progress = 10 + int((current_conversion / total_conversions) * 30)  # 10-40%
                    
                    file_name = file_info['relative_path']
                    self.progress_updated.emit(progress, f"Converting {file_name}...")
                    
                    try:
                        result = processor.convert_file(file_info, conv_type)
                        conversions.append(result)
                    except Exception as e:
                        error_info = {
                            'file': file_info['relative_path'],
                            'error': str(e),
                            'type': conv_type
                        }
                        conversion_errors.append(error_info)
        
        # Step 3: Run validation if requested
        validation_results = None
        if validate:
            self.progress_updated.emit(45, "Validating mod structure...")
            validation_results = self.wine_wrapper.validate_mod_structure(source_dir)
        
        # Step 4: Create PAK file
        self.progress_updated.emit(50, "Creating PAK file...")
        success, output = self.wine_wrapper.create_pak_with_monitoring(
            source_dir, pak_file, progress_callback
        )
        
        # Prepare result data
        result_data = {
            "success": success,
            "output": output,
            "source_dir": source_dir,
            "pak_file": pak_file,
            "validation": validation_results,
            "conversions": conversions,
            "conversion_errors": conversion_errors
        }
        
        self.operation_finished.emit(success, result_data)
    
    def _create_pak_regular(self):
        """Regular PAK creation without conversion"""
        source_dir = self.kwargs.get("source_dir")
        pak_file = self.kwargs.get("pak_file")
        validate = self.kwargs.get("validate", True)
        
        def progress_callback(percentage, message):
            if not self.cancelled:
                self.progress_updated.emit(percentage, message)
        
        # Run validation if requested
        validation_results = None
        if validate:
            self.progress_updated.emit(10, "Validating mod structure...")
            validation_results = self.wine_wrapper.validate_mod_structure(source_dir)
        
        success, output = self.wine_wrapper.create_pak_with_monitoring(
            source_dir, pak_file, progress_callback
        )
        
        result_data = {
            "success": success,
            "output": output,
            "source_dir": source_dir,
            "pak_file": pak_file,
            "validation": validation_results,
            "conversions": [],
            "conversion_errors": []
        }
        
        self.operation_finished.emit(success, result_data)
    
    def cancel_operation(self):
        """Cancel the current operation"""
        self.cancelled = True
        if hasattr(self.wine_wrapper, 'current_monitor') and self.wine_wrapper.current_monitor:
            self.wine_wrapper.current_monitor.cancel()

class DivineOperationThread(QThread):
    """Thread for running divine.exe operations without blocking UI"""
    
    # Signals for communicating with main thread
    progress_updated = pyqtSignal(int, str)  # percentage, message
    operation_finished = pyqtSignal(bool, dict)  # success, result_data
    
    def __init__(self, wine_wrapper, operation_type, **kwargs):
        super().__init__()
        self.wine_wrapper = wine_wrapper
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.cancelled = False
    
    def run(self):
        """Run the divine operation in background thread"""
        try:
            if self.operation_type == "extract_pak":
                self._extract_pak()
            elif self.operation_type == "create_pak":
                self._create_pak()
            elif self.operation_type == "list_pak":
                self._list_pak()
            else:
                self.operation_finished.emit(False, {"error": f"Unknown operation: {self.operation_type}"})
        except Exception as e:
            self.operation_finished.emit(False, {"error": str(e)})
    
    def _extract_pak(self):
        """Extract PAK file operation"""
        pak_file = self.kwargs.get("pak_file")
        dest_dir = self.kwargs.get("dest_dir")
        
        def progress_callback(percentage, message):
            if not self.cancelled:
                self.progress_updated.emit(percentage, message)
        
        success, output = self.wine_wrapper.extract_pak_with_monitoring(
            pak_file, dest_dir, progress_callback
        )
        
        result_data = {
            "success": success,
            "output": output,
            "pak_file": pak_file,
            "dest_dir": dest_dir
        }
        
        self.operation_finished.emit(success, result_data)

    def _create_pak(self):
        """Enhanced create PAK with auto-conversion support"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        # Select source directory
        source_dir = QFileDialog.getExistingDirectory(
            self, "Select Folder to Pack",
            self.settings_manager.get("working_directory", "")
        )
        
        if not source_dir:
            return
        
        self.settings_manager.set("working_directory", source_dir)
        
        # Check for auto-conversion files using your existing classes
        # from larian_parser import AutoConversionProcessor, AutoConversionDialog
        
        processor = AutoConversionProcessor(self.wine_wrapper)
        conversion_files = processor.find_conversion_files(source_dir)
        total_conversions = sum(len(files) for files in conversion_files.values())
        
        # DEBUG: Print what was found
        print(f"Debug: Scanning directory: {source_dir}")
        print(f"Debug: Found {total_conversions} files needing conversion:")
        for conv_type, files in conversion_files.items():
            if files:
                print(f"  {conv_type}: {len(files)} files")
                for file_info in files:
                    print(f"    - {file_info['relative_path']}")
        
        # Show conversion preview if needed
        if total_conversions > 0:
            proceed = AutoConversionDialog.show_conversion_preview(self, conversion_files)
            if not proceed:
                print("Debug: User cancelled conversion")
                return
            print("Debug: User approved conversion - starting enhanced PAK creation")
            
            # Continue with PAK creation
            suggested_name = f"{os.path.basename(source_dir)}.pak"
            pak_file, _ = QFileDialog.getSaveFileName(
                self, "Save PAK File As",
                os.path.join(os.path.dirname(source_dir), suggested_name),
                "PAK Files (*.pak);;All Files (*)"
            )
            
            if not pak_file:
                return
            
            # Start creation with auto-conversion
            self.start_pak_operation_with_conversion("create_pak", 
                                                   source_dir=source_dir, 
                                                   pak_file=pak_file, 
                                                   validate=True)
        else:
            print("Debug: No conversion files found, proceeding with normal PAK creation")
            # Normal PAK creation
            suggested_name = f"{os.path.basename(source_dir)}.pak"
            pak_file, _ = QFileDialog.getSaveFileName(
                self, "Save PAK File As",
                os.path.join(os.path.dirname(source_dir), suggested_name),
                "PAK Files (*.pak);;All Files (*)"
            )
            
            if not pak_file:
                return
            
            self.start_pak_operation("create_pak", source_dir=source_dir, pak_file=pak_file, validate=True)
    
    def _list_pak(self):
        """List PAK contents operation"""
        pak_file = self.kwargs.get("pak_file")
        
        self.progress_updated.emit(20, "Reading PAK contents...")
        
        files = self.wine_wrapper.list_pak_contents(pak_file)
        
        result_data = {
            "success": len(files) > 0,
            "files": files,
            "file_count": len(files),
            "pak_file": pak_file
        }
        
        self.progress_updated.emit(100, "Complete!")
        self.operation_finished.emit(True, result_data)
    
    def cancel_operation(self):
        """Cancel the current operation"""
        self.cancelled = True
        if self.wine_wrapper.current_monitor:
            self.wine_wrapper.current_monitor.cancel()

class IndividualExtractionThread(QThread):
    """Thread for individual file extraction"""
    
    progress_updated = pyqtSignal(int, str)
    extraction_finished = pyqtSignal(bool, dict)
    
    def __init__(self, extractor, pak_file, file_paths, destination):
        super().__init__()
        self.extractor = extractor
        self.pak_file = pak_file
        self.file_paths = file_paths
        self.destination = destination
    
    def run(self):
        """Run extraction in background"""
        try:
            def progress_callback(percent, message):
                self.progress_updated.emit(percent, message)
            
            result = self.extractor.extract_specific_files(
                self.pak_file, self.file_paths, self.destination, progress_callback
            )
            
            self.extraction_finished.emit(result['success'], result)
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'extracted_files': []
            }
            self.extraction_finished.emit(False, error_result)