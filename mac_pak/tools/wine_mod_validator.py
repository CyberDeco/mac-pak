#!/usr/bin/env python3
"""
Mod Validator Module
Handles BG3 mod structure validation and metadata parsing
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path


class WineModValidator:
    """Specialized module for mod validation and metadata operations"""
    
    def __init__(self, wine_env=None, lslib_path=None, settings_manager=None):
        self.wine_env = wine_env
        self.lslib_path = lslib_path
        self.settings_manager = settings_manager
    
    def validate_mod_structure(self, mod_dir):
        """Validate BG3 mod folder structure with detailed analysis"""
        validation = {
            'valid': True,
            'structure': [],
            'warnings': [],
            'errors': [],
            'metadata': {}
        }
    
        if not os.path.exists(mod_dir):
            validation['valid'] = False
            validation['errors'].append(f"Directory does not exist: {mod_dir}")
            return validation
    
        # Check for Mods folder (required)
        mods_path = os.path.join(mod_dir, "Mods")
        if not os.path.exists(mods_path):
            validation['valid'] = False
            validation['errors'].append("Missing required Mods/ directory")
            return validation
        
        validation['structure'].append("Found Mods/")
        
        # Analyze mod subfolders
        self._analyze_mods_directory(mods_path, validation)
        
        # Check for optional folders
        self._check_optional_folders(mod_dir, validation)
        
        # Validate overall structure integrity
        self._validate_structure_integrity(validation)
        
        return validation
    
    def _analyze_mods_directory(self, mods_path, validation):
        """Analyze the Mods/ directory structure"""
        meta_found = False
        
        try:
            mod_subfolders = [d for d in os.listdir(mods_path) if os.path.isdir(os.path.join(mods_path, d))]
            game_content_folders = {"GustavDev", "Gustav", "Shared", "Engine", "Game", "Core"}
            
            if not mod_subfolders:
                validation['warnings'].append("No mod subfolders found in Mods/")
                return
            
            for subfolder in mod_subfolders:
                subfolder_path = os.path.join(mods_path, subfolder)
                
                if subfolder in game_content_folders:
                    validation['structure'].append(f"Game content folder: Mods/{subfolder}/")
                    self._analyze_game_content_folder(subfolder_path, subfolder, validation)
                    continue
                
                # Check for meta.lsx in custom mod folders
                meta_path = os.path.join(subfolder_path, "meta.lsx")
                if os.path.exists(meta_path):
                    validation['structure'].append(f"meta.lsx found in Mods/{subfolder}/")
                    meta_found = True
                    
                    # Parse metadata
                    metadata = self._parse_meta_lsx(meta_path)
                    if metadata:
                        validation['metadata'][subfolder] = metadata
                    
                    # Validate mod folder contents
                    self._validate_mod_folder_contents(subfolder_path, subfolder, validation)
                else:
                    validation['warnings'].append(f"meta.lsx missing in Mods/{subfolder}/")
            
            if not meta_found:
                validation['warnings'].append("No meta.lsx found - this mod may not work properly")
                
        except Exception as e:
            validation['errors'].append(f"Error reading Mods folder: {e}")
    
    def _analyze_game_content_folder(self, folder_path, folder_name, validation):
        """Analyze game content folders for proper structure"""
        expected_subfolders = {
            "Gustav": ["Assets", "Content", "Scripts"],
            "GustavDev": ["Assets", "Content"],
            "Shared": ["Assets", "Content"],
            "Engine": ["Content"],
            "Game": ["Content"],
            "Core": ["Content"]
        }
        
        if folder_name in expected_subfolders:
            for expected_subfolder in expected_subfolders[folder_name]:
                subfolder_path = os.path.join(folder_path, expected_subfolder)
                if os.path.exists(subfolder_path):
                    validation['structure'].append(f"Found Mods/{folder_name}/{expected_subfolder}/")
                else:
                    validation['warnings'].append(f"Missing Mods/{folder_name}/{expected_subfolder}/")
    
    def _validate_mod_folder_contents(self, mod_folder_path, mod_name, validation):
        """Validate contents of a custom mod folder"""
        # Check for common mod file types
        file_types_found = set()
        
        for root, dirs, files in os.walk(mod_folder_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                file_types_found.add(ext)
        
        # Report found file types
        if file_types_found:
            validation['structure'].append(f"File types in {mod_name}: {', '.join(sorted(file_types_found))}")
        
        # Check for specific important files
        important_files = ["meta.lsx"]
        for important_file in important_files:
            file_path = os.path.join(mod_folder_path, important_file)
            if not os.path.exists(file_path):
                validation['warnings'].append(f"Important file missing in {mod_name}: {important_file}")
    
    def _check_optional_folders(self, mod_dir, validation):
        """Check for optional folders and their contents"""
        optional_folders = {
            'Public': 'Game assets and resources',
            'Localization': 'Translation files',
            'Generated': 'Auto-generated content'
        }
        
        for folder, description in optional_folders.items():
            folder_path = os.path.join(mod_dir, folder)
            if os.path.exists(folder_path):
                validation['structure'].append(f"Found {folder}/ ({description})")
                
                # Count files in optional folders
                file_count = sum(len(files) for _, _, files in os.walk(folder_path))
                if file_count > 0:
                    validation['structure'].append(f"  {file_count} files in {folder}/")
                else:
                    validation['warnings'].append(f"{folder}/ is empty")
            else:
                validation['warnings'].append(f"Optional {folder}/ not found")
    
    def _validate_structure_integrity(self, validation):
        """Validate overall mod structure integrity"""
        # Check if we have any actual content
        content_indicators = [
            item for item in validation['structure'] 
            if 'meta.lsx' in item or 'Game content folder' in item
        ]
        
        if not content_indicators:
            validation['valid'] = False
            validation['errors'].append("No valid mod content found (no meta.lsx or game content folders)")
        
        # Check for common issues
        if len(validation['warnings']) > len(validation['structure']):
            validation['warnings'].append("More warnings than structural elements found - review mod structure")
    
    def _parse_meta_lsx(self, meta_path):
        """Parse meta.lsx file to extract mod metadata"""
        try:
            tree = ET.parse(meta_path)
            root = tree.getroot()
            
            metadata = {}
            
            # Extract common metadata fields
            for node in root.iter():
                if node.tag == 'attribute' and 'id' in node.attrib:
                    attr_id = node.attrib['id']
                    value = node.attrib.get('value', '')
                    
                    # Map common attribute IDs to readable names
                    field_mapping = {
                        'Name': 'name',
                        'UUID': 'uuid',
                        'Version': 'version',
                        'Author': 'author',
                        'Description': 'description',
                        'ModuleType': 'module_type'
                    }
                    
                    if attr_id in field_mapping:
                        metadata[field_mapping[attr_id]] = value
            
            return metadata
            
        except Exception as e:
            return {'error': f"Failed to parse meta.lsx: {e}"}
    
    def validate_pak_as_mod(self, pak_file):
        """Validate if a PAK file contains valid mod structure"""
        # This would require extracting the PAK and validating its contents
        # For now, return basic file info
        try:
            file_size = os.path.getsize(pak_file)
            
            validation = {
                'valid': True,  # Assume valid until we can extract and check
                'file_path': pak_file,
                'file_size': file_size,
                'size_formatted': f"{file_size:,} bytes",
                'warnings': ['PAK validation requires extraction - not yet implemented'],
                'structure': [f"PAK file: {os.path.basename(pak_file)}"]
            }
            
            return validation
            
        except Exception as e:
            return {
                'valid': False,
                'file_path': pak_file,
                'error': str(e)
            }
    
    def get_mod_summary(self, mod_dir):
        """Get a comprehensive summary of a mod"""
        validation = self.validate_mod_structure(mod_dir)
        
        summary = {
            'path': mod_dir,
            'valid': validation['valid'],
            'structure_count': len(validation['structure']),
            'warning_count': len(validation['warnings']),
            'error_count': len(validation['errors']),
            'metadata': validation['metadata'],
            'quick_status': 'Valid' if validation['valid'] else 'Invalid'
        }
        
        # Add quick description
        if validation['valid']:
            if validation['metadata']:
                mod_names = [meta.get('name', 'Unknown') for meta in validation['metadata'].values()]
                summary['description'] = f"Contains mods: {', '.join(mod_names)}"
            else:
                summary['description'] = f"Valid mod with {summary['structure_count']} structural elements"
        else:
            summary['description'] = f"Invalid mod: {'; '.join(validation['errors'])}"
        
        return summary
    
    def compare_mod_versions(self, mod_dir1, mod_dir2):
        """Compare two mod directories for differences"""
        summary1 = self.get_mod_summary(mod_dir1)
        summary2 = self.get_mod_summary(mod_dir2)
        
        comparison = {
            'mod1': summary1,
            'mod2': summary2,
            'differences': []
        }
        
        # Compare metadata
        meta1 = summary1.get('metadata', {})
        meta2 = summary2.get('metadata', {})
        
        all_mod_names = set(meta1.keys()) | set(meta2.keys())
        
        for mod_name in all_mod_names:
            if mod_name in meta1 and mod_name in meta2:
                # Compare versions if available
                ver1 = meta1[mod_name].get('version', 'Unknown')
                ver2 = meta2[mod_name].get('version', 'Unknown')
                if ver1 != ver2:
                    comparison['differences'].append(f"Version difference in {mod_name}: {ver1} vs {ver2}")
            elif mod_name in meta1:
                comparison['differences'].append(f"Mod {mod_name} only in first directory")
            else:
                comparison['differences'].append(f"Mod {mod_name} only in second directory")
        
        return comparison