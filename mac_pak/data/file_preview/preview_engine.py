#!/usr/bin/env python3
"""
Core preview engine for BG3 file preview system
"""

import os
from typing import Dict, Optional, Callable

from ..handlers import FormatHandlerRegistry, get_handler_for_file

class FilePreviewEngine:
    """Core engine for generating file previews"""
    
    def __init__(self, wine_wrapper, parser):
        """
        Initialize the preview engine
        
        Args:
            wine_wrapper: Optional BG3Tool instance for file conversions
            parser: Optional UniversalBG3Parser instance for parsing
        """
        self.wine_wrapper = wine_wrapper
        self.parser = parser
        self.registry = FormatHandlerRegistry()
    
    def preview_file(self, file_path: str) -> Dict:
        """
        Generate preview content for a file
        
        Args:
            file_path: Path to the file to preview
            
        Returns:
            dict: Preview data containing 'content', 'thumbnail', and 'metadata'
        """
        try:
            # Validate file exists
            if not file_path or not os.path.isfile(file_path):
                return self._create_error_preview(file_path, "File not found or invalid path")
            
            # Get appropriate handler
            handler = self.registry.get_handler_for_file(file_path)
            
            if not handler:
                return self._create_unsupported_preview(file_path)
            
            # Generate preview using handler with all required arguments
            preview_data = handler.preview(
                file_path,
                wine_wrapper=self.wine_wrapper,
                parser=self.parser
            )
            
            return preview_data
            
        except Exception as e:
            return self._create_error_preview(file_path, f"Preview generation failed: {e}")
    
    def preview_file_with_progress(self, file_path: str, progress_callback: Callable = None) -> Dict:
        """
        Generate preview with progress updates for slow operations
        
        Args:
            file_path: Path to the file to preview
            progress_callback: Optional callback function(progress_percent, message)
            
        Returns:
            dict: Preview data
        """
        try:
            # Validate file exists
            if not file_path or not os.path.isfile(file_path):
                if progress_callback:
                    progress_callback(100, "Error: File not found")
                return self._create_error_preview(file_path, "File not found or invalid path")
            
            if progress_callback:
                progress_callback(0, "Starting preview...")
            
            # Get appropriate handler
            handler = self.registry.get_handler_for_file(file_path)
            
            if not handler:
                if progress_callback:
                    progress_callback(100, "Unsupported file type")
                return self._create_unsupported_preview(file_path)
            
            if progress_callback:
                progress_callback(10, "Analyzing file...")
            
            # Check if this file type needs progress indication
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in ['.lsf', '.lsbs', '.lsbc', '.lsfx']:
                # Binary files may need conversion - use progress-aware method
                if hasattr(handler, 'preview_with_progress'):
                    preview_data = handler.preview_with_progress(
                        file_path,
                        progress_callback,
                        wine_wrapper=self.wine_wrapper,
                        parser=self.parser
                    )
                else:
                    preview_data = handler.preview(
                        file_path,
                        wine_wrapper=self.wine_wrapper,
                        parser=self.parser,
                        progress_callback=progress_callback
                    )
            else:
                # Standard preview
                if progress_callback:
                    progress_callback(50, "Generating preview...")
                
                preview_data = handler.preview(
                    file_path,
                    wine_wrapper=self.wine_wrapper,
                    parser=self.parser,
                    progress_callback=progress_callback
                )
                
                if progress_callback:
                    progress_callback(100, "Preview complete!")
            
            return preview_data
            
        except Exception as e:
            if progress_callback:
                progress_callback(100, f"Error: {e}")
            return self._create_error_preview(file_path, f"Preview generation failed: {e}")
            
            if progress_callback:
                progress_callback(10, "Analyzing file...")
            
            # Check if this file type needs progress indication
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in ['.lsf', '.lsbs', '.lsbc', '.lsfx']:
                # Binary files may need conversion - use progress-aware method
                if hasattr(handler, 'preview_with_progress'):
                    preview_data = handler.preview_with_progress(
                        file_path,
                        progress_callback,
                        wine_wrapper=self.wine_wrapper,
                        parser=self.parser
                    )
                else:
                    preview_data = handler.preview(
                        file_path,
                        wine_wrapper=self.wine_wrapper,
                        parser=self.parser,
                        progress_callback=progress_callback
                    )
            else:
                # Standard preview
                if progress_callback:
                    progress_callback(50, "Generating preview...")
                
                preview_data = handler.preview(
                    file_path,
                    wine_wrapper=self.wine_wrapper,
                    parser=self.parser,
                    progress_callback=progress_callback
                )
                
                if progress_callback:
                    progress_callback(100, "Preview complete!")
            
            return preview_data
            
        except Exception as e:
            if progress_callback:
                progress_callback(100, f"Error: {e}")
            return self._create_error_preview(file_path, f"Preview generation failed: {e}")
    
    def is_supported(self, file_path: str) -> bool:
        """
        Check if a file is supported for preview
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file can be previewed
        """
        return self.registry.is_supported(file_path)
    
    def get_supported_extensions(self) -> list:
        """
        Get list of supported file extensions
        
        Returns:
            List of supported extensions (e.g., ['.lsx', '.dds'])
        """
        return self.registry.get_supported_extensions()
    
    def get_file_icon(self, file_path: str) -> str:
        """
        Get appropriate icon for file type
        
        Args:
            file_path: Path to the file
            
        Returns:
            Unicode emoji string
        """
        handler = self.registry.get_handler_for_file(file_path)
        if handler:
            file_ext = os.path.splitext(file_path)[1].lower()
            return handler.get_file_icon(file_ext)
        return "📄"
    
    def _create_error_preview(self, file_path: str, error_message: str) -> Dict:
        """Create preview data for error cases"""
        return {
            'filename': os.path.basename(file_path) if file_path else 'Unknown',
            'size': 0,
            'extension': '',
            'content': f"Error: {error_message}",
            'thumbnail': None,
            'metadata': {'error': True},
            'error': error_message
        }
    
    def _create_unsupported_preview(self, file_path: str) -> Dict:
        """Create preview data for unsupported file types"""
        try:
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            content = f"File: {os.path.basename(file_path)}\n"
            content += f"Size: {file_size:,} bytes\n"
            content += f"Type: {file_ext}\n"
            content += "-" * 50 + "\n\n"
            content += f"Unsupported file type: {file_ext}\n"
            content += "Supported types: " + ", ".join(self.get_supported_extensions())
            
            return {
                'filename': os.path.basename(file_path),
                'size': file_size,
                'extension': file_ext,
                'content': content,
                'thumbnail': None,
                'metadata': {'supported': False},
                'error': None
            }
            
        except Exception as e:
            return self._create_error_preview(file_path, f"Could not analyze unsupported file: {e}")


# Standalone utility functions
def preview_file_quick(file_path: str, wine_wrapper=None, parser=None) -> Dict:
    """Quick file preview without engine overhead"""
    engine = FilePreviewEngine(wine_wrapper, parser)
    return engine.preview_file(file_path)


def get_file_icon(filename: str) -> str:
    """Get appropriate icon for file type"""
    ext = os.path.splitext(filename)[1].lower()
    
    # Default icon mapping
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
        '.lsfx': '📈',
        '.loca': '🗄️',
    }
    
    return icons.get(ext, '📄')