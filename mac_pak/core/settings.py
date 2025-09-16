#!/usr/bin/env python3
"""
Settings Toolbar
"""

from PyQt6.QtCore import QSettings, QStandardPaths
from pathlib import Path

class SettingsManager:
    """Manage user settings with QSettings for proper Mac integration"""
    
    def __init__(self):
        # Use QSettings for proper Mac preferences handling
        self.settings = QSettings("BG3ModToolkit", "BG3MacPakTool")
        self._ensure_defaults()
    
    def _ensure_defaults(self):
        """Ensure default settings exist"""
        defaults = {
            "working_directory": str(Path.home() / "Desktop"),
            "wine_path": "/opt/homebrew/bin/wine",
            "divine_path": "",
            "window_geometry": None,
            "recent_files": [],
            "storage_mode": "persistent",  # persistent vs temp
            "max_cache_size_gb": 5,
            "auto_cleanup_days": 30,
            "extracted_files_location": str(Path.home() / "Documents" / "BG3ModToolkit"),
        }
        
        for key, value in defaults.items():
            if not self.settings.contains(key):
                self.settings.setValue(key, value)
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.value(key, default)
    
    def set(self, key, value):
        """Set a setting value"""
        self.settings.setValue(key, value)
    
    def sync(self):
        """Force sync settings to disk"""
        self.settings.sync()