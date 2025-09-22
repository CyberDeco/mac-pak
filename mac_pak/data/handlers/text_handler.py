#!/usr/bin/env python3
"""
Text format handler for BG3 preview system
Handles: .lsx, .lsj, .xml, .txt, .json files
"""

import os
from typing import Dict

from .base_handler import FormatHandler


class TextFormatHandler(FormatHandler):
    """Handler for text-based files"""
    
    def can_handle(self, file_ext: str) -> bool:
        """Check if this handler supports the file extension"""
        return file_ext.lower() in ['.lsx', '.lsj', '.xml', '.txt', '.json']
    
    def get_supported_extensions(self):
        """Return list of supported extensions"""
        return ['.lsx', '.lsj', '.xml', '.txt', '.json']
    
    def get_file_icon(self, file_ext: str) -> str:
        """Get appropriate icon for file type"""
        icons = {
            '.lsx': '📄',
            '.lsj': '📋',
            '.xml': '📄',
            '.txt': '📝',
            '.json': '📋'
        }
        return icons.get(file_ext.lower(), '📄')
    
    def preview(self, file_path: str, parser=None, **kwargs) -> Dict:
        """Generate preview for text-based files"""
        preview_data = self._create_base_preview_data(file_path)
        
        if preview_data.get('error'):
            return preview_data
        
        try:
            # Generate header
            content = self._create_header_content(file_path)
            
            # Read and preview text content
            text_content = self._preview_text_file(file_path, preview_data['size'])
            content += text_content
            
            # Add BG3 structure analysis for supported formats
            file_ext = preview_data['extension']
            if file_ext in ['.lsx', '.lsj'] and parser:
                bg3_analysis = self._analyze_bg3_structure(file_path, file_ext, parser)
                content += bg3_analysis
            
            preview_data['content'] = content
            return preview_data
            
        except Exception as e:
            preview_data['error'] = str(e)
            preview_data['content'] = f"Error previewing text file: {e}"
            return preview_data
    
    def _preview_text_file(self, file_path: str, file_size: int) -> str:
        """Preview text-based files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2000)  # First 2KB
                if file_size > 2000:
                    content += f"\n\n... ({file_size-2000:,} more bytes)"
                return content
        except Exception as e:
            return f"Error reading text file: {e}\n"
    
    def _analyze_bg3_structure(self, file_path: str, file_ext: str, parser) -> str:
        """Analyze BG3 file structure using the parser"""
        if not parser or file_ext not in ['.lsx', '.lsj']:
            return ""
        
        try:
            parsed_data = parser.parse_file(file_path)
            if not parsed_data or not isinstance(parsed_data, dict):
                return f"\n\nParser error: {parsed_data}\n" if isinstance(parsed_data, str) else ""
            
            analysis = f"\n\n{'='*30}\nBG3 FILE INFO:\n{'='*30}\n"
            
            # Basic file info
            if 'format' in parsed_data:
                analysis += f"Format: {parsed_data['format'].upper()}\n"
            
            if 'version' in parsed_data and parsed_data['version'] != 'unknown':
                analysis += f"Version: {parsed_data['version']}\n"
            
            # Enhanced region information
            if 'regions' in parsed_data:
                regions = parsed_data['regions']
                if isinstance(regions, list) and regions:
                    analysis += f"Regions: {len(regions)}\n"
                    
                    # Show detailed region info
                    for i, region in enumerate(regions[:3]):  # Show first 3 regions
                        if isinstance(region, dict):
                            region_name = region.get('name') or region.get('id', f'Region_{i}')
                            node_count = len(region.get('nodes', []))
                            analysis += f"  • {region_name}: {node_count} nodes\n"
                    
                    if len(regions) > 3:
                        analysis += f"  ... and {len(regions) - 3} more regions\n"
            
            # Schema information for LSX files
            if file_ext == '.lsx' and 'schema_info' in parsed_data:
                schema = parsed_data['schema_info']
                analysis += f"\nStructure Analysis:\n"
                
                # Data types summary
                if 'data_types' in schema and schema['data_types']:
                    type_summary = []
                    for dtype, count in sorted(schema['data_types'].items(), key=lambda x: x[1], reverse=True)[:5]:
                        type_summary.append(f"{dtype}({count})")
                    analysis += f"Data types: {', '.join(type_summary)}\n"
                
                # Node types summary
                if 'node_types' in schema and schema['node_types']:
                    node_summary = []
                    for ntype, count in sorted(schema['node_types'].items(), key=lambda x: x[1], reverse=True)[:3]:
                        node_summary.append(f"{ntype}({count})")
                    analysis += f"Node types: {', '.join(node_summary)}\n"
                
                # Most common attributes
                if 'common_attributes' in schema and schema['common_attributes']:
                    common_attrs = sorted(schema['common_attributes'].items(), key=lambda x: x[1], reverse=True)[:3]
                    attr_summary = [f"{attr}({count})" for attr, count in common_attrs]
                    analysis += f"Common attributes: {', '.join(attr_summary)}\n"
            
            # Enhanced LSJ-specific info
            elif file_ext == '.lsj':
                if 'raw_data' in parsed_data:
                    raw_data = parsed_data['raw_data']
                    if (isinstance(raw_data, dict) and 
                        'save' in raw_data and 
                        'regions' in raw_data['save']):
                        
                        save_regions = raw_data['save']['regions']
                        if 'dialog' in save_regions:
                            analysis += "Contains dialog data\n"
                            
                            dialog_data = save_regions['dialog']
                            if 'category' in dialog_data:
                                category = dialog_data['category'].get('value', 'unknown')
                                analysis += f"Dialog category: {category}\n"
                            
                            if 'UUID' in dialog_data:
                                uuid = dialog_data['UUID'].get('value', 'unknown')
                                analysis += f"Dialog UUID: {uuid[:8]}...\n"
                            
                            # Count dialog elements
                            if 'speakerlist' in dialog_data:
                                speakers = dialog_data['speakerlist']
                                if isinstance(speakers, list):
                                    analysis += f"Speakers: {len(speakers)}\n"
            
            # File complexity assessment
            total_nodes = sum(len(region.get('nodes', [])) for region in parsed_data.get('regions', []))
            if total_nodes > 0:
                if total_nodes < 10:
                    complexity = "Simple"
                elif total_nodes < 100:
                    complexity = "Moderate"
                else:
                    complexity = "Complex"
                analysis += f"Complexity: {complexity} ({total_nodes} total nodes)\n"
            
            return analysis
            
        except Exception as e:
            return f"\n\nNote: Could not parse BG3 structure: {e}\n"