#!/usr/bin/env python3
"""
For PAK tab drag & drop
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

class DropLabel(QLabel):
    """Custom label that accepts drag and drop operations"""
    
    file_dropped = pyqtSignal(str)  # Signal emitted when file is dropped
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            # Check if any of the dragged files are PAK files
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.pak'):
                    event.acceptProposedAction()
                    self.setStyleSheet(self.styleSheet() + """
                        QLabel {
                            border-color: #007AFF !important;
                            background-color: #f0f8ff !important;
                        }
                    """)
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """Reset styling when drag leaves"""
        # Reset to original styling
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                padding: 20px;
                background-color: #f9f9f9;
                color: #666;
            }
            QLabel:hover {
                border-color: #007AFF;
                background-color: #f0f8ff;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events"""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.pak'):
                self.file_dropped.emit(file_path)
                break
        
        # Reset styling
        self.dragLeaveEvent(event)
        event.acceptProposedAction()