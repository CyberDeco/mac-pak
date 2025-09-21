#!/usr/bin/env python3
"""
Wine Environment Management - App Bundle Compatible
Handles Wine detection, validation, and path management
"""

import subprocess
import os
import sys
import threading
import queue
import time
from pathlib import Path

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
    """Manage Wine environment and validate setup - App Bundle Compatible"""
    
    def __init__(self, wine_path=None, wine_prefix=None, settings_manager=None):
        self.settings_manager = settings_manager
        self.wine_path = wine_path
        self.wine_prefix = wine_prefix
        self._wine_info = None
        self._setup_paths()
    
    def _setup_paths(self):
        """Setup Wine paths for both development and app bundle, respecting user settings"""
        # First check user settings if available
        if self.settings_manager:
            user_wine_path = self.settings_manager.get("wine_path")
            if user_wine_path and os.path.isfile(user_wine_path) and os.access(user_wine_path, os.X_OK):
                self.wine_path = user_wine_path
                self.wine_prefix = self.wine_prefix or str(Path.home() / ".wine")
                return
        
        # App bundle vs development detection
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            bundle_dir = Path(sys._MEIPASS)
            resources_dir = bundle_dir
            
            # Check if we're in a .app bundle
            if 'MacPak.app' in str(bundle_dir):
                # Navigate to Contents/Resources
                app_contents = bundle_dir.parent.parent
                resources_dir = app_contents / 'Resources'
            
            wine_dir = resources_dir / 'wine'
            default_prefix = resources_dir / 'wineprefix'
            
        else:
            # Running in development
            project_root = Path(__file__).parent.parent.parent
            wine_dir = project_root / 'temp' / 'wine'
            default_prefix = project_root / 'temp' / 'wineprefix'
        
        # Set wine prefix with user preference or default
        if self.settings_manager:
            # Use Documents folder for persistent storage in user settings
            user_storage = self.settings_manager.get("extracted_files_location")
            if user_storage:
                self.wine_prefix = self.wine_prefix or str(Path(user_storage) / "wine_prefix")
            else:
                self.wine_prefix = self.wine_prefix or str(default_prefix)
        else:
            self.wine_prefix = self.wine_prefix or str(default_prefix)
        
        # Find Wine executable if not already set
        if not self.wine_path:
            self.wine_path = self._find_wine_executable(wine_dir)
    
    def validate_wine_installation(self):
        """Validate that Wine is properly installed and functional"""
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
    
    def _find_wine_executable(self, wine_dir=None):
        """Find Wine executable on the system"""
        # First try bundled Wine locations
        if wine_dir and wine_dir.exists():
            wine_candidates = [
                wine_dir / 'wine-9.0-osx64' / 'bin' / 'wine64',
                wine_dir / 'wine-9.0-osx64' / 'bin' / 'wine',
                wine_dir / 'bin' / 'wine64',
                wine_dir / 'bin' / 'wine',
                wine_dir / 'wine64',
                wine_dir / 'wine',
            ]
            
            for candidate in wine_candidates:
                if candidate.exists() and candidate.is_file():
                    # Make executable
                    candidate.chmod(0o755)
                    return str(candidate)
        
        # Check PATH
        try:
            for wine_name in ['wine64', 'wine']:
                result = subprocess.run(["which", wine_name], capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
        except:
            pass
        
        # Check specific system paths
        possible_paths = [
            "/usr/local/bin/wine64",
            "/usr/local/bin/wine",
            "/opt/homebrew/bin/wine64",
            "/opt/homebrew/bin/wine",
            "/opt/local/bin/wine64",  # MacPorts
            "/opt/local/bin/wine",
            "/Applications/Wine.app/Contents/Resources/wine/bin/wine64",
            "/Applications/Wine.app/Contents/Resources/wine/bin/wine",
            "/Applications/Wineskin.app/Contents/Resources/wine/bin/wine64",
            "/Applications/Wineskin.app/Contents/Resources/wine/bin/wine"
        ]
        
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
    
    def initialize_wine_prefix(self):
        """Initialize Wine prefix if it doesn't exist"""
        try:
            os.makedirs(self.wine_prefix, exist_ok=True)
            result = subprocess.run([
                self.wine_path, 'wineboot', '--init'
            ], capture_output=True, text=True, timeout=60,
            env={**os.environ, 'WINEPREFIX': self.wine_prefix})
            
            if result.returncode == 0:
                print("Wine prefix initialized successfully")
                return True
            else:
                print(f"Wine prefix initialization failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error initializing Wine prefix: {e}")
            return False
    
    def get_wine_info(self):
        """Get information about the Wine installation"""
        if not self._wine_info:
            self.validate_wine_installation()
        return self._wine_info