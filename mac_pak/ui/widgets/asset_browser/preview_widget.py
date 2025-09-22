#!/usr/bin/env python3
"""
Preview widget for displaying file previews - UI only
"""

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTextEdit
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt

from ...threads.file_preview import FilePreviewThread
from ....data.file_preview import FilePreviewManager

class PreviewWidget(QWidget):
    """Widget for displaying file previews with Mac styling - UI presentation only"""
    
    def __init__(self, parent, wine_wrapper, parser):
        super().__init__(parent)
        self.preview_thread = None
        self._current_file_path = None
        self.preview_manager = FilePreviewManager(wine_wrapper, parser)
        self.parser = parser
        self.wine_wrapper = wine_wrapper
        self.setup_ui()
        
        # Ensure proper cleanup when widget is destroyed
        self.destroyed.connect(self._on_widget_destroyed)
    
    def setup_ui(self):
        """Setup preview widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setFont(QFont("SF Pro Text", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.file_label)
        
        header_layout.addStretch()
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)  # Thin Mac-style progress
        header_layout.addWidget(self.progress_bar)
        
        layout.addLayout(header_layout)
        
        # Thumbnail area
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setMinimumHeight(150)
        self.thumbnail_label.setMaximumHeight(180)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: #f8f8f8;
            }
        """)
        layout.addWidget(self.thumbnail_label)
        
        # Content area
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setFont(QFont("SF Mono", 11))  # Mac monospace
        self.content_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: white;
                padding: 8px;
            }
        """)
        layout.addWidget(self.content_text)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
    
    def preview_file(self, file_path):
        """
        Start preview for a file using the preview manager
        
        Args:
            file_path: Path to the file to preview
            preview_manager: FilePreviewManager instance
        """
        if not file_path or not os.path.isfile(file_path):
            self.clear_preview()
            return
        
        # Cancel any existing preview
        self._cleanup_thread()
        
        # Store current file path for reference
        self._current_file_path = file_path
        
        # Update header
        self.file_label.setText(os.path.basename(file_path))
        
        # Check if file is supported
        if not self.preview_manager.is_supported(file_path):
            self.show_unsupported_file(file_path, self.preview_manager)
            return
        
        # Check if this file might need progress indication
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.lsf', '.lsbs', '.lsbc', '.lsfx']:
            self.show_progress(True)
        
        # Start preview thread
        self.preview_thread = FilePreviewThread(self, self.preview_manager, file_path, self.wine_wrapper, self.parser)
        self.preview_thread.preview_ready.connect(self.display_preview)
        self.preview_thread.progress_updated.connect(self.update_progress)
        self.preview_thread.finished.connect(self._on_thread_finished)
        self.preview_thread.start()
    
    def show_unsupported_file(self, file_path, preview_manager):
        """Show info for unsupported file types"""
        try:
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            content = f"File: {os.path.basename(file_path)}\n"
            content += f"Size: {file_size:,} bytes\n"
            content += f"Type: {file_ext}\n"
            content += "-" * 50 + "\n\n"
            content += f"Unsupported file type: {file_ext}\n"
            content += "Supported types: " + ", ".join(preview_manager.get_supported_extensions())
            
            self.content_text.setPlainText(content)
            self.thumbnail_label.clear()
            self.thumbnail_label.setText("📄\nUnsupported File")
            self.show_progress(False)
        except Exception as e:
            self.content_text.setPlainText(f"Error analyzing file: {e}")
            self.thumbnail_label.clear()
            self.thumbnail_label.setText("❌\nError")
            self.show_progress(False)
    
    def display_preview(self, preview_data):
        """Display preview data from thread"""
        self.show_progress(False)
        
        if not preview_data:
            self.content_text.setPlainText("No preview data received")
            self.thumbnail_label.clear()
            self.thumbnail_label.setText("❌\nNo Data")
            return
        
        # Display content
        content = preview_data.get('content', 'No content available')
        self.content_text.setPlainText(content)
        
        # Handle thumbnail display
        thumbnail = preview_data.get('thumbnail')
        if thumbnail and isinstance(thumbnail, QPixmap):
            # Scale to fit thumbnail area
            scaled_pixmap = thumbnail.scaled(
                self.thumbnail_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.thumbnail_label.setPixmap(scaled_pixmap)
        else:
            # Set appropriate text based on file type
            self._set_default_thumbnail_text(preview_data)
    
    def _set_default_thumbnail_text(self, preview_data):
        """Set default thumbnail text based on file type"""
        file_ext = preview_data.get('extension', '').lower()
        
        # Check if current file is an image that we should try to load directly
        if self._current_file_path and file_ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            try:
                pixmap = QPixmap(self._current_file_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        self.thumbnail_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.thumbnail_label.setPixmap(scaled_pixmap)
                    return
            except Exception:
                pass
        
        # Set text based on file type
        thumbnail_texts = {
            '.dds': "🖼️\nDDS Texture",
            '.gr2': "🎭\n3D Model",
            '.lsx': "📄\nLSX Data",
            '.lsf': "🔒\nBinary Data",
            '.bshd': "🔧\nShader",
            '.shd': "⚙️\nShader",
            '.loca': "🗄️\nLocalization"
        }
        
        thumbnail_text = thumbnail_texts.get(file_ext, "📄\nText Preview")
        self.thumbnail_label.clear()
        self.thumbnail_label.setText(thumbnail_text)
    
    def show_progress(self, show):
        """Show or hide progress indicators"""
        self.progress_bar.setVisible(show)
        self.progress_label.setVisible(show)
        
        if not show:
            self.progress_bar.setValue(0)
            self.progress_label.setText("")
    
    def update_progress(self, percentage, message):
        """Update progress display"""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
    
    def clear_preview(self):
        """Clear the preview display"""
        # Stop any running preview thread
        self._cleanup_thread()
        
        self.file_label.setText("No file selected")
        self.content_text.clear()
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("Select a file to preview")
        self.show_progress(False)
        self._current_file_path = None
    
    def set_content(self, content):
        """Directly set content text (for external use)"""
        self.content_text.setPlainText(content)
    
    def set_thumbnail(self, pixmap):
        """Directly set thumbnail pixmap (for external use)"""
        if pixmap and isinstance(pixmap, QPixmap):
            scaled_pixmap = pixmap.scaled(
                self.thumbnail_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.thumbnail_label.setPixmap(scaled_pixmap)
        else:
            self.thumbnail_label.clear()
    
    def get_current_file(self):
        """Get currently previewed file path"""
        return self._current_file_path
    
    def is_busy(self):
        """Check if preview is currently being generated"""
        return self.preview_thread and self.preview_thread.isRunning()
    
    def _cleanup_thread(self):
        """Properly cleanup any existing preview thread"""
        if not hasattr(self, 'preview_thread') or self.preview_thread is None:
            return
            
        if self.preview_thread.isRunning():
            # Disconnect signals to prevent callbacks during cleanup
            try:
                self.preview_thread.preview_ready.disconnect()
                self.preview_thread.progress_updated.disconnect()
                if hasattr(self.preview_thread, 'finished'):
                    self.preview_thread.finished.disconnect()
            except RuntimeError:
                # Signals might already be disconnected or object destroyed
                pass
            
            # Cancel and wait for thread to finish
            try:
                self.preview_thread.cancel()
                self.preview_thread.quit()
                if not self.preview_thread.wait(2000):  # Wait up to 2 seconds
                    self.preview_thread.terminate()  # Force terminate if needed
                    self.preview_thread.wait(1000)  # Wait for termination
            except RuntimeError:
                # Thread might already be destroyed
                pass
            
        self.preview_thread = None
    
    def _on_thread_finished(self):
        """Handle thread completion"""
        if hasattr(self, 'preview_thread'):
            self.preview_thread = None
    
    def _on_widget_destroyed(self):
        """Handle widget destruction"""
        try:
            self._cleanup_thread()
        except:
            # Ignore any errors during destruction
            pass
    
    def closeEvent(self, event):
        """Handle widget close event - cleanup threads"""
        try:
            self._cleanup_thread()
        except:
            pass
        super().closeEvent(event)
    
    def __del__(self):
        """Destructor - ensure thread cleanup"""
        try:
            if hasattr(self, 'preview_thread'):
                self._cleanup_thread()
        except:
            # Ignore errors during destruction
            pass