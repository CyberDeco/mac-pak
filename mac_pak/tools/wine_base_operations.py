#!/usr/bin/env python3
"""
Base Operations Module
Shared utilities and base functionality for all wine wrapper modules
"""

import os
import subprocess
from pathlib import Path

from .wine_environment import WineProcessMonitor


class BaseWineOperations:
    """Base class with shared functionality for all wine operations"""
    
    def __init__(self, wine_env, lslib_path, settings_manager=None):
        self.wine_env = wine_env
        self.lslib_path = lslib_path
        self.settings_manager = settings_manager
        self.current_monitor = None
    
    def mac_to_wine_path(self, mac_path):
        """Convert Mac path to Wine path format"""
        abs_path = os.path.abspath(mac_path)
        wine_path = f"Z:{abs_path.replace('/', chr(92))}"  # Use chr(92) for backslash
        return wine_path
    
    def wine_to_mac_path(self, wine_path):
        """Convert Wine path back to Mac path format"""
        if wine_path.startswith("Z:"):
            mac_path = wine_path[2:].replace(chr(92), '/')  # Remove Z: and convert backslashes
            return mac_path
        return wine_path
    
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
    
    def run_simple_wine_command(self, command, timeout=300, capture_output=True):
        """Run a simple wine command without divine.exe"""
        wine_cmd = [self.wine_env.wine_path] + command
        env = os.environ.copy()
        env["WINEPREFIX"] = self.wine_env.wine_prefix
        
        try:
            result = subprocess.run(
                wine_cmd, 
                env=env, 
                timeout=timeout, 
                capture_output=capture_output, 
                text=True
            )
            return result.returncode == 0, result.stdout if capture_output else ""
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def cancel_current_operation(self):
        """Cancel the currently running operation"""
        if self.current_monitor:
            self.current_monitor.cancel()
    
    def validate_file_exists(self, file_path, file_type="file"):
        """Validate that a file or directory exists"""
        if not os.path.exists(file_path):
            return False, f"{file_type.capitalize()} does not exist: {file_path}"
        
        if file_type == "file" and not os.path.isfile(file_path):
            return False, f"Path exists but is not a file: {file_path}"
        
        if file_type == "directory" and not os.path.isdir(file_path):
            return False, f"Path exists but is not a directory: {file_path}"
        
        return True, f"{file_type.capitalize()} exists: {file_path}"
    
    def ensure_directory_exists(self, directory_path):
        """Ensure a directory exists, create if it doesn't"""
        try:
            os.makedirs(directory_path, exist_ok=True)
            return True, f"Directory ready: {directory_path}"
        except Exception as e:
            return False, f"Failed to create directory {directory_path}: {e}"
    
    def get_file_info(self, file_path):
        """Get comprehensive file information"""
        try:
            stat = os.stat(file_path)
            
            info = {
                'path': file_path,
                'name': os.path.basename(file_path),
                'size': stat.st_size,
                'size_formatted': f"{stat.st_size:,} bytes",
                'modified': stat.st_mtime,
                'is_file': os.path.isfile(file_path),
                'is_directory': os.path.isdir(file_path),
                'extension': os.path.splitext(file_path)[1].lower()
            }
            
            # Add readable file size
            size = stat.st_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    info['size_human'] = f"{size:.1f} {unit}"
                    break
                size /= 1024.0
            else:
                info['size_human'] = f"{size:.1f} TB"
            
            return info
            
        except Exception as e:
            return {'path': file_path, 'error': str(e)}
    
    def validate_wine_setup(self):
        """Validate that wine environment is properly set up"""
        validation = {
            'wine_available': False,
            'wine_prefix_valid': False,
            'divine_available': False,
            'overall_valid': False,
            'messages': []
        }
        
        # Check Wine
        wine_valid, wine_msg = self.wine_env.validate_wine_installation()
        validation['wine_available'] = wine_valid
        validation['messages'].append(f"Wine: {wine_msg}")
        
        # Check Wine prefix
        prefix_valid, prefix_msg = self.wine_env.validate_wine_prefix()
        validation['wine_prefix_valid'] = prefix_valid
        validation['messages'].append(f"Wine Prefix: {prefix_msg}")
        
        # Check Divine.exe if path provided
        if self.lslib_path:
            divine_path = self.lslib_path.replace("Z:", "") if self.lslib_path.startswith("Z:") else self.lslib_path
            divine_valid, divine_msg = self.validate_file_exists(divine_path, "file")
            validation['divine_available'] = divine_valid
            validation['messages'].append(f"Divine.exe: {divine_msg}")
        else:
            validation['messages'].append("Divine.exe: Path not configured")
        
        # Overall validation
        validation['overall_valid'] = (
            validation['wine_available'] and 
            validation['wine_prefix_valid'] and 
            (validation['divine_available'] or not self.lslib_path)
        )
        
        return validation
    
    def get_supported_formats(self):
        """Get list of supported file formats for this operation type"""
        # This should be overridden by subclasses
        return {
            'input_formats': ['.pak', '.lsx', '.lsf', '.loca'],
            'output_formats': ['.pak', '.lsx', '.lsf', '.xml'],
            'description': 'Base wine operations - supports common Larian formats'
        }
    
    def cleanup_temp_files(self, temp_dir_pattern="*_temp_*"):
        """Clean up temporary files created during operations"""
        import glob
        import shutil
        
        cleanup_count = 0
        errors = []
        
        try:
            # Look for temporary directories
            temp_dirs = glob.glob(temp_dir_pattern)
            
            for temp_dir in temp_dirs:
                if os.path.isdir(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                        cleanup_count += 1
                    except Exception as e:
                        errors.append(f"Failed to remove {temp_dir}: {e}")
            
            return cleanup_count, errors
            
        except Exception as e:
            return 0, [f"Cleanup failed: {e}"]
    
    def estimate_operation_time(self, file_path, operation_type="extract"):
        """Estimate operation time based on file size and type"""
        try:
            file_size = os.path.getsize(file_path)
            
            # Rough estimates in seconds based on file size
            size_mb = file_size / (1024 * 1024)
            
            estimates = {
                'extract': size_mb * 0.1,  # ~0.1 seconds per MB
                'create': size_mb * 0.2,   # ~0.2 seconds per MB  
                'convert': size_mb * 0.05, # ~0.05 seconds per MB
                'analyze': size_mb * 0.01  # ~0.01 seconds per MB
            }
            
            estimated_seconds = estimates.get(operation_type, size_mb * 0.1)
            
            # Convert to human readable
            if estimated_seconds < 60:
                time_str = f"{estimated_seconds:.1f} seconds"
            elif estimated_seconds < 3600:
                time_str = f"{estimated_seconds/60:.1f} minutes"
            else:
                time_str = f"{estimated_seconds/3600:.1f} hours"
            
            return {
                'estimated_seconds': estimated_seconds,
                'estimated_formatted': time_str,
                'file_size_mb': size_mb
            }
            
        except Exception as e:
            return {'error': str(e)}


class OperationResult:
    """Standardized result object for wine operations"""
    
    def __init__(self, success=False, message="", data=None, operation_type="unknown"):
        self.success = success
        self.message = message
        self.data = data or {}
        self.operation_type = operation_type
        self.timestamp = __import__('time').time()
    
    def to_dict(self):
        """Convert result to dictionary"""
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'operation_type': self.operation_type,
            'timestamp': self.timestamp
        }
    
    def __str__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"[{status}] {self.operation_type}: {self.message}"
    
    @classmethod
    def success_result(cls, message, data=None, operation_type="unknown"):
        """Create a success result"""
        return cls(success=True, message=message, data=data, operation_type=operation_type)
    
    @classmethod
    def error_result(cls, message, data=None, operation_type="unknown"):
        """Create an error result"""
        return cls(success=False, message=message, data=data, operation_type=operation_type)


def format_file_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def safe_file_operation(func):
    """Decorator for safe file operations with error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            return OperationResult.error_result(f"File not found: {e}")
        except PermissionError as e:
            return OperationResult.error_result(f"Permission denied: {e}")
        except Exception as e:
            return OperationResult.error_result(f"Operation failed: {e}")
    return wrapper