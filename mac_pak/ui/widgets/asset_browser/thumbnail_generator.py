#!/usr/bin/env python3
"""
Thumbnail generator for file previews
"""

import os
from typing import Optional, Tuple

from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor
from PyQt6.QtCore import Qt

class ThumbnailGenerator:
    """Generate thumbnails and visual previews for files"""
    
    def __init__(self):
        self.default_size = (180, 180)
    
    def generate_for_file(self, file_path: str, max_size: Tuple[int, int] = None) -> Optional[QPixmap]:
        """
        Generate thumbnail for any supported file type
        
        Args:
            file_path: Path to the file
            max_size: Maximum thumbnail size (width, height)
            
        Returns:
            QPixmap thumbnail or None if generation fails
        """
        if max_size is None:
            max_size = self.default_size
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Route to appropriate generator
        if file_ext == '.dds' or '_DDS' in file_path:
            return self.create_dds_thumbnail(file_path, max_size)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
            return self.create_image_thumbnail(file_path, max_size)
        else:
            return self.create_info_placeholder(file_path, max_size)
    
    def create_dds_thumbnail(self, file_path: str, max_size: Tuple[int, int]) -> Optional[QPixmap]:
        """Generate DDS thumbnail using multiple methods"""
        
        # Method 1: Try PIL with DDS support first
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
                
        except Exception:
            pass
        
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
                
        except Exception:
            pass
        
        # Method 3: Generate informative placeholder
        return self.create_dds_info_placeholder(file_path, max_size)
    
    def create_image_thumbnail(self, file_path: str, max_size: Tuple[int, int]) -> Optional[QPixmap]:
        """Generate thumbnail for standard image formats"""
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                return pixmap.scaled(
                    max_size[0], max_size[1],
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
        except Exception:
            pass
        
        return None
    
    def create_info_placeholder(self, file_path: str, max_size: Tuple[int, int]) -> QPixmap:
        """Create informational placeholder for files without thumbnails"""
        pixmap = QPixmap(max_size[0], max_size[1])
        pixmap.fill(QColor(240, 240, 240))  # Light gray background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw border
        painter.setPen(QColor(200, 200, 200))
        painter.drawRect(5, 5, max_size[0]-10, max_size[1]-10)
        
        # Get file info
        filename = os.path.basename(file_path)
        file_ext = os.path.splitext(filename)[1].lower()
        
        # File type specific content
        center_x = max_size[0] // 2
        center_y = max_size[1] // 2
        
        # Draw file type
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.setPen(QColor(100, 100, 100))
        
        type_text = file_ext.upper() if file_ext else "FILE"
        painter.drawText(center_x - 20, center_y - 10, 40, 20, 
                        Qt.AlignmentFlag.AlignCenter, type_text)
        
        # Draw filename (truncated)
        small_font = QFont("Arial", 8)
        painter.setFont(small_font)
        
        display_name = filename
        if len(display_name) > 20:
            display_name = display_name[:17] + "..."
        
        painter.drawText(10, max_size[1] - 20, max_size[0] - 20, 15,
                        Qt.AlignmentFlag.AlignCenter, display_name)
        
        painter.end()
        return pixmap
    
    def create_dds_info_placeholder(self, file_path: str, max_size: Tuple[int, int]) -> QPixmap:
        """Create informative placeholder specifically for DDS files"""
        try:
            pixmap = QPixmap(max_size[0], max_size[1])
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
                painter.drawRect(5, 5, max_size[0]-10, max_size[1]-10)
                
                # Set up fonts
                font = QFont("Arial", 12)
                small_font = QFont("Arial", 10)
                
                center_x = max_size[0] // 2
                
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
            print(f"DDS placeholder creation failed: {e}")
            # Return simple gray pixmap as last resort
            pixmap = QPixmap(max_size[0], max_size[1])
            pixmap.fill(QColor(200, 200, 200))
            return pixmap
    
    def create_text_preview_thumbnail(self, file_path: str, max_size: Tuple[int, int], 
                                    preview_text: str = None) -> QPixmap:
        """Create thumbnail showing text preview"""
        pixmap = QPixmap(max_size[0], max_size[1])
        pixmap.fill(QColor(255, 255, 255))  # White background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw border
        painter.setPen(QColor(180, 180, 180))
        painter.drawRect(5, 5, max_size[0]-10, max_size[1]-10)
        
        # Draw text preview if provided
        if preview_text:
            font = QFont("Courier", 8)  # Monospace font
            painter.setFont(font)
            painter.setPen(QColor(0, 0, 0))
            
            # Truncate text to fit
            text_lines = preview_text.split('\n')[:8]  # Max 8 lines
            for i, line in enumerate(text_lines):
                if len(line) > 25:
                    line = line[:22] + "..."
                painter.drawText(10, 20 + i * 12, line)
        
        painter.end()
        return pixmap