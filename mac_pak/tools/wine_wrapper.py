#!/usr/bin/env python3
"""
Wine Integration for BG3 Mac Tool - Main Wrapper
Coordinates all wine-based operations through specialized modules
"""

import os
import sys
from pathlib import Path

from .wine_environment import WineEnvironmentManager, WineProcessMonitor
from .wine_pak_tools import WinePakTools
from .wine_ls_tools import WineLSTools
from .wine_loca_processor import WineLocaProcessor
from .wine_mod_validator import WineModValidator

from ..data.parsers.larian_parser import *

class WineWrapper:
    """Main BG3 Mac tool with Wine integration - coordinates specialized modules"""
    
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
        
        # Initialize core wine environment
        self.wine_env = WineEnvironmentManager(wine_path, wine_prefix, self.settings_manager)
        self.lslib_path = lslib_path
        self.current_monitor = None
        
        # Initialize specialized modules
        self._initialize_modules()
        
        # Validate setup
        self._validate_setup()
    
    def _initialize_modules(self):
        """Initialize all specialized operation modules"""
        base_config = {
            'wine_env': self.wine_env,
            'lslib_path': self.lslib_path,
            'settings_manager': self.settings_manager
        }
        
        self.pak_ops = WinePakTools(**base_config)
        self.binary_converter = WineLSTools(**base_config)
        self.loca_processor = WineLocaProcessor(**base_config)
        self.mod_validator = WineModValidator(**base_config)
    
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
        """Run Divine.exe command with monitoring - fully async with signals"""
        
        print(f"DEBUG: wine_wrapper.run_divine_command called with action={action}")
        
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
        
        # Create a new monitor for this operation
        self.current_monitor = WineProcessMonitor()
        
        if progress_callback:
            self.current_monitor.progress_updated.connect(
                lambda p, m: progress_callback(p, m)
            )
        
        # Start async process - returns immediately
        self.current_monitor.run_process_async(cmd, env, progress_callback)
        
        # Return the monitor so caller can connect to its signals
        return self.current_monitor
    
    def cancel_current_operation(self):
        """Cancel the currently running operation"""
        if self.current_monitor:
            self.current_monitor.cancel()
        # Also cancel operations in specialized modules
        self.pak_ops.cancel_current_operation()
        self.binary_converter.cancel_current_operation()
        self.loca_processor.cancel_current_operation()
    
    def mac_to_wine_path(self, mac_path):
        """Convert Mac path to Wine path format - shared utility"""
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
    
    # Delegate PAK operations to specialized module
    def extract_pak_with_monitoring(self, pak_file, destination_dir, progress_callback=None):
        """Extract PAK with detailed progress monitoring"""
        return self.pak_ops.extract_pak_with_monitoring(pak_file, destination_dir, progress_callback)
    
    def create_pak_with_monitoring(self, source_dir, pak_file, progress_callback=None):
        """Create PAK with detailed progress monitoring"""
        return self.pak_ops.create_pak_with_monitoring(source_dir, pak_file, progress_callback)
    
    def extract_pak(self, pak_file, destination_dir):
        """Extract PAK file using Divine.exe (simple version)"""
        return self.pak_ops.extract_pak(pak_file, destination_dir)
    
    def create_pak(self, source_dir, pak_file):
        """Create PAK file from directory (simple version)"""
        return self.pak_ops.create_pak(source_dir, pak_file)
    
    def list_pak_contents_threaded(self, pak_file, progress_callback, completion_callback):
        """List PAK contents in background thread"""
        return self.pak_ops.list_pak_contents_threaded(pak_file, progress_callback, completion_callback)
    
    def list_pak_contents(self, pak_file):
        """List contents of PAK file"""
        return self.pak_ops.list_pak_contents(pak_file)
    
    # Delegate mod validation to specialized module
    def validate_mod_structure(self, mod_dir):
        """Validate BG3 mod folder structure"""
        return self.mod_validator.validate_mod_structure(mod_dir)
    
    # Delegate binary file operations to specialized module
    def convert_lsx_to_lsf(self, source, lsf_file, is_content=False):
        """Convert LSX file or content to LSF format"""
        return self.binary_converter.convert_lsx_to_lsf(source, lsf_file, is_content)
    
    def convert_lsf_to_lsx(self, source, lsx_file, is_content=False):
        """Convert LSF file or content to LSX format"""
        return self.binary_converter.convert_lsf_to_lsx(source, lsx_file, is_content)
    
    # Delegate loca operations to specialized module
    def analyze_loca_file_binary(self, loca_path):
        """Analyze .loca file structure without conversion"""
        return self.loca_processor.analyze_loca_file_binary(loca_path)
    
    def convert_loca_to_xml(self, loca_path, xml_path):
        """Convert .loca file to XML using divine.exe"""
        return self.loca_processor.convert_loca_to_xml(loca_path, xml_path)
    
    def extract_loca_from_pak(self, pak_path, loca_pattern="*.loca", output_dir=None):
        """Extract .loca files from PAK"""
        return self.loca_processor.extract_loca_from_pak(pak_path, loca_pattern, output_dir)


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