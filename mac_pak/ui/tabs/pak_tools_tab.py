#!/usr/bin/env python3
"""
PAK Operations tab UI funcs - Simplified async architecture
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, 
    QTextEdit, QLabel, QFileDialog, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Import components with fallbacks
from ..widgets.pak_tools.drop_label import DropLabel
from ..threads.pak_operations_thread import IndividualExtractionThread

from ...data.handlers.pak_operations import PAKOperations, IndividualFileExtractor
from ..dialogs.file_selection_dialog import FileSelectionDialog
from ..dialogs.progress_dialog import ProgressDialog

class PakToolsTab(QWidget):
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__()
        self.parent_window = parent
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        
        # Initialize backend operations
        self.pak_operations = PAKOperations(wine_wrapper) if PAKOperations and wine_wrapper else None
        self.file_extractor = IndividualFileExtractor(wine_wrapper) if IndividualFileExtractor and wine_wrapper else None
        
        # Monitor and dialog attributes (no more thread wrapper!)
        self.current_monitor = None
        self.current_thread = None  # Only for IndividualExtractionThread
        self.progress_dialog = None
        
        self.setup_ui()

    def create_styled_group(self, title, font_size=16):
        """Create a styled QGroupBox with custom font size"""
        group = QGroupBox(title)
        group.setProperty("header", "h2")
        return group

    def setup_ui(self):
        """Setup PAK tools tab with improved layout"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("PAK Operations")
        title_label.setProperty("header", "h1")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Create horizontal layout for operation groups
        operations_layout = QHBoxLayout()
        operations_layout.setSpacing(20)
        
        # Extraction group with better styling
        extract_group = self.create_styled_group("Extract PAKs")
        extract_layout = QVBoxLayout(extract_group)
        
        self.extract_btn = QPushButton("📦 Extract PAK File")
        self.extract_btn.clicked.connect(self.extract_pak_file)
        extract_layout.addWidget(self.extract_btn)
        
        self.list_btn = QPushButton("📋 List PAK Contents")
        self.list_btn.clicked.connect(self.list_pak_contents)
        extract_layout.addWidget(self.list_btn)
        
        self.individual_extract_btn = QPushButton("📄 Extract Individual Files")
        self.individual_extract_btn.clicked.connect(self.show_individual_extraction_dialog)
        extract_layout.addWidget(self.individual_extract_btn)
        
        operations_layout.addWidget(extract_group)
        
        # Creation group
        create_group = self.create_styled_group("Create PAKs") 
        create_layout = QVBoxLayout(create_group)
        
        self.create_btn = QPushButton("🔧 Create PAK from Folder")
        self.create_btn.clicked.connect(self.create_pak_file)
        create_layout.addWidget(self.create_btn)
        
        self.rebuild_btn = QPushButton("🔧 Rebuild Modified PAK")
        self.rebuild_btn.clicked.connect(self.rebuild_pak_file)
        create_layout.addWidget(self.rebuild_btn)
        
        self.validate_btn = QPushButton("✓ Validate Mod Structure")
        self.validate_btn.clicked.connect(self.validate_mod_structure)
        create_layout.addWidget(self.validate_btn)
        
        operations_layout.addWidget(create_group)
        
        layout.addLayout(operations_layout)
        
        # Results area with improved styling
        results_group = self.create_styled_group("Operation Results")
        results_layout = QVBoxLayout(results_group)
        
        # Add clear results button
        clear_results_layout = QHBoxLayout()
        clear_results_layout.addStretch()
        clear_results_btn = QPushButton("Clear Results")
        clear_results_btn.clicked.connect(self.clear_results)
        clear_results_layout.addWidget(clear_results_btn)
        results_layout.addLayout(clear_results_layout)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Monaco", 10))
        self.results_text.setPlaceholderText("Operation results will appear here...")
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)

        # Add drag and drop area if available
        if DropLabel:
            drop_group = self.create_styled_group("Quick Actions")
            drop_layout = QVBoxLayout(drop_group)
            
            self.drop_label = DropLabel("Drag PAK files here for quick operations")
            self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.drop_label.setStyleSheet("""
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
            self.drop_label.setMinimumHeight(80)
            
            # Connect the drop signal
            self.drop_label.file_dropped.connect(self.handle_dropped_pak)
            
            drop_layout.addWidget(self.drop_label)
            layout.addWidget(drop_group)
    
    def clear_results(self):
        """Clear the results text area"""
        self.results_text.clear()

    # ========================================================================
    # INDIVIDUAL FILE EXTRACTION (still uses QThread - has Python logic)
    # ========================================================================
    
    def show_individual_extraction_dialog(self):
        """Show individual file extraction dialog"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        if not FileSelectionDialog:
            QMessageBox.information(self, "Not Available", "Individual file extraction dialog not available.")
            return
        
        # Select PAK file first
        pak_file, _ = QFileDialog.getOpenFileName(
            self, "Select PAK File for Individual Extraction",
            self.settings_manager.get("working_directory", ""),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        # Show file selection dialog
        try:
            dialog = FileSelectionDialog(self, pak_file, self.wine_wrapper)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Start individual extraction
                self.start_individual_extraction(pak_file, dialog.selected_files, dialog.destination)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file selection dialog: {e}")

    def start_individual_extraction(self, pak_file, file_paths, destination):
        """Start individual file extraction - STANDARDIZED to use custom ProgressDialog"""
        if not self.file_extractor:
            QMessageBox.warning(self, "Error", "File extractor not available")
            return
        
        if not IndividualExtractionThread:
            QMessageBox.warning(self, "Error", "Individual extraction threading not available")
            return
        
        self.set_pak_buttons_enabled(False)
        
        # Create CUSTOM progress dialog (replacing QProgressDialog)
        self.progress_dialog = ProgressDialog(
            self,
            message="Extracting selected files...",
            cancel_text="Cancel",
            min_val=0,
            max_val=100
        )
        
        # Set file info
        self.progress_dialog.set_file_info(pak_file)
        
        # Connect canceled signal
        self.progress_dialog.canceled.connect(self.cancel_current_operation)
        
        # Show dialog
        self.progress_dialog.show()
        
        # Create and start thread
        self.extraction_thread = IndividualExtractionThread(
            self.file_extractor,
            pak_file,
            file_paths,
            destination
        )
        
        # Connect signals - using update_progress() method
        self.extraction_thread.progress_updated.connect(self.progress_dialog.update_progress)
        self.extraction_thread.extraction_finished.connect(self.on_individual_extraction_finished)
        
        self.extraction_thread.start()
    
    def on_individual_extraction_finished(self, success, message):
        """Handle individual extraction completion"""
        # Disconnect signals first
        if self.progress_dialog:
            try:
                self.progress_dialog.canceled.disconnect(self.cancel_current_operation)
            except TypeError:
                pass
        
        if self.extraction_thread:
            try:
                self.extraction_thread.progress_updated.disconnect(self.progress_dialog.update_progress)
            except TypeError:
                pass
        
        # Close progress dialog
        if self.progress_dialog:
            try:
                self.progress_dialog.close()
            except RuntimeError:
                pass
            finally:
                self.progress_dialog = None
        
        # Re-enable buttons
        self.set_pak_buttons_enabled(True)
        
        # Show results
        if success:
            self.add_result_text(f"✅ {message}")
            self.add_result_text("-" * 60)
        else:
            self.add_result_text(f"❌ {message}")
            self.add_result_text("-" * 60)
        
        # Cleanup thread
        if self.extraction_thread:
            self.extraction_thread.deleteLater()
            self.extraction_thread = None
    
    def cancel_individual_extraction(self):
        """Cancel individual extraction thread"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.terminate()
            self.add_result_text("Individual extraction cancelled by user")

    # ========================================================================
    # DIRECT ASYNC OPERATIONS (no thread wrapper - QProcess is already async!)
    # ========================================================================

    def extract_pak_file(self):
        """Extract PAK file with progress dialog - direct async"""
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
        
        # Start async operation directly (no thread wrapper!)
        self._start_extract_pak_async(pak_file, dest_dir)
    
    def _start_extract_pak_async(self, pak_file, dest_dir):
        """Start extraction operation - fully async"""
        self.set_pak_buttons_enabled(False)
        
        # Create custom progress dialog
        self.progress_dialog = ProgressDialog(
            self, 
            message="Extracting PAK...",
            cancel_text="Cancel",
            min_val=0,
            max_val=100
        )
        
        # Optionally set file info
        self.progress_dialog.set_file_info(pak_file)
        
        # Connect canceled signal
        self.progress_dialog.canceled.connect(self.cancel_current_operation)
        
        # Show dialog
        self.progress_dialog.show()
        
        # Start async operation
        self.current_monitor = self.wine_wrapper.pak_ops.extract_pak_async(pak_file, dest_dir)
        
        # Connect signals
        self.current_monitor.progress_updated.connect(self.on_operation_progress)
        self.current_monitor.process_finished.connect(
            lambda success, output: self.on_extract_finished(success, output, pak_file, dest_dir)
        )
    
    def on_extract_finished(self, success, output, pak_file, dest_dir):
        """Handle extraction completion"""
        # Disconnect signals FIRST - before closing dialog
        if self.progress_dialog:
            try:
                # Disconnect canceled signal to prevent false "cancelled" message
                self.progress_dialog.canceled.disconnect(self.cancel_current_operation)
            except TypeError:
                pass
        
        if self.current_monitor:
            try:
                self.current_monitor.progress_updated.disconnect(self.on_operation_progress)
            except TypeError:
                pass
        
        # NOW close the dialog
        if self.progress_dialog:
            try:
                self.progress_dialog.close()
            except RuntimeError:
                pass
            finally:
                self.progress_dialog = None
        
        # Re-enable buttons
        self.set_pak_buttons_enabled(True)
        
        # Show results
        if success:
            pak_name = os.path.basename(pak_file)
            self.add_result_text(f"✅ Successfully extracted {pak_name} to {dest_dir}")
            self.add_result_text("-" * 60)
        else:
            self.add_result_text(f"❌ Extraction failed: {output}")
            self.add_result_text("-" * 60)
        
        # Cleanup
        if self.current_monitor:
            self.current_monitor.deleteLater()
            self.current_monitor = None
    
    def create_pak_file(self):
        """Create PAK - direct async"""
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
        
        # Choose output file
        suggested_name = f"{os.path.basename(source_dir)}.pak"
        pak_file, _ = QFileDialog.getSaveFileName(
            self, "Save PAK File As",
            os.path.join(os.path.dirname(source_dir), suggested_name),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        # Start async operation
        self._start_create_pak_async(source_dir, pak_file)
    
    def _start_create_pak_async(self, source_dir, pak_file):
        """Start PAK creation - fully async"""
        self.set_pak_buttons_enabled(False)
        
        # Create custom progress dialog
        self.progress_dialog = ProgressDialog(
            self,
            message="Creating PAK...",
            cancel_text="Cancel"
        )
        
        self.progress_dialog.canceled.connect(self.cancel_current_operation)
        self.progress_dialog.show()
        
        # Start async operation
        self.current_monitor = self.wine_wrapper.pak_ops.create_pak_async(source_dir, pak_file)
        
        # Connect signals
        self.current_monitor.progress_updated.connect(self.on_operation_progress)
        self.current_monitor.process_finished.connect(
            lambda success, output: self.on_create_finished(success, output, source_dir, pak_file)
        )
    
    def on_create_finished(self, success, output, source_dir, pak_file):
        """Handle PAK creation completion"""
        # Disconnect signals FIRST - before closing dialog
        if self.progress_dialog:
            try:
                # Disconnect canceled signal to prevent false "cancelled" message
                self.progress_dialog.canceled.disconnect(self.cancel_current_operation)
            except TypeError:
                pass
        
        if self.current_monitor:
            try:
                self.current_monitor.progress_updated.disconnect(self.on_operation_progress)
            except TypeError:
                pass

        
        # Close progress dialog
        if self.progress_dialog:
            try:
                self.progress_dialog.close()
            except RuntimeError:
                pass
            finally:
                self.progress_dialog = None
        
        # Re-enable buttons
        self.set_pak_buttons_enabled(True)
        
        # Show results
        if success:
            pak_name = os.path.basename(pak_file)
            self.add_result_text(f"✅ Successfully created {pak_name} from {source_dir}")
            self.add_result_text("-" * 60)
        else:
            self.add_result_text(f"❌ PAK creation failed: {output}")
            self.add_result_text("-" * 60)
        
        # Cleanup
        if self.current_monitor:
            self.current_monitor.deleteLater()
            self.current_monitor = None
    
    def rebuild_pak_file(self):
        """Rebuild PAK from extracted/modified folder"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        # Select the folder containing extracted/modified PAK contents
        source_dir = QFileDialog.getExistingDirectory(
            self, "Select Modified PAK Folder",
            self.settings_manager.get("working_directory", "")
        )
        
        if not source_dir:
            return
        
        # Suggest output name based on folder
        suggested_name = f"{os.path.basename(source_dir)}_rebuilt.pak"
        pak_file, _ = QFileDialog.getSaveFileName(
            self, "Save Rebuilt PAK As",
            os.path.join(os.path.dirname(source_dir), suggested_name),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        # Same as create_pak
        self._start_create_pak_async(source_dir, pak_file)
    
    def list_pak_contents(self):
        """List PAK file contents - direct async"""
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
        
        # Start async operation
        self._start_list_pak_async(pak_file)
        
    def _start_list_pak_async(self, pak_file):
        """Start PAK listing - fully async"""
        self.set_pak_buttons_enabled(False)
        
        # Create custom progress dialog
        self.progress_dialog = ProgressDialog(
            self,
            message="Reading PAK contents...",
            cancel_text="Cancel"
        )
        
        self.progress_dialog.set_file_info(pak_file)
        self.progress_dialog.canceled.connect(self.cancel_current_operation)
        self.progress_dialog.show()
        
        # Start async operation
        self.current_monitor = self.wine_wrapper.pak_ops.list_pak_contents_async(pak_file)
        
        # Connect signals
        self.current_monitor.progress_updated.connect(self.on_operation_progress)
        self.current_monitor.process_finished.connect(
            lambda success, output: self.on_list_finished(success, output, pak_file)
        )
    
    def on_list_finished(self, success, output, pak_file):
        """Handle PAK listing completion"""
        # Disconnect signals FIRST - before closing dialog
        if self.progress_dialog:
            try:
                # Disconnect canceled signal to prevent false "cancelled" message
                self.progress_dialog.canceled.disconnect(self.cancel_current_operation)
            except TypeError:
                pass
        
        if self.current_monitor:
            try:
                self.current_monitor.progress_updated.disconnect(self.on_operation_progress)
            except TypeError:
                pass
        
        # Close progress dialog
        if self.progress_dialog:
            try:
                self.progress_dialog.close()
            except RuntimeError:
                pass
            finally:
                self.progress_dialog = None
        
        # Re-enable buttons
        self.set_pak_buttons_enabled(True)
        
        # Parse and display results
        if success:
            files = self._parse_pak_listing(output)
            pak_name = os.path.basename(pak_file)
            
            self.add_result_text(f"\n{pak_name} contains {len(files)} files:")
            self.add_result_text("-" * 60)
            
            # Show first 100 files
            for file_path in files[:100]:
                self.add_result_text(f"  {file_path}")
            
            if len(files) > 100:
                remaining = len(files) - 100
                self.add_result_text(f"\n  ... and {remaining} more files")
            
            self.add_result_text("-" * 60)
        else:
            self.add_result_text(f"❌ Failed to list PAK contents: {output}")
        
        # Cleanup
        if self.current_monitor:
            self.current_monitor.deleteLater()
            self.current_monitor = None
    
    def _parse_pak_listing(self, output):
        """Parse divine.exe list output into file paths"""
        files = []
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('Opening') and not line.startswith('Package') and not line.startswith('Listing'):
                # Extract file path from divine.exe output
                parts = line.split()
                if parts:
                    path_parts = []
                    for part in parts:
                        if part.isdigit():
                            break
                        path_parts.append(part)
                    
                    if path_parts:
                        file_path = ' '.join(path_parts)
                        files.append(file_path)
        return files
    
    def validate_mod_structure(self):
        """Validate mod folder structure - runs synchronously (lightweight operation)"""
        if not self.wine_wrapper:
            QMessageBox.warning(self, "Error", "Backend not initialized. Please check settings.")
            return
        
        if not self.pak_operations:
            QMessageBox.warning(self, "Error", "PAK operations not available")
            return
        
        mod_dir = QFileDialog.getExistingDirectory(
            self, "Select Mod Folder to Validate",
            self.settings_manager.get("working_directory", "")
        )
        
        if not mod_dir:
            return
        
        self.add_result_text(f"Validating mod structure: {os.path.basename(mod_dir)}")
        
        try:
            # This is a lightweight Python operation, no need for async
            validation = self.pak_operations.validate_mod_structure(mod_dir)
            
            if validation['valid']:
                self.add_result_text("✓ Mod structure is valid!")
            else:
                self.add_result_text("⚠ Mod structure has issues:")
            
            # Show structure findings
            if validation['structure']:
                self.add_result_text("Structure found:")
                for item in validation['structure']:
                    self.add_result_text(f"  + {item}")
            
            # Show warnings
            if validation['warnings']:
                self.add_result_text("Warnings:")
                for warning in validation['warnings']:
                    self.add_result_text(f"  - {warning}")
            
            # Show mod info if available
            mod_info = validation.get('mod_info')
            if mod_info and mod_info.get('name', 'Unknown') != 'Unknown':
                self.add_result_text(f"Mod info: {mod_info['name']} v{mod_info.get('version', 'Unknown')}")
                
        except Exception as e:
            self.add_result_text(f"Validation failed: {e}")

    # ========================================================================
    # COMMON HANDLERS
    # ========================================================================

    def on_operation_progress(self, percentage, message):
        """Handle progress updates from async operations"""
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            try:
                self.progress_dialog.setValue(percentage)
                self.progress_dialog.setLabelText(message)
            except RuntimeError:
                # Dialog was deleted
                pass
    
    def cancel_current_operation(self):
        """Cancel the current async operation"""
        if self.current_monitor:
            self.current_monitor.cancel()
            self.add_result_text("Operation cancelled by user")

    def handle_dropped_pak(self, pak_file):
        """Handle PAK files dropped on the interface"""
        self.add_result_text(f"Dropped file: {os.path.basename(pak_file)}")
        
        # Show a dialog with quick action options
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("PAK File Dropped")
        msg.setText(f"What would you like to do with {os.path.basename(pak_file)}?")
        
        extract_btn = msg.addButton("Extract", QMessageBox.ButtonRole.ActionRole)
        list_btn = msg.addButton("List Contents", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.exec()
        
        if msg.clickedButton() == extract_btn:
            # Auto-extract to a folder next to the PAK file
            pak_dir = os.path.dirname(pak_file)
            pak_name = os.path.splitext(os.path.basename(pak_file))[0]
            dest_dir = os.path.join(pak_dir, f"{pak_name}_extracted")
            
            self._start_extract_pak_async(pak_file, dest_dir)
            
        elif msg.clickedButton() == list_btn:
            self._start_list_pak_async(pak_file)

    def set_pak_buttons_enabled(self, enabled):
        """Enable/disable PAK operation buttons"""
        self.extract_btn.setEnabled(enabled)
        self.create_btn.setEnabled(enabled)
        self.rebuild_btn.setEnabled(enabled)
        self.list_btn.setEnabled(enabled)
        self.validate_btn.setEnabled(enabled)
        self.individual_extract_btn.setEnabled(enabled)
    
    def add_result_text(self, text):
        """Add text to results area (thread-safe via Qt's event system)"""
        self.results_text.append(text.rstrip())
        
        # Auto-scroll to bottom
        cursor = self.results_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.results_text.setTextCursor(cursor)