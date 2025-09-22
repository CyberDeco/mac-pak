#!/usr/bin/env python3
"""
Updated file preview thread - simplified to work with new preview system
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional


class FilePreviewThread(QThread):
    """Thread for generating file previews without blocking the UI"""
    
    # Signals
    preview_ready = pyqtSignal(dict)  # Emitted when preview is complete
    progress_updated = pyqtSignal(int, str)  # Emitted during progress (percentage, message)
    error_occurred = pyqtSignal(str)  # Emitted on error
    
    def __init__(self, parent, preview_manager, file_path, wine_wrapper, parser):
        """
        Initialize preview thread
        
        Args:
            preview_manager: FilePreviewManager instance
            file_path: Path to file to preview
            parent: Parent QObject
        """
        super().__init__(parent)
        self.preview_manager = preview_manager
        self.parser = parser
        self.wine_wrapper = wine_wrapper
        self.file_path = file_path
        self._cancelled = False
        self.setTerminationEnabled(True)  # Allow thread termination
    
    def run(self):
        """Generate preview in background thread"""
        try:
            if self._cancelled:
                return
            
            # Generate preview with progress callback
            preview_data = self.preview_manager.get_preview(
                self.file_path,
                use_cache=True,
                progress_callback=self._progress_callback
            )
            
            if not self._cancelled and preview_data:
                self.preview_ready.emit(preview_data)
                
        except Exception as e:
            if not self._cancelled:
                self.error_occurred.emit(f"Preview generation failed: {e}")
        finally:
            # Ensure thread finishes cleanly
            self.finished.emit()
    
    def _progress_callback(self, percentage: int, message: str):
        """Progress callback for preview generation"""
        if not self._cancelled:
            self.progress_updated.emit(percentage, message)
        # Check for cancellation during progress updates
        if self._cancelled:
            raise InterruptedError("Preview generation cancelled")
    
    def cancel(self):
        """Cancel the preview generation"""
        self._cancelled = True
        # Request interruption to stop the thread more quickly
        self.requestInterruption()
    
    def is_cancelled(self) -> bool:
        """Check if preview generation was cancelled"""
        return self._cancelled or self.isInterruptionRequested()


class BatchPreviewThread(QThread):
    """Thread for generating multiple previews in batch"""
    
    # Signals
    batch_progress = pyqtSignal(int, int, str)  # current, total, filename
    preview_completed = pyqtSignal(str, dict)  # file_path, preview_data
    batch_finished = pyqtSignal(list)  # List of completed file paths
    error_occurred = pyqtSignal(str, str)  # file_path, error_message
    
    def __init__(self, preview_manager, file_paths: list, parent=None):
        """
        Initialize batch preview thread
        
        Args:
            preview_manager: FilePreviewManager instance
            file_paths: List of file paths to preview
            parent: Parent QObject
        """
        super().__init__(parent)
        self.preview_manager = preview_manager
        self.file_paths = file_paths
        self._cancelled = False
        self.completed_files = []
        self.setTerminationEnabled(True)
    
    def run(self):
        """Generate previews for all files"""
        try:
            total_files = len(self.file_paths)
            
            for i, file_path in enumerate(self.file_paths):
                if self._cancelled or self.isInterruptionRequested():
                    break
                
                try:
                    # Emit progress
                    filename = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
                    self.batch_progress.emit(i + 1, total_files, filename)
                    
                    # Check for cancellation before processing
                    if self._cancelled or self.isInterruptionRequested():
                        break
                    
                    # Generate preview
                    preview_data = self.preview_manager.get_preview(file_path, use_cache=True)
                    
                    if not self._cancelled and not self.isInterruptionRequested():
                        self.preview_completed.emit(file_path, preview_data)
                        self.completed_files.append(file_path)
                        
                except Exception as e:
                    if not self._cancelled and not self.isInterruptionRequested():
                        self.error_occurred.emit(file_path, str(e))
            
            if not self._cancelled and not self.isInterruptionRequested():
                self.batch_finished.emit(self.completed_files)
                
        except Exception as e:
            if not self._cancelled and not self.isInterruptionRequested():
                self.error_occurred.emit("", f"Batch preview failed: {e}")
        finally:
            self.finished.emit()
    
    def cancel(self):
        """Cancel batch preview generation"""
        self._cancelled = True
        self.requestInterruption()
    
    def is_cancelled(self) -> bool:
        """Check if batch preview was cancelled"""
        return self._cancelled or self.isInterruptionRequested()


class PreviewCacheThread(QThread):
    """Thread for preloading previews into cache"""
    
    # Signals
    cache_progress = pyqtSignal(int, str)  # percentage, current_file
    cache_completed = pyqtSignal(int)  # number of files cached
    
    def __init__(self, preview_manager, file_paths: list, parent=None):
        """
        Initialize cache preload thread
        
        Args:
            preview_manager: FilePreviewManager instance
            file_paths: List of file paths to cache
            parent: Parent QObject
        """
        super().__init__(parent)
        self.preview_manager = preview_manager
        self.file_paths = file_paths
        self._cancelled = False
        self.cached_count = 0
        self.setTerminationEnabled(True)
    
    def run(self):
        """Preload previews into cache"""
        try:
            total_files = len(self.file_paths)
            
            for i, file_path in enumerate(self.file_paths):
                if self._cancelled or self.isInterruptionRequested():
                    break
                
                try:
                    # Check if already cached
                    if file_path not in self.preview_manager.cache:
                        # Emit progress
                        progress = int((i / total_files) * 100)
                        filename = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
                        self.cache_progress.emit(progress, filename)
                        
                        # Check for cancellation
                        if self._cancelled or self.isInterruptionRequested():
                            break
                        
                        # Generate and cache preview
                        self.preview_manager.get_preview(file_path, use_cache=True)
                        self.cached_count += 1
                    
                except Exception as e:
                    # Continue with other files if one fails
                    print(f"Failed to cache {file_path}: {e}")
                    continue
            
            if not self._cancelled and not self.isInterruptionRequested():
                self.cache_progress.emit(100, "Cache preload complete")
                self.cache_completed.emit(self.cached_count)
                
        except Exception as e:
            print(f"Cache preload failed: {e}")
        finally:
            self.finished.emit()
    
    def cancel(self):
        """Cancel cache preloading"""
        self._cancelled = True
        self.requestInterruption()
    
    def is_cancelled(self) -> bool:
        """Check if cache preloading was cancelled"""
        return self._cancelled or self.isInterruptionRequested()