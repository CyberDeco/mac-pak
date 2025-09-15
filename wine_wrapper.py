#!/usr/bin/env python3
"""
Wine Integration for BG3 Mac Tool
Error handling, process monitoring, and Wine environment management
"""

import subprocess
import os

import threading
import queue
import time

from pathlib import Path

from larian_parser import *

class WineProcessMonitor:
    """Monitor Wine processes with real-time output and cancellation support"""
    
    def __init__(self):
        self.process = None
        self.output_queue = queue.Queue()
        self.error_queue = queue.Queue()
        self.cancelled = False
        self.progress_callback = None
    
    def run_process(self, cmd, env=None, progress_callback=None):
        """Run a process with real-time monitoring"""
        self.progress_callback = progress_callback
        self.cancelled = False
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1,
                universal_newlines=True
            )
            
            # Start output monitoring threads
            stdout_thread = threading.Thread(
                target=self._monitor_output,
                args=(self.process.stdout, self.output_queue, "stdout")
            )
            stderr_thread = threading.Thread(
                target=self._monitor_output,
                args=(self.process.stderr, self.error_queue, "stderr")
            )
            
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            # Monitor progress and handle cancellation
            return self._monitor_process()
            
        except Exception as e:
            return False, f"Failed to start process: {e}"
    
    def _monitor_output(self, pipe, output_queue, stream_type):
        """Monitor stdout/stderr in separate thread"""
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    output_queue.put((stream_type, line.strip()))
        except:
            pass
        finally:
            pipe.close()
    
    def _monitor_process(self):
        """Monitor the main process and collect output"""
        stdout_lines = []
        stderr_lines = []
        
        while self.process.poll() is None:
            if self.cancelled:
                self._terminate_process()
                return False, "Operation cancelled by user"
            
            # Collect any new output
            while not self.output_queue.empty():
                try:
                    stream_type, line = self.output_queue.get_nowait()
                    if stream_type == "stdout":
                        stdout_lines.append(line)
                        # Parse progress from Divine.exe output if possible
                        self._parse_progress(line)
                    else:
                        stderr_lines.append(line)
                except queue.Empty:
                    break
            
            time.sleep(0.1)  # Don't overwhelm the CPU
        
        # Collect any remaining output
        while not self.output_queue.empty():
            try:
                stream_type, line = self.output_queue.get_nowait()
                if stream_type == "stdout":
                    stdout_lines.append(line)
                else:
                    stderr_lines.append(line)
            except queue.Empty:
                break
        
        # Check final result
        return_code = self.process.returncode
        stdout_text = '\n'.join(stdout_lines)
        stderr_text = '\n'.join(stderr_lines)
        
        if return_code == 0:
            return True, stdout_text
        else:
            error_msg = stderr_text if stderr_text else "Unknown error"
            return False, error_msg
    
    def _parse_progress(self, line):
        """Parse progress information from Divine.exe output"""
        if self.progress_callback:
            # Divine.exe doesn't provide detailed progress, but we can infer some
            line_lower = line.lower()
            if "extracting" in line_lower:
                self.progress_callback(30, "Extracting files...")
            elif "creating" in line_lower:
                self.progress_callback(40, "Creating archive...")
            elif "processing" in line_lower:
                self.progress_callback(50, "Processing files...")
            elif "completed" in line_lower or "success" in line_lower:
                self.progress_callback(90, "Nearly complete...")
    
    def _terminate_process(self):
        """Safely terminate the Wine process"""
        if self.process:
            try:
                # Try graceful termination first
                self.process.terminate()
                
                # Wait a bit for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    self.process.kill()
                    self.process.wait()
            except:
                pass
    
    def cancel(self):
        """Cancel the running operation"""
        self.cancelled = True

class WineEnvironmentManager:
    """Manage Wine environment and validate setup"""
    
    def __init__(self, wine_path=None, wine_prefix=None):
        self.wine_path = wine_path
        self.wine_prefix = wine_prefix or os.path.expanduser("~/.wine")
        self._wine_info = None
    
    def validate_wine_installation(self):
        """Validate that Wine is properly installed and functional"""
        if not self.wine_path:
            self.wine_path = self._find_wine_executable()
        
        if not self.wine_path:
            return False, "Wine executable not found"
        
        # Test Wine functionality
        try:
            result = subprocess.run(
                [self.wine_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, f"Wine test failed: {result.stderr}"
            
            wine_version = result.stdout.strip()
            self._wine_info = {"version": wine_version}
            
            return True, f"Wine validation successful: {wine_version}"
            
        except subprocess.TimeoutExpired:
            return False, "Wine test timed out"
        except Exception as e:
            return False, f"Wine validation error: {e}"
    
    def _find_wine_executable(self):
        """Find Wine executable on the system"""
        possible_paths = [
            "/usr/local/bin/wine",
            "/opt/homebrew/bin/wine",
            "/opt/local/bin/wine",  # MacPorts
            "/Applications/Wine.app/Contents/Resources/wine/bin/wine",
            "/Applications/Wineskin.app/Contents/Resources/wine/bin/wine"
        ]
        
        # Check PATH first
        try:
            result = subprocess.run(["which", "wine"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # Check specific paths
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        return None
    
    def validate_wine_prefix(self):
        """Validate and optionally create Wine prefix"""
        if not os.path.exists(self.wine_prefix):
            return False, f"Wine prefix not found: {self.wine_prefix}"
        
        # Check for essential Wine directories
        essential_dirs = ["dosdevices", "drive_c"]
        for dir_name in essential_dirs:
            dir_path = os.path.join(self.wine_prefix, dir_name)
            if not os.path.exists(dir_path):
                return False, f"Wine prefix missing {dir_name} directory"
        
        return True, "Wine prefix validation successful"
    
    def get_wine_info(self):
        """Get information about the Wine installation"""
        if not self._wine_info:
            self.validate_wine_installation()
        return self._wine_info

class WineWrapper:
    """ BG3 Mac tool with Wine integration"""
    
    def __init__(self, wine_path=None, lslib_path=None, wine_prefix=None):
        self.wine_env = WineEnvironmentManager(wine_path, wine_prefix)
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
        
        # Validate Wine prefix
        prefix_valid, prefix_msg = self.wine_env.validate_wine_prefix()
        if not prefix_valid:
            print(f"Warning: {prefix_msg}")
        
        # Validate lslib path
        if not self.lslib_path:
            raise ValueError("Divine.exe path must be specified")
        
        if not os.path.exists(self.lslib_path.replace("Z:", "")):
            raise FileNotFoundError(f"Divine.exe not found: {self.lslib_path}")
        
        print(f"Setup validation successful")
        print(f"Wine: {self.wine_env.wine_path}")
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
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "platform": os.sys.platform
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
                
                # Use WineWrapper's list method
                files = self.wine_wrapper.list_pak_contents(pak_file)
                
                if progress_callback:
                    progress_callback(80, f"Found {len(files)} files...")
                
                # Format file information - FIX THE PARSING HERE
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
                                files.append({
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
    
    def convert_lsx_to_lsf(self, lsx_file, lsf_file):
        """Convert LSX file to LSF format using divine.exe"""
        wine_lsx_path = self.mac_to_wine_path(lsx_file)
        wine_lsf_path = self.mac_to_wine_path(lsf_file)
        
        success, output = self.run_divine_command(
            action="convert-resource",
            source=wine_lsx_path,
            destination=wine_lsf_path,
            input_format="lsx",
            output_format="lsf"
        )
        
        if success and os.path.exists(lsf_file):
            print(f"Successfully converted {lsx_file} to {lsf_file}")
            return True
        else:
            print(f"Failed to convert {lsx_file}: {output}")
            return False
    
    def convert_lsf_to_lsx(self, lsf_file, lsx_file):
        """Convert LSF file to LSX format using divine.exe"""
        wine_lsf_path = self.mac_to_wine_path(lsf_file)
        wine_lsx_path = self.mac_to_wine_path(lsx_file)
        
        success, output = self.run_divine_command(
            action="convert-resource",
            source=wine_lsf_path,
            destination=wine_lsx_path,
            input_format="lsf",
            output_format="lsx"
        )
        
        if success and os.path.exists(lsx_file):
            print(f"Successfully converted {lsf_file} to {lsx_file}")
            return True
        else:
            print(f"Failed to convert {lsf_file}: {output}")
            return False

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