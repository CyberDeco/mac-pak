#!/usr/bin/env python3
"""
BG3 Enhanced LSX Tools - Support for LSX, LSJ, and LSF formats
Extended with comprehensive PyQt6 threading support for better performance
"""

import xml.etree.ElementTree as ET
import json
import os
import struct
from pathlib import Path
from collections import defaultdict
import tempfile
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional, Callable, Dict, List, Any
import logging

from PyQt6.QtCore import (
    QThread, QObject, pyqtSignal, QMutex, QMutexLocker, 
    QTimer, QRunnable, QThreadPool, pyqtSlot
)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QTextEdit, QProgressBar,
    QDialogButtonBox, QTabWidget, QWidget, QSplitter,
    QMessageBox, QApplication
)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt

# Configure logging for thread-safe operations
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ProgressUpdate:
    """Thread-safe progress update container"""
    current: int
    total: int
    message: str
    stage: str = ""
    error: Optional[str] = None

@dataclass
class ParseResult:
    """Thread-safe parse result container"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    file_path: str = ""
    processing_time: float = 0.0

class ThreadSafeCounter:
    """Thread-safe counter for tracking operations across threads"""
    def __init__(self, initial_value: int = 0):
        self._value = initial_value
        self._mutex = QMutex()
    
    def increment(self, amount: int = 1) -> int:
        with QMutexLocker(self._mutex):
            self._value += amount
            return self._value
    
    def get_value(self) -> int:
        with QMutexLocker(self._mutex):
            return self._value
    
    def set_value(self, value: int):
        with QMutexLocker(self._mutex):
            self._value = value

class FileParserWorker(QObject):
    """Worker thread for parsing individual files"""
    
    # Signals for thread communication
    progress_updated = pyqtSignal(ProgressUpdate)
    parsing_completed = pyqtSignal(ParseResult)
    error_occurred = pyqtSignal(str, str)  # error_message, file_path
    
    def __init__(self, parser_instance, file_path: str):
        super().__init__()
        self.parser = parser_instance
        self.file_path = file_path
        self.should_stop = False
        self._mutex = QMutex()
    
    @pyqtSlot()
    def parse_file(self):
        """Parse file in worker thread"""
        start_time = time.time()
        
        try:
            with QMutexLocker(self._mutex):
                if self.should_stop:
                    return
            
            self.progress_updated.emit(ProgressUpdate(
                current=0, total=100, 
                message=f"Starting parse: {os.path.basename(self.file_path)}",
                stage="initializing"
            ))
            
            # Perform the actual parsing
            result_data = self.parser.parse_file(self.file_path)
            
            processing_time = time.time() - start_time
            
            if result_data and not isinstance(result_data, str):
                # Success
                result = ParseResult(
                    success=True,
                    data=result_data,
                    file_path=self.file_path,
                    processing_time=processing_time
                )
                self.parsing_completed.emit(result)
                self.progress_updated.emit(ProgressUpdate(
                    current=100, total=100,
                    message=f"Completed: {os.path.basename(self.file_path)}",
                    stage="completed"
                ))
            else:
                # Error case
                error_msg = result_data if isinstance(result_data, str) else "Unknown parsing error"
                result = ParseResult(
                    success=False,
                    error=error_msg,
                    file_path=self.file_path,
                    processing_time=processing_time
                )
                self.parsing_completed.emit(result)
                self.error_occurred.emit(error_msg, self.file_path)
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Exception during parsing: {str(e)}"
            
            result = ParseResult(
                success=False,
                error=error_msg,
                file_path=self.file_path,
                processing_time=processing_time
            )
            self.parsing_completed.emit(result)
            self.error_occurred.emit(error_msg, self.file_path)
    
    def stop_parsing(self):
        """Signal the worker to stop"""
        with QMutexLocker(self._mutex):
            self.should_stop = True

class ConversionWorker(QObject):
    """Worker for file conversion operations"""
    
    # Signals
    progress_updated = pyqtSignal(ProgressUpdate)
    conversion_completed = pyqtSignal(dict)  # conversion result
    
    def __init__(self, processor, workspace_path: str):
        super().__init__()
        self.processor = processor
        self.workspace_path = workspace_path
        self.should_stop = False
        self._mutex = QMutex()
    
    @pyqtSlot()
    def prepare_workspace(self):
        """Prepare workspace with conversions"""
        try:
            def progress_callback(percent, message):
                with QMutexLocker(self._mutex):
                    if self.should_stop:
                        return
                
                self.progress_updated.emit(ProgressUpdate(
                    current=percent, total=100,
                    message=message,
                    stage="conversion"
                ))
            
            result = self.processor.prepare_workspace_for_packing(
                self.workspace_path, 
                progress_callback
            )
            
            self.conversion_completed.emit(result)
            
        except Exception as e:
            self.conversion_completed.emit({
                'temp_path': self.workspace_path,
                'conversions': [],
                'errors': [f"Conversion failed: {str(e)}"],
                'cleanup_needed': False
            })
    
    def stop_conversion(self):
        """Signal worker to stop"""
        with QMutexLocker(self._mutex):
            self.should_stop = True

class UniversalBG3Parser:
    """Universal parser for LSX, LSJ, and LSF files with threading support"""
    
    def __init__(self):
        self.current_file = None
        self.parsed_data = None
        self.file_format = None
        self.wine_wrapper = None
        self._parsing_mutex = QMutex()
    
    def detect_file_format(self, file_path):
        """Detect file format based on extension and content"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.lsx':
            return 'lsx'
        elif ext == '.lsj':
            return 'lsj'
        elif ext == '.lsf':
            return 'lsf'
        elif ext == '.loca':
            return 'loca'
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
        """Parse any supported BG3 file format (thread-safe)"""
        with QMutexLocker(self._parsing_mutex):
            self.current_file = file_path
            self.file_format = self.detect_file_format(file_path)
            
            if self.file_format == 'lsx':
                return self.parse_lsx_file(file_path)
            elif self.file_format == 'lsj':
                return self.parse_lsj_file(file_path)
            elif self.file_format == 'lsf':
                return self.parse_lsf_file(file_path)
            elif self.file_format == 'loca':
                return self.parse_loca_file(file_path)
            else:
                logger.warning(f"Unsupported file format: {file_path}")
                return f"Unsupported file format: {file_path}"

    def parse_loca_file(self, file_path):
        """Parse .loca files by converting to XML first"""
        try:
            # Convert .loca to XML using divine.exe
            temp_xml = file_path + '.temp.xml'
            
            if not self.wine_wrapper:
                return "Error: No BG3 tool available for .loca conversion"
            
            success = self.wine_wrapper.convert_loca_to_xml(file_path, temp_xml)
            
            if success and os.path.exists(temp_xml):
                # Parse the converted XML
                tree = ET.parse(temp_xml)
                root = tree.getroot()
                
                self.parsed_data = {
                    'file': file_path,
                    'format': 'loca',
                    'root_tag': root.tag,
                    'version': root.get('version', 'unknown'),
                    'entries': [],
                    'string_count': 0,
                    'raw_tree': tree
                }
                
                # Parse localization entries
                entries = []
                for content_list in root.findall('.//contentList'):
                    for content in content_list.findall('content'):
                        entry = {
                            'handle': content.get('contentuid', ''),
                            'version': content.get('version', ''),
                            'text': content.text or ''
                        }
                        entries.append(entry)
                
                self.parsed_data['entries'] = entries
                self.parsed_data['string_count'] = len(entries)
                
                # Clean up temp file
                try:
                    os.remove(temp_xml)
                except:
                    pass
                
                logger.info(f"Parsed .loca file: {file_path} ({len(entries)} strings)")
                return self.parsed_data
                
            else:
                return f"Failed to convert .loca file: {file_path}"
                
        except Exception as e:
            logger.error(f"Error parsing .loca: {e}")
            return f"Error parsing .loca: {e}"
    
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
            
            logger.info(f"Parsed LSX file: {file_path}")
            return self.parsed_data
            
        except ET.ParseError as e:
            error_msg = f"XML Parse Error: {e}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error parsing LSX: {e}"
            logger.error(error_msg)
            return error_msg
    
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
            
            logger.info(f"Parsed LSJ file: {file_path}")
            return self.parsed_data
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON Parse Error: {e}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error parsing LSJ: {e}"
            logger.error(error_msg)
            return error_msg

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
                
                logger.info(f"Parsed LSF file: {file_path}")
                return result
            else:
                error_msg = f"Failed to convert LSF file: {file_path}"
                logger.error(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"Error parsing LSF: {e}"
            logger.error(error_msg)
            return error_msg
    
    def set_wine_wrapper(self, wine_wrapper):
        """Set the BG3 tool instance for LSF conversion"""
        self.wine_wrapper = wine_wrapper
    
    def _convert_lsf_to_lsx(self, lsf_path, lsx_path):
        """Convert LSF to LSX using divine.exe via WineWrapper"""
        if not self.wine_wrapper:
            logger.error("No BG3 tool available for LSF conversion")
            return False
        
        try:
            # Use the WineWrapper's convert method
            success = self.wine_wrapper.convert_lsf_to_lsx(lsf_path, lsx_path)
            
            if success and os.path.exists(lsx_path):
                logger.info(f"Successfully converted LSF to LSX: {lsx_path}")
                return True
            else:
                logger.error("LSF conversion failed or output file not found")
                return False
                
        except Exception as e:
            logger.error(f"Error in LSF conversion: {e}")
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

class AutoConversionProcessor:
    """Handles automatic file conversions with threading support"""
    
    def __init__(self, wine_wrapper):
        self.wine_wrapper = wine_wrapper
        self.conversion_log = []
        self._processing_mutex = QMutex()
    
    def find_conversion_files(self, workspace_path):
        """Find files that need conversion in workspace"""
        conversion_files = {
            'lsf_conversions': [],  # .lsf.lsx -> .lsf
            'lsb_conversions': [],  # .lsb.lsx -> .lsb
            'lsbs_conversions': [], # .lsbs.lsx -> .lsbs
            'other_conversions': []
        }
        
        try:
            for root, dirs, files in os.walk(workspace_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_lower = file.lower()
                    
                    if file_lower.endswith('.lsf.lsx'):
                        conversion_files['lsf_conversions'].append({
                            'source': file_path,
                            'relative_path': os.path.relpath(file_path, workspace_path),
                            'target_ext': '.lsf'
                        })
                    elif file_lower.endswith('.lsb.lsx'):
                        conversion_files['lsb_conversions'].append({
                            'source': file_path,
                            'relative_path': os.path.relpath(file_path, workspace_path),
                            'target_ext': '.lsb'
                        })
                    elif file_lower.endswith('.lsbs.lsx'):
                        conversion_files['lsbs_conversions'].append({
                            'source': file_path,
                            'relative_path': os.path.relpath(file_path, workspace_path),
                            'target_ext': '.lsbs'
                        })
                    elif file_lower.endswith('.lsbc.lsx'):
                        conversion_files['other_conversions'].append({
                            'source': file_path,
                            'relative_path': os.path.relpath(file_path, workspace_path),
                            'target_ext': '.lsbc'
                        })
        
        except Exception as e:
            logger.error(f"Error scanning workspace: {e}")
        
        return conversion_files
    
    def prepare_workspace_for_packing(self, workspace_path, progress_callback=None):
        """Prepare workspace by converting files and creating temp copy (thread-safe)"""
        with QMutexLocker(self._processing_mutex):
            conversion_files = self.find_conversion_files(workspace_path)
            total_conversions = sum(len(files) for files in conversion_files.values())
            
            if total_conversions == 0:
                return {
                    'temp_path': workspace_path,
                    'conversions': [],
                    'errors': [],
                    'cleanup_needed': False
                }
            
            if progress_callback:
                progress_callback(5, f"Found {total_conversions} files to convert")
            
            # Create temporary workspace
            temp_workspace = tempfile.mkdtemp(prefix="bg3_workspace_")
            
            try:
                if progress_callback:
                    progress_callback(10, "Copying workspace to temporary location...")
                
                # Copy entire workspace to temp
                shutil.copytree(workspace_path, os.path.join(temp_workspace, "workspace"))
                temp_workspace_path = os.path.join(temp_workspace, "workspace")
                
                if progress_callback:
                    progress_callback(30, "Starting file conversions...")
                
                conversions = []
                errors = []
                processed = 0
                
                # Process each conversion type
                for conversion_type, files in conversion_files.items():
                    for file_info in files:
                        try:
                            # Convert the file in temp workspace
                            temp_source = os.path.join(temp_workspace_path, file_info['relative_path'])
                            result = self.convert_file(temp_source, file_info['target_ext'])
                            
                            conversions.append({
                                'original_path': file_info['source'],
                                'temp_path': temp_source,
                                'target_path': result.get('target_path'),
                                'conversion_type': conversion_type,
                                'success': result['success']
                            })
                            
                            if not result['success']:
                                errors.append(result['error'])
                            
                        except Exception as e:
                            errors.append(f"Error converting {file_info['relative_path']}: {e}")
                        
                        processed += 1
                        if progress_callback:
                            percent = 30 + int((processed / total_conversions) * 60)
                            progress_callback(percent, f"Converted {processed}/{total_conversions} files")
                
                if progress_callback:
                    progress_callback(95, "Finalizing prepared workspace...")
                
                result = {
                    'temp_path': temp_workspace_path,
                    'conversions': conversions,
                    'errors': errors,
                    'cleanup_needed': True,
                    'temp_root': temp_workspace
                }
                
                if progress_callback:
                    success_count = sum(1 for c in conversions if c['success'])
                    progress_callback(100, f"Converted {success_count}/{total_conversions} files successfully")
                
                return result
                
            except Exception as e:
                # Clean up on error
                try:
                    shutil.rmtree(temp_workspace)
                except:
                    pass
                
                return {
                    'temp_path': workspace_path,
                    'conversions': [],
                    'errors': [f"Workspace preparation failed: {e}"],
                    'cleanup_needed': False
                }
    
    def convert_file(self, source_file, target_ext):
        """Convert a single file to target format"""
        try:
            # Generate target filename
            source_path = Path(source_file)
            
            # Remove the .lsx extension and any previous extension
            name_without_lsx = source_path.name[:-4]  # Remove .lsx
            
            # If it ends with .lsf, .lsb, etc., remove that too
            if name_without_lsx.endswith(('.lsf', '.lsb', '.lsbs', '.lsbc')):
                base_name = name_without_lsx.rsplit('.', 1)[0]
            else:
                base_name = name_without_lsx
            
            target_file = source_path.parent / (base_name + target_ext)
            
            # Perform conversion using wine_wrapper
            if target_ext == '.lsf':
                success = self.wine_wrapper.convert_lsx_to_lsf(str(source_file), str(target_file))
            elif target_ext in ['.lsb', '.lsbs', '.lsbc']:
                # These might use different conversion methods
                success = self.wine_wrapper.convert_lsx_to_lsf(str(source_file), str(target_file))
            else:
                return {
                    'success': False,
                    'error': f"Unsupported target format: {target_ext}"
                }
            
            if success:
                # Remove the original .lsx file
                os.remove(source_file)
                
                return {
                    'success': True,
                    'source_path': str(source_file),
                    'target_path': str(target_file)
                }
            else:
                return {
                    'success': False,
                    'error': f"Conversion failed for {source_file}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Exception during conversion: {e}"
            }
    
    def cleanup_temp_workspace(self, temp_root):
        """Clean up temporary workspace"""
        try:
            if temp_root and os.path.exists(temp_root):
                shutil.rmtree(temp_root)
                return True
        except Exception as e:
            logger.warning(f"Could not clean up temp workspace: {e}")
            return False
        return True