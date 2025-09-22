#!/usr/bin/env python3
"""
Binary format handler for BG3 preview system
Handles: .lsf, .lsbs, .lsbc, .lsfx files
"""

import os
import tempfile
from typing import Dict

from .base_handler import FormatHandler

class BinaryFormatHandler(FormatHandler):
    """Handler for binary Larian format files"""
    
    def can_handle(self, file_ext: str) -> bool:
        """Check if this handler supports the file extension"""
        return file_ext.lower() in ['.lsf', '.lsbs', '.lsbc', '.lsfx']
    
    def get_supported_extensions(self):
        """Return list of supported extensions"""
        return ['.lsf', '.lsbs', '.lsbc', '.lsfx']
    
    def get_file_icon(self, file_ext: str) -> str:
        """Get appropriate icon for file type"""
        icons = {
            '.lsf': '🔒',
            '.lsbs': '📦',
            '.lsbc': '📦',
            '.lsfx': '📈'
        }
        return icons.get(file_ext.lower(), '📦')
    
    def preview(self, file_path: str, wine_wrapper=None, parser=None, progress_callback=None, **kwargs) -> Dict:
        """Generate preview for binary Larian files"""
        preview_data = self._create_base_preview_data(file_path)
        
        if preview_data.get('error'):
            return preview_data
        
        try:
            file_ext = preview_data['extension']
            
            # Generate header
            content = self._create_header_content(file_path)
            
            # Try conversion first if we have the tools
            if wine_wrapper:
                converted_preview = self._try_conversion_preview(
                    file_path, file_ext, wine_wrapper, parser, progress_callback
                )
                if converted_preview:
                    content += converted_preview
                else:
                    # Fallback to binary analysis
                    content += self._analyze_binary_fallback(file_path, file_ext)
            else:
                # No conversion tools available
                content += self._analyze_binary_fallback(file_path, file_ext)
            
            preview_data['content'] = content
            return preview_data
            
        except Exception as e:
            preview_data['error'] = str(e)
            preview_data['content'] = f"Error previewing binary file: {e}"
            return preview_data
    
    def _try_conversion_preview(self, file_path: str, file_ext: str, wine_wrapper, parser, progress_callback) -> str:
        """Try to convert binary file and generate preview"""
        temp_lsx = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.lsx', delete=False) as tmp:
                temp_lsx = tmp.name
            
            if progress_callback:
                progress_callback(20, f"Converting {file_ext.upper()} to LSX...")
            
            # Attempt conversion based on file type
            success = False
            if file_ext == '.lsf':
                success = wine_wrapper.convert_lsf_to_lsx(file_path, temp_lsx)
            elif file_ext == '.lsfx':
                success = wine_wrapper.convert_lsf_to_lsx(file_path, temp_lsx)
            elif file_ext in ['.lsbs', '.lsbc']:
                success = wine_wrapper.convert_lsf_to_lsx(file_path, temp_lsx)
            
            if success and os.path.exists(temp_lsx) and parser:
                if progress_callback:
                    progress_callback(70, "Parsing converted file...")
                
                # Parse converted file
                parsed_data = parser.parse_lsx_file(temp_lsx)
                
                if parsed_data and isinstance(parsed_data, dict):
                    result = f"{file_ext.upper()} Binary File (converted)\n\n"
                    result += f"Format: {file_ext.upper()}\n"
                    result += f"Converted size: {os.path.getsize(temp_lsx):,} bytes\n"
                    
                    # Show BG3 structure info
                    if 'regions' in parsed_data:
                        regions = parsed_data['regions']
                        if isinstance(regions, list):
                            result += f"Regions: {len(regions)}\n"
                            for region in regions[:3]:
                                if isinstance(region, dict):
                                    region_name = region.get('name') or region.get('id', 'unknown')
                                    node_count = len(region.get('nodes', []))
                                    result += f"  • {region_name}: {node_count} nodes\n"
                    
                    # Add converted content preview
                    try:
                        with open(temp_lsx, 'r', encoding='utf-8', errors='ignore') as f:
                            converted_content = f.read(1500)  # First 1.5KB
                            if len(converted_content) >= 1500:
                                converted_content += "\n\n... (content truncated)"
                        
                        result += f"\n{'='*30}\nCONVERTED CONTENT:\n{'='*30}\n"
                        result += converted_content
                    except Exception:
                        pass
                    
                    return result
            
            return None
            
        except Exception as e:
            return f"Conversion failed: {e}\n"
        finally:
            # Clean up temp file
            if temp_lsx and os.path.exists(temp_lsx):
                try:
                    os.remove(temp_lsx)
                except:
                    pass
    
    def _analyze_binary_fallback(self, file_path: str, file_ext: str) -> str:
        """Basic binary analysis when conversion isn't available"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(64)
            
            file_size = os.path.getsize(file_path)
            content = f"Larian Binary File ({file_ext.upper()})\n\n"
            
            # Look for magic bytes or signatures
            readable_header = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in header[:32])
            content += f"Header: {readable_header}\n"
            content += f"File size: {file_size:,} bytes\n"
            
            # Check for common Larian signatures
            if header.startswith(b'LSOF') or header.startswith(b'LSFW'):
                content += "Contains Larian format signature\n"
            
            # Check for compression indicators
            if header.startswith(b'\x1f\x8b'):
                content += "Format: GZIP compressed\n"
            elif header.startswith(b'PK'):
                content += "Format: ZIP compressed\n"
            
            content += f"\nNote: {file_ext.upper()} files require divine.exe conversion for full analysis.\n"
            content += "Install Wine and divine.exe for detailed preview.\n"
            
            return content
            
        except Exception as e:
            return f"Error analyzing {file_ext.upper()} file: {e}\n"
    
    def preview_with_progress(self, file_path: str, progress_callback, **kwargs) -> Dict:
        """Preview with progress updates for conversion operations"""
        if progress_callback:
            progress_callback(10, "Preparing binary file analysis...")
        
        result = self.preview(file_path, progress_callback=progress_callback, **kwargs)
        
        if progress_callback:
            progress_callback(100, "Binary analysis complete!")
        
        return result