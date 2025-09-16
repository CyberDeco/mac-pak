#!/usr/bin/env python3
"""
Progress bar funcs
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt

class ProgressDialog(QWidget):
    """Native Mac-style progress dialog"""
    
    def __init__(self, parent, title):
        super().__init__(parent, Qt.WindowType.Sheet)
        self.setWindowTitle(title)
        self.setFixedSize(400, 150)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        
        self.setup_ui()
        self.center_on_parent()
        
        # Reference to the operation thread for cancellation
        self.operation_thread = None
    
    def setup_ui(self):
        """Setup the progress dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # File info label (add this)
        self.file_info_label = QLabel("")
        self.file_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.file_info_label)
        
        # Progress label
        self.status_label = QLabel("Preparing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress bar with Mac styling
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_operation)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def update_progress(self, percentage, message):
        """Update progress display"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
        
        if percentage >= 100:
            self.cancel_button.setText("Close")
    
    def set_operation_thread(self, thread):
        """Set the operation thread for cancellation"""
        self.operation_thread = thread
    
    def cancel_operation(self):
        """Cancel operation or close dialog"""
        if self.operation_thread and self.operation_thread.isRunning():
            self.operation_thread.cancel_operation()
            self.operation_thread.quit()
            self.operation_thread.wait(3000)
        
        self.close()
    
    def center_on_parent(self):
        """Center dialog on parent window"""
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
    
    def set_file_info(self, file_path):
        """Set file information"""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        size_mb = file_size / (1024 * 1024)
        
        self.file_info_label.setText(f"📁 {file_name} ({size_mb:.1f} MB)")