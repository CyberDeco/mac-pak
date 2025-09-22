#!/usr/bin/env python3
"""
Model format handler for BG3 preview system
Handles: .gr2 (Granny 3D) model files
"""

import os
from typing import Dict

from .base_handler import FormatHandler

class ModelFormatHandler(FormatHandler):
    """Handler for 3D model files (.gr2)"""
    
    def can_handle(self, file_ext: str) -> bool:
        """Check if this handler supports the file extension"""
        return file_ext.lower() == '.gr2'
    
    def get_supported_extensions(self):
        """Return list of supported extensions"""
        return ['.gr2']
    
    def get_file_icon(self, file_ext: str) -> str:
        """Get appropriate icon for file type"""
        return "🎭"
    
    def preview(self, file_path: str, **kwargs) -> Dict:
        """Generate preview for GR2 model files"""
        preview_data = self._create_base_preview_data(file_path)
        
        if preview_data.get('error'):
            return preview_data
        
        try:
            # Generate header
            content = self._create_header_content(file_path)
            
            # Add GR2-specific analysis
            gr2_analysis = self._analyze_gr2_file(file_path, preview_data['size'])
            content += gr2_analysis
            
            preview_data['content'] = content
            return preview_data
            
        except Exception as e:
            preview_data['error'] = str(e)
            preview_data['content'] = f"Error previewing GR2 file: {e}"
            return preview_data
    
    def _analyze_gr2_file(self, file_path: str, file_size: int) -> str:
        """Analyze GR2 (Granny 3D) file structure"""
        try:
            with open(file_path, 'rb') as f:
                header_data = f.read(1024)
                
            content = "Granny 3D Model File\n\n"
            
            # Better GR2 detection
            gr2_detected = False
            signatures = [b'GR2', b'Granny3D', b'granny', b'GRANNY']
            
            for sig in signatures:
                if sig in header_data[:128].lower():
                    gr2_detected = True
                    break
            
            # Alternative detection methods
            if not gr2_detected and file_size > 1000:
                if b'\x00\x00\x80\x3f' in header_data or b'\x00\x00\x00\x3f' in header_data:
                    gr2_detected = True
                    content += "Detected via binary patterns (likely 3D data)\n"
            
            if gr2_detected:
                content += "Valid GR2/3D model file detected\n"
            else:
                content += "Warning: Unusual format or compressed GR2 file\n"
            
            # Enhanced structure analysis
            structure_info = self._analyze_gr2_structure(file_path)
            
            if 'error' not in structure_info:
                content += f"\nStructure Analysis:\n"
                content += f"Size: {file_size:,} bytes\n"
                
                if structure_info['meshes'] > 0:
                    content += f"Meshes detected: {structure_info['meshes']}\n"
                if structure_info['skeletons'] > 0:
                    content += f"Skeleton/Bone data: {structure_info['skeletons']}\n"
                if structure_info['animations'] > 0:
                    content += f"Animation data: {structure_info['animations']}\n"
                if structure_info['materials'] > 0:
                    content += f"Material references: {structure_info['materials']}\n"
                if structure_info['vertex_data'] > 0:
                    content += f"Vertex data indicators: {structure_info['vertex_data']}\n"
                
                # Estimate model complexity
                total_indicators = sum([
                    structure_info['meshes'],
                    structure_info['materials'],
                    structure_info['vertex_data']
                ])
                
                if total_indicators < 5:
                    complexity = "Simple"
                elif total_indicators < 20:
                    complexity = "Moderate"
                else:
                    complexity = "Complex"
                
                content += f"Estimated complexity: {complexity}\n"
            
            content += "\nNote: GR2 files contain 3D models. Use Blender with GR2 import plugins for editing.\n"
            return content
            
        except Exception as e:
            return f"Error analyzing GR2 file: {e}\n"
    
    def _analyze_gr2_structure(self, file_path: str) -> Dict:
        """Analyze GR2 file structure for model components"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(4096)
                
            analysis = {
                'meshes': 0,
                'skeletons': 0, 
                'animations': 0,
                'materials': 0,
                'bones': 0,
                'vertex_data': 0
            }
            
            # Search for various indicators (case-insensitive)
            data_lower = data.lower()
            
            # Count occurrences of key terms
            analysis['meshes'] = data_lower.count(b'mesh')
            analysis['skeletons'] = data_lower.count(b'skeleton') + data_lower.count(b'bone')
            analysis['animations'] = data_lower.count(b'animation') + data_lower.count(b'track')
            analysis['materials'] = data_lower.count(b'material') + data_lower.count(b'texture')
            analysis['bones'] = data_lower.count(b'bone')
            
            # Look for vertex data indicators
            vertex_indicators = (
                data_lower.count(b'vertex') + 
                data_lower.count(b'position') + 
                data_lower.count(b'normal') +
                data_lower.count(b'uv')
            )
            analysis['vertex_data'] = vertex_indicators
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}