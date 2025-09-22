#!/usr/bin/env python3
"""
Shader format handler for BG3 preview system
Handles: .bshd, .shd shader files
"""

import os
from typing import Dict

from .base_handler import FormatHandler

class ShaderFormatHandler(FormatHandler):
    """Handler for shader files (.bshd, .shd)"""
    
    def can_handle(self, file_ext: str) -> bool:
        """Check if this handler supports the file extension"""
        return file_ext.lower() in ['.bshd', '.shd']
    
    def get_supported_extensions(self):
        """Return list of supported extensions"""
        return ['.bshd', '.shd']
    
    def get_file_icon(self, file_ext: str) -> str:
        """Get appropriate icon for file type"""
        icons = {
            '.bshd': '🔧',
            '.shd': '⚙️'
        }
        return icons.get(file_ext.lower(), '🔧')
    
    def preview(self, file_path: str, **kwargs) -> Dict:
        """Generate preview for shader files"""
        preview_data = self._create_base_preview_data(file_path)
        
        if preview_data.get('error'):
            return preview_data
        
        try:
            file_ext = preview_data['extension']
            
            # Generate header
            content = self._create_header_content(file_path)
            
            # Route to appropriate handler
            if file_ext == '.bshd':
                shader_analysis = self._analyze_bshd_file(file_path, preview_data['size'])
            else:  # .shd
                shader_analysis = self._analyze_shd_file(file_path, preview_data['size'])
            
            content += shader_analysis
            
            preview_data['content'] = content
            return preview_data
            
        except Exception as e:
            preview_data['error'] = str(e)
            preview_data['content'] = f"Error previewing shader file: {e}"
            return preview_data
    
    def _analyze_bshd_file(self, file_path: str, file_size: int) -> str:
        """Analyze BSHD (Binary Shader) files"""
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
                content += self._analyze_shader_filename(filename)
                
            else:
                content += "⚠️ Invalid BSHD header\n"
                
            content += f"\nFile size: {file_size:,} bytes\n"
            content += "\nNote: BSHD files are compiled shaders. Use shader tools for editing.\n"
            
            return content
            
        except Exception as e:
            return f"Error analyzing BSHD file: {e}\n"
    
    def _analyze_shd_file(self, file_path: str, file_size: int) -> str:
        """Analyze SHD (Shader) files"""
        try:
            # Check if it's text or binary
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content_preview = f.read(512)
                
                # Text-based shader file
                result = "Shader File (SHD)\n\n"
                result += content_preview[:500]
                if file_size > 500:
                    result += f"\n\n... ({file_size-500:,} more bytes)"
                    
                # Analyze shader content
                full_content = content_preview
                if file_size > 512:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            full_content = f.read()
                    except:
                        full_content = content_preview
                
                result += f"\n\n{'='*30}\nSHADER INFO:\n{'='*30}\n"
                result += self._analyze_shader_content(full_content, file_path)
                
                return result
                    
            except UnicodeDecodeError:
                # Binary shader file
                with open(file_path, 'rb') as f:
                    header = f.read(64)
                    
                result = "Binary Shader File (SHD)\n\n"
                result += self._analyze_binary_shader(header, file_size, file_path)
                
                return result
                
        except Exception as e:
            return f"Error analyzing SHD file: {e}\n"
    
    def _analyze_shader_filename(self, filename: str) -> str:
        """Analyze filename for shader stage and properties"""
        analysis = ""
        
        # Shader stage detection
        if '_VT_' in filename or filename.endswith('_VT.bshd'):
            analysis += "Stage: Vertex shader\n"
        elif '_PS_' in filename or filename.endswith('_PS.bshd'):
            analysis += "Stage: Pixel shader\n"
        elif '_GS_' in filename:
            analysis += "Stage: Geometry shader\n"
        elif '_CS_' in filename:
            analysis += "Stage: Compute shader\n"
        
        # API detection
        if 'DX12' in filename:
            analysis += "Target API: DirectX 12\n"
        elif 'Vulkan' in filename:
            analysis += "Target API: Vulkan\n"
        elif 'DX11' in filename:
            analysis += "Target API: DirectX 11\n"
        
        # Feature detection
        features = []
        if 'AlphaTested' in filename:
            features.append("Alpha testing")
        if 'SSS' in filename:
            features.append("Subsurface scattering")
        if 'Fresnel' in filename:
            features.append("Fresnel effects")
        if 'PBR' in filename:
            features.append("Physically Based Rendering")
        if 'Shadow' in filename:
            features.append("Shadow mapping")
        
        if features:
            analysis += f"Features: {', '.join(features)}\n"
        
        return analysis
    
    def _analyze_shader_content(self, content: str, file_path: str) -> str:
        """Analyze text-based shader content"""
        analysis = ""
        
        lines = content.split('\n')
        analysis += f"Lines of code: {len(lines)}\n"

        # Language detection
        if 'HLSL' in content:
            analysis += "Language: HLSL (High-Level Shader Language)\n"
        elif 'GLSL' in content:
            analysis += "Language: GLSL (OpenGL Shading Language)\n"
        elif '#version' in content:
            analysis += "Language: GLSL\n"
        
        # HLSL-specific analysis
        hlsl_features = []
        if 'cbuffer' in content:
            hlsl_features.append("constant buffers")
        if 'SamplerState' in content:
            hlsl_features.append("texture samplers")
        if 'StructuredBuffer' in content:
            hlsl_features.append("structured buffers")
        if 'RWTexture' in content:
            hlsl_features.append("read-write textures")
        
        if hlsl_features:
            analysis += f"HLSL features: {', '.join(hlsl_features)}\n"
        
        # Count shader stages
        vertex_functions = content.count('VertexShader') + content.count('VS_') + content.count('vertex')
        pixel_functions = content.count('PixelShader') + content.count('PS_') + content.count('fragment')
        
        if vertex_functions > 0:
            analysis += f"Vertex shader functions: {vertex_functions}\n"
        if pixel_functions > 0:
            analysis += f"Pixel shader functions: {pixel_functions}\n"
        
        # Look for common BG3 shader features
        bg3_features = []
        if 'Fresnel' in content:
            bg3_features.append("Fresnel effects")
        if 'AlphaTested' in content or 'AlphaTest' in content:
            bg3_features.append("Alpha testing")
        if 'SSS' in content or 'SubSurface' in content:
            bg3_features.append("Subsurface scattering")
        if 'PBR' in content or 'MetallicRoughness' in content:
            bg3_features.append("PBR materials")
        
        if bg3_features:
            analysis += f"BG3 features: {', '.join(bg3_features)}\n"
        
        # General shader elements
        elements = []
        if 'uniform' in content.lower():
            elements.append("uniform variables")
        if 'texture' in content.lower():
            elements.append("textures")
        if 'light' in content.lower():
            elements.append("lighting")
        if 'shadow' in content.lower():
            elements.append("shadows")
        
        if elements:
            analysis += f"Elements: {', '.join(elements)}\n"
        
        return analysis
    
    def _analyze_binary_shader(self, header: bytes, file_size: int, file_path: str) -> str:
        """Analyze binary shader file"""
        analysis = ""
        
        # Look for common binary shader signatures
        if header.startswith(b'DXBC') or header.startswith(b'DX'):
            analysis += "DirectX bytecode detected\n"
        elif header.startswith(b'SPIR') or b'SPIR-V' in header:
            analysis += "SPIR-V bytecode detected\n"
        else:
            analysis += "Unknown shader format\n"
        
        # Extract readable strings
        readable_chars = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in header)
        analysis += f"Header: {readable_chars[:40]}...\n"
        
        # Analyze filename
        filename = os.path.basename(file_path)
        analysis += self._analyze_shader_filename(filename)
        
        analysis += f"File size: {file_size:,} bytes\n"
        analysis += "\nNote: Binary shader file - use shader tools for analysis.\n"
        
        return analysis