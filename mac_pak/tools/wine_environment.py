#!/usr/bin/env python3
"""
Wine Environment Management - App Bundle Compatible
Handles Wine detection, validation, and path management
"""

import subprocess
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, QObject, pyqtSignal, QTimer

import logging

# Set up logger at the top of your file
logger = logging.getLogger(__name__)

class WineProcessMonitor(QObject):
    """Monitor Wine processes using PyQt6's QProcess - truly asynchronous"""
    
    # Signals for process monitoring
    progress_updated = pyqtSignal(int, str)
    process_finished = pyqtSignal(bool, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.cancelled = False
        self.progress_callback = None
        self.stdout_data = []
        self.stderr_data = []
        self.timeout_timer = None

    def run_process(self, cmd, env=None, progress_callback=None):
        """Run a process synchronously - blocks until complete"""
        self.progress_callback = progress_callback
        self.cancelled = False
        self.stdout_data = []
        self.stderr_data = []
        
        try:
            self.process = QProcess()
            
            # Set up environment
            if env:
                process_env = QProcessEnvironment.systemEnvironment()
                for key, value in env.items():
                    process_env.insert(key, value)
                self.process.setProcessEnvironment(process_env)
            
            # Connect signals
            self.process.readyReadStandardOutput.connect(self._on_stdout_ready)
            self.process.readyReadStandardError.connect(self._on_stderr_ready)
            
            if progress_callback:
                progress_callback(5, "Starting process...")
            
            # Start the process
            program = cmd[0]
            arguments = cmd[1:] if len(cmd) > 1 else []
            self.process.start(program, arguments)
            
            # Wait for finish - blocks but is efficient
            if not self.process.waitForFinished(120000):  # 2 minutes
                self.process.kill()
                return False, "Process timed out"
            
            # Get results
            stdout_text = '\n'.join(self.stdout_data)
            stderr_text = '\n'.join(self.stderr_data)
            
            if self.progress_callback:
                self.progress_callback(100, "Complete")
            
            if self.process.exitCode() == 0:
                return True, stdout_text
            else:
                error_msg = stderr_text if stderr_text else f"Process failed with exit code {self.process.exitCode()}"
                return False, error_msg
                
        except Exception as e:
            return False, f"Failed to start process: {e}"

    def run_process_async(self, cmd, env=None, progress_callback=None):
        """Run a process asynchronously - returns immediately"""
        self.progress_callback = progress_callback
        self.cancelled = False
        self.stdout_data = []
        self.stderr_data = []
        
        try:
            self.process = QProcess()
            
            # Set up environment
            if env:
                process_env = QProcessEnvironment.systemEnvironment()
                for key, value in env.items():
                    process_env.insert(key, value)
                self.process.setProcessEnvironment(process_env)
            
            # Connect signals for ASYNC operation
            self.process.started.connect(self._on_process_started)
            self.process.errorOccurred.connect(self._on_process_error)
            self.process.finished.connect(self._on_process_finished)
            self.process.readyReadStandardOutput.connect(self._on_stdout_ready)
            self.process.readyReadStandardError.connect(self._on_stderr_ready)
            
            # Set timeout timer
            self.timeout_timer = QTimer()
            self.timeout_timer.timeout.connect(self._on_timeout)
            self.timeout_timer.start(120000)  # 2 minutes
            
            if progress_callback:
                progress_callback(5, "Starting process...")
            
            # Start the process - RETURNS IMMEDIATELY
            program = cmd[0]
            arguments = cmd[1:] if len(cmd) > 1 else []
            self.process.start(program, arguments)
            
        except Exception as e:
            self.process_finished.emit(False, f"Failed to start process: {e}")
    
    def _on_process_started(self):
        """Handle process started"""
        if self.progress_callback:
            self.progress_callback(20, "Process started, waiting for completion...")
    
    def _on_process_error(self, error):
        """Handle process errors"""
        error_msgs = {
            QProcess.ProcessError.FailedToStart: "Failed to start",
            QProcess.ProcessError.Crashed: "Process crashed", 
            QProcess.ProcessError.Timedout: "Process timed out",
            QProcess.ProcessError.WriteError: "Write error",
            QProcess.ProcessError.ReadError: "Read error",
            QProcess.ProcessError.UnknownError: "Unknown error"
        }
        
        error_msg = error_msgs.get(error, "Unknown error")
        self.process_finished.emit(False, f"Process error: {error_msg}")
        self._cleanup()
    
    def _on_timeout(self):
        """Handle process timeout"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process_finished.emit(False, "Process timed out")
        self._cleanup()
    
    def _on_process_finished(self, exit_code, exit_status):
        """Handle process completion - runs in main thread via signal"""
        print(f"DEBUG: Process finished with exit_code={exit_code}, exit_status={exit_status}")
        
        self._cleanup_timer()  # Stop timeout timer
        
        stdout_text = '\n'.join(self.stdout_data)
        stderr_text = '\n'.join(self.stderr_data)
        
        if self.progress_callback:
            self.progress_callback(100, "Process completed")
        
        # Divine.exe sometimes returns non-zero exit codes even on success
        # Check for success indicators in the output instead
        success_indicators = [
            "wrote resource to",
            "extracted",
            "created package",
            "conversion complete",
            "successfully",
        ]
        
        # Check if operation succeeded based on output
        output_lower = stdout_text.lower()
        has_success_indicator = any(indicator in output_lower for indicator in success_indicators)
        
        # Consider it successful if:
        # 1. Exit code is 0 and normal exit, OR
        # 2. Has success indicator in output (Divine.exe quirk)
        if (exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit) or has_success_indicator:
            print(f"DEBUG: Emitting process_finished(True, ...)")
            self.process_finished.emit(True, stdout_text)
        else:
            error_msg = stderr_text if stderr_text else f"Process failed with exit code {exit_code}"
            print(f"DEBUG: Emitting process_finished(False, {error_msg})")
            self.process_finished.emit(False, error_msg)
        
        self._cleanup()
    
    def _cleanup(self):
        """Clean up process and timer"""
        self._cleanup_timer()
        if self.process:
            self.process.deleteLater()
            self.process = None
    
    def _cleanup_timer(self):
        """Clean up timeout timer"""
        if self.timeout_timer:
            self.timeout_timer.stop()
            self.timeout_timer.deleteLater()
            self.timeout_timer = None
    
    def _on_stdout_ready(self):
        """Handle stdout data ready"""
        if self.process:
            data = self.process.readAllStandardOutput().data().decode('utf-8')
            lines = data.strip().split('\n')
            for line in lines:
                if line.strip():
                    print(f"DEBUG STDOUT: {line.strip()}")
                    self.stdout_data.append(line.strip())
                    self._parse_progress(line.strip())
                    logger.info(f"Wine: {line.strip()}")
    
    def _on_stderr_ready(self):
        """Handle stderr data ready"""
        if self.process:
            data = self.process.readAllStandardError().data().decode('utf-8')
            lines = data.strip().split('\n')
            for line in lines:
                if line.strip():
                    # Log Wine errors instead of storing them
                    if "err:" in line.lower() or "fixme:" in line.lower():
                        logger.warning(f"Wine: {line.strip()}")
                    print(f"DEBUG STDERR: {line.strip()}")
    
    def _parse_progress(self, line):
        """Parse progress information from Divine.exe output"""
        if self.progress_callback:
            line_lower = line.lower()
            
            # Emit progress based on output patterns
            if "opening" in line_lower or "reading" in line_lower:
                self.progress_callback(10, "Opening PAK file...")
            elif "extracting" in line_lower or "unpacking" in line_lower:
                self.progress_callback(50, "Extracting files...")
            elif "creating" in line_lower or "packing" in line_lower:
                self.progress_callback(50, "Creating archive...")
            elif "processing" in line_lower:
                self.progress_callback(60, "Processing files...")
            elif "writing" in line_lower:
                self.progress_callback(70, "Writing files...")
            elif "completed" in line_lower or "success" in line_lower or "done" in line_lower:
                self.progress_callback(90, "Nearly complete...")
            else:
                # For any other output, show intermediate progress
                # This keeps the dialog responsive even without specific keywords
                current_value = getattr(self, '_last_progress', 20)
                if current_value < 80:
                    self._last_progress = min(current_value + 5, 80)
                    self.progress_callback(self._last_progress, "Processing...")
    
    def cancel(self):
        """Cancel the running operation"""
        self.cancelled = True
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate()
            
            # Set a timer to kill if it doesn't terminate
            QTimer.singleShot(3000, lambda: self._force_kill())
        
        self._cleanup()
    
    def _force_kill(self):
        """Force kill if process doesn't terminate gracefully"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()

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