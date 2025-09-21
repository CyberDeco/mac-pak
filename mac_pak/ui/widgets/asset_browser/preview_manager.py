#!/usr/bin/env python3
"""
BG3 File Preview System - Standalone file analysis and preview generator
"""

import os
import xml.etree.ElementTree as ET
import tempfile
import threading
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTextEdit
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt

from ...threads.file_preview import FilePreviewThread

class PreviewWidget(QWidget):
    """Widget for displaying file previews with Mac styling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.preview_thread = None
    
    def setup_ui(self):
        """Setup preview widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setFont(QFont("SF Pro Text", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.file_label)
        
        header_layout.addStretch()
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(4)  # Thin Mac-style progress
        header_layout.addWidget(self.progress_bar)
        
        layout.addLayout(header_layout)
        
        # Thumbnail area
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setMinimumHeight(150)  # Reduce thumbnail space
        self.thumbnail_label.setMaximumHeight(180)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: #f8f8f8;
            }
        """)
        layout.addWidget(self.thumbnail_label)
        
        # Content area
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setFont(QFont("SF Mono", 11))  # Mac monospace
        self.content_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: white;
                padding: 8px;
            }
        """)
        layout.addWidget(self.content_text)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
    
    def preview_file(self, file_path, preview_manager):
        """Preview a file with progress indication"""
        if not file_path or not os.path.isfile(file_path):
            self.clear_preview()
            return
        
        # Cancel any existing preview
        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.cancel()
            self.preview_thread.quit()
            self.preview_thread.wait(1000)
        
        # Update header
        self.file_label.setText(os.path.basename(file_path))
        
        # Check if file is supported
        if not preview_manager.is_supported(file_path):
            self.show_unsupported_file(file_path, preview_manager)
            return
        
        # Check if this file might need progress indication
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.lsf', '.lsbs', '.lsbc', '.lsfx']:
            self.show_progress(True)
        
        # Start preview thread
        self.preview_thread = FilePreviewThread(preview_manager, file_path)
        self.preview_thread.preview_ready.connect(self.display_preview)
        self.preview_thread.progress_updated.connect(self.update_progress)
        self.preview_thread.start()
    
    def show_unsupported_file(self, file_path, preview_manager):
        """Show info for unsupported file types"""
        file_size = os.path.getsize(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        content = f"File: {os.path.basename(file_path)}\n"
        content += f"Size: {file_size:,} bytes\n"
        content += f"Type: {file_ext}\n"
        content += "-" * 50 + "\n\n"
        content += f"Unsupported file type: {file_ext}\n"
        content += "Supported types: " + ", ".join(preview_manager.get_supported_extensions())
        
        self.content_text.setPlainText(content)
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("📄\nUnsupported File")
        self.show_progress(False)
    
    def display_preview(self, preview_data):
        """Display preview data from thread with enhanced image support"""
        self.show_progress(False)
        
        # Display content
        self.content_text.setPlainText(preview_data.get('content', ''))
        
        # Enhanced thumbnail handling
        if preview_data.get('thumbnail'):
            thumbnail = preview_data['thumbnail']
            
            # Try to display actual image thumbnail
            if isinstance(thumbnail, QPixmap):
                # Scale to fit thumbnail area
                scaled_pixmap = thumbnail.scaled(
                    self.thumbnail_label.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.thumbnail_label.setPixmap(scaled_pixmap)
                return
            else:
                self.thumbnail_label.setText("🖼️\nImage Preview")
        else:
            # Check if file is an image type
            file_path = getattr(self, '_current_file_path', '')
            if file_path and any(file_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp']):
                try:
                    # Load standard image formats directly
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(
                            self.thumbnail_label.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        self.thumbnail_label.setPixmap(scaled_pixmap)
                    else:
                        self.thumbnail_label.setText("📄\nText Preview")
                except:
                    self.thumbnail_label.setText("📄\nText Preview")
            else:
                self.thumbnail_label.clear()
                self.thumbnail_label.setText("📄\nText Preview")
    
    def show_progress(self, show):
        """Show or hide progress indicators"""
        self.progress_bar.setVisible(show)
        self.progress_label.setVisible(show)
        
        if not show:
            self.progress_bar.setValue(0)
            self.progress_label.setText("")
    
    def update_progress(self, percentage, message):
        """Update progress display"""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
    
    def clear_preview(self):
        """Clear the preview display"""
        self.file_label.setText("No file selected")
        self.content_text.clear()
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("Select a file to preview")
        self.show_progress(False)

class FilePreviewTools:
    """Standalone file preview system for BG3 assets"""
    
    def __init__(self, wine_wrapper=None, parser=None):
        """
        Initialize the preview system
        
        Args:
            wine_wrapper: Optional BG3Tool instance for file conversions
            parser: Optional UniversalBG3Parser instance for parsing
        """
        self.wine_wrapper = wine_wrapper
        self.parser = parser
    
    def preview_file(self, file_path):
        """
        Generate preview content for a file
        
        Args:
            file_path: Path to the file to preview
            
        Returns:
            dict: Preview data containing 'content', 'thumbnail', and 'metadata'
        """
        try:
            # Get basic file info
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            preview_data = {
                'filename': os.path.basename(file_path),
                'size': file_size,
                'extension': file_ext,
                'content': '',
                'thumbnail': None,
                'metadata': {},
                'error': None
            }
            
            # Generate basic header
            preview_content = f"File: {os.path.basename(file_path)}\n"
            preview_content += f"Size: {file_size:,} bytes\n"
            preview_content += f"Type: {file_ext}\n"
            preview_content += "-" * 50 + "\n\n"
            
            # Route to appropriate preview method
            if file_ext in ['.lsx', '.lsj', '.xml', '.txt', '.json']:
                preview_content += self._preview_text_file(file_path, file_size)
                preview_content += self._analyze_bg3_structure(file_path, file_ext)
            elif file_ext == '.gr2':
                preview_content += self._preview_gr2_file(file_path, file_size)
            elif file_ext == '.bshd':
                preview_content += self._preview_bshd_file(file_path, file_size)
            elif file_ext == '.shd':
                preview_content += self._preview_shd_file(file_path, file_size)
            elif file_ext in ['.lsbs', '.lsbc']:
                preview_content += self._preview_larian_binary(file_path, file_ext)
            elif file_ext == '.lsf':
                preview_content += self._preview_lsf_file(file_path)
            elif file_ext == '.lsfx':
                preview_content += self._preview_lsfx_file(file_path)
            elif file_ext == '.dds' or 'DDS' in file_path:
                preview_content += self._preview_dds_file(file_path)
                preview_data['thumbnail'] = self._generate_dds_thumbnail(file_path)
            elif file_ext == '.loca':
                preview_content += self._preview_loca_file(file_path)
            else:
                preview_content += f"Binary file - cannot preview\nExtension: {file_ext}"
            
            preview_data['content'] = preview_content
            return preview_data
            
        except Exception as e:
            return {
                'filename': os.path.basename(file_path) if file_path else 'Unknown',
                'size': 0,
                'extension': '',
                'content': f"Error previewing file: {e}",
                'thumbnail': None,
                'metadata': {},
                'error': str(e)
            }
    
    def _preview_text_file(self, file_path, file_size):
        """Preview text-based files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2000)  # First 2KB
                if file_size > 2000:
                    content += f"\n\n... ({file_size-2000:,} more bytes)"
                return content
        except Exception as e:
            return f"Error reading text file: {e}\n"
    
    def _analyze_bg3_structure(self, file_path, file_ext):
        """Analyze BG3 file structure"""
        if not self.parser or file_ext not in ['.lsx', '.lsj', '.lsf', '.lsfx']:
            return ""
        
        try:
            parsed_data = self.parser.parse_file(file_path)
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
    
    def _preview_gr2_file(self, file_path, file_size):
        """Preview GR2 (Granny 3D) files"""
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
            
            content += "\nNote: GR2 files contain 3D models. Use Blender with GR2 import plugins for editing.\n"
            return content
            
        except Exception as e:
            return f"Error analyzing GR2 file: {e}\n"
    
    def _analyze_gr2_structure(self, file_path):
        """Analyze GR2 file structure"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(4096)
                
            analysis = {
                'meshes': 0,
                'skeletons': 0, 
                'animations': 0,
                'materials': 0,
                'bones': 0
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
    
    def _preview_bshd_file(self, file_path, file_size):
        """Preview BSHD (Binary Shader) files"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(64)
                
            content = "Binary Shader File (BSHD)\n\n"
            
            if header.startswith(b'BSHD'):
                content += "✅ Valid BSHD file\n"
                
                # Try to extract basic info from header
                if len(header) > 4:
                    header_str = header[4:32].decode('ascii', errors='ignore')
                    clean_header = ''.join(c if c.isprintable() else '.' for c in header_str)
                    content += f"Header info: {clean_header}\n"
                
                # Analyze filename for shader properties
                filename = os.path.basename(file_path)
                
                # Shader stage detection
                if '_VT_' in filename or filename.endswith('_VT.bshd'):
                    content += "Stage: Vertex shader\n"
                elif '_PS_' in filename or filename.endswith('_PS.bshd'):
                    content += "Stage: Pixel shader\n"
                elif '_GS_' in filename:
                    content += "Stage: Geometry shader\n"
                elif '_CS_' in filename:
                    content += "Stage: Compute shader\n"
                
                # API detection
                if 'DX12' in filename:
                    content += "Target API: DirectX 12\n"
                elif 'Vulkan' in filename:
                    content += "Target API: Vulkan\n"
                elif 'DX11' in filename:
                    content += "Target API: DirectX 11\n"
                
                # Feature detection
                if 'AlphaTested' in filename:
                    content += "Features: Alpha testing\n"
                if 'SSS' in filename:
                    content += "Features: Subsurface scattering\n"
                if 'Fresnel' in filename:
                    content += "Features: Fresnel effects\n"
                    
            else:
                content += "⚠️ Invalid BSHD header\n"
                
            content += f"\nFile size: {file_size:,} bytes\n"
            content += "\nNote: BSHD files are compiled shaders. Use shader tools for editing.\n"
            
            return content
            
        except Exception as e:
            return f"Error analyzing BSHD file: {e}\n"
    
    def _preview_shd_file(self, file_path, file_size):
        """Preview SHD (Shader) files"""
        try:
            # Check if it's text or binary
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(512)
                
                # Text-based shader file
                result = "Shader File (SHD)\n\n"
                result += content[:500]
                if file_size > 500:
                    result += f"\n\n... ({file_size-500:,} more bytes)"
                    
                # Analyze shader content
                full_content = content
                if file_size > 512:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        full_content = f.read()
                
                result += f"\n\n{'='*30}\nSHADER INFO:\n{'='*30}\n"
                
                lines = full_content.split('\n')
                result += f"Lines of code: {len(lines)}\n"

                # HLSL-specific analysis
                if 'HLSL' in full_content:
                    result += "Language: HLSL (High-Level Shader Language)\n"
                
                # Look for specific HLSL features
                if 'cbuffer' in full_content:
                    result += "Uses constant buffers\n"
                if 'SamplerState' in full_content:
                    result += "Uses texture samplers\n"
                if 'StructuredBuffer' in full_content:
                    result += "Uses structured buffers\n"
                
                # Count shader stages
                vertex_functions = full_content.count('VertexShader') + full_content.count('VS_')
                pixel_functions = full_content.count('PixelShader') + full_content.count('PS_')
                if vertex_functions > 0:
                    result += f"Vertex shader functions: {vertex_functions}\n"
                if pixel_functions > 0:
                    result += f"Pixel shader functions: {pixel_functions}\n"
                
                # Look for common BG3 shader features
                if 'Fresnel' in full_content:
                    result += "Features: Fresnel effects\n"
                if 'AlphaTested' in full_content or 'AlphaTest' in full_content:
                    result += "Features: Alpha testing\n"
                if 'SSS' in full_content or 'SubSurface' in full_content:
                    result += "Features: Subsurface scattering\n"
                
                # Look for shader elements
                if 'vertex' in full_content.lower():
                    result += "Contains vertex shader code\n"
                if 'pixel' in full_content.lower() or 'fragment' in full_content.lower():
                    result += "Contains pixel/fragment shader code\n"
                if 'uniform' in full_content:
                    result += "Uses uniform variables\n"
                if 'texture' in full_content.lower():
                    result += "Uses textures\n"
                
                return result
                    
            except UnicodeDecodeError:
                # Binary shader file
                with open(file_path, 'rb') as f:
                    header = f.read(64)
                    
                result = "Binary Shader File (SHD)\n\n"
                
                # Look for common binary shader signatures
                if header.startswith(b'DXBC') or header.startswith(b'DX'):
                    result += "DirectX bytecode detected\n"
                elif header.startswith(b'SPIR') or b'SPIR-V' in header:
                    result += "SPIR-V bytecode detected\n"
                else:
                    result += "Unknown shader format\n"
                
                # Extract readable strings
                readable_chars = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in header)
                result += f"Header: {readable_chars[:40]}...\n"
                
                result += f"File size: {file_size:,} bytes\n"
                result += "\nNote: Binary shader file - use shader tools for analysis.\n"
                
                return result
                
        except Exception as e:
            return f"Error analyzing SHD file: {e}\n"
    
    def _preview_larian_binary(self, file_path, file_ext):
        """Preview LSBS/LSBC files"""
        try:
            # Try conversion first if we have the tools
            if self.wine_wrapper:
                temp_lsx = None
                try:
                    with tempfile.NamedTemporaryFile(suffix='.lsx', delete=False) as tmp:
                        temp_lsx = tmp.name
                    
                    # Attempt conversion
                    if file_ext == '.lsbs':
                        conversion_success = self._try_lsbs_conversion(file_path, temp_lsx)
                    else:  # .lsbc
                        conversion_success = self._try_lsbc_conversion(file_path, temp_lsx)
                    
                    if conversion_success and os.path.exists(temp_lsx) and self.parser:
                        # Parse converted file
                        parsed_data = self.parser.parse_lsx_file(temp_lsx)
                        
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
                            
                            return result
                        
                finally:
                    # Clean up temp file
                    if temp_lsx and os.path.exists(temp_lsx):
                        try:
                            os.remove(temp_lsx)
                        except:
                            pass
            
            # Fallback to binary analysis
            return self._analyze_larian_binary(file_path, file_ext)
            
        except Exception as e:
            return f"Error analyzing {file_ext.upper()} file: {e}\n"
    
    def _preview_lsf_file(self, file_path):
        """Preview LSF files with conversion"""
        if not self.wine_wrapper:
            return self._analyze_larian_binary(file_path, '.lsf')
        
        temp_lsx = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.lsx', delete=False) as tmp:
                temp_lsx = tmp.name
            
            # Convert LSF to LSX
            success = self.wine_wrapper.convert_lsf_to_lsx(file_path, temp_lsx)
            
            if success and os.path.exists(temp_lsx) and self.parser:
                parsed_data = self.parser.parse_lsx_file(temp_lsx)
                
                if parsed_data and isinstance(parsed_data, dict):
                    result = "LSF Binary File (converted)\n\n"
                    result += f"Format: LSF\n"
                    result += f"Converted size: {os.path.getsize(temp_lsx):,} bytes\n"
                    
                    if 'regions' in parsed_data:
                        regions = parsed_data['regions']
                        if isinstance(regions, list):
                            result += f"Regions: {len(regions)}\n"
                            for region in regions[:3]:
                                if isinstance(region, dict):
                                    region_name = region.get('name') or region.get('id', 'unknown')
                                    node_count = len(region.get('nodes', []))
                                    result += f"  • {region_name}: {node_count} nodes\n"
                    
                    return result
            
            return self._analyze_larian_binary(file_path, '.lsf')
            
        finally:
            if temp_lsx and os.path.exists(temp_lsx):
                try:
                    os.remove(temp_lsx)
                except:
                    pass
    
    def _preview_lsfx_file(self, file_path):
        """Preview LSFX files with conversion"""
        if not self.wine_wrapper:
            return self._analyze_larian_binary(file_path, '.lsfx')
        
        temp_lsx = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.lsx', delete=False) as tmp:
                temp_lsx = tmp.name
            
            # Convert LSFX to LSX
            success = self._try_lsfx_conversion(file_path, temp_lsx)
            
            if success and os.path.exists(temp_lsx) and self.parser:
                parsed_data = self.parser.parse_lsx_file(temp_lsx)
                
                if parsed_data and isinstance(parsed_data, dict):
                    result = "LSFX Binary File (converted)\n\n"
                    result += f"Format: LSFX\n"
                    result += f"Converted size: {os.path.getsize(temp_lsx):,} bytes\n"
                    
                    if 'regions' in parsed_data:
                        regions = parsed_data['regions']
                        if isinstance(regions, list):
                            result += f"Regions: {len(regions)}\n"
                            for region in regions[:3]:
                                if isinstance(region, dict):
                                    region_name = region.get('name') or region.get('id', 'unknown')
                                    node_count = len(region.get('nodes', []))
                                    result += f"  • {region_name}: {node_count} nodes\n"
                    
                    return result
            
            return self._analyze_larian_binary(file_path, '.lsfx')
            
        finally:
            if temp_lsx and os.path.exists(temp_lsx):
                try:
                    os.remove(temp_lsx)
                except:
                    pass
    
    def _preview_dds_file(self, file_path):
        """Preview DDS texture files"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(128)
                
            content = "DirectDraw Surface (DDS) Texture\n\n"
            
            if header[:4] == b'DDS ':
                content += "Valid DDS file\n"
                
                # Extract dimensions
                if len(header) >= 20:
                    height = int.from_bytes(header[12:16], 'little')
                    width = int.from_bytes(header[16:20], 'little')
                    content += f"Dimensions: {width}x{height} pixels\n"
                
                # Extract mipmap info
                if len(header) >= 28:
                    mipmap_count = int.from_bytes(header[28:32], 'little')
                    if mipmap_count > 1:
                        content += f"Mipmaps: {mipmap_count} levels\n"
                    else:
                        content += "Mipmaps: None\n"
                
                # Get detailed format information
                format_info = self._parse_dds_format(header)
                content += format_info
                
            else:
                content += "Warning: Invalid DDS header\n"
                
            content += "\nNote: DDS files are compressed textures. Use image tools for viewing.\n"
            
            return content
            
        except Exception as e:
            return f"Error analyzing DDS file: {e}\n"
    
    def _parse_dds_format(self, header):
        """Extract detailed DDS format information"""
        if len(header) >= 84:  # DDS_PIXELFORMAT starts at offset 76
            pf_flags = int.from_bytes(header[80:84], 'little')
            fourcc = header[84:88]
            
            formats = {
                b'DXT1': 'BC1 (DXT1) - 4bpp',
                b'DXT3': 'BC2 (DXT3) - 8bpp', 
                b'DXT5': 'BC3 (DXT5) - 8bpp',
                b'BC7\x00': 'BC7 - 8bpp (high quality)',
                b'ATI2': 'BC5 (3Dc) - Normal maps',
                b'ATI1': 'BC4 (ATI1) - Single channel',
                b'DX10': 'DX10 format (see extended header)'
            }
            
            format_name = formats.get(fourcc, f"Unknown fourCC: {fourcc}")
            
            # Check for uncompressed formats
            if pf_flags & 0x40:  # DDPF_RGB
                rgb_bit_count = int.from_bytes(header[88:92], 'little') if len(header) >= 92 else 0
                format_name = f"Uncompressed RGB - {rgb_bit_count}bpp"
            elif pf_flags & 0x20000:  # DDPF_LUMINANCE
                format_name = "Luminance format"
            
            return f"Format: {format_name}\n"
        return "Format: Unknown\n"

    def _preview_loca_file(self, file_path):
        """Preview .loca files"""
        try:
            content = "Localization File (.loca)\n\n"
            
            # Try using the LocaManager for parsing
            from loca_manager import LocaManager
            loca_manager = LocaManager(self.wine_wrapper, None)
            
            parsed_data = loca_manager.parse_loca_file(file_path)
            
            if parsed_data and parsed_data.get('entries'):
                entries = parsed_data['entries']
                content += f"Successfully parsed!\n"
                content += f"Method: {parsed_data.get('format', 'unknown')}\n"
                content += f"Total entries: {len(entries)}\n\n"
                
                if entries:
                    content += "Sample entries:\n"
                    content += "-" * 50 + "\n"
                    
                    for i, entry in enumerate(entries[:5]):
                        content += f"#{i+1}\n"
                        content += f"Handle: {entry['handle']}\n"
                        if entry['text']:
                            preview_text = entry['text'][:150]
                            if len(entry['text']) > 150:
                                preview_text += "..."
                            content += f"Text: {preview_text}\n"
                        content += "\n"
                    
                    if len(entries) > 5:
                        content += f"... and {len(entries) - 5} more entries\n"
            else:
                content += "Could not parse .loca file.\n"
                content += self._analyze_loca_binary_fallback(file_path)
            
            return content
            
        except Exception as e:
            return f"Error previewing .loca file: {e}\n"
    
    def _analyze_loca_binary_fallback(self, file_path):
        """Fallback binary analysis when divine.exe isn't available"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(512)  # Read first 512 bytes
            
            content = "\nBinary Analysis:\n"
            content += f"File size: {os.path.getsize(file_path):,} bytes\n"
            
            # Look for text patterns
            if b'content' in data.lower():
                content += "Contains 'content' - likely localization data\n"
            
            if b'handle' in data.lower():
                content += "Contains 'handle' - likely UUID references\n"
            
            # Check for compression
            if data.startswith(b'\x1f\x8b'):
                content += "Format: GZIP compressed\n"
            elif data.startswith(b'PK'):
                content += "Format: ZIP compressed\n"
            elif data.startswith(b'LSOF'):
                content += "Format: Larian binary (LSOF)\n"
            else:
                content += "Format: Unknown binary\n"
            
            # Show readable strings
            readable_chars = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[:100])
            content += f"Header preview: {readable_chars}\n"
            
            return content
            
        except Exception as e:
            return f"\nBinary analysis failed: {e}\n"
    
    def _analyze_larian_binary(self, file_path, file_ext):
        """Basic binary analysis for unknown Larian formats"""
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
            
            content += f"\nNote: {file_ext.upper()} files require divine.exe conversion for full analysis.\n"
            
            return content
            
        except Exception as e:
            return f"Error analyzing {file_ext.upper()} file: {e}\n"
    
    def _generate_dds_thumbnail(self, file_path, max_size=(180, 180)):
        """Generate DDS thumbnail using multiple methods for PyQt6"""
        
        # Method 1: Try PIL with DDS support first (most reliable for DDS)
        try:
            from PIL import Image
            import io
            
            with Image.open(file_path) as img:
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Convert PIL Image to QPixmap
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                pixmap = QPixmap()
                pixmap.loadFromData(img_buffer.getvalue())
                return pixmap
                
        except Exception as e:
            print(f"PIL DDS thumbnail generation failed: {e}")
        
        # Method 2: Try Wand/ImageMagick as fallback
        try:
            from wand.image import Image as WandImage
            import io
            
            with WandImage(filename=file_path) as img:
                img.thumbnail(max_size[0], max_size[1])
                img_buffer = io.BytesIO()
                img.format = 'png'
                img.save(img_buffer)
                img_buffer.seek(0)
                
                pixmap = QPixmap()
                pixmap.loadFromData(img_buffer.getvalue())
                return pixmap
                
        except Exception as e:
            print(f"Wand thumbnail generation failed: {e}")
        
        # Method 3: Generate informative placeholder when both methods fail
        return self._create_dds_info_placeholder(file_path, max_size)

    def _create_dds_info_placeholder(self, file_path, canvas_size=(180, 180)):
        """Create an informative placeholder when thumbnail generation fails"""
        from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor
        from PyQt6.QtCore import Qt
        
        try:
            # Create a QPixmap
            pixmap = QPixmap(canvas_size[0], canvas_size[1])
            pixmap.fill(QColor(220, 220, 220))  # Light gray background
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Get DDS info
            with open(file_path, 'rb') as f:
                header = f.read(128)
            
            if header[:4] == b'DDS ' and len(header) >= 20:
                width = int.from_bytes(header[16:20], 'little')
                height = int.from_bytes(header[12:16], 'little')
                
                # Draw border
                painter.setPen(QColor(0, 0, 0))
                painter.drawRect(5, 5, canvas_size[0]-10, canvas_size[1]-10)
                
                # Set up fonts
                font = QFont("Arial", 12)
                small_font = QFont("Arial", 10)
                
                center_x = canvas_size[0] // 2
                
                # Draw text
                painter.setFont(font)
                painter.drawText(center_x - 50, 30, 100, 20, Qt.AlignmentFlag.AlignCenter, "DDS TEXTURE")
                
                painter.setFont(small_font)
                painter.setPen(QColor(0, 0, 255))
                painter.drawText(center_x - 50, 50, 100, 20, Qt.AlignmentFlag.AlignCenter, f"{width}x{height}")
                
                painter.setPen(QColor(255, 0, 0))
                painter.drawText(center_x - 70, 70, 140, 20, Qt.AlignmentFlag.AlignCenter, "Preview unavailable")
                
                # Determine texture type
                filename = os.path.basename(file_path).lower()
                if '_nm' in filename:
                    texture_type = "Normal Map"
                elif '_d' in filename or '_diffuse' in filename:
                    texture_type = "Diffuse"
                elif '_spec' in filename:
                    texture_type = "Specular"
                elif '_gm' in filename:
                    texture_type = "Gradient Map"
                else:
                    texture_type = "Unknown Type"
                
                painter.setPen(QColor(0, 0, 139))
                painter.drawText(center_x - 60, 90, 120, 20, Qt.AlignmentFlag.AlignCenter, texture_type)
            
            painter.end()
            return pixmap
            
        except Exception as e:
            print(f"QPixmap placeholder creation failed: {e}")
            # Return a simple gray pixmap as last resort
            pixmap = QPixmap(canvas_size[0], canvas_size[1])
            pixmap.fill(QColor(200, 200, 200))
            return pixmap
    
    # Conversion helper methods
    def _try_lsbs_conversion(self, lsbs_path, output_path):
        """Try to convert LSBS file using divine.exe"""
        if not self.wine_wrapper:
            return False
        
        try:
            success = self.wine_wrapper.convert_lsf_to_lsx(lsbs_path, output_path)
            return success
        except:
            return False
    
    def _try_lsbc_conversion(self, lsbc_path, output_path):
        """Try to convert LSBC file using divine.exe"""
        if not self.wine_wrapper:
            return False
        
        try:
            success = self.wine_wrapper.convert_lsf_to_lsx(lsbc_path, output_path)
            return success
        except:
            return False

    def _try_lsfx_conversion(self, lsfx_path, output_path):
        """Try to convert LSFX file using divine.exe"""
        if not self.wine_wrapper:
            return False
        
        try:
            success = self.wine_wrapper.convert_lsf_to_lsx(lsfx_path, output_path)
            return success
        except:
            return False
    
    def preview_file_with_progress(self, file_path, progress_callback=None):
        """
        Preview file with progress updates for slow operations
        
        Args:
            file_path: Path to the file to preview
            progress_callback: Optional callback function(progress_percent, message)
            
        Returns:
            dict: Preview data
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Check if this file type needs progress dialog
        if file_ext in ['.lsf', '.lsbs', '.lsbc', '.lsfx']:
            return self._preview_with_conversion_progress(file_path, progress_callback)
        else:
            if progress_callback:
                progress_callback(0, "Starting preview...")
                progress_callback(50, "Analyzing file...")
            
            result = self.preview_file(file_path)
            
            if progress_callback:
                progress_callback(100, "Preview complete!")
            
            return result
    
    def _preview_with_conversion_progress(self, file_path, progress_callback):
        """Preview file with progress updates for conversion operations"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if progress_callback:
                progress_callback(10, f"Preparing {file_ext.upper()} conversion...")
            
            temp_lsx = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.lsx', delete=False) as tmp:
                    temp_lsx = tmp.name
                
                if progress_callback:
                    progress_callback(20, "Starting conversion...")
                
                # Do the actual conversion
                if file_ext == '.lsf':
                    success = self.wine_wrapper.convert_lsf_to_lsx(file_path, temp_lsx) if self.wine_wrapper else False
                elif file_ext == '.lsfx':
                    success = self._try_lsfx_conversion(file_path, temp_lsx)
                elif file_ext in ['.lsbs', '.lsbc']:
                    if file_ext == '.lsbs':
                        success = self._try_lsbs_conversion(file_path, temp_lsx)
                    else:
                        success = self._try_lsbc_conversion(file_path, temp_lsx)
                
                if progress_callback:
                    progress_callback(70, "Processing converted file...")
                
                if success and os.path.exists(temp_lsx):
                    # Read the converted LSX content
                    converted_content = None
                    try:
                        with open(temp_lsx, 'r', encoding='utf-8', errors='ignore') as f:
                            converted_content = f.read()
                    except Exception as e:
                        print(f"Warning: Could not read converted content: {e}")
                    
                    # Parse the converted file if we have a parser
                    parsed_data = None
                    if self.parser:
                        parsed_data = self.parser.parse_lsx_file(temp_lsx)
                    
                    if progress_callback:
                        progress_callback(90, "Generating preview...")
                    
                    # Generate preview with converted data
                    preview_data = self._generate_conversion_preview(file_path, parsed_data, file_ext, converted_content)
                    
                    if progress_callback:
                        progress_callback(100, "Complete!")
                    
                    return preview_data
                else:
                    # Fallback to basic binary analysis
                    if progress_callback:
                        progress_callback(90, "Using fallback analysis...")
                    
                    result = self.preview_file(file_path)
                    
                    if progress_callback:
                        progress_callback(100, "Complete!")
                    
                    return result
                
            finally:
                # Clean up temp file
                if temp_lsx and os.path.exists(temp_lsx):
                    try:
                        os.remove(temp_lsx)
                    except:
                        pass
                
        except Exception as e:
            error_result = {
                'filename': os.path.basename(file_path),
                'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'extension': file_ext,
                'content': f"Error converting {file_ext.upper()}: {e}",
                'thumbnail': None,
                'metadata': {},
                'error': str(e)
            }
            
            if progress_callback:
                progress_callback(100, f"Error: {e}")
            
            return error_result
    
    def _generate_conversion_preview(self, file_path, parsed_data, file_ext, converted_content=None):
        """Generate preview content from converted file data"""
        file_size = os.path.getsize(file_path)
        
        preview_content = f"File: {os.path.basename(file_path)}\n"
        preview_content += f"Size: {file_size:,} bytes\n"
        preview_content += f"Type: {file_ext}\n"
        preview_content += "-" * 50 + "\n\n"
        
        if parsed_data and isinstance(parsed_data, dict):
            preview_content += f"{file_ext.upper()} Binary File (converted)\n\n"
            preview_content += f"={'='*30}\nBG3 FILE INFO:\n{'='*30}\n"
            preview_content += f"Format: {parsed_data.get('format', file_ext).upper()}\n"
            
            if 'version' in parsed_data and parsed_data['version'] != 'unknown':
                preview_content += f"Version: {parsed_data['version']}\n"
            
            if 'regions' in parsed_data:
                regions = parsed_data['regions']
                if isinstance(regions, list):
                    preview_content += f"Regions: {len(regions)}\n"
                    for region in regions[:3]:
                        if isinstance(region, dict):
                            region_name = region.get('name') or region.get('id', 'unknown')
                            node_count = len(region.get('nodes', []))
                            preview_content += f"  • {region_name}: {node_count} nodes\n"
            
            total_nodes = sum(len(region.get('nodes', [])) for region in parsed_data.get('regions', []))
            if total_nodes > 0:
                if total_nodes < 10:
                    complexity = "Simple"
                elif total_nodes < 100:
                    complexity = "Moderate"
                else:
                    complexity = "Complex"
                preview_content += f"Complexity: {complexity} ({total_nodes} total nodes)\n"
            
            # Add the converted LSX content if available
            if converted_content:
                preview_content += f"\n{'='*30}\nCONVERTED LSX CONTENT:\n{'='*30}\n"
                # Show first 2000 characters of converted content
                if len(converted_content) > 2000:
                    preview_content += converted_content[:2000]
                    preview_content += f"\n\n... ({len(converted_content)-2000:,} more characters)"
                else:
                    preview_content += converted_content
        else:
            preview_content += f"Could not parse {file_ext.upper()} file\n"
        
        return {
            'filename': os.path.basename(file_path),
            'size': file_size,
            'extension': file_ext,
            'content': preview_content,
            'thumbnail': None,
            'metadata': {'converted': True, 'format': file_ext, 'has_content': bool(converted_content)},
            'error': None
        }

# Example usage and utility functions
class FilePreviewManager:
    """Manager class for handling multiple file previews"""
    
    def __init__(self, wine_wrapper=None, parser=None):
        self.preview_system = FilePreviewTools(wine_wrapper, parser)
        self.cache = {}
        self.cache_size_limit = 100
    
    def get_preview(self, file_path, use_cache=True, progress_callback=None):
        """Get file preview with optional caching"""
        if use_cache and file_path in self.cache:
            return self.cache[file_path]
        
        # Generate preview
        if progress_callback:
            preview_data = self.preview_system.preview_file_with_progress(file_path, progress_callback)
        else:
            preview_data = self.preview_system.preview_file(file_path)
        
        # Cache the result if caching is enabled
        if use_cache:
            # Simple cache size management
            if len(self.cache) >= self.cache_size_limit:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
            
            self.cache[file_path] = preview_data
        
        return preview_data
    
    def clear_cache(self):
        """Clear the preview cache"""
        self.cache.clear()

    def get_supported_extensions(self):
        """Get list of supported file extensions"""
        return [
            '.lsx', '.lsj', '.xml', '.txt', '.json',  # Text files
            '.lsf', '.lsfx', '.lsbs', '.lsbc',        # Binary Larian formats
            '.loca',                                  # Localization files
            '.gr2',                                   # Granny 3D models
            '.bshd', '.shd',                         # Shader files
            '.dds'                                   # DirectDraw Surface textures
        ]
    
    def is_supported(self, file_path):
        """Check if a file is supported for preview"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.get_supported_extensions()

# Standalone utility functions
def preview_file_quick(file_path, wine_wrapper=None, parser=None):
    """Quick file preview without manager overhead"""
    preview_system = FilePreviewTools(wine_wrapper, parser)
    return preview_system.preview_file(file_path)

def get_file_icon(filename):
    """Get appropriate icon for file type"""
    ext = os.path.splitext(filename)[1].lower()
    
    icons = {
        '.lsx': '📄',
        '.lsf': '🔒',
        '.xml': '📄',
        '.txt': '📝',
        '.dds': '🖼️',
        '.gr2': '🎭',
        '.json': '📋', 
        '.bshd': '🔧',
        '.shd': '⚙️',
        '.lsbs': '📦',
        '.lsbc': '📦',
        '.lsfx': '🔈',
        '.loca': '🗄️',
    }
    
    return icons.get(ext, '📄')