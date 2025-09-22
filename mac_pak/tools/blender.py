"""Checks if Blender is installed"""
import os
import subprocess
from pathlib import Path

class BlenderIntegration:
    def __init__(self, settings_manager=None):
        self.settings_manager = settings_manager
        self.blender_path = self._find_blender()
    
    def _find_blender(self):
        """Find Blender installation on the system"""
        # Check user settings first
        if self.settings_manager:
            user_blender_path = self.settings_manager.get("blender_path")
            if user_blender_path and os.path.isfile(user_blender_path):
                return user_blender_path
        
        # Common Blender installation paths on macOS
        common_paths = [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            "/Applications/Blender.app/Contents/MacOS/blender",
            "/usr/local/bin/blender",
            "/opt/homebrew/bin/blender",
            # Check user's Applications folder
            os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender"),
        ]
        
        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        
        return None
    
    def is_available(self):
        """Check if Blender is available"""
        return self.blender_path is not None
    
    def get_version(self):
        """Get Blender version"""
        if not self.is_available():
            return None
        
        try:
            result = subprocess.run([
                self.blender_path, "--version"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse version from output
                for line in result.stdout.split('\n'):
                    if 'Blender' in line:
                        return line.strip()
            return "Unknown version"
        except Exception:
            return None
    
    def launch_blender(self, file_path=None):
        """Launch Blender with optional file"""
        if not self.is_available():
            raise RuntimeError("Blender not found")
        
        cmd = [self.blender_path]
        if file_path:
            cmd.append(file_path)
        
        subprocess.Popen(cmd)