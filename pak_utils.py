#!/usr/bin/env python3
"""
PAK Operations Module
Handles all Divine.exe operations with progress feedback
Separated from GUI for cleaner architecture
"""

import os
import time
import threading
from pathlib import Path

class PAKOperations:
    """High-level PAK operations with progress feedback"""
    
    def __init__(self, bg3_tool):
        self.bg3_tool = bg3_tool
    
    def extract_pak_threaded(self, pak_file, destination_dir, progress_callback=None, completion_callback=None):
        """Extract PAK with threaded progress tracking"""
        
        def extraction_worker():
            try:
                if progress_callback:
                    progress_callback(10, "Starting extraction...")
                
                # Use the enhanced monitoring method from BG3MacTool
                success, output = self.bg3_tool.extract_pak_with_monitoring(
                    pak_file, destination_dir, progress_callback
                )
                
                if completion_callback:
                    completion_callback(success, output if success else f"Extraction failed: {output}")
                
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Error: {e}")
                if completion_callback:
                    completion_callback(False, f"Exception during extraction: {e}")
        
        # Start in background thread
        thread = threading.Thread(target=extraction_worker, daemon=True)
        thread.start()
        return thread
    
    def create_pak_threaded(self, source_dir, pak_file, progress_callback=None, completion_callback=None, validate=True):
        """Create PAK with threaded progress tracking and optional validation"""
        
        def creation_worker():
            try:
                if progress_callback:
                    progress_callback(5, "Preparing...")
                
                # Optional validation step
                validation_results = None
                if validate:
                    if progress_callback:
                        progress_callback(15, "Validating mod structure...")
                    
                    validation_results = self.validate_mod_structure(source_dir)
                    
                    if progress_callback:
                        progress_callback(25, "Validation complete")
                
                # Create the PAK
                if progress_callback:
                    progress_callback(30, "Creating PAK file...")
                
                success, output = self.bg3_tool.create_pak_with_monitoring(
                    source_dir, pak_file, progress_callback
                )
                
                # Prepare result data
                result_data = {
                    'success': success,
                    'output': output,
                    'validation': validation_results,
                    'pak_file': pak_file,
                    'source_dir': source_dir
                }
                
                if completion_callback:
                    completion_callback(result_data)
                
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Error: {e}")
                if completion_callback:
                    completion_callback({
                        'success': False,
                        'output': f"Exception during PAK creation: {e}",
                        'validation': None
                    })
        
        # Start in background thread
        thread = threading.Thread(target=creation_worker, daemon=True)
        thread.start()
        return thread
    
    def list_pak_contents_threaded(self, pak_file, progress_callback=None, completion_callback=None):
        """List PAK contents with threaded progress tracking"""
        
        def listing_worker():
            try:
                if progress_callback:
                    progress_callback(20, "Reading PAK file...")
                
                files = self.bg3_tool.list_pak_contents(pak_file)
                
                if progress_callback:
                    progress_callback(80, "Processing file list...")
                
                # Organize results
                result_data = {
                    'success': True,
                    'file_count': len(files),
                    'files': files,
                    'pak_file': pak_file
                }
                
                if progress_callback:
                    progress_callback(100, "Complete!")
                
                if completion_callback:
                    completion_callback(result_data)
                
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Error: {e}")
                if completion_callback:
                    completion_callback({
                        'success': False,
                        'error': str(e),
                        'pak_file': pak_file
                    })
        
        # Start in background thread
        thread = threading.Thread(target=listing_worker, daemon=True)
        thread.start()
        return thread
    
    def validate_mod_structure(self, mod_dir):
        """Validate BG3 mod folder structure (synchronous)"""
        validation = {
            'valid': True,
            'structure': [],
            'warnings': [],
            'mod_dir': mod_dir
        }
        
        if not os.path.exists(mod_dir):
            validation['valid'] = False
            validation['warnings'].append(f"Directory does not exist: {mod_dir}")
            return validation
        
        # Expected structure for BG3 mods
        expected_structure = {
            'Mods': {
                'required': True,
                'description': 'Main mod folder'
            },
            'Public': {
                'required': False,
                'description': 'Public assets'
            },
            'Localization': {
                'required': False,
                'description': 'Translation files'
            }
        }
        
        for folder_name, info in expected_structure.items():
            folder_path = os.path.join(mod_dir, folder_name)
            if os.path.exists(folder_path):
                validation['structure'].append(f"Found {folder_name}/")
                
                # Check for meta.lsx in Mods folder
                if folder_name == 'Mods':
                    try:
                        mod_subfolders = [d for d in os.listdir(folder_path) 
                                        if os.path.isdir(os.path.join(folder_path, d))]
                        for subfolder in mod_subfolders:
                            meta_path = os.path.join(folder_path, subfolder, 'meta.lsx')
                            if os.path.exists(meta_path):
                                validation['structure'].append(f"Found {subfolder}/meta.lsx")
                                
                                # Basic meta.lsx validation
                                try:
                                    meta_issues = self._validate_meta_lsx(meta_path)
                                    if meta_issues:
                                        validation['warnings'].extend([f"meta.lsx: {issue}" for issue in meta_issues])
                                except Exception as e:
                                    validation['warnings'].append(f"Could not validate meta.lsx: {e}")
                            else:
                                validation['warnings'].append(f"Missing meta.lsx in {subfolder}/")
                    except PermissionError:
                        validation['warnings'].append(f"Cannot read {folder_name}/ - permission denied")
                            
            else:
                if info['required']:
                    validation['valid'] = False
                    validation['warnings'].append(f"Missing required {folder_name}/")
                else:
                    validation['warnings'].append(f"Optional {folder_name}/ not found")
        
        return validation
    
    def _validate_meta_lsx(self, meta_path):
        """Basic validation of meta.lsx file"""
        issues = []
        
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(meta_path)
            root = tree.getroot()
            
            # Check for required fields
            module_info = root.find('.//node[@id="ModuleInfo"]')
            if module_info is None:
                issues.append("Missing ModuleInfo node")
                return issues
            
            required_attributes = ['UUID', 'Name', 'Author', 'Version64', 'Folder']
            for attr_name in required_attributes:
                attr = module_info.find(f'.//attribute[@id="{attr_name}"]')
                if attr is None:
                    issues.append(f"Missing required attribute: {attr_name}")
                elif not attr.get('value', '').strip():
                    issues.append(f"Empty value for: {attr_name}")
            
            # Validate UUID format
            uuid_attr = module_info.find('.//attribute[@id="UUID"]')
            if uuid_attr is not None:
                import re
                uuid_value = uuid_attr.get('value', '')
                if not re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', uuid_value):
                    issues.append(f"Invalid UUID format: {uuid_value}")
            
        except ET.ParseError as e:
            issues.append(f"XML parsing error: {e}")
        except Exception as e:
            issues.append(f"Validation error: {e}")
            
        return issues