#!/usr/bin/env python3
"""
Loca Processor Module
Handles .loca file operations and localization processing
"""

import os
import shutil
import tempfile
from pathlib import Path

from .wine_base_operations import BaseWineOperations, OperationResult, safe_file_operation
from .wine_pak_tools import WinePakTools


class WineLocaProcessor(BaseWineOperations):
    """Specialized module for .loca file operations"""
    
    def __init__(self, wine_env, lslib_path, settings_manager=None):
        super().__init__(wine_env, lslib_path, settings_manager)
    
    def get_supported_formats(self):
        """Get loca operation supported formats"""
        return {
            'input_formats': ['.loca', '.xml'],
            'output_formats': ['.loca', '.xml'],
            'operations': ['convert_loca_to_xml', 'convert_xml_to_loca', 'extract_from_pak', 'batch_convert'],
            'description': 'Localization file operations - .loca file processing for BG3'
        }
    
    def mac_to_wine_path(self, mac_path):
        """Convert Mac path to Wine path format"""
        abs_path = os.path.abspath(mac_path)
        wine_path = f"Z:{abs_path.replace('/', chr(92))}"
        return wine_path
    
    def run_divine_command(self, action, source=None, destination=None, progress_callback=None, **kwargs):
        """Run Divine.exe command specific to loca operations"""
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
            progress_callback(100, "Loca operation complete!")
        
        return success, output
    
    def cancel_current_operation(self):
        """Cancel the currently running loca operation"""
        if self.current_monitor:
            self.current_monitor.cancel()
    
    def analyze_loca_file_binary(self, loca_path):
        """Analyze .loca file structure without conversion"""
        try:
            with open(loca_path, 'rb') as f:
                header = f.read(64)
                file_size = os.path.getsize(loca_path)
            
            analysis = {
                'file_path': loca_path,
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
            elif header.startswith(b'LOCA'):
                analysis['likely_format'] = 'Larian Localization'
            
            return analysis
            
        except Exception as e:
            return {'file_path': loca_path, 'error': str(e)}
    
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
    
    def convert_xml_to_loca(self, xml_path, loca_path):
        """Convert XML file to .loca format using divine.exe"""
        try:
            os.makedirs(os.path.dirname(loca_path), exist_ok=True)
            
            success, output = self.run_divine_command(
                action="convert-resource",
                source=self.mac_to_wine_path(xml_path),
                destination=self.mac_to_wine_path(loca_path),
                input_format="xml",
                output_format="loca"
            )
            
            if success and os.path.exists(loca_path):
                return True
            else:
                print(f"XML to Loca conversion failed: {output}")
                return False
                
        except Exception as e:
            print(f"XML to Loca conversion error: {e}")
            return False
    
    def extract_loca_from_pak(self, pak_path, loca_pattern="*.loca", output_dir=None):
        """Extract .loca files from PAK"""
        if not output_dir:
            output_dir = os.path.splitext(pak_path)[0] + "_loca_extracted"
        
        # First extract the entire PAK to a temp location
        temp_dir = pak_path + "_temp_extract"

        pak_ops = PakOperations(self.wine_env, self.lslib_path, self.settings_manager)
        
        success = pak_ops.extract_pak(pak_path, temp_dir)
        
        if success:
            # Find all .loca files
            loca_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith('.loca'):
                        loca_files.append(os.path.join(root, file))
            
            # Copy .loca files to output directory
            os.makedirs(output_dir, exist_ok=True)
            extracted_loca_files = []
            
            for loca_file in loca_files:
                rel_path = os.path.relpath(loca_file, temp_dir)
                dest_path = os.path.join(output_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(loca_file, dest_path)
                extracted_loca_files.append(dest_path)
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return extracted_loca_files
        
        return []
    
    def batch_convert_loca_to_xml(self, source_dir, output_dir, progress_callback=None):
        """Convert multiple .loca files to XML format"""
        loca_files = []
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith('.loca'):
                    loca_files.append(os.path.join(root, file))
        
        if not loca_files:
            return False, "No .loca files found"
        
        os.makedirs(output_dir, exist_ok=True)
        
        successful_conversions = 0
        total_files = len(loca_files)
        
        for i, loca_file in enumerate(loca_files):
            if progress_callback:
                progress_callback(
                    int((i / total_files) * 90), 
                    f"Converting {os.path.basename(loca_file)} ({i+1}/{total_files})"
                )
            
            # Maintain directory structure
            rel_path = os.path.relpath(loca_file, source_dir)
            xml_file = os.path.join(output_dir, os.path.splitext(rel_path)[0] + '.xml')
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(xml_file), exist_ok=True)
            
            if self.convert_loca_to_xml(loca_file, xml_file):
                successful_conversions += 1
        
        if progress_callback:
            progress_callback(100, f"Converted {successful_conversions}/{total_files} files")
        
        return successful_conversions == total_files, f"Converted {successful_conversions}/{total_files} files"
    
    def extract_and_convert_loca_from_pak(self, pak_path, output_dir=None, convert_to_xml=True, progress_callback=None):
        """Extract .loca files from PAK and optionally convert to XML"""
        if progress_callback:
            progress_callback(10, "Extracting .loca files from PAK...")
        
        # Extract .loca files
        loca_files = self.extract_loca_from_pak(pak_path, output_dir=output_dir)
        
        if not loca_files:
            return False, "No .loca files found in PAK"
        
        if not convert_to_xml:
            return True, f"Extracted {len(loca_files)} .loca files"
        
        if progress_callback:
            progress_callback(50, f"Converting {len(loca_files)} .loca files to XML...")
        
        # Convert to XML
        xml_dir = output_dir + "_xml" if output_dir else os.path.splitext(pak_path)[0] + "_loca_xml"
        
        def conversion_progress(percent, message):
            if progress_callback:
                # Scale progress from 50-100
                scaled_percent = 50 + (percent * 0.5)
                progress_callback(int(scaled_percent), message)
        
        success, message = self.batch_convert_loca_to_xml(
            output_dir or os.path.splitext(pak_path)[0] + "_loca_extracted",
            xml_dir,
            conversion_progress
        )
        
        return success, f"Extracted and converted {len(loca_files)} .loca files"
    
    def create_loca_translation_template(self, loca_file, template_file):
        """Create a translation template from a .loca file"""
        try:
            # First convert to XML for easier parsing
            temp_xml = loca_file + "_temp.xml"
            
            if self.convert_loca_to_xml(loca_file, temp_xml):
                # Parse XML and create template
                # This would typically involve XML parsing to extract translatable strings
                # For now, just copy the XML as a template
                shutil.copy2(temp_xml, template_file)
                
                # Clean up temp file
                os.remove(temp_xml)
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Template creation error: {e}")
            return False