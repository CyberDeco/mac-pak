#!/usr/bin/env python3
"""
Progress bar funcs
"""

import os
import time
from collections import deque

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

class ProgressDialog(QWidget):
    """Native Mac-style progress dialog"""
    
    # Add signal for cancellation
    canceled = pyqtSignal()
    
    def __init__(self, parent, message, cancel_text="Cancel", min_val=0, max_val=100):
        super().__init__(parent, Qt.WindowType.Sheet)
        self.setWindowTitle("Operation Progress")
        self.setFixedSize(400, 180)  # Increased height for time label
        self.setWindowModality(Qt.WindowModality.WindowModal)
        
        self._canceled = False
        self._message = message
        self._min = min_val
        self._max = max_val
        
        self.start_time = None
        self.progress_samples = deque(maxlen=10)  # Last 10 samples
        
        self.setup_ui()
        self.center_on_parent()
    
    def setup_ui(self):
        """Setup the progress dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # File info label
        self.file_info_label = QLabel("")
        self.file_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.file_info_label)
        
        # Progress label
        self.status_label = QLabel(self._message)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress bar with Mac styling
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(self._min)
        self.progress_bar.setMaximum(self._max)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Time label
        self.time_label = QLabel("")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(self.time_label)
        
        # Cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def _on_cancel_clicked(self):
        """Handle cancel button click"""
        self._canceled = True
        self.canceled.emit()
        self.close()
    
    def setValue(self, value):
        """Set progress with smoothed time estimation"""
        current_time = time.time()
        
        if self.start_time is None:
            self.start_time = current_time
        
        self.progress_bar.setValue(value)
        
        # Store sample
        elapsed = current_time - self.start_time
        self.progress_samples.append((elapsed, value))
        
        if value > 5 and value < self._max and len(self.progress_samples) >= 2:
            # Calculate rate from samples
            oldest = self.progress_samples[0]
            newest = self.progress_samples[-1]
            
            time_diff = newest[0] - oldest[0]
            progress_diff = newest[1] - oldest[1]
            
            if time_diff > 0 and progress_diff > 0:
                rate = progress_diff / time_diff
                remaining_progress = self._max - value
                estimated_seconds = remaining_progress / rate
                
                self._update_time_label(elapsed, estimated_seconds)
        
        elif value >= self._max:
            if self.start_time:
                elapsed = time.time() - self.start_time
                self.time_label.setText(f"Completed in {self._format_time(elapsed)}")
            self.cancel_button.setText("Close")
            self.cancel_button.clicked.disconnect()
            self.cancel_button.clicked.connect(self.close)
    
    def _update_time_label(self, elapsed, remaining):
        """Update the time display"""
        elapsed_str = self._format_time(elapsed)
        remaining_str = self._format_time(remaining)
        self.time_label.setText(f"Elapsed: {elapsed_str} | Remaining: ~{remaining_str}")
    
    def _format_time(self, seconds):
        """Format seconds into readable time"""
        if seconds < 0:
            return "0s"
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def setLabelText(self, text):
        """Set status text (QProgressDialog compatible)"""
        self.status_label.setText(text)
    
    def wasCanceled(self):
        """Check if dialog was cancelled (QProgressDialog compatible)"""
        return self._canceled
    
    def setRange(self, min_val, max_val):
        """Set progress range"""
        self._min = min_val
        self._max = max_val
        self.progress_bar.setMinimum(min_val)
        self.progress_bar.setMaximum(max_val)
    
    def reset(self):
        """Reset the dialog"""
        self._canceled = False
        self.progress_bar.setValue(0)
        self.start_time = None
        self.progress_samples.clear()
        self.time_label.setText("")
    
    def closeEvent(self, event):
        """Handle close event"""
        if not self._canceled and self.progress_bar.value() < self._max:
            # Closing without completing - treat as cancel
            self._canceled = True
            self.canceled.emit()
        event.accept()
    
    # Custom methods
    def update_progress(self, percentage, message):
        """Update progress display (convenience method)"""
        self.setValue(percentage)
        self.setLabelText(message)
    
    def center_on_parent(self):
        """Center dialog on parent window"""
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
    
    def set_file_info(self, file_path):
        """Set file information"""
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            self.file_info_label.setText(f"📁 {file_name} ({size_mb:.1f} MB)")
        else:
            self.file_info_label.setText(f"📁 {os.path.basename(file_path)}")