#!/usr/bin/env python3
"""
Preview manager with caching and coordination for BG3 file preview system
"""

import os
from typing import Dict, Optional, Callable

from .preview_engine import FilePreviewEngine

class FilePreviewManager:
    """Manager class for handling multiple file previews with caching"""
    
    def __init__(self, wine_wrapper, parser):
        """
        Initialize the preview manager
        
        Args:
            wine_wrapper: Optional BG3Tool instance for file conversions
            parser: Optional UniversalBG3Parser instance for parsing
        """
        self.wine_wrapper = wine_wrapper
        self.parser = parser
        self.preview_engine = FilePreviewEngine(wine_wrapper, parser)
        self.cache = {}
        self.cache_size_limit = 100
    
    def get_preview(self, file_path: str, use_cache: bool = True, progress_callback: Optional[Callable] = None) -> Dict:
        """
        Get file preview with optional caching
        
        Args:
            file_path: Path to the file to preview
            use_cache: Whether to use cached results
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary containing preview data
        """
        # Check cache first if enabled
        if use_cache and file_path in self.cache:
            # Verify cached file still exists and hasn't changed
            if self._is_cache_valid(file_path):
                return self.cache[file_path]
            else:
                # Remove invalid cache entry
                del self.cache[file_path]
        
        # Generate new preview
        if progress_callback:
            preview_data = self.preview_engine.preview_file_with_progress(file_path, progress_callback)
        else:
            preview_data = self.preview_engine.preview_file(file_path)
        
        # Cache the result if caching is enabled and no error occurred
        if use_cache and not preview_data.get('error'):
            self._add_to_cache(file_path, preview_data)
        
        return preview_data
    
    def is_supported(self, file_path: str) -> bool:
        """
        Check if a file is supported for preview
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file can be previewed
        """
        return self.preview_engine.is_supported(file_path)
    
    def get_supported_extensions(self) -> list:
        """
        Get list of supported file extensions
        
        Returns:
            List of supported extensions
        """
        return self.preview_engine.get_supported_extensions()
    
    def get_file_icon(self, file_path: str) -> str:
        """
        Get appropriate icon for file type
        
        Args:
            file_path: Path to the file
            
        Returns:
            Unicode emoji string
        """
        return self.preview_engine.get_file_icon(file_path)
    
    def clear_cache(self):
        """Clear the preview cache"""
        self.cache.clear()
    
    def get_cache_size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def get_cache_info(self) -> Dict:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'limit': self.cache_size_limit,
            'files': list(self.cache.keys())
        }
    
    def remove_from_cache(self, file_path: str) -> bool:
        """
        Remove specific file from cache
        
        Args:
            file_path: Path to remove from cache
            
        Returns:
            True if file was in cache and removed
        """
        if file_path in self.cache:
            del self.cache[file_path]
            return True
        return False
    
    def _add_to_cache(self, file_path: str, preview_data: Dict):
        """Add preview data to cache with size management"""
        # Simple cache size management
        if len(self.cache) >= self.cache_size_limit:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self.cache.keys())[:len(self.cache) - self.cache_size_limit + 1]
            for key in oldest_keys:
                del self.cache[key]
        
        # Add file modification time for cache validation
        try:
            file_stat = os.stat(file_path)
            preview_data['_cache_mtime'] = file_stat.st_mtime
            preview_data['_cache_size'] = file_stat.st_size
        except:
            pass
        
        self.cache[file_path] = preview_data
    
    def _is_cache_valid(self, file_path: str) -> bool:
        """Check if cached preview is still valid"""
        if file_path not in self.cache:
            return False
        
        cached_data = self.cache[file_path]
        
        try:
            # Check if file still exists
            if not os.path.exists(file_path):
                return False
            
            # Check if file has been modified
            file_stat = os.stat(file_path)
            cached_mtime = cached_data.get('_cache_mtime')
            cached_size = cached_data.get('_cache_size')
            
            if cached_mtime is not None and cached_size is not None:
                return (file_stat.st_mtime == cached_mtime and 
                       file_stat.st_size == cached_size)
            
            # If no cache metadata, assume valid (fallback)
            return True
            
        except:
            # If we can't check, assume invalid
            return False
    
    def invalidate_cache_for_directory(self, directory: str):
        """
        Invalidate all cached entries for files in a directory
        
        Args:
            directory: Directory path to invalidate
        """
        directory = os.path.abspath(directory)
        keys_to_remove = []
        
        for file_path in self.cache:
            try:
                if os.path.abspath(file_path).startswith(directory):
                    keys_to_remove.append(file_path)
            except:
                # If path processing fails, remove it to be safe
                keys_to_remove.append(file_path)
        
        for key in keys_to_remove:
            del self.cache[key]
    
    def preload_previews(self, file_paths: list, progress_callback: Optional[Callable] = None):
        """
        Preload previews for multiple files
        
        Args:
            file_paths: List of file paths to preload
            progress_callback: Optional callback for overall progress
        """
        total_files = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            if progress_callback:
                progress = int((i / total_files) * 100)
                progress_callback(progress, f"Preloading {os.path.basename(file_path)}")
            
            # Only preload if not already cached
            if file_path not in self.cache:
                try:
                    self.get_preview(file_path, use_cache=True)
                except Exception as e:
                    # Continue with other files if one fails
                    print(f"Failed to preload {file_path}: {e}")
                    continue
        
        if progress_callback:
            progress_callback(100, f"Preloaded {total_files} files")


class PreviewCache:
    """Standalone cache implementation for preview data"""
    
    def __init__(self, size_limit: int = 100):
        """
        Initialize cache
        
        Args:
            size_limit: Maximum number of entries to cache
        """
        self.cache = {}
        self.size_limit = size_limit
        self.access_order = []  # For LRU eviction
    
    def get(self, key: str) -> Optional[Dict]:
        """Get item from cache"""
        if key in self.cache:
            # Move to end (most recently accessed)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Dict):
        """Set item in cache"""
        if key in self.cache:
            # Update existing
            self.cache[key] = value
            self.access_order.remove(key)
            self.access_order.append(key)
        else:
            # Add new
            if len(self.cache) >= self.size_limit:
                # Remove least recently used
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]
            
            self.cache[key] = value
            self.access_order.append(key)
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.access_order.clear()
    
    def remove(self, key: str) -> bool:
        """Remove specific key from cache"""
        if key in self.cache:
            del self.cache[key]
            self.access_order.remove(key)
            return True
        return False
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def keys(self) -> list:
        """Get all cached keys"""
        return list(self.cache.keys())