#!/usr/bin/env python3
"""
PAK Operations Module
Handles all PAK file creation/export, 
extraction/compression, and analysis operations
"""

import os
import threading
from pathlib import Path

from .wine_base_operations import BaseWineOperations, OperationResult, safe_file_operation
from .wine_environment import WineProcessMonitor

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

class WinePakTools(BaseWineOperations):
    """Specialized module for PAK file operations"""
    
    def __init__(self, wine_env, lslib_path, settings_manager=None):
        super().__init__(wine_env, lslib_path, settings_manager)
        
        # Initialize compression methods
        self.compression_methods = {
            'none': {'method': 'none', 'description': 'No compression (fastest)'},
            'zlib': {'method': 'zlib', 'description': 'Standard zlib compression'},
            'zlibfast': {'method': 'zlibfast', 'description': 'Fast zlib compression'},
            'lz4': {'method': 'lz4', 'description': 'LZ4 compression (fast)'},
            'lz4hc': {'method': 'lz4hc', 'description': 'LZ4 high compression (default)'}
        }
    
    def get_supported_formats(self):
        """Get PAK operation supported formats"""
        return {
            'input_formats': ['.pak'],
            'output_formats': ['.pak'],
            'operations': [
                'extract', 'create', 'list', 'analyze',
                'create_with_compression', 'extract_with_filter', 'extract_single_file',
                'batch_extract', 'batch_create', 'list_with_filter', 'set_priority'
            ],
            'compression_methods': list(self.compression_methods.keys()),
            'description': 'Advanced PAK operations with compression, filtering, and batch processing'
        }
    
    def mac_to_wine_path(self, mac_path):
        """Convert Mac path to Wine path format"""
        abs_path = os.path.abspath(mac_path)
        wine_path = f"Z:{abs_path.replace('/', chr(92))}"
        return wine_path
    
    def run_divine_command(self, action, source=None, destination=None, progress_callback=None, **kwargs):
        """Run Divine.exe command - returns monitor for async handling"""
        
        print(f"DEBUG: wine_pak_tools.run_divine_command called with action={action}")
        
        # Build command
        cmd = [self.wine_env.wine_path, self.lslib_path, "--action", action, "--game", "bg3"]
        
        if source:
            cmd.extend(["--source", source])
        if destination:
            cmd.extend(["--destination", destination])
        
        for key, value in kwargs.items():
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])
        
        # Setup environment
        env = os.environ.copy()
        env["WINEPREFIX"] = self.wine_env.wine_prefix
        
        # Create monitor
        self.current_monitor = WineProcessMonitor()
        
        if progress_callback:
            self.current_monitor.progress_updated.connect(
                lambda p, m: progress_callback(p, m)
            )
        
        # Start async
        self.current_monitor.run_process_async(cmd, env, progress_callback)
        
        return self.current_monitor
    
    def cancel_current_operation(self):
        """Cancel the currently running PAK operation"""
        if self.current_monitor:
            self.current_monitor.cancel()
    
    def extract_pak_async(self, pak_file, dest_dir):
        """Extract PAK asynchronously - returns WineProcessMonitor immediately"""
        wine_pak_path = self.mac_to_wine_path(pak_file)
        wine_dest_path = self.mac_to_wine_path(dest_dir)
        
        os.makedirs(dest_dir, exist_ok=True)
        
        cmd = [
            self.wine_env.wine_path, self.lslib_path,
            "--action", "extract-package",
            "--game", "bg3",
            "--source", wine_pak_path,
            "--destination", wine_dest_path
        ]
        
        env = os.environ.copy()
        env["WINEPREFIX"] = self.wine_env.wine_prefix
        
        # Create monitor
        self.current_monitor = WineProcessMonitor()
        
        # Start async - returns immediately!
        self.current_monitor.run_process_async(cmd, env)
        
        return self.current_monitor
    
    def create_pak_async(self, source_dir, pak_file):
        """Create PAK asynchronously - returns WineProcessMonitor immediately"""
        wine_source_path = self.mac_to_wine_path(source_dir)
        wine_pak_path = self.mac_to_wine_path(pak_file)
        
        if not os.path.exists(source_dir):
            raise ValueError(f"Source directory does not exist: {source_dir}")
        
        pak_dir = os.path.dirname(pak_file)
        if pak_dir:
            os.makedirs(pak_dir, exist_ok=True)
        
        cmd = [
            self.wine_env.wine_path, self.lslib_path,
            "--action", "create-package",
            "--game", "bg3",
            "--source", wine_source_path,
            "--destination", wine_pak_path
        ]
        
        env = os.environ.copy()
        env["WINEPREFIX"] = self.wine_env.wine_prefix
        
        self.current_monitor = WineProcessMonitor()
        self.current_monitor.run_process_async(cmd, env)
        
        return self.current_monitor
    
    def list_pak_contents_async(self, pak_file):
        """List PAK contents asynchronously - returns WineProcessMonitor immediately"""
        wine_pak_path = self.mac_to_wine_path(pak_file)
        
        cmd = [
            self.wine_env.wine_path, self.lslib_path,
            "--action", "list-package",
            "--game", "bg3",
            "--source", wine_pak_path
        ]
        
        env = os.environ.copy()
        env["WINEPREFIX"] = self.wine_env.wine_prefix
        
        self.current_monitor = WineProcessMonitor()
        self.current_monitor.run_process_async(cmd, env)
        
        return self.current_monitor
    
    def get_pak_info(self, pak_file):
        """Get detailed information about a PAK file"""
        try:
            file_size = os.path.getsize(pak_file)
            file_count = len(self.list_pak_contents(pak_file))
            
            return {
                'file_path': pak_file,
                'file_size': file_size,
                'file_count': file_count,
                'size_formatted': f"{file_size:,} bytes",
                'size_human': format_file_size(file_size)
            }
        except Exception as e:
            return {
                'file_path': pak_file,
                'error': str(e)
            }
    
    @safe_file_operation
    def create_pak_with_compression(self, source_dir, pak_file, compression='lz4hc', 
                                   priority=0, use_package_name=False, progress_callback=None):
        """Create PAK with specific compression and priority settings"""
        
        if compression not in self.compression_methods:
            return OperationResult.error_result(
                f"Invalid compression method: {compression}. Available: {', '.join(self.compression_methods.keys())}",
                operation_type="create_pak_with_compression"
            )
        
        # Build command arguments
        kwargs = {
            "compression_method": compression
        }
        
        if priority != 0:
            kwargs["package_priority"] = priority
        
        if use_package_name:
            kwargs["use_package_name"] = True
        
        self.ensure_directory_exists(os.path.dirname(pak_file))
        
        if progress_callback:
            comp_desc = self.compression_methods[compression]['description']
            progress_callback(10, f"Creating PAK with {comp_desc}...")
        
        success, output = self.run_divine_command(
            action="create-package",
            source=self.mac_to_wine_path(source_dir),
            destination=self.mac_to_wine_path(pak_file),
            progress_callback=progress_callback,
            **kwargs
        )
        
        if success and os.path.exists(pak_file):
            file_info = self.get_pak_info(pak_file)
            return OperationResult.success_result(
                f"Successfully created PAK with {compression} compression",
                data={
                    "pak_file": pak_file,
                    "compression": compression,
                    "priority": priority,
                    "file_info": file_info
                },
                operation_type="create_pak_with_compression"
            )
        else:
            return OperationResult.error_result(
                f"PAK creation failed: {output}",
                operation_type="create_pak_with_compression"
            )
    
    @safe_file_operation
    def extract_single_file(self, pak_file, packaged_path, output_file, progress_callback=None):
        """Extract a single specific file from PAK"""
        
        self.ensure_directory_exists(os.path.dirname(output_file))
        
        if progress_callback:
            progress_callback(20, f"Extracting {packaged_path}...")
        
        success, output = self.run_divine_command(
            action="extract-single-file",
            source=self.mac_to_wine_path(pak_file),
            destination=self.mac_to_wine_path(output_file),
            packaged_path=packaged_path,
            progress_callback=progress_callback
        )
        
        if success and os.path.exists(output_file):
            file_info = self.get_file_info(output_file)
            return OperationResult.success_result(
                f"Successfully extracted {packaged_path}",
                data={"output_file": output_file, "file_info": file_info},
                operation_type="extract_single_file"
            )
        else:
            return OperationResult.error_result(
                f"Single file extraction failed: {output}",
                operation_type="extract_single_file"
            )
    
    def extract_with_filter(self, pak_file, output_dir, expression="*", use_regex=False, 
                          progress_callback=None):
        """Extract PAK contents with glob or regex filtering"""
        
        kwargs = {
            "expression": expression
        }
        
        if use_regex:
            kwargs["use_regex"] = True
        
        self.ensure_directory_exists(output_dir)
        
        if progress_callback:
            filter_type = "regex" if use_regex else "glob"
            progress_callback(15, f"Extracting with {filter_type} filter: {expression}")
        
        success, output = self.run_divine_command(
            action="extract-package",
            source=self.mac_to_wine_path(pak_file),
            destination=self.mac_to_wine_path(output_dir),
            progress_callback=progress_callback,
            **kwargs
        )
        
        if success:
            # Count extracted files
            extracted_files = []
            for root, dirs, files in os.walk(output_dir):
                extracted_files.extend(files)
            
            return OperationResult.success_result(
                f"Successfully extracted {len(extracted_files)} files matching '{expression}'",
                data={
                    "output_dir": output_dir,
                    "extracted_count": len(extracted_files),
                    "filter_expression": expression,
                    "filter_type": "regex" if use_regex else "glob"
                },
                operation_type="extract_with_filter"
            )
        else:
            return OperationResult.error_result(
                f"Filtered extraction failed: {output}",
                operation_type="extract_with_filter"
            )
    
    def list_pak_with_filter(self, pak_file, expression="*", use_regex=False):
        """List PAK contents with filtering"""
        
        kwargs = {
            "expression": expression
        }
        
        if use_regex:
            kwargs["use_regex"] = True
        
        success, output = self.run_divine_command(
            action="list-package",
            source=self.mac_to_wine_path(pak_file),
            **kwargs
        )
        
        if success:
            # Parse output to extract filtered file list
            files = []
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('Opening') and not line.startswith('Package') and not line.startswith('Listing'):
                    # Parse divine.exe output
                    parts = line.split()
                    if parts:
                        file_path = parts[0]
                        files.append({
                            'name': file_path,
                            'type': os.path.splitext(file_path)[1].lower() if '.' in file_path else 'folder'
                        })
            
            return OperationResult.success_result(
                f"Found {len(files)} files matching '{expression}'",
                data={
                    "files": files,
                    "file_count": len(files),
                    "filter_expression": expression,
                    "filter_type": "regex" if use_regex else "glob"
                },
                operation_type="list_pak_with_filter"
            )
        else:
            return OperationResult.error_result(
                f"PAK listing failed: {output}",
                operation_type="list_pak_with_filter"
            )
    
    def batch_extract_paks(self, pak_directory, output_base_dir, expression="*", 
                          use_package_name=True, progress_callback=None):
        """Extract multiple PAK files in a directory"""
        
        # Find all PAK files
        pak_files = []
        for root, dirs, files in os.walk(pak_directory):
            for file in files:
                if file.lower().endswith('.pak'):
                    pak_files.append(os.path.join(root, file))
        
        if not pak_files:
            return OperationResult.error_result(
                f"No PAK files found in {pak_directory}",
                operation_type="batch_extract_paks"
            )
        
        kwargs = {
            "expression": expression
        }
        
        if use_package_name:
            kwargs["use_package_name"] = True
        
        self.ensure_directory_exists(output_base_dir)
        
        if progress_callback:
            progress_callback(10, f"Starting batch extraction of {len(pak_files)} PAK files...")
        
        success, output = self.run_divine_command(
            action="extract-packages",
            source=self.mac_to_wine_path(pak_directory),
            destination=self.mac_to_wine_path(output_base_dir),
            progress_callback=progress_callback,
            **kwargs
        )
        
        if success:
            # Count total extracted files
            total_extracted = 0
            for root, dirs, files in os.walk(output_base_dir):
                total_extracted += len(files)
            
            return OperationResult.success_result(
                f"Successfully extracted {len(pak_files)} PAK files ({total_extracted} total files)",
                data={
                    "pak_count": len(pak_files),
                    "total_extracted": total_extracted,
                    "output_dir": output_base_dir
                },
                operation_type="batch_extract_paks"
            )
        else:
            return OperationResult.error_result(
                f"Batch extraction failed: {output}",
                operation_type="batch_extract_paks"
            )
    
    def create_pak_with_priority(self, source_dir, pak_file, priority, compression='lz4hc'):
        """Create a PAK file with specific load priority"""
        return self.create_pak_with_compression(
            source_dir, pak_file, compression=compression, priority=priority
        )
    
    def extract_by_file_type(self, pak_file, output_dir, file_extensions, progress_callback=None):
        """Extract only files with specific extensions from PAK"""
        
        # Build regex pattern for file extensions
        if isinstance(file_extensions, str):
            file_extensions = [file_extensions]
        
        # Remove dots and create regex pattern
        extensions = [ext.lstrip('.') for ext in file_extensions]
        pattern = r'.*\.(' + '|'.join(extensions) + r')$'
        
        return self.extract_with_filter(
            pak_file, output_dir, 
            expression=pattern, 
            use_regex=True, 
            progress_callback=progress_callback
        )
    
    def extract_game_assets_by_type(self, pak_file, output_dir, asset_type, progress_callback=None):
        """Extract specific game asset types with predefined patterns"""
        
        asset_patterns = {
            'textures': r'.*\.(dds|png|jpg|tga)$',
            'models': r'.*\.(gr2|dae)$',
            'audio': r'.*\.(wem|ogg|wav)$',
            'scripts': r'.*\.(lsx|lsf|lsj|lua)$',
            'localization': r'.*\.loca$',
            'materials': r'.*/Materials/.*\.(lsf|lsx)$',
            'animations': r'.*/Animations/.*\.gr2$',
            'fx': r'.*/FX/.*\.(lsf|lsx)$'
        }
        
        if asset_type not in asset_patterns:
            return OperationResult.error_result(
                f"Unknown asset type: {asset_type}. Available: {', '.join(asset_patterns.keys())}",
                operation_type="extract_game_assets_by_type"
            )
        
        pattern = asset_patterns[asset_type]
        
        if progress_callback:
            progress_callback(5, f"Extracting {asset_type} assets...")
        
        return self.extract_with_filter(
            pak_file, output_dir,
            expression=pattern,
            use_regex=True,
            progress_callback=progress_callback
        )
    
    def analyze_pak_compression(self, pak_file):
        """Analyze PAK file compression and structure"""
        try:
            # Get basic file info
            file_info = self.get_pak_info(pak_file)
            
            # List contents to get file count
            list_result = self.list_pak_with_filter(pak_file)
            
            analysis = {
                'file_path': pak_file,
                'file_size': file_info['file_size'],
                'size_human': file_info['size_human'],
                'estimated_compression': 'unknown'
            }
            
            if list_result.success:
                file_count = list_result.data['file_count']
                analysis['file_count'] = file_count
                
                # Estimate compression ratio (very rough)
                avg_file_size = file_info['file_size'] / max(file_count, 1)
                if avg_file_size < 1024:  # Very small average = high compression
                    analysis['estimated_compression'] = 'high (likely lz4hc or zlib)'
                elif avg_file_size < 4096:
                    analysis['estimated_compression'] = 'medium (likely lz4)'
                else:
                    analysis['estimated_compression'] = 'low or none'
            
            return analysis
            
        except Exception as e:
            return {'file_path': pak_file, 'error': str(e)}
    
    def get_compression_recommendations(self, source_dir):
        """Get compression method recommendations based on content"""
        try:
            # Analyze directory contents
            total_size = 0
            file_count = 0
            file_types = {}
            
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    total_size += size
                    file_count += 1
                    
                    ext = os.path.splitext(file)[1].lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
            
            recommendations = {
                'total_size': total_size,
                'total_size_human': format_file_size(total_size),
                'file_count': file_count,
                'file_types': file_types,
                'recommended_compression': 'lz4hc',  # Default
                'reasoning': []
            }
            
            # Analyze content to recommend compression
            if total_size > 100 * 1024 * 1024:  # > 100MB
                recommendations['recommended_compression'] = 'lz4hc'
                recommendations['reasoning'].append("Large archive - use high compression")
            elif total_size < 10 * 1024 * 1024:  # < 10MB
                recommendations['recommended_compression'] = 'lz4'
                recommendations['reasoning'].append("Small archive - prioritize speed")
            
            # Check for already compressed content
            compressed_formats = ['.dds', '.ogg', '.wem', '.jpg', '.png']
            compressed_files = sum(count for ext, count in file_types.items() if ext in compressed_formats)
            
            if compressed_files > file_count * 0.7:  # >70% already compressed
                recommendations['recommended_compression'] = 'lz4'
                recommendations['reasoning'].append("Mostly pre-compressed files - light compression")
            
            # Check for text/script heavy content
            text_formats = ['.lsx', '.lsj', '.lua', '.txt', '.xml']
            text_files = sum(count for ext, count in file_types.items() if ext in text_formats)
            
            if text_files > file_count * 0.5:  # >50% text files
                recommendations['recommended_compression'] = 'lz4hc'
                recommendations['reasoning'].append("Text-heavy content - high compression beneficial")
            
            return recommendations
            
        except Exception as e:
            return {'error': str(e)}