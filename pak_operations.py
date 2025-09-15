#!/usr/bin/env python3
"""
PAK Operations Backend for PyQt6 Version
Handles all PAK file operations with proper threading and progress reporting
This replaces the pak_utils.py functionality with PyQt6 threading
"""

import os
import threading
import time
import tempfile
import shutil
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QHBoxLayout, QMessageBox, QFileDialog,
                            QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QGroupBox, QCheckBox)

class PAKOperations(QObject):
    """PAK operations backend that integrates with WineWrapper"""
    
    # Signals for progress reporting
    progress_updated = pyqtSignal(int, str)  # percentage, message
    operation_completed = pyqtSignal(bool, dict)  # success, result_data
    
    def __init__(self, wine_wrapper):
        super().__init__()
        self.wine_wrapper = wine_wrapper
    
    def extract_pak_threaded(self, pak_file, dest_dir, progress_callback, completion_callback):
        """Extract PAK file in background thread"""
        def extract_worker():
            try:
                # Progress callback wrapper
                def progress_wrapper(percentage, message):
                    if progress_callback:
                        progress_callback(percentage, message)
                
                # Use WineWrapper's extract method with monitoring
                success, output = self.wine_wrapper.extract_pak_with_monitoring(
                    pak_file, dest_dir, progress_wrapper
                )
                
                # Call completion callback
                if completion_callback:
                    result_data = {
                        'success': success,
                        'output': output,
                        'pak_file': pak_file,
                        'dest_dir': dest_dir
                    }
                    completion_callback(result_data)
                    
            except Exception as e:
                if completion_callback:
                    result_data = {
                        'success': False,
                        'output': str(e),
                        'pak_file': pak_file,
                        'dest_dir': dest_dir
                    }
                    completion_callback(result_data)
        
        # Start thread
        thread = threading.Thread(target=extract_worker, daemon=True)
        thread.start()
    
    def create_pak_threaded(self, source_dir, pak_file, progress_callback, completion_callback, validate=True):
        """Create PAK file in background thread with optional validation"""
        def create_worker():
            try:
                result_data = {
                    'success': False,
                    'output': '',
                    'source_dir': source_dir,
                    'pak_file': pak_file,
                    'validation': None
                }
                
                # Progress callback wrapper
                def progress_wrapper(percentage, message):
                    if progress_callback:
                        progress_callback(percentage, message)
                
                # Run validation if requested
                if validate:
                    if progress_callback:
                        progress_callback(10, "Validating mod structure...")
                    
                    validation = self.validate_mod_structure(source_dir)
                    result_data['validation'] = validation
                    
                    if not validation['valid']:
                        if progress_callback:
                            progress_callback(100, "Validation failed")
                        
                        result_data['output'] = "Mod structure validation failed. Check warnings above."
                        if completion_callback:
                            completion_callback(result_data)
                        return
                
                # Create PAK using WineWrapper
                success, output = self.wine_wrapper.create_pak_with_monitoring(
                    source_dir, pak_file, progress_wrapper
                )
                
                result_data['success'] = success
                result_data['output'] = output
                
                if completion_callback:
                    completion_callback(result_data)
                    
            except Exception as e:
                result_data = {
                    'success': False,
                    'output': str(e),
                    'source_dir': source_dir,
                    'pak_file': pak_file,
                    'validation': None
                }
                if completion_callback:
                    completion_callback(result_data)
        
        # Start thread
        thread = threading.Thread(target=create_worker, daemon=True)
        thread.start()
    
    def list_pak_contents_threaded(self, pak_file, progress_callback, completion_callback):
        """List PAK contents in background thread"""
        def list_worker():
            try:
                if progress_callback:
                    progress_callback(20, "Reading PAK structure...")
                
                # Use WineWrapper's list method
                files = self.wine_wrapper.list_pak_contents(pak_file)
                
                if progress_callback:
                    progress_callback(80, f"Found {len(files)} files...")
                
                # Format file information
                formatted_files = []
                for file_info in files:
                    if isinstance(file_info, dict):
                        formatted_files.append(file_info)
                    else:
                        # Convert string to dict format
                        file_name = str(file_info)
                        file_type = 'folder' if '.' not in file_name else 'file'
                        formatted_files.append({
                            'name': file_name,
                            'type': file_type
                        })
                
                result_data = {
                    'success': len(formatted_files) > 0,
                    'files': formatted_files,
                    'file_count': len(formatted_files),
                    'pak_file': pak_file
                }
                
                if progress_callback:
                    progress_callback(100, "Complete!")
                
                if completion_callback:
                    completion_callback(result_data)
                    
            except Exception as e:
                result_data = {
                    'success': False,
                    'error': str(e),
                    'files': [],
                    'file_count': 0,
                    'pak_file': pak_file
                }
                if completion_callback:
                    completion_callback(result_data)
        
        # Start thread
        thread = threading.Thread(target=list_worker, daemon=True)
        thread.start()
    
    def validate_mod_structure(self, mod_dir):
        """
        Enhanced mod validation - builds on WineWrapper's basic validation
        This version is more comprehensive for BG3 mods
        """
        validation = {
            'valid': True,
            'structure': [],
            'warnings': [],
            'mod_info': {}
        }
        
        if not os.path.exists(mod_dir):
            validation['valid'] = False
            validation['warnings'].append(f"Directory does not exist: {mod_dir}")
            return validation
        
        # Check for essential BG3 mod structure
        mods_path = os.path.join(mod_dir, "Mods")
        if not os.path.exists(mods_path):
            validation['valid'] = False
            validation['warnings'].append("Missing required 'Mods' folder")
            return validation
        
        validation['structure'].append("Found Mods/ folder")
        
        # Look for mod subfolders and meta.lsx files
        # Look for mod subfolders and meta.lsx files
        meta_found = False
        mod_folders = []
        
        try:
            for item in os.listdir(mods_path):
                item_path = os.path.join(mods_path, item)
                if os.path.isdir(item_path):
                    mod_folders.append(item)
                    
                    # Check for meta.lsx
                    meta_path = os.path.join(item_path, "meta.lsx")
                    if os.path.exists(meta_path):
                        validation['structure'].append(f"Found meta.lsx in Mods/{item}/")
                        meta_found = True
                        
                        # Try to parse meta.lsx for mod info
                        try:
                            mod_info = self.parse_meta_lsx(meta_path)
                            validation['mod_info'] = mod_info
                        except Exception as e:
                            validation['warnings'].append(f"Could not parse meta.lsx: {e}")
                    else:
                        validation['warnings'].append(f"meta.lsx missing in Mods/{item}/")
            
            if not mod_folders:
                validation['warnings'].append("No mod subfolders found in Mods/")
                
        except Exception as e:
            validation['warnings'].append(f"Error reading Mods folder: {e}")
        
        if not meta_found:
            validation['warnings'].append("No meta.lsx found - mod may not load properly")
        
        # Check for optional but common folders
        optional_folders = ['Public', 'Localization', 'Generated']
        for folder in optional_folders:
            folder_path = os.path.join(mod_dir, folder)
            if os.path.exists(folder_path):
                validation['structure'].append(f"Found {folder}/ folder")
                
                # Check folder contents
                if folder == 'Public':
                    self.validate_public_folder(folder_path, validation)
                elif folder == 'Localization':
                    self.validate_localization_folder(folder_path, validation)
        
        # Check for common file structure issues
        self.check_common_issues(mod_dir, validation)
        
        return validation
    
    def parse_meta_lsx(self, meta_path):
        """Parse meta.lsx file for mod information"""
        import xml.etree.ElementTree as ET
        
        mod_info = {
            'name': 'Unknown',
            'uuid': 'Unknown',
            'version': 'Unknown',
            'author': 'Unknown',
            'description': 'No description'
        }
        
        try:
            tree = ET.parse(meta_path)
            root = tree.getroot()
            
            # Find ModuleInfo node
            for node in root.findall(".//node[@id='ModuleInfo']"):
                for attr in node.findall(".//attribute"):
                    attr_id = attr.get('id')
                    attr_value = attr.get('value', '')
                    
                    if attr_id == 'Name':
                        mod_info['name'] = attr_value
                    elif attr_id == 'UUID':
                        mod_info['uuid'] = attr_value
                    elif attr_id == 'Version64':
                        mod_info['version'] = attr_value
                    elif attr_id == 'Author':
                        mod_info['author'] = attr_value
                    elif attr_id == 'Description':
                        mod_info['description'] = attr_value
        
        except Exception as e:
            print(f"Error parsing meta.lsx: {e}")
        
        return mod_info
    
    def validate_public_folder(self, public_path, validation):
        """Validate Public folder structure"""
        # Look for common Public folder contents
        common_subfolders = ['Game', 'Shared', 'Gustav']
        found_subfolders = []
        
        try:
            for item in os.listdir(public_path):
                if os.path.isdir(os.path.join(public_path, item)):
                    found_subfolders.append(item)
                    if item in common_subfolders:
                        validation['structure'].append(f"Found Public/{item}/ folder")
        
        except Exception as e:
            validation['warnings'].append(f"Error reading Public folder: {e}")
        
        if not found_subfolders:
            validation['warnings'].append("Public folder is empty")
    
    def validate_localization_folder(self, loc_path, validation):
        """Validate Localization folder structure"""
        try:
            # Look for language folders
            language_folders = []
            for item in os.listdir(loc_path):
                item_path = os.path.join(loc_path, item)
                if os.path.isdir(item_path):
                    language_folders.append(item)
                    
                    # Check for .loca files
                    loca_files = [f for f in os.listdir(item_path) if f.endswith('.loca')]
                    if loca_files:
                        validation['structure'].append(f"Found localization for {item} ({len(loca_files)} files)")
                    else:
                        validation['warnings'].append(f"No .loca files in Localization/{item}/")
            
            if not language_folders:
                validation['warnings'].append("Localization folder contains no language folders")
        
        except Exception as e:
            validation['warnings'].append(f"Error reading Localization folder: {e}")
    
    def check_common_issues(self, mod_dir, validation):
        """Check for common mod structure issues"""
        
        # Check for files in root that should be in subfolders
        try:
            root_files = [f for f in os.listdir(mod_dir) if os.path.isfile(os.path.join(mod_dir, f))]
            
            problematic_files = []
            for file in root_files:
                if file.lower().endswith(('.lsx', '.lsf', '.loca', '.dds', '.gr2')):
                    problematic_files.append(file)
            
            if problematic_files:
                validation['warnings'].append(
                    f"Game files found in root directory (should be in subfolders): {', '.join(problematic_files[:3])}"
                    + ("..." if len(problematic_files) > 3 else "")
                )
        
        except Exception as e:
            validation['warnings'].append(f"Error checking root directory: {e}")
        
        # Check for case sensitivity issues (common on Mac/Linux)
        self.check_case_sensitivity_issues(mod_dir, validation)
    
    def check_case_sensitivity_issues(self, mod_dir, validation):
        """Check for potential case sensitivity issues"""
        
        # Common folders that should have specific capitalization
        expected_folders = {
            'mods': 'Mods',
            'public': 'Public', 
            'localization': 'Localization',
            'generated': 'Generated'
        }
        
        try:
            actual_folders = [f for f in os.listdir(mod_dir) if os.path.isdir(os.path.join(mod_dir, f))]
            
            for actual in actual_folders:
                actual_lower = actual.lower()
                if actual_lower in expected_folders and actual != expected_folders[actual_lower]:
                    validation['warnings'].append(
                        f"Folder '{actual}' should be '{expected_folders[actual_lower]}' (case sensitive)"
                    )
        
        except Exception as e:
            validation['warnings'].append(f"Error checking case sensitivity: {e}")
    
    def get_pak_info(self, pak_file):
        """Get detailed information about a PAK file"""
        try:
            file_size = os.path.getsize(pak_file)
            files = self.wine_wrapper.list_pak_contents(pak_file)
            
            info = {
                'file_path': pak_file,
                'file_name': os.path.basename(pak_file),
                'file_size': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'file_count': len(files),
                'files': files[:100],  # First 100 files
                'has_more_files': len(files) > 100
            }
            
            # Analyze file types
            file_types = {}
            for file_info in files:
                if isinstance(file_info, dict):
                    name = file_info.get('name', '')
                else:
                    name = str(file_info)
                
                ext = os.path.splitext(name)[1].lower()
                if ext:
                    file_types[ext] = file_types.get(ext, 0) + 1
                else:
                    file_types['no_extension'] = file_types.get('no_extension', 0) + 1
            
            info['file_types'] = dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True))
            
            return info
            
        except Exception as e:
            return {'error': str(e)}
    
    def estimate_extraction_time(self, pak_file):
        """Estimate extraction time based on file size and count"""
        try:
            file_size = os.path.getsize(pak_file)
            files = self.wine_wrapper.list_pak_contents(pak_file)
            file_count = len(files)
            
            # Rough estimates based on typical performance
            # These are very rough estimates and will vary by system
            size_factor = file_size / (1024 * 1024)  # MB
            count_factor = file_count / 100
            
            estimated_seconds = (size_factor * 0.5) + (count_factor * 2)  # Very rough formula
            
            return max(5, min(300, estimated_seconds))  # Between 5 seconds and 5 minutes
            
        except:
            return 30  # Default estimate

class IndividualFileExtractor:
    """Handles extraction of specific files from PAK archives"""
    
    def __init__(self, wine_wrapper):
        self.wine_wrapper = wine_wrapper
    
    def extract_specific_files(self, pak_file, file_paths, destination, progress_callback=None):
        """
        Extract specific files from PAK
        
        Args:
            pak_file: Path to PAK file
            file_paths: List of file paths within PAK to extract
            destination: Destination directory
            progress_callback: Progress callback function
            
        Returns:
            dict: Results with success status and extracted files
        """
        try:
            if progress_callback:
                progress_callback(5, "Preparing extraction...")
            
            # Create temporary directory for full extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                if progress_callback:
                    progress_callback(10, "Extracting PAK to temporary location...")
                
                # Extract entire PAK to temp (this is the limitation of divine.exe)
                def temp_progress(pct, msg):
                    # Scale progress from 10-70%
                    scaled_pct = 10 + int(pct * 0.6)
                    progress_callback(scaled_pct, f"Extracting PAK: {msg}")
                
                success, output = self.wine_wrapper.extract_pak_with_monitoring(
                    pak_file, temp_dir, temp_progress if progress_callback else None
                )
                
                if not success:
                    return {
                        'success': False,
                        'error': f"Failed to extract PAK: {output}",
                        'extracted_files': []
                    }
                
                if progress_callback:
                    progress_callback(75, "Copying requested files...")
                
                # Copy only the requested files
                extracted_files = []
                total_files = len(file_paths)
                
                for i, file_path in enumerate(file_paths):
                    # Convert forward slashes to OS-specific separators
                    normalized_path = file_path.replace('/', os.sep)
                    source_file = os.path.join(temp_dir, normalized_path)
                    
                    if os.path.exists(source_file):
                        # Create destination path maintaining directory structure
                        dest_file = os.path.join(destination, normalized_path)
                        dest_dir = os.path.dirname(dest_file)
                        
                        # Create destination directory if needed
                        os.makedirs(dest_dir, exist_ok=True)
                        
                        # Copy file
                        shutil.copy2(source_file, dest_file)
                        extracted_files.append({
                            'source_path': file_path,
                            'dest_path': dest_file,
                            'size': os.path.getsize(source_file)
                        })
                    else:
                        print(f"Warning: File not found in PAK: {file_path}")
                    
                    # Update progress
                    if progress_callback and total_files > 0:
                        file_progress = 75 + int((i / total_files) * 20)
                        progress_callback(file_progress, f"Copied {i+1}/{total_files} files")
                
                if progress_callback:
                    progress_callback(100, f"Extracted {len(extracted_files)} files")
                
                return {
                    'success': True,
                    'extracted_files': extracted_files,
                    'destination': destination
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'extracted_files': []
            }

class FileSelectionDialog(QDialog):
    """Dialog for selecting specific files from a PAK for extraction"""
    
    def __init__(self, parent, pak_file, wine_wrapper):
        super().__init__(parent)
        self.pak_file = pak_file
        self.wine_wrapper = wine_wrapper
        self.files_list = []
        self.selected_files = []
        
        self.setWindowTitle(f"Select Files to Extract - {Path(pak_file).name}")
        self.setModal(True)
        self.resize(600, 500)
        
        self.setup_ui()
        self.load_pak_contents()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(f"Select files to extract from: {Path(self.pak_file).name}")
        layout.addWidget(info_label)
        
        # Search/filter
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Filter:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter filename or extension to filter...")
        self.search_edit.textChanged.connect(self.filter_files)
        search_layout.addWidget(self.search_edit)
        
        layout.addLayout(search_layout)
        
        # Selection controls
        selection_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_files)
        selection_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self.select_no_files)
        selection_layout.addWidget(select_none_btn)
        
        select_by_type_btn = QPushButton("Select by Type...")
        select_by_type_btn.clicked.connect(self.select_by_type)
        selection_layout.addWidget(select_by_type_btn)
        
        selection_layout.addStretch()
        layout.addLayout(selection_layout)
        
        # File tree
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(['File Name', 'Type', 'Path'])
        self.file_tree.setRootIsDecorated(False)
        self.file_tree.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.file_tree)
        
        # Selection info
        self.selection_info = QLabel("0 files selected")
        layout.addWidget(self.selection_info)
        
        # Destination selection
        dest_group = QGroupBox("Extraction Destination")
        dest_layout = QHBoxLayout(dest_group)
        
        self.dest_edit = QLineEdit()
        dest_layout.addWidget(self.dest_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_destination)
        dest_layout.addWidget(browse_btn)
        
        layout.addWidget(dest_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        self.maintain_structure_cb = QCheckBox("Maintain directory structure")
        self.maintain_structure_cb.setChecked(True)
        options_layout.addWidget(self.maintain_structure_cb)
        
        self.auto_convert_cb = QCheckBox("Auto-convert LSF files to LSX")
        options_layout.addWidget(self.auto_convert_cb)
        
        layout.addWidget(options_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.extract_btn = QPushButton("Extract Selected")
        self.extract_btn.clicked.connect(self.start_extraction)
        self.extract_btn.setEnabled(False)
        button_layout.addWidget(self.extract_btn)
        
        layout.addLayout(button_layout)
    
    def load_pak_contents(self):
        """Load PAK contents into tree"""
        try:
            files = self.wine_wrapper.list_pak_contents(self.pak_file)
            self.files_list = files
            
            self.populate_file_tree(files)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read PAK contents: {e}")
    
    def populate_file_tree(self, files):
        """Populate file tree with files"""
        self.file_tree.clear()
        
        for file_info in files:
            # Handle different formats of file_info
            if isinstance(file_info, dict):
                file_path = file_info.get('name', str(file_info))
                file_size = file_info.get('size', 0)
            else:
                # If it's a string, split by whitespace to separate path from metadata
                file_str = str(file_info).strip()
                parts = file_str.split()
                
                # The file path is everything except the last few numeric parts
                # Look for where the numeric metadata starts
                path_parts = []
                for part in parts:
                    # If this part looks like a number, stop adding to path
                    if part.isdigit():
                        break
                    path_parts.append(part)
                
                file_path = ' '.join(path_parts) if path_parts else file_str
                file_size = 0
            
            # Skip directories for individual file extraction
            file_name = Path(file_path).name
            if '.' not in file_name or not file_path.strip():
                continue
            
            item = QTreeWidgetItem(self.file_tree)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)  # Start unchecked so user can select
            
            file_ext = Path(file_path).suffix.lower()
            
            # Set the correct columns
            item.setText(0, file_name)      # File Name column
            item.setText(1, file_ext)       # Type column  
            item.setText(2, file_path)      # Path column (clean path without metadata)
            
            # Store the clean path for extraction
            item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            
            print(f"Debug: Added file to tree: '{file_path}'")  # Debug output
        
        # Resize columns to content
        for i in range(3):
            self.file_tree.resizeColumnToContents(i)
    
    def filter_files(self):
        """Filter files based on search term"""
        search_term = self.search_edit.text().lower()
        
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            
            if not search_term:
                item.setHidden(False)
            else:
                # Check if search term matches filename, extension, or path
                file_name = item.text(0).lower()
                file_ext = item.text(1).lower()
                file_path = item.text(2).lower()
                
                matches = (search_term in file_name or 
                          search_term in file_ext or 
                          search_term in file_path)
                
                item.setHidden(not matches)
    
    def select_all_files(self):
        """Select all visible files"""
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            if not item.isHidden():
                item.setCheckState(0, Qt.CheckState.Checked)
    
    def select_no_files(self):
        """Deselect all files"""
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Unchecked)
    
    def select_by_type(self):
        """Select files by extension"""
        from PyQt6.QtWidgets import QInputDialog
        
        # Get all unique extensions
        extensions = set()
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            ext = item.text(1)
            if ext:
                extensions.add(ext)
        
        extensions = sorted(list(extensions))
        
        if not extensions:
            return
        
        extension, ok = QInputDialog.getItem(
            self, "Select by Type", 
            "Choose file type:", 
            extensions, 0, False
        )
        
        if ok:
            for i in range(self.file_tree.topLevelItemCount()):
                item = self.file_tree.topLevelItem(i)
                if item.text(1) == extension:
                    item.setCheckState(0, Qt.CheckState.Checked)
    
    def on_item_changed(self, item):
        """Handle item check state changes"""
        self.update_selection_info()
    
    def update_selection_info(self):
        """Update selection information"""
        selected_count = 0
        
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                selected_count += 1
        
        self.selection_info.setText(f"{selected_count} files selected")
        self.extract_btn.setEnabled(selected_count > 0 and bool(self.dest_edit.text()))
    
    def browse_destination(self):
        """Browse for extraction destination"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Extraction Destination"
        )
        
        if directory:
            self.dest_edit.setText(directory)
            self.update_selection_info()
    
    def start_extraction(self):
        """Start the extraction process"""
        # Get selected files
        selected_files = []
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                file_path = item.data(0, Qt.ItemDataRole.UserRole)
                selected_files.append(file_path)
        
        if not selected_files:
            QMessageBox.warning(self, "No Selection", "Please select files to extract.")
            return
        
        destination = self.dest_edit.text()
        if not destination:
            QMessageBox.warning(self, "No Destination", "Please select an extraction destination.")
            return
        
        self.selected_files = selected_files
        self.destination = destination
        self.accept()

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