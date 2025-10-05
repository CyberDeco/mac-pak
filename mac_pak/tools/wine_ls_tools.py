#!/usr/bin/env python3
"""
Binary File Converter Module
Handles LSX/LSF conversions and other binary file format operations
"""

import os
import tempfile
from pathlib import Path

from .wine_base_operations import BaseWineOperations, OperationResult, safe_file_operation
from .wine_environment import WineProcessMonitor


class WineLSTools(BaseWineOperations):
    """Specialized module for binary file format conversions"""
    
    def __init__(self, wine_env, lslib_path, settings_manager=None):
        super().__init__(wine_env, lslib_path, settings_manager)
        self.current_monitor = None
    
    def get_supported_formats(self):
        """Get binary conversion supported formats"""
        return {
            'input_formats': ['.lsx', '.lsf'],
            'output_formats': ['.lsx', '.lsf'],
            'operations': ['convert_lsx_to_lsf', 'convert_lsf_to_lsx', 'batch_convert', 'analyze'],
            'description': 'Binary file conversions - LSX/LSF format conversions for BG3'
        }
    
    def mac_to_wine_path(self, mac_path):
        """Convert Mac path to Wine path format"""
        abs_path = os.path.abspath(mac_path)
        wine_path = f"Z:{abs_path.replace('/', chr(92))}"
        return wine_path
    
    def run_divine_command(self, action, source=None, destination=None, progress_callback=None, **kwargs):
        """Run Divine.exe command specific to binary conversions"""
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
            progress_callback(100, "Conversion complete!")
        
        return success, output
    
    def cancel_current_operation(self):
        """Cancel the currently running conversion operation"""
        if self.current_monitor:
            self.current_monitor.cancel()
    
    def convert_lsx_to_lsf(self, source, lsf_file, is_content=False, progress_callback=None):
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
                output_format="lsf",
                progress_callback=progress_callback
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
    
    def convert_lsf_to_lsx(self, source, lsx_file, is_content=False, progress_callback=None):
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
                output_format="lsx",
                progress_callback=progress_callback
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
    
    def batch_convert_lsx_to_lsf(self, source_dir, output_dir, progress_callback=None):
        """Convert multiple LSX files to LSF format"""
        lsx_files = []
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith('.lsx'):
                    lsx_files.append(os.path.join(root, file))
        
        if not lsx_files:
            return False, "No LSX files found"
        
        os.makedirs(output_dir, exist_ok=True)
        
        successful_conversions = 0
        total_files = len(lsx_files)
        
        for i, lsx_file in enumerate(lsx_files):
            if progress_callback:
                progress_callback(
                    int((i / total_files) * 90), 
                    f"Converting {os.path.basename(lsx_file)} ({i+1}/{total_files})"
                )
            
            # Maintain directory structure
            rel_path = os.path.relpath(lsx_file, source_dir)
            lsf_file = os.path.join(output_dir, os.path.splitext(rel_path)[0] + '.lsf')
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(lsf_file), exist_ok=True)
            
            if self.convert_lsx_to_lsf(lsx_file, lsf_file):
                successful_conversions += 1
        
        if progress_callback:
            progress_callback(100, f"Converted {successful_conversions}/{total_files} files")
        
        return successful_conversions == total_files, f"Converted {successful_conversions}/{total_files} files"
    
    def batch_convert_lsf_to_lsx(self, source_dir, output_dir, progress_callback=None):
        """Convert multiple LSF files to LSX format"""
        lsf_files = []
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith('.lsf'):
                    lsf_files.append(os.path.join(root, file))
        
        if not lsf_files:
            return False, "No LSF files found"
        
        os.makedirs(output_dir, exist_ok=True)
        
        successful_conversions = 0
        total_files = len(lsf_files)
        
        for i, lsf_file in enumerate(lsf_files):
            if progress_callback:
                progress_callback(
                    int((i / total_files) * 90), 
                    f"Converting {os.path.basename(lsf_file)} ({i+1}/{total_files})"
                )
            
            # Maintain directory structure
            rel_path = os.path.relpath(lsf_file, source_dir)
            lsx_file = os.path.join(output_dir, os.path.splitext(rel_path)[0] + '.lsx')
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(lsx_file), exist_ok=True)
            
            if self.convert_lsf_to_lsx(lsf_file, lsx_file):
                successful_conversions += 1
        
        if progress_callback:
            progress_callback(100, f"Converted {successful_conversions}/{total_files} files")
        
        return successful_conversions == total_files, f"Converted {successful_conversions}/{total_files} files"
    
    def analyze_binary_file(self, file_path):
        """Analyze binary file structure and format"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(64)
                file_size = os.path.getsize(file_path)
            
            analysis = {
                'file_path': file_path,
                'file_size': file_size,
                'header_hex': header[:16].hex(),
                'header_ascii': ''.join(chr(b) if 32 <= b <= 126 else '.' for b in header[:32]),
                'likely_format': 'unknown'
            }
            
            # Check for common Larian file signatures
            if header.startswith(b'LSOF') or header.startswith(b'LSFW'):
                analysis['likely_format'] = 'Larian Binary (LSF)'
            elif header.startswith(b'<?xml') or b'<save>' in header:
                analysis['likely_format'] = 'Larian XML (LSX)'
            elif header.startswith(b'LOCA'):
                analysis['likely_format'] = 'Larian Localization (LOCA)'
            elif b'xml' in header.lower() or b'<' in header:
                analysis['likely_format'] = 'XML-based'
            
            return analysis
            
        except Exception as e:
            return {'file_path': file_path, 'error': str(e)}
    
    def convert_with_format_detection(self, source_file, output_file, progress_callback=None):
        """Convert file with automatic format detection"""
        analysis = self.analyze_binary_file(source_file)
        
        if progress_callback:
            progress_callback(20, f"Detected format: {analysis.get('likely_format', 'unknown')}")
        
        # Determine conversion based on detected format
        if analysis['likely_format'] == 'Larian Binary (LSF)':
            return self.convert_lsf_to_lsx(source_file, output_file, progress_callback=progress_callback)
        elif analysis['likely_format'] == 'Larian XML (LSX)':
            return self.convert_lsx_to_lsf(source_file, output_file, progress_callback=progress_callback)
        else:
            return False, f"Unsupported format: {analysis['likely_format']}"