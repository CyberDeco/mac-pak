#!/usr/bin/env python3
"""
3D Model Converter Module
Handles GR2, DAE, GLTF, and GLB model format conversions with advanced options
"""

import os
import threading
from pathlib import Path

from .wine_base_operations import BaseWineOperations, OperationResult, safe_file_operation


class ModelConverter(BaseWineOperations):
    """Specialized module for 3D model format conversions"""
    
    def __init__(self, wine_env, lslib_path, settings_manager=None):
        super().__init__(wine_env, lslib_path, settings_manager)
        
        # Default GR2 conversion options
        self.default_gr2_options = {
            "export-normals": True,
            "export-tangents": True,
            "export-uvs": True,
            "export-colors": True,
            "deduplicate-vertices": True,
            "deduplicate-uvs": True,
            "recalculate-normals": False,
            "recalculate-tangents": False,
            "recalculate-iwt": False,
            "flip-uvs": True,
            "ignore-uv-nan": True,
            "disable-qtangents": False,
            "y-up-skeletons": True,
            "force-legacy-version": False,
            "compact-tris": True,
            "build-dummy-skeleton": True,
            "apply-basis-transforms": True,
            "mirror-skeletons": False,
            "x-flip-meshes": False,
            "conform": False,
            "conform-copy": False
        }
    
    def get_supported_formats(self):
        """Get model conversion supported formats"""
        return {
            'input_formats': ['.gr2', '.dae', '.glb', '.gltf'],
            'output_formats': ['.gr2', '.dae', '.glb', '.gltf'],
            'operations': ['convert_model', 'convert_models', 'batch_convert', 'conform_model'],
            'description': '3D model conversions - GR2, DAE, GLTF, GLB format conversions for BG3'
        }
    
    @safe_file_operation
    def convert_model(self, source_file, output_file, input_format=None, output_format=None, 
                     gr2_options=None, conform_path=None, progress_callback=None):
        """Convert a single 3D model file with options"""
        
        # Auto-detect formats if not specified
        if not input_format:
            input_format = os.path.splitext(source_file)[1][1:].lower()
        
        if not output_format:
            output_format = os.path.splitext(output_file)[1][1:].lower()
        
        # Validate formats
        supported_formats = ["gr2", "dae", "glb", "gltf"]
        if input_format not in supported_formats or output_format not in supported_formats:
            return OperationResult.error_result(
                f"Unsupported format conversion: {input_format} -> {output_format}",
                operation_type="convert_model"
            )
        
        # Build command arguments
        kwargs = {
            "input_format": input_format,
            "output_format": output_format
        }
        
        # Add GR2 options if converting GR2 files
        if input_format == "gr2" or output_format == "gr2":
            options = self._build_gr2_options(gr2_options)
            if options:
                kwargs["gr2_options"] = options
        
        # Add conform path if specified
        if conform_path:
            kwargs["conform_path"] = self.mac_to_wine_path(conform_path)
        
        # Ensure output directory exists
        self.ensure_directory_exists(os.path.dirname(output_file))
        
        if progress_callback:
            progress_callback(10, f"Converting {input_format.upper()} to {output_format.upper()}...")
        
        success, output = self.run_divine_command(
            action="convert-model",
            source=self.mac_to_wine_path(source_file),
            destination=self.mac_to_wine_path(output_file),
            progress_callback=progress_callback,
            **kwargs
        )
        
        if success and os.path.exists(output_file):
            file_info = self.get_file_info(output_file)
            return OperationResult.success_result(
                f"Successfully converted {os.path.basename(source_file)} to {output_format.upper()}",
                data={"output_file": output_file, "file_info": file_info},
                operation_type="convert_model"
            )
        else:
            return OperationResult.error_result(
                f"Model conversion failed: {output}",
                operation_type="convert_model"
            )
    
    def batch_convert_models(self, source_dir, output_dir, input_format, output_format,
                           gr2_options=None, conform_path=None, progress_callback=None):
        """Convert multiple model files in a directory"""
        
        # Find all files with the specified input format
        model_files = []
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith(f'.{input_format.lower()}'):
                    model_files.append(os.path.join(root, file))
        
        if not model_files:
            return OperationResult.error_result(
                f"No {input_format.upper()} files found in {source_dir}",
                operation_type="batch_convert_models"
            )
        
        # Build batch command arguments
        kwargs = {
            "input_format": input_format,
            "output_format": output_format
        }
        
        # Add GR2 options if needed
        if input_format == "gr2" or output_format == "gr2":
            options = self._build_gr2_options(gr2_options)
            if options:
                kwargs["gr2_options"] = options
        
        if conform_path:
            kwargs["conform_path"] = self.mac_to_wine_path(conform_path)
        
        self.ensure_directory_exists(output_dir)
        
        if progress_callback:
            progress_callback(10, f"Starting batch conversion of {len(model_files)} files...")
        
        success, output = self.run_divine_command(
            action="convert-models",
            source=self.mac_to_wine_path(source_dir),
            destination=self.mac_to_wine_path(output_dir),
            progress_callback=progress_callback,
            **kwargs
        )
        
        if success:
            # Count converted files
            converted_files = []
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if file.lower().endswith(f'.{output_format.lower()}'):
                        converted_files.append(os.path.join(root, file))
            
            return OperationResult.success_result(
                f"Successfully converted {len(converted_files)} files from {input_format.upper()} to {output_format.upper()}",
                data={"converted_count": len(converted_files), "output_dir": output_dir},
                operation_type="batch_convert_models"
            )
        else:
            return OperationResult.error_result(
                f"Batch model conversion failed: {output}",
                operation_type="batch_convert_models"
            )
    
    def conform_model_to_original(self, source_file, output_file, conform_path, 
                                 copy_mode=False, progress_callback=None):
        """Conform a model to match the structure of an original model"""
        
        gr2_options = self.default_gr2_options.copy()
        gr2_options["conform"] = True
        gr2_options["conform-copy"] = copy_mode
        
        return self.convert_model(
            source_file, output_file,
            conform_path=conform_path,
            gr2_options=gr2_options,
            progress_callback=progress_callback
        )
    
    def extract_model_from_pak(self, pak_file, model_path, output_file, 
                              convert_to_format=None, progress_callback=None):
        """Extract a specific model from PAK and optionally convert it"""
        
        if progress_callback:
            progress_callback(20, f"Extracting {model_path} from PAK...")
        
        # First extract the specific file
        success, output = self.run_divine_command(
            action="extract-single-file",
            source=self.mac_to_wine_path(pak_file),
            destination=self.mac_to_wine_path(output_file),
            packaged_path=model_path,
            progress_callback=lambda p, m: progress_callback(p * 0.6, m) if progress_callback else None
        )
        
        if not success:
            return OperationResult.error_result(
                f"Failed to extract {model_path}: {output}",
                operation_type="extract_model_from_pak"
            )
        
        # Convert if requested
        if convert_to_format and convert_to_format != os.path.splitext(output_file)[1][1:]:
            if progress_callback:
                progress_callback(70, f"Converting to {convert_to_format.upper()}...")
            
            converted_file = os.path.splitext(output_file)[0] + f".{convert_to_format}"
            convert_result = self.convert_model(
                output_file, converted_file,
                output_format=convert_to_format,
                progress_callback=lambda p, m: progress_callback(70 + p * 0.3, m) if progress_callback else None
            )
            
            if convert_result.success:
                # Remove original extracted file if conversion successful
                try:
                    os.remove(output_file)
                except:
                    pass
                output_file = converted_file
        
        return OperationResult.success_result(
            f"Successfully extracted and processed {model_path}",
            data={"output_file": output_file},
            operation_type="extract_model_from_pak"
        )
    
    def analyze_model_file(self, model_file):
        """Analyze a 3D model file for structure and content information"""
        try:
            file_info = self.get_file_info(model_file)
            format_type = file_info['extension'][1:].upper() if file_info['extension'] else 'UNKNOWN'
            
            analysis = {
                'file_path': model_file,
                'format': format_type,
                'file_size': file_info['size'],
                'size_human': file_info['size_human'],
                'supported_operations': []
            }
            
            # Determine supported operations based on format
            if format_type.lower() in ['gr2', 'dae', 'glb', 'gltf']:
                analysis['supported_operations'] = ['convert', 'extract_from_pak']
                
                if format_type.lower() == 'gr2':
                    analysis['supported_operations'].extend(['conform', 'apply_gr2_options'])
            
            # Try to get more detailed info if it's a GR2 file
            if format_type.lower() == 'gr2':
                analysis.update(self._analyze_gr2_file(model_file))
            
            return analysis
            
        except Exception as e:
            return {'file_path': model_file, 'error': str(e)}
    
    def _analyze_gr2_file(self, gr2_file):
        """Analyze GR2 file specifically (placeholder - would need actual GR2 parsing)"""
        # This would require more detailed GR2 file parsing
        # For now, return basic analysis
        return {
            'gr2_specific': True,
            'notes': 'GR2 format - supports advanced conversion options',
            'recommended_output': 'dae'  # DAE is often more compatible
        }
    
    def _build_gr2_options(self, custom_options=None):
        """Build GR2 options string for divine.exe"""
        options = self.default_gr2_options.copy()
        
        if custom_options:
            options.update(custom_options)
        
        # Only include options that are set to True
        enabled_options = [key for key, value in options.items() if value]
        
        return enabled_options if enabled_options else None
    
    def get_conversion_presets(self):
        """Get predefined conversion presets for common use cases"""
        return {
            'bg3_export': {
                'description': 'Export GR2 models from BG3 for editing',
                'input_format': 'gr2',
                'output_format': 'dae',
                'gr2_options': {
                    'export-normals': True,
                    'export-tangents': True,
                    'export-uvs': True,
                    'export-colors': True,
                    'flip-uvs': True,
                    'y-up-skeletons': True
                }
            },
            'bg3_import': {
                'description': 'Import edited models back to BG3 format',
                'input_format': 'dae',
                'output_format': 'gr2',
                'gr2_options': {
                    'deduplicate-vertices': True,
                    'compact-tris': True,
                    'build-dummy-skeleton': True,
                    'apply-basis-transforms': True
                }
            },
            'modern_export': {
                'description': 'Export to modern GLTF format',
                'input_format': 'gr2',
                'output_format': 'gltf',
                'gr2_options': {
                    'export-normals': True,
                    'export-tangents': True,
                    'export-uvs': True,
                    'export-colors': True
                }
            }
        }
    
    def convert_with_preset(self, source_file, output_file, preset_name, progress_callback=None):
        """Convert using a predefined preset"""
        presets = self.get_conversion_presets()
        
        if preset_name not in presets:
            return OperationResult.error_result(
                f"Unknown preset: {preset_name}. Available: {', '.join(presets.keys())}",
                operation_type="convert_with_preset"
            )
        
        preset = presets[preset_name]
        
        return self.convert_model(
            source_file, output_file,
            input_format=preset['input_format'],
            output_format=preset['output_format'],
            gr2_options=preset.get('gr2_options'),
            progress_callback=progress_callback
        )