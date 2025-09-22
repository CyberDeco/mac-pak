#!/usr/bin/env python3
"""
Wine Integration for BG3 Mac Tool - App Bundle Compatible Version
Main wrapper class using the wine environment manager
"""

import subprocess
import os
import sys
import shutil
import threading
import tempfile
from pathlib import Path

from .wine_environment import WineEnvironmentManager, WineProcessMonitor

from ..data.parsers.larian_parser import *

class WineLSTools:
    """Wine integration for LSF/LSX/LSJ, etc. handling"""

     def __init__(self, wine_path, lslib_path, wine_prefix, settings_manager):
        super().__init__(parent)
        
        self.wine_path = wine_path
        self.settings_manager = settings_manager
        self.parser = UniversalBG3Parser()
        
        def convert_lsx_to_lsf(self, source, lsf_file, is_content=False):
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
                output_format="lsf"
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
    
    def convert_lsf_to_lsx(self, source, lsx_file, is_content=False):
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
                output_format="lsx"
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