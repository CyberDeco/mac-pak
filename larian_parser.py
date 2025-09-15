#!/usr/bin/env python3
"""
BG3 Enhanced LSX Tools - Support for LSX, LSJ, and LSF formats
Extended from original LSX tools to handle all BG3 data formats
"""

import xml.etree.ElementTree as ET
import json
import os
import struct
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from collections import defaultdict
import threading
import tempfile


class UniversalBG3Parser:
    """Universal parser for LSX, LSJ, and LSF files"""
    
    def __init__(self):
        self.current_file = None
        self.parsed_data = None
        self.file_format = None
    
    def detect_file_format(self, file_path):
        """Detect file format based on extension and content"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.lsx':
            return 'lsx'
        elif ext == '.lsj':
            return 'lsj'
        elif ext == '.lsf':
            return 'lsf'
        else:
            # Try to detect by content
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(16)
                
                # LSF files typically start with specific magic bytes
                if header.startswith(b'LSOF') or header.startswith(b'LSFW'):
                    return 'lsf'
                
                # Try to parse as JSON
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                return 'lsj'
                
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            
            # Try to parse as XML
            try:
                ET.parse(file_path)
                return 'lsx'
            except ET.ParseError:
                pass
        
        return 'unknown'
    
    def parse_file(self, file_path):
        """Parse any supported BG3 file format"""
        self.current_file = file_path
        self.file_format = self.detect_file_format(file_path)
        
        if self.file_format == 'lsx':
            return self.parse_lsx_file(file_path)
        elif self.file_format == 'lsj':
            return self.parse_lsj_file(file_path)
        elif self.file_format == 'lsf':
            return self.parse_lsf_file(file_path)
        else:
            print(f"❌ Unsupported file format: {file_path}")
            return None
    
    def parse_lsx_file(self, file_path):
        """Parse LSX (XML) files with comprehensive structure analysis"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            self.parsed_data = {
                'file': file_path,
                'format': 'lsx',
                'root_tag': root.tag,
                'version': root.get('version', 'unknown'),
                'regions': [],
                'nodes': [],
                'attributes': {},
                'raw_tree': tree
            }
            
            # Parse regions and nodes with full detail
            for region in root.findall('.//region'):
                region_info = {
                    'id': region.get('id'),
                    'name': region.get('id'),  # For consistency with LSJ parser
                    'nodes': []
                }
                
                for node in region.findall('.//node'):
                    node_info = {
                        'id': node.get('id'),
                        'attributes': []
                    }
                    
                    # Parse attributes with full details
                    for attr in node.findall('.//attribute'):
                        attr_info = {
                            'id': attr.get('id'),
                            'type': attr.get('type'),
                            'value': attr.get('value'),
                            'handle': attr.get('handle')
                        }
                        node_info['attributes'].append(attr_info)
                    
                    region_info['nodes'].append(node_info)
                
                self.parsed_data['regions'].append(region_info)
            
            # Add schema analysis
            schema_info = self.get_lsx_schema_info()
            if schema_info:
                self.parsed_data['schema_info'] = schema_info
            
            print(f"✅ Parsed LSX file: {file_path}")
            return self.parsed_data
            
        except ET.ParseError as e:
            print(f"❌ XML Parse Error: {e}")
            return f"XML Parse Error: {e}"
        except Exception as e:
            print(f"❌ Error parsing LSX: {e}")
            return f"Error parsing LSX: {e}"
    
    def get_lsx_schema_info(self, lsx_file=None):
        """Analyze LSX structure and data types"""
        if lsx_file:
            self.parse_lsx_file(lsx_file)
        
        if not self.parsed_data:
            return None
        
        schema_info = {
            'file_type': self.parsed_data['root_tag'],
            'regions': {},
            'data_types': defaultdict(int),
            'common_attributes': defaultdict(int),
            'node_types': defaultdict(int)
        }
        
        for region in self.parsed_data['regions']:
            region_id = region['id']
            schema_info['regions'][region_id] = {
                'node_count': len(region['nodes']),
                'node_types': []
            }
            
            for node in region['nodes']:
                node_id = node['id']
                schema_info['node_types'][node_id] += 1
                schema_info['regions'][region_id]['node_types'].append(node_id)
                
                for attr in node['attributes']:
                    attr_type = attr['type']
                    attr_id = attr['id']
                    schema_info['data_types'][attr_type] += 1
                    schema_info['common_attributes'][attr_id] += 1
        
        return schema_info
    
    def get_enhanced_file_info(self):
        """Get comprehensive file information including schema analysis"""
        if not self.parsed_data:
            return None
        
        info = {
            'basic_info': {
                'file': self.parsed_data.get('file'),
                'format': self.parsed_data.get('format'),
                'version': self.parsed_data.get('version'),
                'root_tag': self.parsed_data.get('root_tag')
            },
            'structure': {
                'region_count': len(self.parsed_data.get('regions', [])),
                'total_nodes': sum(len(region.get('nodes', [])) for region in self.parsed_data.get('regions', [])),
                'total_attributes': sum(
                    len(node.get('attributes', [])) 
                    for region in self.parsed_data.get('regions', [])
                    for node in region.get('nodes', [])
                )
            }
        }
        
        # Add schema info if available
        if 'schema_info' in self.parsed_data:
            schema = self.parsed_data['schema_info']
            info['schema'] = {
                'data_types': dict(schema['data_types']),
                'most_common_attributes': dict(sorted(
                    schema['common_attributes'].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10]),
                'node_types': dict(schema['node_types'])
            }
        
        return info
    
    def parse_lsj_file(self, file_path):
        """Parse LSJ (JSON) files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            self.parsed_data = {
                'file': file_path,
                'format': 'lsj',
                'root_tag': 'save' if 'save' in json_data else 'root',
                'regions': [],
                'raw_data': json_data
            }
            
            # Extract version from the proper location
            if 'save' in json_data and 'header' in json_data['save']:
                self.parsed_data['version'] = json_data['save']['header'].get('version', 'unknown')
            else:
                self.parsed_data['version'] = json_data.get('version', 'unknown')
            
            # Parse JSON structure - handle regions as dictionary
            if 'save' in json_data:
                save_data = json_data['save']
                if 'regions' in save_data:
                    regions_dict = save_data['regions']
                    
                    # Regions is a dictionary, not a list
                    if isinstance(regions_dict, dict):
                        for region_name, region_data in regions_dict.items():
                            region_info = self._parse_json_region_dict(region_name, region_data)
                            self.parsed_data['regions'].append(region_info)
                    elif isinstance(regions_dict, list):
                        # Handle case where regions might be a list
                        for region_data in regions_dict:
                            region_info = self._parse_json_region(region_data)
                            self.parsed_data['regions'].append(region_info)
            
            print(f"✅ Parsed LSJ file: {file_path}")
            return self.parsed_data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            return f"JSON Parse Error: {e}"
        except Exception as e:
            print(f"❌ Error parsing LSJ: {e}")
            return f"Error parsing LSJ: {e}"

    def _parse_json_region_dict(self, region_name, region_data):
        """Parse JSON region data when regions is a dictionary"""
        region_info = {
            'id': region_name,
            'name': region_name,
            'nodes': [],
            'data': region_data
        }
        
        # For dialog regions, extract basic info
        if region_name == 'dialog':
            if isinstance(region_data, dict):
                # Extract basic dialog info
                if 'category' in region_data:
                    region_info['category'] = region_data['category'].get('value', 'unknown')
                if 'UUID' in region_data:
                    region_info['uuid'] = region_data['UUID'].get('value', 'unknown')
        
        return region_info
    
    def parse_lsf_file(self, file_path):
        """Parse LSF (binary) files - requires divine.exe conversion"""
        try:
            # For LSF files, we need to convert to LSX first using divine.exe
            # This is a placeholder - you'll need to integrate with your divine wrapper
            
            temp_lsx = file_path + '.temp.lsx'
            
            # Use your existing divine wrapper to convert LSF to LSX
            success = self._convert_lsf_to_lsx(file_path, temp_lsx)
            
            if success and os.path.exists(temp_lsx):
                # Parse the converted LSX
                result = self.parse_lsx_file(temp_lsx)
                if result:
                    result['format'] = 'lsf'
                    result['original_file'] = file_path
                
                # Clean up temp file
                try:
                    os.remove(temp_lsx)
                except:
                    pass
                
                print(f"✅ Parsed LSF file: {file_path}")
                return result
            else:
                print(f"❌ Failed to convert LSF file: {file_path}")
                return None
                
        except Exception as e:
            print(f"❌ Error parsing LSF: {e}")
            return None
    
    def set_bg3_tool(self, bg3_tool):
        """Set the BG3 tool instance for LSF conversion"""
        self.bg3_tool = bg3_tool
    
    def _convert_lsf_to_lsx(self, lsf_path, lsx_path):
        """Convert LSF to LSX using divine.exe via WineWrapper"""
        if not self.bg3_tool:
            print("No BG3 tool available for LSF conversion")
            return False
        
        try:
            # Use the WineWrapper's convert method
            success = self.bg3_tool.convert_lsf_to_lsx(lsf_path, lsx_path)
            
            if success and os.path.exists(lsx_path):
                print(f"Successfully converted LSF to LSX: {lsx_path}")
                return True
            else:
                print(f"LSF conversion failed or output file not found")
                return False
                
        except Exception as e:
            print(f"Error in LSF conversion: {e}")
            return False
    
    def _parse_region(self, region_element):
        """Parse XML region element"""
        region_info = {
            'id': region_element.get('id'),
            'nodes': []
        }
        
        for node in region_element.findall('.//node'):
            node_info = {
                'id': node.get('id'),
                'attributes': []
            }
            
            for attr in node.findall('.//attribute'):
                attr_info = {
                    'id': attr.get('id'),
                    'type': attr.get('type'),
                    'value': attr.get('value'),
                    'handle': attr.get('handle')
                }
                node_info['attributes'].append(attr_info)
            
            region_info['nodes'].append(node_info)
        
        return region_info
    
    def _parse_json_region(self, region_data):
        """Parse JSON region data"""
        # Adapt this based on actual LSJ structure
        region_info = {
            'id': region_data.get('id', 'unknown'),
            'nodes': []
        }
        
        # Parse nodes from JSON structure
        if 'node' in region_data:
            nodes = region_data['node']
            if not isinstance(nodes, list):
                nodes = [nodes]
            
            for node_data in nodes:
                node_info = {
                    'id': node_data.get('id', 'unknown'),
                    'attributes': []
                }
                
                # Parse attributes
                if 'attribute' in node_data:
                    attrs = node_data['attribute']
                    if not isinstance(attrs, list):
                        attrs = [attrs]
                    
                    for attr_data in attrs:
                        attr_info = {
                            'id': attr_data.get('id'),
                            'type': attr_data.get('type'),
                            'value': attr_data.get('value'),
                            'handle': attr_data.get('handle')
                        }
                        node_info['attributes'].append(attr_info)
                
                region_info['nodes'].append(node_info)
        
        return region_info