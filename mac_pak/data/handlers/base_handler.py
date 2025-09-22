#!/usr/bin/env python3
"""
Base handler interface for file format previews
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class FormatHandler(ABC):
    """Abstract base class for file format handlers"""
    
    @abstractmethod
    def can_handle(self, file_ext: str) -> bool:
        """
        Check if this handler supports the given file extension
        
        Args:
            file_ext: File extension (e.g., '.lsx', '.dds')
            
        Returns:
            True if this handler can process the file type
        """
        pass
    
    @abstractmethod
    def preview(self, file_path: str, **kwargs) -> Dict:
        """
        Generate preview data for the file
        
        Args:
            file_path: Path to the file to preview
            **kwargs: Additional arguments (wine_wrapper, parser, etc.)
            
        Returns:
            Dictionary containing preview data with keys:
            - filename: Base filename
            - size: File size in bytes
            - extension: File extension
            - content: Preview text content
            - thumbnail: Thumbnail data (QPixmap or None)
            - metadata: Additional metadata dict
            - error: Error message if any
        """
        pass
    
    def get_supported_extensions(self) -> List[str]:
        """
        Return list of file extensions this handler supports
        
        Returns:
            List of supported extensions (e.g., ['.lsx', '.xml'])
        """
        return []
    
    def get_file_icon(self, file_ext: str) -> str:
        """
        Get emoji icon for file type
        
        Args:
            file_ext: File extension
            
        Returns:
            Unicode emoji string
        """
        return "📄"
    
    def _create_base_preview_data(self, file_path: str) -> Dict:
        """
        Create base preview data structure with common fields
        
        Args:
            file_path: Path to the file
            
        Returns:
            Base preview data dictionary
        """
        import os
        
        try:
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            return {
                'filename': os.path.basename(file_path),
                'size': file_size,
                'extension': file_ext,
                'content': '',
                'thumbnail': None,
                'metadata': {},
                'error': None
            }
        except Exception as e:
            return {
                'filename': os.path.basename(file_path) if file_path else 'Unknown',
                'size': 0,
                'extension': '',
                'content': f"Error accessing file: {e}",
                'thumbnail': None,
                'metadata': {},
                'error': str(e)
            }
    
    def _create_header_content(self, file_path: str) -> str:
        """
        Create standard header content for preview
        
        Args:
            file_path: Path to the file
            
        Returns:
            Formatted header string
        """
        import os
        
        try:
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            content = f"File: {os.path.basename(file_path)}\n"
            content += f"Size: {file_size:,} bytes\n"
            content += f"Type: {file_ext}\n"
            content += "-" * 50 + "\n\n"
            return content
        except Exception as e:
            return f"Error reading file info: {e}\n\n"