#!/usr/bin/env python3
"""
Utility functions for BG3 file preview system
"""

import os
import mimetypes
from typing import Dict, List, Optional

def get_file_info(file_path: str) -> Dict:
    """
    Get basic file information
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary containing file information
    """
    try:
        stat_info = os.stat(file_path)
        filename = os.path.basename(file_path)
        file_ext = os.path.splitext(filename)[1].lower()
        
        return {
            'filename': filename,
            'extension': file_ext,
            'size': stat_info.st_size,
            'size_formatted': format_file_size(stat_info.st_size),
            'modified_time': stat_info.st_mtime,
            'is_binary': is_binary_file(file_path),
            'mime_type': get_mime_type(file_path),
            'exists': True
        }
    except Exception as e:
        return {
            'filename': os.path.basename(file_path) if file_path else 'Unknown',
            'extension': '',
            'size': 0,
            'size_formatted': '0 bytes',
            'modified_time': 0,
            'is_binary': True,
            'mime_type': 'application/octet-stream',
            'exists': False,
            'error': str(e)
        }


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 bytes"
    
    size_units = ['bytes', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024.0 and unit_index < len(size_units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {size_units[unit_index]}"
    else:
        return f"{size:.1f} {size_units[unit_index]}"


def is_binary_file(file_path: str, chunk_size: int = 1024) -> bool:
    """
    Check if a file is binary by examining its content
    
    Args:
        file_path: Path to the file
        chunk_size: Number of bytes to read for analysis
        
    Returns:
        True if file appears to be binary
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
        
        # Check for null bytes (common in binary files)
        if b'\x00' in chunk:
            return True
        
        # Check for high ratio of non-printable characters
        printable_chars = sum(1 for byte in chunk if 32 <= byte <= 126 or byte in [9, 10, 13])
        if len(chunk) > 0 and (printable_chars / len(chunk)) < 0.3:
            return True
        
        return False
        
    except Exception:
        # If we can't read the file, assume it's binary
        return True


def get_mime_type(file_path: str) -> str:
    """
    Get MIME type for a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'


def get_file_icon(filename: str) -> str:
    """
    Get appropriate emoji icon for file type
    
    Args:
        filename: Name of the file
        
    Returns:
        Unicode emoji string
    """
    ext = os.path.splitext(filename)[1].lower()
    
    icons = {
        # Text files
        '.lsx': '📄',
        '.lsj': '📋',
        '.xml': '📄',
        '.txt': '📝',
        '.json': '📋',
        
        # Binary Larian formats
        '.lsf': '🔒',
        '.lsbs': '📃',
        '.lsbc': '📃',
        '.lsfx': '✨',
        
        # Media files
        '.dds': '🖼️',
        '.png': '🖼️',
        '.jpg': '🖼️',
        '.jpeg': '🖼️',
        '.gif': '🖼️',
        '.bmp': '🖼️',
        '.gr2': '🖌️',
        
        # Shader files
        '.bshd': '🔧',
        '.shd': '⚙️',
        
        # Localization
        '.loca': '🗄️',
        
        # Common file types

        '.pdf': '📕',
        '.zip': '📦',
        '.rar': '📦',
        '.7z': '📦',
        '.pak': '📦',
    }
    
    return icons.get(ext, '📄')


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def safe_read_text(file_path: str, max_bytes: int = 2048, encoding: str = 'utf-8') -> str:
    """
    Safely read text from a file with error handling
    
    Args:
        file_path: Path to the file
        max_bytes: Maximum bytes to read
        encoding: Text encoding to use
        
    Returns:
        File content as string
    """
    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            return f.read(max_bytes)
    except Exception as e:
        return f"Error reading file: {e}"


def extract_readable_strings(data: bytes, min_length: int = 4) -> List[str]:
    """
    Extract readable strings from binary data
    
    Args:
        data: Binary data
        min_length: Minimum string length to extract
        
    Returns:
        List of readable strings found
    """
    strings = []
    current_string = ""
    
    for byte in data:
        if 32 <= byte <= 126:  # Printable ASCII
            current_string += chr(byte)
        else:
            if len(current_string) >= min_length:
                strings.append(current_string)
            current_string = ""
    
    # Don't forget the last string
    if len(current_string) >= min_length:
        strings.append(current_string)
    
    return strings


def create_content_header(file_path: str) -> str:
    """
    Create a standard content header for preview
    
    Args:
        file_path: Path to the file
        
    Returns:
        Formatted header string
    """
    try:
        file_info = get_file_info(file_path)
        
        header = f"File: {file_info['filename']}\n"
        header += f"Size: {file_info['size_formatted']}\n"
        header += f"Type: {file_info['extension']}\n"
        header += "-" * 50 + "\n\n"
        
        return header
    except Exception as e:
        return f"Error creating header: {e}\n\n"


def is_bg3_format(file_ext: str) -> bool:
    """
    Check if file extension is a BG3-specific format
    
    Args:
        file_ext: File extension (e.g., '.lsx')
        
    Returns:
        True if it's a BG3 format
    """
    bg3_formats = {
        '.lsx', '.lsj', '.lsf', '.lsfx', 
        '.lsbs', '.lsbc', '.loca'
    }
    return file_ext.lower() in bg3_formats


def detect_text_encoding(file_path: str) -> str:
    """
    Detect text encoding of a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        Detected encoding name
    """
    try:
        import chardet
        
        with open(file_path, 'rb') as f:
            raw_data = f.read(8192)  # Read first 8KB
        
        result = chardet.detect(raw_data)
        return result.get('encoding', 'utf-8') or 'utf-8'
        
    except ImportError:
        # Fallback if chardet not available
        return 'utf-8'
    except Exception:
        return 'utf-8'


def normalize_path(file_path: str) -> str:
    """
    Normalize file path for consistent handling
    
    Args:
        file_path: File path to normalize
        
    Returns:
        Normalized path
    """
    if not file_path:
        return ""
    
    return os.path.normpath(os.path.abspath(file_path))


def get_relative_path(file_path: str, base_path: str) -> str:
    """
    Get relative path from base path
    
    Args:
        file_path: Target file path
        base_path: Base directory path
        
    Returns:
        Relative path string
    """
    try:
        return os.path.relpath(file_path, base_path)
    except ValueError:
        # Paths are on different drives (Windows)
        return file_path


def estimate_preview_complexity(file_path: str) -> str:
    """
    Estimate preview generation complexity
    
    Args:
        file_path: Path to the file
        
    Returns:
        Complexity level ('simple', 'moderate', 'complex')
    """
    try:
        file_info = get_file_info(file_path)
        file_ext = file_info['extension']
        file_size = file_info['size']
        
        # Binary files requiring conversion are complex
        if file_ext in ['.lsf', '.lsbs', '.lsbc', '.lsfx']:
            return 'complex'
        
        # Large files are more complex
        if file_size > 10 * 1024 * 1024:  # 10MB
            return 'complex'
        elif file_size > 1024 * 1024:  # 1MB
            return 'moderate'
        
        # Text files are generally simple
        if file_ext in ['.txt', '.xml', '.json']:
            return 'simple'
        
        # Image files depend on format
        if file_ext == '.dds':
            return 'moderate'  # May need thumbnail generation
        
        return 'simple'
        
    except Exception:
        return 'moderate'