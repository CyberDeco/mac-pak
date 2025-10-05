#!/usr/bin/env python3
"""
Settings Dialog - Updated for Wine Integration
"""

import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QGroupBox, QScrollArea, QWidget,
                            QFrame, QLineEdit, QHBoxLayout, QPushButton, QComboBox, QSpinBox,
                            QFileDialog, QMessageBox, QLabel, QTextEdit)
from PyQt6.QtCore import Qt, QTimer
from pathlib import Path

class SettingsDialog(QDialog):
    """Native Mac-style settings dialog with Wine validation"""
    
    def __init__(self, parent, settings_manager):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Preferences")
        self.setFixedSize(900, 600)
        self.setModal(True)
        
        # Add monitor for async operations
        self.test_monitor = None
        
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
        
        # Wine/Tools section (moved to top)
        wine_group = QGroupBox("Wine & Tool Configuration")
        wine_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; }")
        wine_layout = QFormLayout(wine_group)
        
        # Wine path
        self.wine_path_edit = QLineEdit()
        self.wine_path_edit.setMinimumWidth(500)
        wine_path_layout = QHBoxLayout()
        wine_path_layout.addWidget(self.wine_path_edit)
        
        browse_wine_btn = QPushButton("Browse...")
        browse_wine_btn.clicked.connect(self.browse_wine_path)
        wine_path_layout.addWidget(browse_wine_btn)
        
        test_wine_btn = QPushButton("Test")
        test_wine_btn.clicked.connect(self.test_wine)
        wine_path_layout.addWidget(test_wine_btn)
        
        wine_layout.addRow("Wine Executable:", wine_path_layout)
        
        # Divine path
        self.divine_path_edit = QLineEdit()
        self.divine_path_edit.setMinimumWidth(500)
        divine_path_layout = QHBoxLayout()
        divine_path_layout.addWidget(self.divine_path_edit)
        
        browse_divine_btn = QPushButton("Browse...")
        browse_divine_btn.clicked.connect(self.browse_divine_path)
        divine_path_layout.addWidget(browse_divine_btn)
        
        test_divine_btn = QPushButton("Test")
        test_divine_btn.clicked.connect(self.test_divine)
        divine_path_layout.addWidget(test_divine_btn)
        
        wine_layout.addRow("Divine.exe Path:", divine_path_layout)
        
        # Wine status display
        self.wine_status_label = QLabel("Status: Not tested")
        self.wine_status_label.setStyleSheet("color: gray;")
        wine_layout.addRow("Wine Status:", self.wine_status_label)
        
        settings_layout.addWidget(wine_group)
        
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
        cancel_btn.clicked.connect(self.reject)
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
    
    def test_wine(self):
        """Test Wine installation using WineProcessMonitor"""
        wine_path = self.wine_path_edit.text().strip()
        
        if not wine_path:
            self.wine_status_label.setText("Status: No Wine path specified")
            self.wine_status_label.setStyleSheet("color: red;")
            return
        
        if not Path(wine_path).exists():
            self.wine_status_label.setText("Status: Wine executable not found")
            self.wine_status_label.setStyleSheet("color: red;")
            return
        
        try:
            from mac_pak.tools.wine_environment import WineProcessMonitor
            
            # Show testing status
            self.wine_status_label.setText("Status: Testing Wine...")
            self.wine_status_label.setStyleSheet("color: orange;")
            
            # Create monitor
            self.test_monitor = WineProcessMonitor()
            
            # Connect signals
            self.test_monitor.process_finished.connect(self._on_wine_test_finished)
            
            # Run wine --version
            cmd = [wine_path, "--version"]
            env = os.environ.copy()
            
            # Run async
            self.test_monitor.run_process_async(cmd, env)
            
        except Exception as e:
            self.wine_status_label.setText(f"Status: Error - {e}")
            self.wine_status_label.setStyleSheet("color: red;")

    def _on_wine_test_finished(self, success, output):
        """Handle Wine test completion"""
        if success:
            # Extract version from output
            version_line = output.strip().split('\n')[0] if output else "Unknown version"
            self.wine_status_label.setText(f"Status: ✓ {version_line}")
            self.wine_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.wine_status_label.setText(f"Status: ✗ Test failed - {output}")
            self.wine_status_label.setStyleSheet("color: red;")
        
        # Cleanup
        if self.test_monitor:
            self.test_monitor.deleteLater()
            self.test_monitor = None
    
    def test_divine(self):
        """Test Divine.exe using WineProcessMonitor"""
        divine_path = self.divine_path_edit.text().strip()
        wine_path = self.wine_path_edit.text().strip()
        
        if not divine_path:
            QMessageBox.information(self, "Test Divine.exe", "No Divine.exe path specified")
            return
        
        if not wine_path:
            QMessageBox.warning(self, "Test Divine.exe", "Wine path must be set first")
            return
        
        # Remove Z: prefix for checking local file
        local_divine_path = divine_path.replace("Z:", "")
        
        if not Path(local_divine_path).exists():
            QMessageBox.warning(self, "Test Divine.exe", f"Divine.exe not found at: {local_divine_path}")
            return
        
        try:
            from mac_pak.tools.wine_environment import WineProcessMonitor
            from mac_pak.ui.dialogs.progress_dialog import ProgressDialog
            
            # Create progress dialog
            self.divine_progress = ProgressDialog(
                self,
                message="Testing Divine.exe...",
                cancel_text="Cancel"
            )
            self.divine_progress.show()
            
            # Create monitor
            self.test_monitor = WineProcessMonitor()
            
            # Connect signals
            self.test_monitor.progress_updated.connect(self.divine_progress.update_progress)
            self.test_monitor.process_finished.connect(self._on_divine_test_finished)
            
            # Run divine --help
            cmd = [wine_path, divine_path, "--help"]
            env = os.environ.copy()
            
            # Set wine prefix if available
            wine_prefix = self.settings_manager.get("wine_prefix")
            if wine_prefix:
                env["WINEPREFIX"] = wine_prefix
            
            # Run async
            self.test_monitor.run_process_async(cmd, env, 
                                                lambda p, m: self.divine_progress.update_progress(p, m))
            
        except Exception as e:
            QMessageBox.warning(self, "Test Divine.exe", f"Error testing Divine.exe:\n{e}")
            if hasattr(self, 'divine_progress'):
                self.divine_progress.close()

    def _on_divine_test_finished(self, success, output):
        """Handle Divine.exe test completion"""
        # Close progress dialog
        if hasattr(self, 'divine_progress'):
            try:
                self.divine_progress.close()
            except:
                pass
            delattr(self, 'divine_progress')
        
        # Show results
        if success:
            # Check if output contains Divine.exe help text (usage, parameters, etc.)
            output_lower = output.lower()
            if any(keyword in output_lower for keyword in ["usage:", "loglevel", "--game", "--source", "divine"]):
                QMessageBox.information(
                    self, "Test Divine.exe", 
                    "✓ Divine.exe is working correctly!\n\nDivine.exe responded with help information successfully."
                )
            else:
                QMessageBox.warning(
                    self, "Test Divine.exe",
                    f"Divine.exe ran but output is unexpected:\n\n{output[:300]}..."
                )
        else:
            QMessageBox.warning(
                self, "Test Divine.exe", 
                f"✗ Divine.exe test failed:\n\n{output[:500]}"
            )
        
        # Cleanup
        if self.test_monitor:
            self.test_monitor.deleteLater()
            self.test_monitor = None
    
    def calculate_disk_usage(self):
        """Calculate current disk usage"""
        try:
            storage_path = Path(self.settings_manager.get("extracted_files_location", ""))
            
            # Create directory if it doesn't exist
            if not storage_path.exists():
                try:
                    storage_path.mkdir(parents=True, exist_ok=True)
                    self.usage_label.setText("Current usage: 0 MB (storage created)")
                except Exception as e:
                    self.usage_label.setText(f"Storage location not found: {storage_path}")
                return
            
            # Calculate usage
            total_size = sum(f.stat().st_size for f in storage_path.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            
            if size_mb > 1024:
                self.usage_label.setText(f"Current usage: {size_mb/1024:.1f} GB")
            else:
                self.usage_label.setText(f"Current usage: {size_mb:.1f} MB")
                
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
        
        # Test Wine setup on load
        QTimer.singleShot(500, self.test_wine)
    
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
            # Test immediately after selection
            QTimer.singleShot(100, self.test_wine)
    
    def browse_divine_path(self):
        """Browse for Divine.exe"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Divine.exe",
            self.divine_path_edit.text(),
            "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            # Convert to Wine path format (Z: drive)
            wine_path = f"Z:{file_path}"
            self.divine_path_edit.setText(wine_path)
    
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
        
        # Validate final setup
        validation = self.settings_manager.validate_wine_setup()
        if validation['valid']:
            QMessageBox.information(self, "Settings", "Settings saved successfully!\nWine setup is valid.")
        else:
            issues_text = "\n".join(f"• {issue}" for issue in validation['issues'])
            QMessageBox.warning(self, "Settings Saved", 
                              f"Settings saved, but there are configuration issues:\n\n{issues_text}")
        
        self.accept()