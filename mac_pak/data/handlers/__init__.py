#!/usr/bin/env python3
"""
Format handlers for BG3 file preview system
"""

from .base_handler import FormatHandler
from .text_handler import TextFormatHandler
from .binary_handler import BinaryFormatHandler
from .texture_handler import TextureFormatHandler
from .model_handler import ModelFormatHandler
from .shader_handler import ShaderFormatHandler
from .localization_handler import LocalizationHandler

class FormatHandlerRegistry:
    """Registry for managing format handlers"""
    
    def __init__(self):
        self._handlers = [
            TextFormatHandler(),
            BinaryFormatHandler(),
            TextureFormatHandler(),
            ModelFormatHandler(),
            ShaderFormatHandler(),
            LocalizationHandler()
        ]
    
    def get_handler_for_file(self, file_path: str) -> FormatHandler:
        """Get appropriate handler for a file"""
        import os
        file_ext = os.path.splitext(file_path)[1].lower()
        
        for handler in self._handlers:
            if handler.can_handle(file_ext):
                return handler
        
        return None
    
    def get_supported_extensions(self) -> list:
        """Get all supported file extensions"""
        extensions = []
        for handler in self._handlers:
            extensions.extend(handler.get_supported_extensions())
        return sorted(list(set(extensions)))
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file is supported by any handler"""
        return self.get_handler_for_file(file_path) is not None


# Create default registry instance
default_registry = FormatHandlerRegistry()

# Convenience functions
def get_handler_for_file(file_path: str) -> FormatHandler:
    """Get handler for file using default registry"""
    return default_registry.get_handler_for_file(file_path)


def get_supported_extensions() -> list:
    """Get supported extensions from default registry"""
    return default_registry.get_supported_extensions()


def is_supported_file(file_path: str) -> bool:
    """Check if file is supported using default registry"""
    return default_registry.is_supported(file_path)


__all__ = [
    'FormatHandler',
    'TextFormatHandler',
    'BinaryFormatHandler', 
    'TextureFormatHandler',
    'ModelFormatHandler',
    'ShaderFormatHandler',
    'LocalizationHandler',
    'FormatHandlerRegistry',
    'default_registry',
    'get_handler_for_file',
    'get_supported_extensions',
    'is_supported_file'
]