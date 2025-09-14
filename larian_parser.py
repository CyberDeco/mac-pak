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
        """Parse LSX (XML) files"""
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
                'raw_tree': tree
            }
            
            # Parse structure
            for region in root.findall('.//region'):
                region_info = self._parse_region(region)
                self.parsed_data['regions'].append(region_info)
            
            print(f"✅ Parsed LSX file: {file_path}")
            return self.parsed_data
            
        except ET.ParseError as e:
            print(f"❌ XML Parse Error: {e}")
            return None
        except Exception as e:
            print(f"❌ Error parsing LSX: {e}")
            return None
    
    def parse_lsj_file(self, file_path):
        """Parse LSJ (JSON) files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            self.parsed_data = {
                'file': file_path,
                'format': 'lsj',
                'root_tag': 'save' if 'save' in json_data else 'root',
                'version': json_data.get('version', 'unknown'),
                'regions': [],
                'raw_data': json_data
            }
            
            # Parse JSON structure - adapt based on actual LSJ format
            if 'save' in json_data:
                save_data = json_data['save']
                if 'regions' in save_data:
                    for region_data in save_data['regions']:
                        region_info = self._parse_json_region(region_data)
                        self.parsed_data['regions'].append(region_info)
            
            print(f"✅ Parsed LSJ file: {file_path}")
            return self.parsed_data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            return None
        except Exception as e:
            print(f"❌ Error parsing LSJ: {e}")
            return None
    
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
    
    def _convert_lsf_to_lsx(self, lsf_path, lsx_path):
        """Convert LSF to LSX using divine.exe - integrate with your wine wrapper"""
        # This requires a bg3_tool instance - should be injected when needed
        # For now, return False until we have proper integration
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