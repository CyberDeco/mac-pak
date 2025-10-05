#!/usr/bin/env python3
"""
PAK Create Operations
Handles all PAK creation and validation functionality
"""

import os
from PyQt6.QtWidgets import (
    QFileDialog, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QComboBox, QSpinBox, QLabel, QPushButton
)
from PyQt6.QtCore import QObject

from ...dialogs.progress_dialog import ProgressDialog
from ....data.handlers.pak_operations import PAKOperations


class CreateOperations(QObject):
    """Handles all PAK creation operations"""
    
    def __init__(self, parent_tab, wine_wrapper, settings_manager):
        super().__init__()
        self.tab = parent_tab
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.current_monitor = None
        self.pak_operations = PAKOperations(wine_wrapper) if wine_wrapper else None
    
    def create_pak_file(self):
        """Create PAK with options - async"""
        if not self.wine_wrapper:
            QMessageBox.warning(self.tab, "Error", "Backend not initialized. Please check settings.")
            return
        
        source_dir = QFileDialog.getExistingDirectory(
            self.tab, "Select Folder to Pack",
            self.settings_manager.get("working_directory", "")
        )
        
        if not source_dir:
            return
        
        self.settings_manager.set("working_directory", source_dir)
        
        suggested_name = f"{os.path.basename(source_dir)}.pak"
        pak_file, _ = QFileDialog.getSaveFileName(
            self.tab, "Save PAK File As",
            os.path.join(os.path.dirname(source_dir), suggested_name),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        # Show options dialog
        compression, priority = self._show_pak_creation_options()
        if compression is None:
            return
        
        self._start_create_pak_async(source_dir, pak_file, compression, priority)
    
    def _show_pak_creation_options(self):
        """Show dialog for PAK creation options"""
        dialog = QDialog(self.tab)
        dialog.setWindowTitle("PAK Creation Options")
        dialog.setFixedWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        options_group = QGroupBox("Package Settings")
        options_layout = QFormLayout(options_group)
        
        # Compression
        compression_combo = QComboBox()
        compression_combo.addItems(['lz4hc', 'lz4', 'zlib', 'zlibfast', 'none'])
        compression_combo.setCurrentText('lz4hc')
        options_layout.addRow("Compression:", compression_combo)
        
        # Priority
        priority_spin = QSpinBox()
        priority_spin.setRange(0, 100)
        priority_spin.setValue(0)
        priority_spin.setToolTip(
            "Controls mod load order. Higher values load later.\n"
            "0 = default priority, 50 = high priority override"
        )
        options_layout.addRow("Load Priority:", priority_spin)
        
        # Help text
        help_text = QLabel(dialog)
        help_text.setText(
            "<i>lz4hc = best compression (default)<br>"
            "lz4 = fast compression<br>"
            "Priority 0 = normal mod, 50+ = override mod</i>"
        )
        help_text.setWordWrap(True)
        options_layout.addRow("", help_text)
        
        layout.addWidget(options_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("Create PAK")
        create_btn.setDefault(True)
        create_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return compression_combo.currentText(), priority_spin.value()
        return None, None
    
    def _start_create_pak_async(self, source_dir, pak_file, compression='lz4hc', priority=0):
        """Start async PAK creation with options"""
        self.tab.add_result_text(f"Creating PAK from {os.path.basename(source_dir)}...")
        self.tab.add_result_text(f"Compression: {compression}, Priority: {priority}")
        self.tab.set_pak_buttons_enabled(False)
        
        self.tab.progress_dialog = ProgressDialog(
            self.tab,
            "Creating PAK",
            f"Creating {os.path.basename(pak_file)}..."
        )
        self.tab.progress_dialog.canceled.connect(self.cancel_current_operation)
        self.tab.progress_dialog.show()
        
        # Use advanced creation with options
        def progress_callback(percentage, message):
            if self.tab.progress_dialog and not self.tab.progress_dialog.wasCanceled():
                try:
                    self.tab.progress_dialog.setValue(percentage)
                    self.tab.progress_dialog.setLabelText(message)
                except RuntimeError:
                    pass
        
        # Call synchronous method with progress callback
        # (Wine PAK tools use synchronous blocking calls internally)
        try:
            result = self.wine_wrapper.pak_ops.create_pak_with_compression(
                source_dir, pak_file,
                compression=compression,
                priority=priority,
                progress_callback=progress_callback
            )
            
            # Handle result
            self._on_create_finished(result.success, result.message, source_dir, pak_file)
        
        except Exception as e:
            self._on_create_finished(False, str(e), source_dir, pak_file)
    
    def _on_create_finished(self, success, output, source_dir, pak_file):
        """Handle creation completion"""
        if self.tab.progress_dialog:
            try:
                self.tab.progress_dialog.close()
            except RuntimeError:
                pass
            finally:
                self.tab.progress_dialog = None
        
        self.tab.set_pak_buttons_enabled(True)
        
        if success:
            pak_name = os.path.basename(pak_file)
            self.tab.add_result_text(f"✅ Successfully created {pak_name}")
            self.tab.add_result_text("-" * 60)
        else:
            self.tab.add_result_text(f"❌ PAK creation failed: {output}")
            self.tab.add_result_text("-" * 60)
        
        if self.current_monitor:
            self.current_monitor.deleteLater()
            self.current_monitor = None
    
    def rebuild_pak_file(self):
        """Rebuild PAK from extracted/modified folder"""
        if not self.wine_wrapper:
            QMessageBox.warning(self.tab, "Error", "Backend not initialized. Please check settings.")
            return
        
        source_dir = QFileDialog.getExistingDirectory(
            self.tab, "Select Modified PAK Folder",
            self.settings_manager.get("working_directory", "")
        )
        
        if not source_dir:
            return
        
        suggested_name = f"{os.path.basename(source_dir)}_rebuilt.pak"
        pak_file, _ = QFileDialog.getSaveFileName(
            self.tab, "Save Rebuilt PAK As",
            os.path.join(os.path.dirname(source_dir), suggested_name),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        # Show options and create
        compression, priority = self._show_pak_creation_options()
        if compression is None:
            return
        
        self._start_create_pak_async(source_dir, pak_file, compression, priority)
    
    def validate_mod_structure(self):
        """Validate mod folder structure"""
        if not self.wine_wrapper:
            QMessageBox.warning(self.tab, "Error", "Backend not initialized. Please check settings.")
            return
        
        if not self.pak_operations:
            QMessageBox.warning(self.tab, "Error", "PAK operations not available")
            return
        
        mod_dir = QFileDialog.getExistingDirectory(
            self.tab, "Select Mod Folder to Validate",
            self.settings_manager.get("working_directory", "")
        )
        
        if not mod_dir:
            return
        
        self.tab.add_result_text(f"Validating mod structure: {os.path.basename(mod_dir)}")
        
        try:
            validation = self.pak_operations.validate_mod_structure(mod_dir)
            
            if validation['valid']:
                self.tab.add_result_text("✓ Mod structure is valid!")
            else:
                self.tab.add_result_text("⚠ Mod structure has issues:")
            
            if validation['structure']:
                self.tab.add_result_text("Structure found:")
                for item in validation['structure']:
                    self.tab.add_result_text(f"  + {item}")
            
            if validation['warnings']:
                self.tab.add_result_text("Warnings:")
                for warning in validation['warnings']:
                    self.tab.add_result_text(f"  - {warning}")
            
            mod_info = validation.get('mod_info')
            if mod_info and mod_info.get('name', 'Unknown') != 'Unknown':
                self.tab.add_result_text(f"Mod info: {mod_info['name']} v{mod_info.get('version', 'Unknown')}")
        
        except Exception as e:
            self.tab.add_result_text(f"Validation failed: {e}")
    
    def cancel_current_operation(self):
        """Cancel current operation"""
        if self.current_monitor:
            self.current_monitor.cancel()
            self.tab.add_result_text("Operation cancelled by user")