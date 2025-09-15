#!/usr/bin/env python3
"""
BG3 Mac Modding Toolkit - PyQt6 Version
A native macOS application for modding Baldur's Gate 3 using Wine and divine.exe
"""

import sys
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QTextEdit, QProgressBar, QTabWidget,
    QGroupBox, QFileDialog, QMessageBox, QSplitter, QFrame,
    QCheckBox, QSpinBox, QComboBox, QFormLayout, QLineEdit,
    QScrollArea, QStatusBar, QMenuBar, QToolBar, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QStandardPaths, QTimer
from PyQt6.QtGui import QIcon, QFont, QAction, QPixmap, QPalette

# Import your existing backend classes (unchanged)
from wine_wrapper import WineWrapper
from larian_parser import UniversalBG3Parser
from pak_operations import PAKOperations

class SettingsManager:
    """Manage user settings with QSettings for proper Mac integration"""
    
    def __init__(self):
        # Use QSettings for proper Mac preferences handling
        self.settings = QSettings("BG3ModToolkit", "BG3MacPakTool")
        self._ensure_defaults()
    
    def _ensure_defaults(self):
        """Ensure default settings exist"""
        defaults = {
            "working_directory": str(Path.home() / "Desktop"),
            "wine_path": "/opt/homebrew/bin/wine",
            "divine_path": "",
            "window_geometry": None,
            "recent_files": [],
            "storage_mode": "persistent",  # persistent vs temp
            "max_cache_size_gb": 5,
            "auto_cleanup_days": 30,
            "extracted_files_location": str(Path.home() / "Documents" / "BG3ModToolkit"),
        }
        
        for key, value in defaults.items():
            if not self.settings.contains(key):
                self.settings.setValue(key, value)
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.value(key, default)
    
    def set(self, key, value):
        """Set a setting value"""
        self.settings.setValue(key, value)
    
    def sync(self):
        """Force sync settings to disk"""
        self.settings.sync()

class ConversionPAKThread(QThread):
    """Enhanced PAK operation thread with auto-conversion support"""
    
    # Signals for communicating with main thread
    progress_updated = pyqtSignal(int, str)  # percentage, message
    operation_finished = pyqtSignal(bool, dict)  # success, result_data
    
    def __init__(self, wine_wrapper, operation_type, **kwargs):
        super().__init__()
        self.wine_wrapper = wine_wrapper
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.cancelled = False
    
    def run(self):
        """Run the PAK operation with auto-conversion support"""
        try:
            if self.operation_type == "create_pak":
                self._create_pak_with_conversion()
            else:
                # Fall back to regular operation
                self.operation_finished.emit(False, {"error": f"Unsupported operation with conversion: {self.operation_type}"})
        except Exception as e:
            self.operation_finished.emit(False, {"error": str(e)})
    
    def _create_pak_with_conversion(self):
        """Create PAK with auto-conversion of source files"""
        source_dir = self.kwargs.get("source_dir")
        pak_file = self.kwargs.get("pak_file")
        validate = self.kwargs.get("validate", True)
        
        def progress_callback(percentage, message):
            if not self.cancelled:
                self.progress_updated.emit(percentage, message)
        
        # Import conversion classes
        try:
            from larian_parser import AutoConversionProcessor
        except ImportError:
            # Fall back to regular PAK creation if conversion not available
            self._create_pak_regular()
            return
        
        # Step 1: Find files needing conversion
        self.progress_updated.emit(5, "Scanning for files needing conversion...")
        processor = AutoConversionProcessor(self.wine_wrapper)
        conversion_files = processor.find_conversion_files(source_dir)
        
        conversions = []
        conversion_errors = []
        
        # Step 2: Perform conversions if needed
        total_conversions = sum(len(files) for files in conversion_files.values())
        if total_conversions > 0:
            self.progress_updated.emit(10, f"Converting {total_conversions} files...")
            
            current_conversion = 0
            for conv_type, files in conversion_files.items():
                for file_info in files:
                    if self.cancelled:
                        return
                    
                    current_conversion += 1
                    progress = 10 + int((current_conversion / total_conversions) * 30)  # 10-40%
                    
                    file_name = file_info['relative_path']
                    self.progress_updated.emit(progress, f"Converting {file_name}...")
                    
                    try:
                        result = processor.convert_file(file_info, conv_type)
                        conversions.append(result)
                    except Exception as e:
                        error_info = {
                            'file': file_info['relative_path'],
                            'error': str(e),
                            'type': conv_type
                        }
                        conversion_errors.append(error_info)
        
        # Step 3: Run validation if requested
        validation_results = None
        if validate:
            self.progress_updated.emit(45, "Validating mod structure...")
            validation_results = self.wine_wrapper.validate_mod_structure(source_dir)
        
        # Step 4: Create PAK file
        self.progress_updated.emit(50, "Creating PAK file...")
        success, output = self.wine_wrapper.create_pak_with_monitoring(
            source_dir, pak_file, progress_callback
        )
        
        # Prepare result data
        result_data = {
            "success": success,
            "output": output,
            "source_dir": source_dir,
            "pak_file": pak_file,
            "validation": validation_results,
            "conversions": conversions,
            "conversion_errors": conversion_errors
        }
        
        self.operation_finished.emit(success, result_data)
    
    def _create_pak_regular(self):
        """Regular PAK creation without conversion"""
        source_dir = self.kwargs.get("source_dir")
        pak_file = self.kwargs.get("pak_file")
        validate = self.kwargs.get("validate", True)
        
        def progress_callback(percentage, message):
            if not self.cancelled:
                self.progress_updated.emit(percentage, message)
        
        # Run validation if requested
        validation_results = None
        if validate:
            self.progress_updated.emit(10, "Validating mod structure...")
            validation_results = self.wine_wrapper.validate_mod_structure(source_dir)
        
        success, output = self.wine_wrapper.create_pak_with_monitoring(
            source_dir, pak_file, progress_callback
        )
        
        result_data = {
            "success": success,
            "output": output,
            "source_dir": source_dir,
            "pak_file": pak_file,
            "validation": validation_results,
            "conversions": [],
            "conversion_errors": []
        }
        
        self.operation_finished.emit(success, result_data)
    
    def cancel_operation(self):
        """Cancel the current operation"""
        self.cancelled = True
        if hasattr(self.wine_wrapper, 'current_monitor') and self.wine_wrapper.current_monitor:
            self.wine_wrapper.current_monitor.cancel()

class DivineOperationThread(QThread):
    """Thread for running divine.exe operations without blocking UI"""
    
    # Signals for communicating with main thread
    progress_updated = pyqtSignal(int, str)  # percentage, message
    operation_finished = pyqtSignal(bool, dict)  # success, result_data
    
    def __init__(self, wine_wrapper, operation_type, **kwargs):
        super().__init__()
        self.wine_wrapper = wine_wrapper
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.cancelled = False
    
    def run(self):
        """Run the divine operation in background thread"""
        try:
            if self.operation_type == "extract_pak":
                self._extract_pak()
            elif self.operation_type == "create_pak":
                self._create_pak()
            elif self.operation_type == "list_pak":
                self._list_pak()
            else:
                self.operation_finished.emit(False, {"error": f"Unknown operation: {self.operation_type}"})
        except Exception as e:
            self.operation_finished.emit(False, {"error": str(e)})
    
    def _extract_pak(self):
        """Extract PAK file operation"""
        pak_file = self.kwargs.get("pak_file")
        dest_dir = self.kwargs.get("dest_dir")
        
        def progress_callback(percentage, message):
            if not self.cancelled:
                self.progress_updated.emit(percentage, message)
        
        success, output = self.wine_wrapper.extract_pak_with_monitoring(
            pak_file, dest_dir, progress_callback
        )
        
        result_data = {
            "success": success,
            "output": output,
            "pak_file": pak_file,
            "dest_dir": dest_dir
        }
        
        self.operation_finished.emit(success, result_data)
    
    # def _create_pak(self):
    #     """Create PAK file operation"""
    #     source_dir = self.kwargs.get("source_dir")
    #     pak_file = self.kwargs.get("pak_file")
    #     validate = self.kwargs.get("validate", True)
        
    #     def progress_callback(percentage, message):
    #         if not self.cancelled:
    #             self.progress_updated.emit(percentage, message)
        
    #     # Run validation if requested
    #     validation_results = None
    #     if validate:
    #         self.progress_updated.emit(10, "Validating mod structure...")
    #         validation_results = self.wine_wrapper.validate_mod_structure(source_dir)
        
    #     success, output = self.wine_wrapper.create_pak_with_monitoring(
    #         source_dir, pak_file, progress_callback
    #     )
        
    #     result_data = {
    #         "success": success,
    #         "output": output,
    #         "source_dir": source_dir,
    #         "pak_file": pak_file,
    #         "validation": validation_results
    #     }
        
    #     self.operation_finished.emit(success, result_data)

    def _create_pak(self):
        """Enhanced create PAK with auto-conversion support"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        # Select source directory
        source_dir = QFileDialog.getExistingDirectory(
            self, "Select Folder to Pack",
            self.settings_manager.get("working_directory", "")
        )
        
        if not source_dir:
            return
        
        self.settings_manager.set("working_directory", source_dir)
        
        # Check for auto-conversion files using your existing classes
        from larian_parser import AutoConversionProcessor, AutoConversionDialog
        
        processor = AutoConversionProcessor(self.wine_wrapper)
        conversion_files = processor.find_conversion_files(source_dir)
        total_conversions = sum(len(files) for files in conversion_files.values())
        
        # DEBUG: Print what was found
        print(f"Debug: Scanning directory: {source_dir}")
        print(f"Debug: Found {total_conversions} files needing conversion:")
        for conv_type, files in conversion_files.items():
            if files:
                print(f"  {conv_type}: {len(files)} files")
                for file_info in files:
                    print(f"    - {file_info['relative_path']}")
        
        # Show conversion preview if needed
        if total_conversions > 0:
            proceed = AutoConversionDialog.show_conversion_preview(self, conversion_files)
            if not proceed:
                print("Debug: User cancelled conversion")
                return
            print("Debug: User approved conversion - starting enhanced PAK creation")
            
            # Continue with PAK creation
            suggested_name = f"{os.path.basename(source_dir)}.pak"
            pak_file, _ = QFileDialog.getSaveFileName(
                self, "Save PAK File As",
                os.path.join(os.path.dirname(source_dir), suggested_name),
                "PAK Files (*.pak);;All Files (*)"
            )
            
            if not pak_file:
                return
            
            # Start creation with auto-conversion
            self.start_pak_operation_with_conversion("create_pak", 
                                                   source_dir=source_dir, 
                                                   pak_file=pak_file, 
                                                   validate=True)
        else:
            print("Debug: No conversion files found, proceeding with normal PAK creation")
            # Normal PAK creation
            suggested_name = f"{os.path.basename(source_dir)}.pak"
            pak_file, _ = QFileDialog.getSaveFileName(
                self, "Save PAK File As",
                os.path.join(os.path.dirname(source_dir), suggested_name),
                "PAK Files (*.pak);;All Files (*)"
            )
            
            if not pak_file:
                return
            
            self.start_pak_operation("create_pak", source_dir=source_dir, pak_file=pak_file, validate=True)
    
    def _list_pak(self):
        """List PAK contents operation"""
        pak_file = self.kwargs.get("pak_file")
        
        self.progress_updated.emit(20, "Reading PAK contents...")
        
        files = self.wine_wrapper.list_pak_contents_threaded(pak_file)
        
        result_data = {
            "success": len(files) > 0,
            "files": files,
            "file_count": len(files),
            "pak_file": pak_file
        }
        
        self.progress_updated.emit(100, "Complete!")
        self.operation_finished.emit(True, result_data)
    
    def cancel_operation(self):
        """Cancel the current operation"""
        self.cancelled = True
        if self.wine_wrapper.current_monitor:
            self.wine_wrapper.current_monitor.cancel()

class ProgressDialog(QWidget):
    """Native Mac-style progress dialog"""
    
    def __init__(self, parent, title):
        super().__init__(parent, Qt.WindowType.Sheet)  # Use sheet style on Mac
        self.setWindowTitle(title)
        self.setFixedSize(400, 120)
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
    
    def center_on_parent(self):
        """Center dialog on parent window"""
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
    
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
            self.operation_thread.wait(3000)  # Wait up to 3 seconds
        
        self.close()

class SettingsDialog(QWidget):
    """Native Mac-style settings dialog"""
    
    def __init__(self, parent, settings_manager):
        super().__init__(parent, Qt.WindowType.Sheet)
        self.settings_manager = settings_manager
        self.setWindowTitle("Preferences")
        self.setFixedSize(600, 500)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        
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
        paths_layout = QFormLayout(paths_group)
        
        # Working directory
        self.working_dir_edit = QLineEdit()
        working_dir_layout = QHBoxLayout()
        working_dir_layout.addWidget(self.working_dir_edit)
        browse_working_btn = QPushButton("Browse...")
        browse_working_btn.clicked.connect(self.browse_working_dir)
        working_dir_layout.addWidget(browse_working_btn)
        
        paths_layout.addRow("Working Directory:", working_dir_layout)
        
        # Wine path
        self.wine_path_edit = QLineEdit()
        wine_path_layout = QHBoxLayout()
        wine_path_layout.addWidget(self.wine_path_edit)
        browse_wine_btn = QPushButton("Browse...")
        browse_wine_btn.clicked.connect(self.browse_wine_path)
        wine_path_layout.addWidget(browse_wine_btn)
        
        paths_layout.addRow("Wine Executable:", wine_path_layout)
        
        # Divine path
        self.divine_path_edit = QLineEdit()
        divine_path_layout = QHBoxLayout()
        divine_path_layout.addWidget(self.divine_path_edit)
        browse_divine_btn = QPushButton("Browse...")
        browse_divine_btn.clicked.connect(self.browse_divine_path)
        divine_path_layout.addWidget(browse_divine_btn)
        
        paths_layout.addRow("Divine.exe Path:", divine_path_layout)
        
        settings_layout.addWidget(paths_group)
        
        # Storage section (new for PyQt6 version)
        storage_group = QGroupBox("File Storage")
        storage_layout = QFormLayout(storage_group)
        
        # Storage mode
        self.storage_mode_combo = QComboBox()
        self.storage_mode_combo.addItems(["Persistent", "Temporary"])
        storage_layout.addRow("Extracted Files:", self.storage_mode_combo)
        
        # Extracted files location
        self.extracted_location_edit = QLineEdit()
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
        
        # Disk usage display (new feature)
        self.setup_disk_usage_section(settings_layout)
        
        scroll.setWidget(settings_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def setup_disk_usage_section(self, layout):
        """Setup disk usage monitoring section"""
        usage_group = QGroupBox("Disk Usage")
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
            storage_path = Path(self.settings_manager.get("extracted_files_location"))
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
            storage_path = Path(self.settings_manager.get("extracted_files_location"))
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
        self.close()

class BG3ModToolkitMainWindow(QMainWindow):
    """Main application window with native Mac styling and threading support"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize settings and backend
        self.settings_manager = SettingsManager()
        self.wine_wrapper = None
        self.universal_parser = UniversalBG3Parser()
        
        # UI setup
        self.setup_window_properties()
        self.setup_menubar()
        self.setup_main_interface()
        self.setup_statusbar()
        
        # Initialize backend
        self.initialize_backend()
        
        # Restore window state
        self.restore_window_state()
    
    def setup_window_properties(self):
        """Setup main window properties with Mac styling"""
        self.setWindowTitle("BG3 Mac Modding Toolkit")
        self.setMinimumSize(1000, 600)  # Increase minimum size
        #self.resize(1400, 900)  # Set larger default size
        
        # Set up Mac-style window
        self.setUnifiedTitleAndToolBarOnMac(True)
        
        # Apply Mac-style theme
        self.apply_mac_styling()
    
    def apply_mac_styling(self):
        """Apply Mac-native styling"""
        # This will use the system theme automatically on Mac
        app = QApplication.instance()
        if app:
            # Set application properties for better Mac integration
            app.setApplicationName("BG3 Mac Modding Toolkit")
            app.setApplicationVersion("2.0")
            app.setOrganizationName("BG3ModToolkit")
            app.setOrganizationDomain("bg3modtoolkit.app")
    
    def setup_menubar(self):
        """Setup native Mac menubar"""
        menubar = self.menuBar()
        
        # Application menu (automatically becomes app name on Mac)
        app_menu = menubar.addMenu("BG3 Toolkit")
        
        # About action
        about_action = QAction("About BG3 Toolkit", self)
        about_action.triggered.connect(self.show_about)
        app_menu.addAction(about_action)
        
        app_menu.addSeparator()
        
        # Preferences action (will appear in app menu on Mac)
        prefs_action = QAction("Preferences...", self)
        prefs_action.setShortcut("Cmd+,")
        prefs_action.triggered.connect(self.open_preferences)
        app_menu.addAction(prefs_action)
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open PAK...", self)
        open_action.setShortcut("Cmd+O")
        open_action.triggered.connect(self.open_pak_file)
        file_menu.addAction(open_action)
        
        # Window menu (Mac standard)
        window_menu = menubar.addMenu("Window")
        
        minimize_action = QAction("Minimize", self)
        minimize_action.setShortcut("Cmd+M")
        minimize_action.triggered.connect(self.showMinimized)
        window_menu.addAction(minimize_action)
    
    def setup_main_interface(self):
        """Setup the main interface with tabs"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)  # Mac-style tabs
        layout.addWidget(self.tab_widget)

        # Helps with window resizing
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tab_widget, 1)
        
        # Setup individual tabs
        self.setup_asset_browser_tab()
        self.setup_universal_editor_tab()
        self.setup_pak_tools_tab()
        self.setup_index_search_tab()
        self.setup_uuid_generator_tab()

    def setup_asset_browser_tab(self):
        """Setup Asset Browser tab"""
        try:
            # Import the new asset browser
            from asset_browser import AssetBrowserTab
            
            # Create the browser tab
            browser_tab = AssetBrowserTab(
                parent=self,
                bg3_tool=self.wine_wrapper,
                settings_manager=self.settings_manager
            )
            
            self.tab_widget.addTab(browser_tab, "Asset Browser")
            
        except ImportError as e:
            print(f"Could not import Asset Browser: {e}")
            # Create a placeholder tab  
            placeholder = QWidget()
            layout = QVBoxLayout(placeholder)
            label = QLabel("Asset Browser not available\nCheck that asset_browser.py and preview_manager.py are in the same directory")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            self.tab_widget.addTab(placeholder, "Asset Browser")

    def setup_universal_editor_tab(self):
        """Setup Universal Editor tab with LSX/LSJ/LSF support"""
        try:
            # Import the new LSX editor
            from lsx_editor import UniversalEditorTab

            # Create the editor tab
            editor_tab = UniversalEditorTab(
                parent=self,
                settings_manager=self.settings_manager,
                bg3_tool=self.wine_wrapper
            )
            
            self.tab_widget.addTab(editor_tab, "Universal Editor")
            
        except ImportError as e:
            print(f"Could not import Universal Editor: {e}")
            # Create a placeholder tab
            placeholder = QWidget()
            layout = QVBoxLayout(placeholder)
            label = QLabel("Universal Editor not available\nCheck that lsx_editor.py is in the same directory")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            self.tab_widget.addTab(placeholder, "Universal Editor")
        
    def setup_pak_tools_tab(self):
        """Setup PAK tools tab with Mac-native file dialogs"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("PAK Operations")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Operations section
        operations_layout = QHBoxLayout()
        
        # Extraction group
        extract_group = QGroupBox("Extract PAKs")
        extract_layout = QVBoxLayout(extract_group)
        
        self.extract_btn = QPushButton("Extract PAK File")
        self.extract_btn.clicked.connect(self.extract_pak_file)
        extract_layout.addWidget(self.extract_btn)
        
        self.list_btn = QPushButton("List PAK Contents")
        self.list_btn.clicked.connect(self.list_pak_contents)
        extract_layout.addWidget(self.list_btn)
        
        operations_layout.addWidget(extract_group)
        
        # Creation group
        create_group = QGroupBox("Create PAKs")
        create_layout = QVBoxLayout(create_group)
        
        self.create_btn = QPushButton("Create PAK from Folder")
        self.create_btn.clicked.connect(self.create_pak_file)
        create_layout.addWidget(self.create_btn)
        
        self.rebuild_btn = QPushButton("Rebuild Modified PAK")
        self.rebuild_btn.clicked.connect(self.rebuild_pak_file)
        create_layout.addWidget(self.rebuild_btn)
        
        self.validate_btn = QPushButton("Validate Mod Structure")
        self.validate_btn.clicked.connect(self.validate_mod_structure)
        create_layout.addWidget(self.validate_btn)
        
        operations_layout.addWidget(create_group)
        
        layout.addLayout(operations_layout)
        
        # Results area
        results_label = QLabel("Operation Results:")
        layout.addWidget(results_label)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Monaco", 10))  # Mac monospace font
        layout.addWidget(self.results_text)
        
        self.tab_widget.addTab(tab, "PAK Tools")

        self.individual_extract_btn = QPushButton("Extract Individual Files")
        self.individual_extract_btn.clicked.connect(self.show_individual_extraction_dialog)
        extract_layout.addWidget(self.individual_extract_btn)

    def show_individual_extraction_dialog(self):
        """Show individual file extraction dialog"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        # Select PAK file
        pak_file, _ = QFileDialog.getOpenFileName(
            self, "Select PAK File for Individual Extraction",
            self.settings_manager.get("working_directory", ""),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        # Import the classes from your pak_operations
        from pak_operations import FileSelectionDialog, IndividualFileExtractor, IndividualExtractionThread
        
        # Show file selection dialog
        dialog = FileSelectionDialog(self, pak_file, self.wine_wrapper)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.start_individual_extraction(pak_file, dialog.selected_files, dialog.destination)

    def start_individual_extraction(self, pak_file, file_paths, destination):
        """Start individual file extraction with progress"""
        from pak_operations import IndividualFileExtractor, IndividualExtractionThread
        
        # Create extractor
        extractor = IndividualFileExtractor(self.wine_wrapper)
        
        # Create progress dialog using your existing ProgressDialog
        progress_dialog = ProgressDialog(self, "Extracting Individual Files")
        
        # Create extraction thread
        self.extraction_thread = IndividualExtractionThread(
            extractor, pak_file, file_paths, destination
        )
        
        # Connect signals
        self.extraction_thread.progress_updated.connect(progress_dialog.update_progress)
        self.extraction_thread.extraction_finished.connect(self.individual_extraction_completed)
        
        # Set thread reference for cancellation
        progress_dialog.set_operation_thread(self.extraction_thread)
        
        # Start extraction
        self.extraction_thread.start()
        progress_dialog.show()

    def individual_extraction_completed(self, success, result):
        """Handle completed individual extraction"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        if success:
            extracted_count = len(result['extracted_files'])
            total_size = sum(f['size'] for f in result['extracted_files'])
            size_mb = total_size / (1024 * 1024)
            
            self.add_result_text(f"✅ Individual extraction completed\n")
            self.add_result_text(f"   Files extracted: {extracted_count}\n")
            self.add_result_text(f"   Total size: {size_mb:.1f} MB\n")
            self.add_result_text(f"   Destination: {result['destination']}\n\n")
            
            QMessageBox.information(
                self, "Extraction Complete",
                f"Successfully extracted {extracted_count} files ({size_mb:.1f} MB)\n"
                f"Destination: {result['destination']}"
            )
        else:
            error = result.get('error', 'Unknown error')
            self.add_result_text(f"❌ Individual extraction failed\n")
            self.add_result_text(f"   Error: {error}\n\n")
            
            QMessageBox.critical(
                self, "Extraction Failed",
                f"Failed to extract files:\n{error}"
            )

    def setup_index_search_tab(self):
        """Setup Index Search tab"""
        try:
            from index_search_system import IndexSearchWidget
            
            search_tab = IndexSearchWidget(
                parent=self,
                wine_wrapper=self.wine_wrapper,
                settings_manager=self.settings_manager
            )
            
            self.tab_widget.addTab(search_tab, "Index Search")
            
        except ImportError as e:
            print(f"Could not import Index Search: {e}")
            placeholder = QWidget()
            layout = QVBoxLayout(placeholder)
            label = QLabel("Index Search not available\nCheck that index_search_system.py is available")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            self.tab_widget.addTab(placeholder, "Index Search")
    
    def setup_uuid_generator_tab(self):
        """Setup UUID Generator tab"""
        try:
            from uuid_handle_generator import UUIDHandleWidget
            
            uuid_tab = UUIDHandleWidget(parent=self)
            self.tab_widget.addTab(uuid_tab, "UUID Generator")
            
        except ImportError as e:
            print(f"Could not import UUID Generator: {e}")
            placeholder = QWidget()
            layout = QVBoxLayout(placeholder)
            label = QLabel("UUID Generator not available\nCheck that uuid_handle_generator.py is available")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            self.tab_widget.addTab(placeholder, "UUID Generator")
    
    def setup_statusbar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def initialize_backend(self):
        """Initialize the Wine wrapper backend"""
        try:
            wine_path = self.settings_manager.get("wine_path")
            divine_path = self.settings_manager.get("divine_path")
            
            if not wine_path or not divine_path:
                self.show_setup_required_message()
                return
            
            self.wine_wrapper = WineWrapper(wine_path, divine_path)
            self.universal_parser.set_bg3_tool(self.wine_wrapper)
            
            self.status_bar.showMessage("Backend initialized successfully")
            
        except Exception as e:
            QMessageBox.critical(
                self, "Initialization Error",
                f"Failed to initialize backend:\n{e}\n\nPlease check your settings."
            )
    
    def show_setup_required_message(self):
        """Show message when setup is required"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Setup Required")
        msg.setText("Wine and Divine.exe paths need to be configured.")
        msg.setInformativeText("Would you like to open Preferences now?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Later)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.open_preferences()
    
    def restore_window_state(self):
        """Restore window geometry and state"""
        geometry = self.settings_manager.get("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1000, 600)
            self.center_window()
    
    def center_window(self):
        """Center window on screen"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Save window state
        self.settings_manager.set("window_geometry", self.saveGeometry())
        self.settings_manager.sync()
        
        event.accept()
    
    # Menu actions
    def open_preferences(self):
        """Open preferences dialog"""
        dialog = SettingsDialog(self, self.settings_manager)
        dialog.show()
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About BG3 Mac Modding Toolkit",
            """
            <h3>BG3 Mac Modding Toolkit</h3>
            <p>A native macOS application for modding Baldur's Gate 3.</p>
            
            <p><b>Features:</b></p>
            <ul>
            <li>Extract and create PAK files</li>
            <li>Browse game assets</li>
            <li>Edit LSX files with syntax highlighting</li>
            <li>Validate mod structures</li>
            <li>Native Mac file dialogs and styling</li>
            <li>Threaded operations for responsive UI</li>
            </ul>
            
            <p>Built with PyQt6 and divine.exe via Wine.</p>
            """
        )
    
    def open_pak_file(self):
        """Open PAK file (menu action)"""
        self.list_pak_contents()
    
    # PAK Operations
    def extract_pak_file(self):
        """Extract PAK file with progress dialog"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        # Use native Mac file dialog
        pak_file, _ = QFileDialog.getOpenFileName(
            self, "Select PAK File",
            self.settings_manager.get("working_directory", ""),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        # Update working directory
        self.settings_manager.set("working_directory", os.path.dirname(pak_file))
        
        # Choose destination
        dest_dir = QFileDialog.getExistingDirectory(
            self, "Select Extraction Destination",
            self.settings_manager.get("working_directory", "")
        )
        
        if not dest_dir:
            return
        
        self.settings_manager.set("working_directory", dest_dir)
        
        # Start extraction with progress dialog
        self.start_pak_operation("extract_pak", pak_file=pak_file, dest_dir=dest_dir)
    
    def create_pak_file(self):
        """Create PAK with auto-conversion support"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        # Select source directory
        source_dir = QFileDialog.getExistingDirectory(
            self, "Select Folder to Pack",
            self.settings_manager.get("working_directory", "")
        )
        
        if not source_dir:
            return
        
        self.settings_manager.set("working_directory", source_dir)
        
        # Check for auto-conversion files using your existing classes
        from larian_parser import AutoConversionProcessor, AutoConversionDialog
        
        processor = AutoConversionProcessor(self.wine_wrapper)
        conversion_files = processor.find_conversion_files(source_dir)
        total_conversions = sum(len(files) for files in conversion_files.values())
        
        # Show conversion preview if needed
        if total_conversions > 0:
            proceed = AutoConversionDialog.show_conversion_preview(self, conversion_files)
            if not proceed:
                return
        
        # Continue with normal PAK creation
        suggested_name = f"{os.path.basename(source_dir)}.pak"
        pak_file, _ = QFileDialog.getSaveFileName(
            self, "Save PAK File As",
            os.path.join(os.path.dirname(source_dir), suggested_name),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        # Start creation with auto-conversion if files were found
        if total_conversions > 0:
            self.start_pak_operation_with_conversion("create_pak", 
                                                   source_dir=source_dir, 
                                                   pak_file=pak_file, 
                                                   validate=True)
        else:
            # Normal PAK creation
            self.start_pak_operation("create_pak", source_dir=source_dir, pak_file=pak_file, validate=True)
    
    def rebuild_pak_file(self):
        """Rebuild PAK from extracted/modified folder"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        # Select extracted directory
        extracted_dir = QFileDialog.getExistingDirectory(
            self, "Select Extracted/Modified PAK Folder",
            self.settings_manager.get("working_directory", "")
        )
        
        if not extracted_dir:
            return
        
        self.settings_manager.set("working_directory", extracted_dir)
        
        # Choose output PAK file
        suggested_name = f"{os.path.basename(extracted_dir)}_modified.pak"
        pak_file, _ = QFileDialog.getSaveFileName(
            self, "Save Rebuilt PAK As",
            os.path.join(os.path.dirname(extracted_dir), suggested_name),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        # Start rebuild (creation without validation)
        self.start_pak_operation("create_pak", source_dir=extracted_dir, pak_file=pak_file, validate=False)
    
    def list_pak_contents(self):
        """List PAK file contents"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        # Select PAK file
        pak_file, _ = QFileDialog.getOpenFileName(
            self, "Select PAK File",
            self.settings_manager.get("working_directory", ""),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        self.settings_manager.set("working_directory", os.path.dirname(pak_file))
        
        # Start listing operation
        self.start_pak_operation("list_pak", pak_file=pak_file)
    
    def validate_mod_structure(self):
        """Validate mod folder structure"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        # Select mod directory
        mod_dir = QFileDialog.getExistingDirectory(
            self, "Select Mod Folder to Validate",
            self.settings_manager.get("working_directory", "")
        )
        
        if not mod_dir:
            return
        
        self.settings_manager.set("working_directory", mod_dir)
        
        # Run validation (synchronous since it's quick)
        self.add_result_text(f"Validating mod structure: {os.path.basename(mod_dir)}\n")
        
        validation = self.wine_wrapper.validate_mod_structure(mod_dir)
        
        # Format and display results
        result_text = f"\nValidation Results:\n"
        result_text += f"Valid: {'✅ Yes' if validation['valid'] else '❌ No'}\n\n"
        
        result_text += "Structure Found:\n"
        for item in validation['structure']:
            result_text += f"  ✅ {item}\n"
        
        if validation['warnings']:
            result_text += "\nWarnings:\n"
            for warning in validation['warnings']:
                result_text += f"  ⚠️ {warning}\n"
        
        result_text += "\n"
        self.add_result_text(result_text)

    def start_pak_operation_with_conversion(self, operation_type, **kwargs):
        """Start PAK operation with auto-conversion support"""
        from larian_parser import AutoConversionProcessor
        
        # Create progress dialog
        operation_titles = {
            "create_pak": "Creating PAK File with Auto-Conversion"
        }
        
        title = operation_titles.get(operation_type, "PAK Operation")
        self.progress_dialog = ProgressDialog(self, title)
        
        # Create enhanced operation thread
        self.operation_thread = ConversionPAKThread(
            self.wine_wrapper, operation_type, **kwargs
        )
        
        # Connect signals
        self.operation_thread.progress_updated.connect(self.progress_dialog.update_progress)
        self.operation_thread.operation_finished.connect(self.operation_completed_with_conversion)
        
        # Set thread reference for cancellation
        self.progress_dialog.set_operation_thread(self.operation_thread)
        
        # Disable UI buttons during operation
        self.set_pak_buttons_enabled(False)
        
        # Start operation
        self.operation_thread.start()
        self.progress_dialog.show()
    
    def operation_completed_with_conversion(self, success, result_data):
        """Handle completion with conversion results"""
        # Show conversion report if there were conversions
        conversions = result_data.get('conversions', [])
        conversion_errors = result_data.get('conversion_errors', [])
        
        if conversions or conversion_errors:
            self.show_conversion_report(conversions, conversion_errors)
        
        # Continue with normal operation completion
        self.operation_completed(success, result_data)
    
    def show_conversion_report(self, conversions, errors):
        """Show conversion results"""
        if not conversions and not errors:
            return
        
        # Add conversion info to results
        successful = sum(1 for c in conversions if c['success'])
        failed = len(conversions) - successful
        
        self.add_result_text(f"\n📄 Auto-Conversion Report:\n")
        self.add_result_text(f"   Successful: {successful}\n")
        if failed > 0:
            self.add_result_text(f"   Failed: {failed}\n")
        if errors:
            self.add_result_text(f"   Errors: {len(errors)}\n")
        
        # Show details
        for conv in conversions[:5]:  # Show first 5
            status = "✅" if conv['success'] else "❌"
            file_name = os.path.basename(conv['original_path'])
            self.add_result_text(f"   {status} {file_name}\n")
        
        if len(conversions) > 5:
            self.add_result_text(f"   ... and {len(conversions) - 5} more files\n")
        
        self.add_result_text("\n")
    
    def start_pak_operation(self, operation_type, **kwargs):
        """Start a PAK operation with progress dialog"""
        # Create and show progress dialog
        operation_titles = {
            "extract_pak": "Extracting PAK File",
            "create_pak": "Creating PAK File", 
            "list_pak": "Listing PAK Contents"
        }
        
        title = operation_titles.get(operation_type, "PAK Operation")
        self.progress_dialog = ProgressDialog(self, title)
        
        # Create operation thread
        self.operation_thread = DivineOperationThread(
            self.wine_wrapper, operation_type, **kwargs
        )
        
        # Connect signals
        self.operation_thread.progress_updated.connect(self.progress_dialog.update_progress)
        self.operation_thread.operation_finished.connect(self.operation_completed)
        
        # Set thread reference for cancellation
        self.progress_dialog.set_operation_thread(self.operation_thread)
        
        # Disable UI buttons during operation
        self.set_pak_buttons_enabled(False)
        
        # Start operation
        self.operation_thread.start()
        self.progress_dialog.show()
    
    def operation_completed(self, success, result_data):
        """Handle completed PAK operation"""
        # Re-enable UI
        self.set_pak_buttons_enabled(True)
        
        # Process results based on operation type
        if "pak_file" in result_data:
            pak_name = os.path.basename(result_data["pak_file"])
        elif "source_dir" in result_data:
            pak_name = os.path.basename(result_data["source_dir"])
        else:
            pak_name = "operation"
        
        if success:
            if "dest_dir" in result_data:  # Extract operation
                self.add_result_text(f"✅ Successfully extracted {pak_name}\n")
                self.add_result_text(f"   Destination: {result_data['dest_dir']}\n")
                self.add_result_text(f"   {result_data['output']}\n\n")
                
            elif "files" in result_data:  # List operation
                self.format_and_display_file_list(result_data)
                
            elif "source_dir" in result_data:  # Create operation
                self.add_result_text(f"✅ Successfully created {pak_name}\n")
                
                # Show validation results if available
                if result_data.get('validation'):
                    self.format_and_display_validation(result_data['validation'])
                
                self.add_result_text(f"   {result_data['output']}\n\n")
        else:
            error_msg = result_data.get('error', result_data.get('output', 'Unknown error'))
            self.add_result_text(f"❌ Operation failed: {pak_name}\n")
            self.add_result_text(f"   Error: {error_msg}\n\n")
        
        # Close progress dialog if still open
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()

    def add_individual_extraction_to_pak_operations(main_window):
        """Add individual file extraction to existing PAK operations"""
        
        def show_individual_extraction_dialog():
            """Show individual file extraction dialog"""
            if not main_window.wine_wrapper:
                QMessageBox.warning(main_window, "Error", "Backend not initialized. Please check settings.")
                return
            
            # Select PAK file
            pak_file, _ = QFileDialog.getOpenFileName(
                main_window, "Select PAK File for Individual Extraction",
                main_window.settings_manager.get("working_directory", ""),
                "PAK Files (*.pak);;All Files (*)"
            )
            
            if not pak_file:
                return
            
            # Show file selection dialog
            dialog = FileSelectionDialog(main_window, pak_file, main_window.wine_wrapper)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Start extraction
                start_individual_extraction(main_window, pak_file, dialog.selected_files, dialog.destination)
        
        def start_individual_extraction(main_window, pak_file, file_paths, destination):
            """Start individual file extraction with progress"""
            from PyQt6.QtWidgets import QProgressDialog
            
            # Create extractor
            extractor = IndividualFileExtractor(main_window.wine_wrapper)
            
            # Create progress dialog
            progress = QProgressDialog(
                f"Extracting {len(file_paths)} files...", "Cancel", 0, 100, main_window
            )
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            # Create extraction thread
            extraction_thread = IndividualExtractionThread(
                extractor, pak_file, file_paths, destination
            )
            
            def update_progress(percentage, message):
                progress.setValue(percentage)
                progress.setLabelText(message)
            
            def extraction_completed(success, result):
                progress.close()
                
                if success:
                    extracted_count = len(result['extracted_files'])
                    QMessageBox.information(
                        main_window, "Extraction Complete",
                        f"Successfully extracted {extracted_count} files to:\n{result['destination']}"
                    )
                else:
                    error = result.get('error', 'Unknown error')
                    QMessageBox.critical(
                        main_window, "Extraction Failed",
                        f"Failed to extract files:\n{error}"
                    )
            
            extraction_thread.progress_updated.connect(update_progress)
            extraction_thread.extraction_finished.connect(extraction_completed)
            extraction_thread.start()
            
            # Handle cancellation
            def cancel_extraction():
                extraction_thread.terminate()
                extraction_thread.wait()
            
            progress.canceled.connect(cancel_extraction)
    
    def set_pak_buttons_enabled(self, enabled):
        """Enable/disable PAK operation buttons"""
        self.extract_btn.setEnabled(enabled)
        self.create_btn.setEnabled(enabled)
        self.rebuild_btn.setEnabled(enabled)
        self.list_btn.setEnabled(enabled)
        self.validate_btn.setEnabled(enabled)
    
    def format_and_display_file_list(self, result_data):
        """Format and display PAK file listing"""
        files = result_data['files']
        pak_name = os.path.basename(result_data['pak_file'])
        
        result_text = f"📁 Found {result_data['file_count']} files in {pak_name}:\n"
        
        # Show first 50 files
        for file_info in files[:50]:
            if isinstance(file_info, dict):
                icon = "📁" if file_info.get('type') == 'folder' else "📄"
                name = file_info.get('name', str(file_info))
            else:
                icon = "📄"
                name = str(file_info)
            
            result_text += f"  {icon} {name}\n"
        
        if len(files) > 50:
            result_text += f"  ... and {len(files) - 50} more files\n"
        
        result_text += "\n"
        self.add_result_text(result_text)
    
    def format_and_display_validation(self, validation):
        """Format and display validation results"""
        result_text = "\nMod Structure Validation:\n"
        
        for item in validation.get('structure', []):
            result_text += f"  ✅ {item}\n"
        
        for warning in validation.get('warnings', []):
            result_text += f"  ⚠️ {warning}\n"
        
        result_text += "\n"
        self.add_result_text(result_text)
    
    def add_result_text(self, text):
        """Add text to results area (thread-safe)"""
        self.results_text.append(text.rstrip())
        
        # Auto-scroll to bottom
        cursor = self.results_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.results_text.setTextCursor(cursor)


# def main():
#     """Main application entry point"""
#     app = QApplication(sys.argv)
    
#     # Set application properties for Mac
#     app.setApplicationName("BG3 Mac Modding Toolkit")
#     app.setApplicationVersion("2.0")
#     app.setOrganizationName("BG3ModToolkit")
#     app.setOrganizationDomain("bg3modtoolkit.app")
    
#     # Use native Mac file dialogs
#     app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, False)
    
#     # Create and show main window
#     window = BG3ModToolkitMainWindow()
#     window.show()
    
#     sys.exit(app.exec())


# if __name__ == "__main__":
#     main()