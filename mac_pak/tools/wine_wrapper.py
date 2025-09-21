#!/usr/bin/env python3
"""
Wine Integration for BG3 Mac Tool - App Bundle Compatible Version
Main wrapper class using the wine environment manager
"""

import subprocess
import os
import sys
import shutil
import threading
import tempfile
from pathlib import Path

from .wine_environment import WineEnvironmentManager, WineProcessMonitor
from ..data.parsers.larian_parser import *

class WineWrapper:
    """BG3 Mac tool with Wine integration - App Bundle Compatible"""
    
    def __init__(self, wine_path=None, lslib_path=None, wine_prefix=None, settings_manager=None):
        # Import settings manager if not provided
        if settings_manager is None:
            try:
                from ..core.settings import SettingsManager
                self.settings_manager = SettingsManager()
            except ImportError:
                self.settings_manager = None
        else:
            self.settings_manager = settings_manager
        
        # Get divine path from settings if not provided
        if not lslib_path and self.settings_manager:
            lslib_path = self.settings_manager.get("divine_path")
        
        self.wine_env = WineEnvironmentManager(wine_path, wine_prefix, self.settings_manager)
        self.lslib_path = lslib_path
        self.current_monitor = None
        
        # Validate setup
        self._validate_setup()
    
    def _validate_setup(self):
        """Validate entire tool setup"""
        # Validate Wine
        wine_valid, wine_msg = self.wine_env.validate_wine_installation()
        if not wine_valid:
            raise RuntimeError(f"Wine validation failed: {wine_msg}")
        
        # Validate Wine prefix (create if needed in app bundle)
        prefix_valid, prefix_msg = self.wine_env.validate_wine_prefix()
        if not prefix_valid:
            print(f"Warning: {prefix_msg}")
            # Try to initialize prefix
            self.wine_env.initialize_wine_prefix()
        
        # Validate lslib path
        if self.lslib_path and not os.path.exists(self.lslib_path.replace("Z:", "")):
            print(f"Warning: Divine.exe not found: {self.lslib_path}")
        
        print(f"Setup validation successful")
        print(f"Wine: {self.wine_env.wine_path}")
        if self.lslib_path:
            print(f"Divine.exe: {self.lslib_path}")
    
    def run_divine_command(self, action, source=None, destination=None, progress_callback=None, **kwargs):
        """Run Divine.exe command with monitoring"""
        
        # Build command
        cmd = [self.wine_env.wine_path, self.lslib_path, "--action", action, "--game", "bg3"]
        
        if source:
            cmd.extend(["--source", source])
        if destination:
            cmd.extend(["--destination", destination])
        
        # Add additional arguments
        for key, value in kwargs.items():
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])
        
        # Setup environment
        env = os.environ.copy()
        env["WINEPREFIX"] = self.wine_env.wine_prefix
        
        # Use process monitor for real-time feedback
        self.current_monitor = WineProcessMonitor()
        
        if progress_callback:
            progress_callback(5, f"Starting {action}...")
        
        success, output = self.current_monitor.run_process(cmd, env, progress_callback)
        
        if progress_callback and success:
            progress_callback(100, "Operation complete!")
        
        return success, output
    
    def cancel_current_operation(self):
        """Cancel the currently running operation"""
        if self.current_monitor:
            self.current_monitor.cancel()
    
    def extract_pak_with_monitoring(self, pak_file, destination_dir, progress_callback=None):
        """Extract PAK with detailed progress monitoring"""
        
        wine_pak_path = self.mac_to_wine_path(pak_file)
        wine_dest_path = self.mac_to_wine_path(destination_dir)
        
        # Create destination directory
        os.makedirs(destination_dir, exist_ok=True)
        
        if progress_callback:
            progress_callback(10, "Preparing extraction...")
        
        # Get PAK info first for better progress estimation
        if progress_callback:
            progress_callback(15, "Analyzing PAK file...")
            
        # Run extraction
        success, output = self.run_divine_command(
            action="extract-package",
            source=wine_pak_path,
            destination=wine_dest_path,
            progress_callback=progress_callback
        )
        
        if success:
            # Verify extraction
            if progress_callback:
                progress_callback(95, "Verifying extraction...")
            
            extracted_files = []
            for root, dirs, files in os.walk(destination_dir):
                extracted_files.extend(files)
            
            return True, f"Successfully extracted {len(extracted_files)} files"
        else:
            return False, output
    
    def create_pak_with_monitoring(self, source_dir, pak_file, progress_callback=None):
        """Create PAK with detailed progress monitoring"""
        
        wine_source_path = self.mac_to_wine_path(source_dir)
        wine_pak_path = self.mac_to_wine_path(pak_file)
        
        if not os.path.exists(source_dir):
            return False, f"Source directory does not exist: {source_dir}"
        
        # Ensure output directory exists
        pak_dir = os.path.dirname(pak_file)
        if pak_dir:
            os.makedirs(pak_dir, exist_ok=True)
        
        if progress_callback:
            progress_callback(10, "Analyzing source files...")
        
        # Count files for better progress estimation
        total_files = sum(len(files) for _, _, files in os.walk(source_dir))
        
        if progress_callback:
            progress_callback(20, f"Preparing to pack {total_files} files...")
        
        success, output = self.run_divine_command(
            action="create-package",
            source=wine_source_path,
            destination=wine_pak_path,
            progress_callback=progress_callback
        )
        
        if success:
            if os.path.exists(pak_file):
                file_size = os.path.getsize(pak_file)
                return True, f"Successfully created PAK: {file_size:,} bytes"
            else:
                return False, "PAK creation reported success but file not found"
        else:
            return False, output
    
    def mac_to_wine_path(self, mac_path):
        """Convert Mac path to Wine path format"""
        abs_path = os.path.abspath(mac_path)
        wine_path = f"Z:{abs_path.replace('/', chr(92))}"  # Use chr(92) for backslash
        return wine_path
    
    def get_system_info(self):
        """Get comprehensive system information for debugging"""
        info = {
            "wine_info": self.wine_env.get_wine_info(),
            "wine_path": self.wine_env.wine_path,
            "wine_prefix": self.wine_env.wine_prefix,
            "lslib_path": self.lslib_path,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
            "is_bundled": getattr(sys, 'frozen', False)
        }
        return info

    def extract_pak(self, pak_file, destination_dir):
        """Extract PAK file using Divine.exe (simple version for backward compatibility)"""
        wine_pak_path = self.mac_to_wine_path(pak_file)
        wine_dest_path = self.mac_to_wine_path(destination_dir)
        
        # Create destination directory
        os.makedirs(destination_dir, exist_ok=True)
        
        success, output = self.run_divine_command(
            action="extract-package",
            source=wine_pak_path,
            destination=wine_dest_path
        )
        
        return success
    
    def create_pak(self, source_dir, pak_file):
        """Create PAK file from directory (simple version for backward compatibility)"""
        wine_source_path = self.mac_to_wine_path(source_dir)
        wine_pak_path = self.mac_to_wine_path(pak_file)
        
        # Ensure output directory exists
        pak_dir = os.path.dirname(pak_file)
        if pak_dir:
            os.makedirs(pak_dir, exist_ok=True)
        
        success, output = self.run_divine_command(
            action="create-package",
            source=wine_source_path,
            destination=wine_pak_path
        )
        
        return success

    def list_pak_contents_threaded(self, pak_file, progress_callback, completion_callback):
        """List PAK contents in background thread"""
        def list_worker():
            try:
                if progress_callback:
                    progress_callback(20, "Reading PAK structure...")
                
                # Use this wrapper's list method
                files = self.list_pak_contents(pak_file)
                
                if progress_callback:
                    progress_callback(80, f"Found {len(files)} files...")
                
                # Format file information
                formatted_files = []
                for file_info in files:
                    if isinstance(file_info, dict):
                        formatted_files.append(file_info)
                    else:
                        # Parse the divine.exe output line properly
                        file_line = str(file_info).strip()
                        
                        # Divine.exe output format is typically: "filepath filesize flags"
                        # Split and take only the first part (the actual file path)
                        parts = file_line.split()
                        if parts:
                            # Extract just the file path (first part before any numeric data)
                            file_path = parts[0]
                            
                            # Handle paths with spaces - reconstruct the path properly
                            path_parts = []
                            for part in parts:
                                if part.isdigit():  # Stop when we hit numeric metadata
                                    break
                                path_parts.append(part)
                            
                            if path_parts:
                                file_path = ' '.join(path_parts)
                                formatted_files.append({
                                    'name': file_path,  # Clean file path only
                                    'type': os.path.splitext(file_path)[1].lower() if '.' in file_path else 'folder'
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
    
    def list_pak_contents(self, pak_file):
        """List contents of PAK file"""
        wine_pak_path = self.mac_to_wine_path(pak_file)
        
        success, output = self.run_divine_command(
            action="list-package",
            source=wine_pak_path
        )
        
        if success:
            print("PAK Contents:")
            # Parse Divine.exe output to extract file list
            files = []
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('Opening') and not line.startswith('Package') and not line.startswith('Listing'):
                    # Parse divine.exe output: "filepath filesize flags"
                    parts = line.split()
                    if parts:
                        # Extract just the file path (first part before any numeric data)
                        file_path = parts[0]
                        
                        # Handle paths with spaces - reconstruct the path properly
                        path_parts = []
                        for part in parts:
                            if part.isdigit():  # Stop when we hit numeric metadata
                                break
                            path_parts.append(part)
                        
                        if path_parts:
                            file_path = ' '.join(path_parts)
                            files.append({
                                'name': file_path,  # Clean file path only
                                'type': os.path.splitext(file_path)[1].lower() if '.' in file_path else 'folder'
                            })
            return files
        else:
            return []

    def validate_mod_structure(self, mod_dir):
        """Validate BG3 mod folder structure (simple version - pak_operations has the advanced one)"""
        validation = {
            'valid': True,
            'structure': [],
            'warnings': []
        }
    
        if not os.path.exists(mod_dir):
            validation['valid'] = False
            validation['warnings'].append(f"Directory does not exist: {mod_dir}")
            return validation
    
        # Check for Mods folder (required)
        mods_path = os.path.join(mod_dir, "Mods")
        if not os.path.exists(mods_path):
            validation['valid'] = False
            validation['warnings'].append("Missing required Mods/")
            return validation
        
        validation['structure'].append("Found Mods/")
        
        # Look for mod subfolders
        meta_found = False
        try:
            mod_subfolders = [d for d in os.listdir(mods_path) if os.path.isdir(os.path.join(mods_path, d))]
            game_content_folders = {"GustavDev", "Gustav", "Shared", "Engine", "Game", "Core"}
            
            if mod_subfolders:
                for subfolder in mod_subfolders:
                    if subfolder in game_content_folders:
                        validation['structure'].append(f"Game content folder: Mods/{subfolder}/")
                        continue
                    
                    meta_path = os.path.join(mods_path, subfolder, "meta.lsx")
                    if os.path.exists(meta_path):
                        validation['structure'].append(f"meta.lsx found in Mods/{subfolder}/")
                        meta_found = True
                    else:
                        validation['warnings'].append(f"meta.lsx missing in Mods/{subfolder}/")
            else:
                validation['warnings'].append("No mod subfolders found in Mods/")
        except Exception as e:
            validation['warnings'].append(f"Error reading Mods folder: {e}")
        
        if not meta_found:
            validation['warnings'].append("No meta.lsx found - this mod may not work properly")
        
        # Check for optional folders
        optional_folders = ['Public', 'Localization']
        for folder in optional_folders:
            folder_path = os.path.join(mod_dir, folder)
            if os.path.exists(folder_path):
                validation['structure'].append(f"Found {folder}/")
            else:
                validation['warnings'].append(f"Optional {folder}/ not found")
        
        return validation
    
    def convert_lsx_to_lsf(self, source, lsf_file, is_content=False):
        """Convert LSX file or content to LSF format using divine.exe"""
        if is_content:
            # Create temporary file from content
            temp_fd, temp_lsx_file = tempfile.mkstemp(suffix=".lsx")
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    f.write(source)
                source_file = temp_lsx_file
            except Exception as e:
                os.close(temp_fd)
                return False
        else:
            source_file = source
        
        try:
            wine_lsx_path = self.mac_to_wine_path(source_file)
            wine_lsf_path = self.mac_to_wine_path(lsf_file)
            
            success, output = self.run_divine_command(
                action="convert-resource",
                source=wine_lsx_path,
                destination=wine_lsf_path,
                input_format="lsx",
                output_format="lsf"
            )
            
            if success and os.path.exists(lsf_file):
                print(f"Successfully converted to {lsf_file}")
                return True
            else:
                print(f"Failed to convert: {output}")
                return False
        finally:
            # Clean up temporary file if created
            if is_content and 'temp_lsx_file' in locals():
                try:
                    os.remove(temp_lsx_file)
                except:
                    pass
    
    def convert_lsf_to_lsx(self, source, lsx_file, is_content=False):
        """Convert LSF file or content to LSX format using divine.exe"""
        if is_content:
            # Create temporary file from content
            temp_fd, temp_lsf_file = tempfile.mkstemp(suffix=".lsf")
            try:
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(source if isinstance(source, bytes) else source.encode('utf-8'))
                source_file = temp_lsf_file
            except Exception as e:
                os.close(temp_fd)
                return False
        else:
            source_file = source
        
        try:
            wine_lsf_path = self.mac_to_wine_path(source_file)
            wine_lsx_path = self.mac_to_wine_path(lsx_file)
            
            success, output = self.run_divine_command(
                action="convert-resource",
                source=wine_lsf_path,
                destination=wine_lsx_path,
                input_format="lsf",
                output_format="lsx"
            )
            
            if success and os.path.exists(lsx_file):
                print(f"Successfully converted to {lsx_file}")
                return True
            else:
                print(f"Failed to convert: {output}")
                return False
        finally:
            # Clean up temporary file if created
            if is_content and 'temp_lsf_file' in locals():
                try:
                    os.remove(temp_lsf_file)
                except:
                    pass

    def analyze_loca_file_binary(self, loca_path):
        """Analyze .loca file structure without conversion"""
        try:
            with open(loca_path, 'rb') as f:
                header = f.read(64)
                file_size = os.path.getsize(loca_path)
            
            analysis = {
                'file_size': file_size,
                'header_hex': header[:16].hex(),
                'header_ascii': ''.join(chr(b) if 32 <= b <= 126 else '.' for b in header[:32]),
                'likely_format': 'unknown'
            }
            
            # Check for common .loca signatures
            if header.startswith(b'LSOF') or header.startswith(b'LSFW'):
                analysis['likely_format'] = 'Larian Binary'
            elif b'xml' in header.lower() or b'<' in header:
                analysis['likely_format'] = 'XML-based'
            elif b'content' in header.lower():
                analysis['likely_format'] = 'Text-based'
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}

    def convert_loca_to_xml(self, loca_path, xml_path):
        """Convert .loca file to XML using divine.exe"""
        try:
            os.makedirs(os.path.dirname(xml_path), exist_ok=True)
            
            success, output = self.run_divine_command(
                action="convert-resource",
                source=self.mac_to_wine_path(loca_path),
                destination=self.mac_to_wine_path(xml_path),
                output_format="xml"
            )
            
            if success and os.path.exists(xml_path):
                return True
            else:
                print(f"Loca conversion failed: {output}")
                return False
                
        except Exception as e:
            print(f"Loca conversion error: {e}")
            return False

    def extract_loca_from_pak(self, pak_path, loca_pattern="*.loca", output_dir=None):
        """Extract .loca files from PAK"""
        if not output_dir:
            output_dir = os.path.splitext(pak_path)[0] + "_loca_extracted"
        
        # First extract the entire PAK to a temp location
        temp_dir = pak_path + "_temp_extract"
        success = self.extract_pak(pak_path, temp_dir)
        
        if success:
            # Find all .loca files
            loca_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith('.loca'):
                        loca_files.append(os.path.join(root, file))
            
            # Copy .loca files to output directory
            os.makedirs(output_dir, exist_ok=True)
            for loca_file in loca_files:
                rel_path = os.path.relpath(loca_file, temp_dir)
                dest_path = os.path.join(output_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(loca_file, dest_path)
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return loca_files
        
        return []


# Backward compatibility functions and global instance
wine_wrapper = None

def get_wine_wrapper(settings_manager=None):
    """Get or create the global wine wrapper instance"""
    global wine_wrapper
    if wine_wrapper is None:
        try:
            wine_wrapper = WineWrapper(settings_manager=settings_manager)
        except Exception as e:
            print(f"Warning: Failed to initialize Wine wrapper: {e}")
            wine_wrapper = None
    return wine_wrapper

def is_wine_available(settings_manager=None):
    """Check if Wine is available"""
    wrapper = get_wine_wrapper(settings_manager)
    return wrapper is not None and wrapper.wine_env.wine_path is not None

def run_wine_command(command, timeout=None, settings_manager=None, **kwargs):
    """Run a command through Wine"""
    wrapper = get_wine_wrapper(settings_manager)
    if not wrapper:
        raise RuntimeError("Wine wrapper not available")
    
    # Use the wine_env directly for simple commands
    wine_cmd = [wrapper.wine_env.wine_path] + command
    env = os.environ.copy()
    env["WINEPREFIX"] = wrapper.wine_env.wine_prefix
    
    return subprocess.run(wine_cmd, env=env, timeout=timeout, **kwargs)

def run_lslib_command(lslib_path, args, timeout=300, settings_manager=None):
    """Run LSLib through Wine"""
    wrapper = get_wine_wrapper(settings_manager)
    if not wrapper:
        raise RuntimeError("Wine wrapper not available")
    
    # Simple wrapper for backward compatibility
    wine_cmd = [wrapper.wine_env.wine_path, lslib_path] + args
    env = os.environ.copy()
    env["WINEPREFIX"] = wrapper.wine_env.wine_prefix
    
    return subprocess.run(wine_cmd, env=env, timeout=timeout, capture_output=True, text=True)