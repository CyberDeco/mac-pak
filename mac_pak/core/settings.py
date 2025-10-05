#!/usr/bin/env python3
"""
Settings Manager - Updated for Wine Integration
"""

import sys
import os
from PyQt6.QtCore import QSettings, QStandardPaths
from pathlib import Path

class SettingsManager:
    """Manage user settings with QSettings for proper Mac integration"""
    
    def __init__(self):
        # Use QSettings for proper Mac preferences handling
        self.settings = QSettings("MacPak", "BG3MacPak")
        self._ensure_defaults()
        
    def _ensure_defaults(self):
        """Ensure default settings exist"""
        # Detect if we're in an app bundle for default wine path
        default_wine_path = self._get_default_wine_path()
        default_divine_path = self._get_default_divine_path()
        
        # Get config directory for database
        if getattr(sys, 'frozen', False):
            # In app bundle
            config_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        else:
            # Development
            config_dir = Path(__file__).parent.parent / "config"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Default storage location
        default_storage = Path.home() / "Documents" / "MacPak"
        
        defaults = {
            "working_directory": str(Path.home() / "Desktop"),
            "wine_path": default_wine_path,
            "divine_path": default_divine_path,
            "wine_prefix": os.getenv("WINE_PREFIX", str(Path.home() / ".wine")),
            "database_path": str(config_dir / "bg3_file_index.db"),
            "window_geometry": None,
            "recent_files": [],
            "storage_mode": "persistent",
            "max_cache_size_gb": 5,
            "auto_cleanup_days": 30,
            "extracted_files_location": str(default_storage),
            "blender_path": self._get_default_blender_path(),
        }
        
        for key, value in defaults.items():
            if not self.settings.contains(key):
                self.settings.setValue(key, value)
        
        # Create storage location if it doesn't exist
        storage_path = Path(self.get("extracted_files_location"))
        storage_path.mkdir(parents=True, exist_ok=True)
    
    def _get_default_wine_path(self):
        """Get default wine path based on environment"""
        if getattr(sys, 'frozen', False):
            bundle_dir = Path(sys._MEIPASS)
            
            if 'MacPak.app' in str(bundle_dir):
                app_contents = bundle_dir.parent.parent
                wine_candidates = [
                    app_contents / 'Resources' / 'wine' / 'wine-stable-*' / 'bin' / 'wine64',
                    app_contents / 'Resources' / 'wine' / 'bin' / 'wine64',
                    app_contents / 'Resources' / 'wine' / 'wine64',
                ]
                
                # Use glob pattern matching for wine-stable-* directories
                import glob
                wine_dir = app_contents / 'Resources' / 'wine'
                if wine_dir.exists():
                    for pattern in ['wine-stable-*/bin/wine64', 'bin/wine64', 'wine64']:
                        matches = list(wine_dir.glob(pattern))
                        if matches:
                            return str(matches[0])
                
                for candidate in wine_candidates:
                    if candidate.exists():
                        return str(candidate)
        
        # Development or system wine paths
        system_paths = [
            "/opt/homebrew/bin/wine64",
            "/opt/homebrew/bin/wine",
            "/usr/local/bin/wine64", 
            "/usr/local/bin/wine",
            "/opt/local/bin/wine64",  # MacPorts
            "/opt/local/bin/wine",
        ]
        
        for path in system_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        return ""  # Return empty string if nothing found
    
    def _get_default_divine_path(self):
        """Get default Divine.exe path based on environment"""
        # Check if we're in an app bundle first
        if getattr(sys, 'frozen', False):
            bundle_dir = Path(sys._MEIPASS)
            
            if 'MacPak.app' in str(bundle_dir):
                # We're in an app bundle - look for bundled Divine.exe
                app_contents = bundle_dir.parent.parent
                lslib_dir = app_contents / 'Resources' / 'lslib'
                
                # Search for Divine.exe in the lslib directory
                for root, dirs, files in os.walk(lslib_dir):
                    for file in files:
                        if file.lower() == 'divine.exe':
                            # Convert to Wine Z: path format
                            divine_path = os.path.join(root, file)
                            wine_path = f"Z:{divine_path.replace('/', chr(92))}"
                            return wine_path
        
        # Development or manual installation - empty default
        return ""

    def _get_default_blender_path(self):
        """Get default Blender path"""
        common_paths = [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            "/usr/local/bin/blender",
            "/opt/homebrew/bin/blender",
        ]
        
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        return ""
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.value(key, default)
    
    def set(self, key, value):
        """Set a setting value"""
        self.settings.setValue(key, value)
    
    def sync(self):
        """Force sync settings to disk"""
        self.settings.sync()
    
    def get_wine_settings(self):
        """Get wine-specific settings as a dict for easy access"""
        return {
            'wine_path': self.get('wine_path'),
            'divine_path': self.get('divine_path'),
            'extracted_files_location': self.get('extracted_files_location'),
            'storage_mode': self.get('storage_mode'),
        }
    
    def validate_wine_setup(self):
        """Validate current wine setup and return status"""
        wine_path = self.get('wine_path')
        divine_path = self.get('divine_path')
        
        issues = []
        
        if not wine_path or not os.path.isfile(wine_path):
            issues.append("Wine executable not found or not set")
        elif not os.access(wine_path, os.X_OK):
            issues.append("Wine executable is not executable")
        
        if divine_path:
            # Remove Z: prefix if present for checking
            local_divine_path = divine_path.replace("Z:", "")
            if not os.path.isfile(local_divine_path):
                issues.append("Divine.exe not found at specified path")
        else:
            issues.append("Divine.exe path not set")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'wine_path': wine_path,
            'divine_path': divine_path
        }