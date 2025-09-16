#!/usr/bin/env python3
"""
Threaded file preview pane in Asset Browser tab
"""

import os
from PyQt6.QtCore import QThread, pyqtSignal

class FilePreviewThread(QThread):
    """Thread for handling file previews that might take time"""
    
    preview_ready = pyqtSignal(dict)  # preview_data
    progress_updated = pyqtSignal(int, str)  # percentage, message
    
    def __init__(self, preview_manager, file_path):
        super().__init__()
        self.preview_manager = preview_manager
        self.file_path = file_path
        self.cancelled = False
    
    def run(self):
        """Run preview generation in background"""
        try:
            file_ext = os.path.splitext(self.file_path)[1].lower()
            
            def progress_callback(percent, message):
                if not self.cancelled:
                    self.progress_updated.emit(percent, message)
            
            # Use the full preview system with progress
            preview_data = self.preview_manager.get_preview(
                self.file_path, use_cache=True, progress_callback=progress_callback
            )
            
            if not self.cancelled:
                self.preview_ready.emit(preview_data)
                
        except Exception as e:
            if not self.cancelled:
                error_data = {
                    'content': f"Error previewing file: {e}",
                    'thumbnail': None
                }
                self.preview_ready.emit(error_data)
    
    def cancel(self):
        """Cancel the preview operation"""
        self.cancelled = True