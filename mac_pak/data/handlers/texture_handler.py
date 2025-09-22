#!/usr/bin/env python3
"""
Texture format handler for BG3 preview system
Handles: .dds texture files
"""

import os
from typing import Dict, Optional

from .base_handler import FormatHandler

class TextureFormatHandler(FormatHandler):
    """Handler for texture files (.dds)"""
    
    def can_handle(self, file_ext: str) -> bool:
        """Check if this handler supports the file extension"""
        return file_ext.lower() == '.dds' or 'DDS' in file_ext
    
    def get_supported_extensions(self):
        """Return list of supported extensions"""
        return ['.dds']
    
    def get_file_icon(self, file_ext: str) -> str:
        """Get appropriate icon for file type"""
        return "🖼️"
    
    def preview(self, file_path: str, **kwargs) -> Dict:
        """Generate preview for DDS texture files"""
        preview_data = self._create_base_preview_data(file_path)
        
        if preview_data.get('error'):
            return preview_data
        
        try:
            # Generate header
            content = self._create_header_content(file_path)
            
            # Add DDS-specific analysis
            dds_analysis = self._analyze_dds_file(file_path)
            content += dds_analysis
            
            # Generate thumbnail
            thumbnail = self._generate_dds_thumbnail(file_path)
            
            preview_data['content'] = content
            preview_data['thumbnail'] = thumbnail
            return preview_data
            
        except Exception as e:
            preview_data['error'] = str(e)
            preview_data['content'] = f"Error previewing DDS file: {e}"
            return preview_data
    
    def _analyze_dds_file(self, file_path: str) -> str:
        """Analyze DDS texture file structure"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(128)
            
            file_size = os.path.getsize(file_path)
            content = "DirectDraw Surface (DDS) Texture\n\n"
            
            if header[:4] == b'DDS ':
                content += "✅ Valid DDS file\n"
                
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
                
                # Analyze filename for texture purpose
                filename = os.path.basename(file_path).lower()
                content += self._analyze_texture_purpose(filename)
                
            else:
                content += "⚠️ Invalid DDS header\n"
            
            content += f"\nFile size: {file_size:,} bytes\n"
            content += "\nNote: DDS files are compressed textures. Use image tools for viewing.\n"
            
            return content
            
        except Exception as e:
            return f"Error analyzing DDS file: {e}\n"
    
    def _parse_dds_format(self, header: bytes) -> str:
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
    
    def _analyze_texture_purpose(self, filename: str) -> str:
        """Analyze filename to determine texture purpose"""
        purpose_info = ""
        
        # Common BG3 texture naming conventions
        if '_nm' in filename or '_normal' in filename:
            purpose_info += "Purpose: Normal map\n"
        elif '_d' in filename or '_diffuse' in filename:
            purpose_info += "Purpose: Diffuse/Albedo\n"
        elif '_spec' in filename or '_specular' in filename:
            purpose_info += "Purpose: Specular map\n"
        elif '_rough' in filename or '_roughness' in filename:
            purpose_info += "Purpose: Roughness map\n"
        elif '_metal' in filename or '_metallic' in filename:
            purpose_info += "Purpose: Metallic map\n"
        elif '_ao' in filename or '_occlusion' in filename:
            purpose_info += "Purpose: Ambient occlusion\n"
        elif '_em' in filename or '_emission' in filename:
            purpose_info += "Purpose: Emission map\n"
        elif '_gm' in filename:
            purpose_info += "Purpose: Gradient map\n"
        elif '_mask' in filename:
            purpose_info += "Purpose: Mask texture\n"
        
        return purpose_info
    
    def _generate_dds_thumbnail(self, file_path: str, max_size=(180, 180)):
        """Generate DDS thumbnail using multiple methods"""
        # Method 1: Try PIL with DDS support first
        try:
            from PIL import Image
            import io
            from PyQt6.QtGui import QPixmap
            
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
                
        except Exception:
            pass
        
        # Method 2: Try Wand/ImageMagick as fallback
        try:
            from wand.image import Image as WandImage
            import io
            from PyQt6.QtGui import QPixmap
            
            with WandImage(filename=file_path) as img:
                img.thumbnail(max_size[0], max_size[1])
                img_buffer = io.BytesIO()
                img.format = 'png'
                img.save(img_buffer)
                img_buffer.seek(0)
                
                pixmap = QPixmap()
                pixmap.loadFromData(img_buffer.getvalue())
                return pixmap
                
        except Exception:
            pass
        
        # Method 3: Generate informative placeholder
        return self._create_dds_info_placeholder(file_path, max_size)
    
    def _create_dds_info_placeholder(self, file_path: str, canvas_size=(180, 180)):
        """Create an informative placeholder when thumbnail generation fails"""
        try:
            from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor
            from PyQt6.QtCore import Qt
            
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
            from PyQt6.QtGui import QPixmap, QColor
            pixmap = QPixmap(canvas_size[0], canvas_size[1])
            pixmap.fill(QColor(200, 200, 200))
            return pixmap