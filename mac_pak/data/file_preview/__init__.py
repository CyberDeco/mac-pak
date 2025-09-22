#!/usr/bin/env python3
"""
BG3 File Preview System

This module provides comprehensive file preview capabilities for Baldur's Gate 3
modding tools, supporting various file formats including:

- Text formats: .lsx, .lsj, .xml, .txt, .json
- Binary Larian formats: .lsf, .lsbs, .lsbc, .lsfx
- Texture formats: .dds
- Model formats: .gr2
- Shader formats: .bshd, .shd
- Localization formats: .loca

Usage:
    from data.preview import FilePreviewManager
    
    manager = FilePreviewManager(wine_wrapper, parser)
    preview_data = manager.get_preview("path/to/file.lsx")
"""

from ...version import *
from .preview_engine import FilePreviewEngine, preview_file_quick, get_file_icon
from .preview_manager import FilePreviewManager, PreviewCache
from .utils import (
    get_file_info, 
    format_file_size, 
    is_binary_file,
    get_file_icon as get_icon_from_filename,
    estimate_preview_complexity
)

__all__ = [
    # Main classes
    'FilePreviewEngine',
    'FilePreviewManager', 
    'PreviewCache',
    
    # Utility functions
    'preview_file_quick',
    'get_file_icon',
    'get_file_info',
    'format_file_size',
    'is_binary_file',
    'get_icon_from_filename',
    'estimate_preview_complexity'
]