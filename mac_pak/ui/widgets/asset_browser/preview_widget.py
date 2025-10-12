#!/usr/bin/env python3
"""
Preview widget with zoom controls and copy functionality
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QProgressBar, QTextEdit, QPushButton, QSlider,
                            QApplication, QMessageBox, QScrollArea)
from PyQt6.QtGui import QFont, QPixmap, QKeyEvent
from PyQt6.QtCore import Qt, pyqtSignal

from ...threads.file_preview import FilePreviewThread
from ....data.file_preview import FilePreviewManager


class ZoomableImageLabel(QLabel):
    """Label that can display zoomed images"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._zoom_level = 1.0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def set_pixmap(self, pixmap):
        """Set pixmap and store original"""
        self._pixmap = pixmap
        self._zoom_level = 1.0
        self.update_display()
    
    def set_zoom(self, zoom_level):
        """Set zoom level (1.0 = 100%)"""
        self._zoom_level = zoom_level
        self.update_display()
    
    def update_display(self):
        """Update displayed pixmap with current zoom"""
        if self._pixmap:
            size = self._pixmap.size() * self._zoom_level
            scaled = self._pixmap.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            super().setPixmap(scaled)
        else:
            self.clear()
    
    def clear_pixmap(self):
        """Clear the pixmap"""
        self._pixmap = None
        self._zoom_level = 1.0
        self.clear()


class PreviewWidget(QWidget):
    """Preview widget with zoom and copy controls"""
    
    zoom_changed = pyqtSignal(int)  # Emits zoom percentage
    
    def __init__(self, parent, wine_wrapper, parser):
        super().__init__(parent)
        self.preview_thread = None
        self._current_file_path = None
        self.preview_manager = FilePreviewManager(wine_wrapper, parser)
        self.parser = parser
        self.wine_wrapper = wine_wrapper
        self._current_zoom = 100  # 100%
        
        self.setup_ui()
        
        # Ensure proper cleanup when widget is destroyed
        self.destroyed.connect(self._on_widget_destroyed)
        
    def setup_ui(self):
        """Setup enhanced preview widget UI with unified display"""
        from PyQt6.QtWidgets import QStackedWidget
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header with controls
        header_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setFont(QFont("SF Pro Text", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.file_label)
        
        header_layout.addStretch()
        
        # Copy button
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setToolTip("Copy preview content to clipboard")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_content)
        header_layout.addWidget(self.copy_btn)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        header_layout.addWidget(self.progress_bar)
        
        # Progress label for detailed status
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        header_layout.addWidget(self.progress_label)
        
        layout.addLayout(header_layout)
        
        # Create stacked widget for unified display (either thumbnail OR text)
        self.display_stack = QStackedWidget()
        
        # ===== Page 0: Thumbnail/Image View =====
        thumbnail_page = QWidget()
        thumbnail_layout = QVBoxLayout(thumbnail_page)
        thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        thumbnail_layout.setSpacing(4)
        
        # Zoom controls
        zoom_controls = QHBoxLayout()
        
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedSize(30, 30)
        self.zoom_out_btn.setEnabled(False)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_controls.addWidget(self.zoom_out_btn)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(25)  # 25%
        self.zoom_slider.setMaximum(400)  # 400%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setEnabled(False)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        zoom_controls.addWidget(self.zoom_slider)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(30, 30)
        self.zoom_in_btn.setEnabled(False)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_controls.addWidget(self.zoom_in_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_controls.addWidget(self.zoom_label)
        
        self.zoom_reset_btn = QPushButton("⊙")
        self.zoom_reset_btn.setFixedSize(30, 30)
        self.zoom_reset_btn.setToolTip("Reset zoom to 100%")
        self.zoom_reset_btn.setEnabled(False)
        self.zoom_reset_btn.clicked.connect(self.zoom_reset)
        zoom_controls.addWidget(self.zoom_reset_btn)
        
        thumbnail_layout.addLayout(zoom_controls)
        
        # Scrollable thumbnail area
        self.thumbnail_scroll = QScrollArea()
        self.thumbnail_scroll.setWidgetResizable(True)
        self.thumbnail_scroll.setMinimumHeight(300)
        self.thumbnail_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: #f8f8f8;
            }
        """)
        
        self.thumbnail_label = ZoomableImageLabel()
        self.thumbnail_label.setMinimumHeight(280)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #f8f8f8;
            }
        """)
        self.thumbnail_scroll.setWidget(self.thumbnail_label)
        
        thumbnail_layout.addWidget(self.thumbnail_scroll)
        self.display_stack.addWidget(thumbnail_page)
        
        # ===== Page 1: Text Content View =====
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setFont(QFont("SF Mono", 11))
        self.content_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: white;
                padding: 8px;
            }
        """)
        self.display_stack.addWidget(self.content_text)
        
        # Add the stacked widget to main layout
        layout.addWidget(self.display_stack)
        
        # Default to text view
        self.display_stack.setCurrentIndex(1)

    def keyPressEvent(self, event):
        """Handle key presses for navigation"""
        
        # Down key - refresh current file or move to next
        if event.key() == Qt.Key.Key_Down:
            if self._current_file_path:
                # Refresh current preview
                self.preview_file(self._current_file_path)
            event.accept()
            return
        
        # Up key - refresh current file or move to previous  
        elif event.key() == Qt.Key.Key_Up:
            if self._current_file_path:
                # Refresh current preview
                self.preview_file(self._current_file_path)
            event.accept()
            return
        
        # R key - refresh
        elif event.key() == Qt.Key.Key_R and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if self._current_file_path:
                self.preview_file(self._current_file_path)
            event.accept()
            return
        
        # Pass other keys to parent
        super().keyPressEvent(event)
    
    def preview_file(self, file_path):
        """Start preview for a file"""
        if not file_path or not os.path.isfile(file_path):
            self.clear_preview()
            return
        
        # Cancel any existing preview
        self._cleanup_thread()
        
        # Store current file path
        self._current_file_path = file_path
        
        # Update header
        self.file_label.setText(os.path.basename(file_path))
        self.copy_btn.setEnabled(False)
        
        # Reset zoom
        self.zoom_reset()
        
        # Check if file is supported
        if not self.preview_manager.is_supported(file_path):
            self.show_unsupported_file(file_path, self.preview_manager)
            return
        
        # Show progress for binary files
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.lsf', '.lsbs', '.lsbc', '.lsfx']:
            self.show_progress(True)
        
        # Start preview thread
        self.preview_thread = FilePreviewThread(
            self, self.preview_manager, file_path, 
            self.wine_wrapper, self.parser
        )
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
            content += "Supported types: " + ", ".join(
                preview_manager.get_supported_extensions()
            )
            
            self.content_text.setPlainText(content)
            self.thumbnail_label.clear_pixmap()
            self.thumbnail_label.setText("📄\nUnsupported File")
            self.show_progress(False)
            self.copy_btn.setEnabled(True)
        except Exception as e:
            self.content_text.setPlainText(f"Error analyzing file: {e}")
            self.thumbnail_label.clear_pixmap()
            self.thumbnail_label.setText("❌\nError")
            self.show_progress(False)
    
    def display_preview(self, preview_data):
        """Display preview data from thread"""
        self.show_progress(False)
        
        if not preview_data:
            self.content_text.setPlainText("No preview data received")
            self.display_stack.setCurrentIndex(1)  # Show text view
            return
        
        # Check if we have a thumbnail
        thumbnail = preview_data.get('thumbnail')
        file_ext = preview_data.get('extension', '').lower()
        
        # Decide which view to show
        if thumbnail and isinstance(thumbnail, QPixmap):
            # Show thumbnail view
            self.display_stack.setCurrentIndex(0)
            self.thumbnail_label.set_pixmap(thumbnail)
            self.enable_zoom_controls(True)
            self.copy_btn.setEnabled(False)  # Can't copy image
        elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.dds']:
            # Image file - try to load or show placeholder
            self.display_stack.setCurrentIndex(0)
            self._set_default_thumbnail_text(preview_data)
            self.enable_zoom_controls(False)
            self.copy_btn.setEnabled(False)
        else:
            # Text content - show in text view
            self.display_stack.setCurrentIndex(1)
            content = preview_data.get('content', 'No content available')
            self.content_text.setPlainText(content)
            self.copy_btn.setEnabled(True)
            self.enable_zoom_controls(False)
    
    def _set_default_thumbnail_text(self, preview_data):
        """Set default thumbnail text based on file type"""
        file_ext = preview_data.get('extension', '').lower()
        
        # Check if current file is an image we should try to load directly
        if self._current_file_path and file_ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            try:
                pixmap = QPixmap(self._current_file_path)
                if not pixmap.isNull():
                    self.thumbnail_label.set_pixmap(pixmap)
                    self.enable_zoom_controls(True)
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
        self.thumbnail_label.clear_pixmap()
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
        self._cleanup_thread()
        
        self.file_label.setText("No file selected")
        self.content_text.clear()
        self.thumbnail_label.clear_pixmap()
        self.thumbnail_label.setText("Select a file to preview")
        self.display_stack.setCurrentIndex(1)  # Default to text view
        self.show_progress(False)
        self._current_file_path = None
        self.copy_btn.setEnabled(False)
        self.enable_zoom_controls(False)
        self.zoom_reset()
    
    def copy_content(self):
        """Copy preview content to clipboard"""
        content = self.content_text.toPlainText()
        if content:
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            
            # Show temporary feedback
            original_text = self.copy_btn.text()
            self.copy_btn.setText("✓ Copied!")
            self.copy_btn.setEnabled(False)
            
            # Reset after 1 second
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self._reset_copy_button(original_text))
    
    def _reset_copy_button(self, original_text):
        """Reset copy button to original state"""
        self.copy_btn.setText(original_text)
        self.copy_btn.setEnabled(True)
    
    def enable_zoom_controls(self, enabled):
        """Enable or disable zoom controls"""
        self.zoom_in_btn.setEnabled(enabled)
        self.zoom_out_btn.setEnabled(enabled)
        self.zoom_slider.setEnabled(enabled)
        self.zoom_reset_btn.setEnabled(enabled)
    
    def zoom_in(self):
        """Zoom in by 25%"""
        new_zoom = min(400, self._current_zoom + 25)
        self.zoom_slider.setValue(new_zoom)
    
    def zoom_out(self):
        """Zoom out by 25%"""
        new_zoom = max(25, self._current_zoom - 25)
        self.zoom_slider.setValue(new_zoom)
    
    def zoom_reset(self):
        """Reset zoom to 100%"""
        self.zoom_slider.setValue(100)
    
    def on_zoom_changed(self, value):
        """Handle zoom slider change"""
        self._current_zoom = value
        self.zoom_label.setText(f"{value}%")
        
        # Update thumbnail display
        zoom_factor = value / 100.0
        self.thumbnail_label.set_zoom(zoom_factor)
        
        # Emit signal
        self.zoom_changed.emit(value)
    
    def set_content(self, content):
        """Directly set content text"""
        self.content_text.setPlainText(content)
        self.copy_btn.setEnabled(True)
    
    def set_thumbnail(self, pixmap):
        """Directly set thumbnail pixmap"""
        if pixmap and isinstance(pixmap, QPixmap):
            self.thumbnail_label.set_pixmap(pixmap)
            self.enable_zoom_controls(True)
        else:
            self.thumbnail_label.clear_pixmap()
            self.enable_zoom_controls(False)
    
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
                pass
            
            # Cancel and wait for thread to finish
            try:
                self.preview_thread.cancel()
                self.preview_thread.quit()
                if not self.preview_thread.wait(2000):
                    self.preview_thread.terminate()
                    self.preview_thread.wait(1000)
            except RuntimeError:
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
            pass
    
    def closeEvent(self, event):
        """Handle widget close event"""
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
            pass