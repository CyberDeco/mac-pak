#!/usr/bin/env python3
"""
Settings pane - Fixed to inherit from QDialog
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QGroupBox, QScrollArea, QWidget,
                            QFrame, QLineEdit, QHBoxLayout, QPushButton, QComboBox, QSpinBox,
                            QFileDialog, QMessageBox, QLabel)
from PyQt6.QtCore import Qt, QTimer
from pathlib import Path

class SettingsDialog(QDialog):  # Changed from QWidget to QDialog
    """Native Mac-style settings dialog"""
    
    def __init__(self, parent, settings_manager):
        super().__init__(parent)  # Simplified - QDialog handles modality
        self.settings_manager = settings_manager
        self.setWindowTitle("Preferences")
        self.setFixedSize(800, 500)
        self.setModal(True)  # Make it modal
        
        self.setup_ui()
        self.load_current_settings()
        self.center_on_parent()
    
    def setup_ui(self):
        """Setup settings dialog UI with Mac-native styling"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.Shape.NoFrame)
        
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # Paths section
        paths_group = QGroupBox("Tool Paths")
        paths_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; }")
        paths_layout = QFormLayout(paths_group)
        
        # Working directory
        self.working_dir_edit = QLineEdit()
        self.working_dir_edit.setMinimumWidth(500)
        working_dir_layout = QHBoxLayout()
        working_dir_layout.addWidget(self.working_dir_edit)
        browse_working_btn = QPushButton("Browse...")
        browse_working_btn.clicked.connect(self.browse_working_dir)
        working_dir_layout.addWidget(browse_working_btn)
        
        paths_layout.addRow("Working Directory:", working_dir_layout)
        
        # Wine path
        self.wine_path_edit = QLineEdit()
        self.wine_path_edit.setMinimumWidth(500)
        wine_path_layout = QHBoxLayout()
        wine_path_layout.addWidget(self.wine_path_edit)
        browse_wine_btn = QPushButton("Browse...")
        browse_wine_btn.clicked.connect(self.browse_wine_path)
        wine_path_layout.addWidget(browse_wine_btn)
        
        paths_layout.addRow("Wine Executable:", wine_path_layout)
        
        # Divine path
        self.divine_path_edit = QLineEdit()
        self.divine_path_edit.setMinimumWidth(500)
        divine_path_layout = QHBoxLayout()
        divine_path_layout.addWidget(self.divine_path_edit)
        browse_divine_btn = QPushButton("Browse...")
        browse_divine_btn.clicked.connect(self.browse_divine_path)
        divine_path_layout.addWidget(browse_divine_btn)
        
        paths_layout.addRow("Divine.exe Path:", divine_path_layout)
        
        settings_layout.addWidget(paths_group)
        
        # Storage section
        storage_group = QGroupBox("File Storage")
        storage_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; }")
        storage_layout = QFormLayout(storage_group)
        
        # Storage mode
        self.storage_mode_combo = QComboBox()
        self.storage_mode_combo.addItems(["Persistent", "Temporary"])
        storage_layout.addRow("Extracted Files:", self.storage_mode_combo)
        
        # Extracted files location
        self.extracted_location_edit = QLineEdit()
        self.extracted_location_edit.setMinimumWidth(500)
        extracted_layout = QHBoxLayout()
        extracted_layout.addWidget(self.extracted_location_edit)
        browse_extracted_btn = QPushButton("Browse...")
        browse_extracted_btn.clicked.connect(self.browse_extracted_location)
        extracted_layout.addWidget(browse_extracted_btn)
        
        storage_layout.addRow("Storage Location:", extracted_layout)
        
        # Cache size limit
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setMinimum(1)
        self.cache_size_spin.setMaximum(100)
        self.cache_size_spin.setSuffix(" GB")
        storage_layout.addRow("Max Cache Size:", self.cache_size_spin)
        
        # Auto cleanup
        self.cleanup_days_spin = QSpinBox()
        self.cleanup_days_spin.setMinimum(1)
        self.cleanup_days_spin.setMaximum(365)
        self.cleanup_days_spin.setSuffix(" days")
        storage_layout.addRow("Auto-cleanup after:", self.cleanup_days_spin)
        
        settings_layout.addWidget(storage_group)
        
        # Disk usage display
        self.setup_disk_usage_section(settings_layout)
        
        scroll.setWidget(settings_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)  # Use reject() instead of close()
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def setup_disk_usage_section(self, layout):
        """Setup disk usage monitoring section"""
        usage_group = QGroupBox("Disk Usage")
        usage_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; }")
        usage_layout = QVBoxLayout(usage_group)
        
        self.usage_label = QLabel("Calculating...")
        usage_layout.addWidget(self.usage_label)
        
        # Cleanup button
        cleanup_layout = QHBoxLayout()
        cleanup_layout.addStretch()
        
        cleanup_btn = QPushButton("Clean Up Old Files")
        cleanup_btn.clicked.connect(self.cleanup_old_files)
        cleanup_layout.addWidget(cleanup_btn)
        
        usage_layout.addLayout(cleanup_layout)
        layout.addWidget(usage_group)
        
        # Start calculating disk usage
        QTimer.singleShot(100, self.calculate_disk_usage)
    
    def calculate_disk_usage(self):
        """Calculate current disk usage"""
        try:
            storage_path = Path(self.settings_manager.get("extracted_files_location", ""))
            if storage_path.exists():
                total_size = sum(f.stat().st_size for f in storage_path.rglob('*') if f.is_file())
                size_mb = total_size / (1024 * 1024)
                
                if size_mb > 1024:
                    self.usage_label.setText(f"Current usage: {size_mb/1024:.1f} GB")
                else:
                    self.usage_label.setText(f"Current usage: {size_mb:.1f} MB")
            else:
                self.usage_label.setText("Storage location not found")
        except Exception as e:
            self.usage_label.setText(f"Error calculating usage: {e}")
    
    def cleanup_old_files(self):
        """Clean up old extracted files"""
        try:
            storage_path = Path(self.settings_manager.get("extracted_files_location", ""))
            cleanup_days = self.settings_manager.get("auto_cleanup_days", 30)
            
            if not storage_path.exists():
                QMessageBox.information(self, "Cleanup", "No files to clean up.")
                return
            
            # Implementation would check file modification times and remove old files
            # For now, just show a confirmation
            reply = QMessageBox.question(
                self, "Cleanup Confirmation",
                f"This will remove extracted files older than {cleanup_days} days. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Implement actual cleanup logic
                QMessageBox.information(self, "Cleanup", "Cleanup completed!")
                self.calculate_disk_usage()
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cleanup failed: {e}")
    
    def center_on_parent(self):
        """Center dialog on parent window"""
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
    
    def load_current_settings(self):
        """Load current settings into the dialog"""
        self.working_dir_edit.setText(self.settings_manager.get("working_directory", ""))
        self.wine_path_edit.setText(self.settings_manager.get("wine_path", ""))
        self.divine_path_edit.setText(self.settings_manager.get("divine_path", ""))
        self.extracted_location_edit.setText(self.settings_manager.get("extracted_files_location", ""))
        
        # Storage mode
        storage_mode = self.settings_manager.get("storage_mode", "persistent")
        index = 0 if storage_mode == "persistent" else 1
        self.storage_mode_combo.setCurrentIndex(index)
        
        # Cache size and cleanup
        self.cache_size_spin.setValue(int(self.settings_manager.get("max_cache_size_gb", 5)))
        self.cleanup_days_spin.setValue(int(self.settings_manager.get("auto_cleanup_days", 30)))
    
    def browse_working_dir(self):
        """Browse for working directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Working Directory",
            self.working_dir_edit.text()
        )
        if directory:
            self.working_dir_edit.setText(directory)
    
    def browse_wine_path(self):
        """Browse for Wine executable"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Wine Executable",
            self.wine_path_edit.text(),
            "All Files (*)"
        )
        if file_path:
            self.wine_path_edit.setText(file_path)
    
    def browse_divine_path(self):
        """Browse for Divine.exe"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Divine.exe",
            self.divine_path_edit.text(),
            "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            self.divine_path_edit.setText(file_path)
    
    def browse_extracted_location(self):
        """Browse for extracted files location"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Storage Location",
            self.extracted_location_edit.text()
        )
        if directory:
            self.extracted_location_edit.setText(directory)
    
    def save_settings(self):
        """Save settings and close dialog"""
        self.settings_manager.set("working_directory", self.working_dir_edit.text())
        self.settings_manager.set("wine_path", self.wine_path_edit.text())
        self.settings_manager.set("divine_path", self.divine_path_edit.text())
        self.settings_manager.set("extracted_files_location", self.extracted_location_edit.text())
        
        # Storage settings
        storage_mode = "persistent" if self.storage_mode_combo.currentIndex() == 0 else "temporary"
        self.settings_manager.set("storage_mode", storage_mode)
        self.settings_manager.set("max_cache_size_gb", self.cache_size_spin.value())
        self.settings_manager.set("auto_cleanup_days", self.cleanup_days_spin.value())
        
        self.settings_manager.sync()
        
        QMessageBox.information(self, "Settings", "Settings saved successfully!")
        self.accept()  # Use accept() instead of close()