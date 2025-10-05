#!/usr/bin/env python3
"""
PAK Extract Operations
Handles all PAK extraction functionality
"""

import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal, QObject

from ...threads.pak_operations_thread import IndividualExtractionThread
from ...dialogs.file_selection_dialog import FileSelectionDialog
from ...dialogs.progress_dialog import ProgressDialog


class ExtractOperations(QObject):
    """Handles all PAK extraction operations"""
    
    def __init__(self, parent_tab, wine_wrapper, settings_manager):
        super().__init__()
        self.tab = parent_tab
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.current_monitor = None
        self.current_thread = None
    
    def extract_pak_file(self):
        """Extract entire PAK file - async"""
        if not self.wine_wrapper:
            QMessageBox.warning(self.tab, "Error", "Backend not initialized. Please check settings.")
            return
        
        pak_file, _ = QFileDialog.getOpenFileName(
            self.tab, "Select PAK File to Extract",
            self.settings_manager.get("working_directory", ""),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        self.settings_manager.set("working_directory", os.path.dirname(pak_file))
        
        dest_dir = QFileDialog.getExistingDirectory(
            self.tab, "Select Destination Folder",
            os.path.dirname(pak_file)
        )
        
        if not dest_dir:
            return
        
        self._start_extract_pak_async(pak_file, dest_dir)
    
    def _start_extract_pak_async(self, pak_file, dest_dir):
        """Start async PAK extraction"""
        self.tab.add_result_text(f"Extracting {os.path.basename(pak_file)}...")
        self.tab.set_pak_buttons_enabled(False)
        
        # Create progress dialog
        self.tab.progress_dialog = ProgressDialog(
            self.tab, 
            "Extracting PAK", 
            f"Extracting {os.path.basename(pak_file)}..."
        )
        self.tab.progress_dialog.canceled.connect(self.cancel_current_operation)
        self.tab.progress_dialog.show()
        
        # Start async extraction
        self.current_monitor = self.wine_wrapper.pak_ops.extract_pak_async(pak_file, dest_dir)
        self.current_monitor.progress_updated.connect(self.on_operation_progress)
        self.current_monitor.process_finished.connect(
            lambda success, output: self._on_extract_finished(success, output, pak_file, dest_dir)
        )
    
    def _on_extract_finished(self, success, output, pak_file, dest_dir):
        """Handle extraction completion"""
        try:
            self.current_monitor.progress_updated.disconnect(self.on_operation_progress)
        except TypeError:
            pass
        
        if self.tab.progress_dialog:
            try:
                self.tab.progress_dialog.close()
            except RuntimeError:
                pass
            finally:
                self.tab.progress_dialog = None
        
        self.tab.set_pak_buttons_enabled(True)
        
        if success:
            file_count = len([f for root, dirs, files in os.walk(dest_dir) for f in files])
            self.tab.add_result_text(f"✅ Successfully extracted {file_count} files to {dest_dir}")
            self.tab.add_result_text("-" * 60)
        else:
            self.tab.add_result_text(f"❌ Extraction failed: {output}")
            self.tab.add_result_text("-" * 60)
        
        if self.current_monitor:
            self.current_monitor.deleteLater()
            self.current_monitor = None
    
    def show_individual_extraction_dialog(self):
        """Show dialog for extracting individual files"""
        if not self.wine_wrapper:
            QMessageBox.warning(self.tab, "Error", "Backend not initialized. Please check settings.")
            return
        
        pak_file, _ = QFileDialog.getOpenFileName(
            self.tab, "Select PAK File",
            self.settings_manager.get("working_directory", ""),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        self.settings_manager.set("working_directory", os.path.dirname(pak_file))
        
        # List PAK contents first
        self.tab.add_result_text(f"Loading contents of {os.path.basename(pak_file)}...")
        
        try:
            files = self.wine_wrapper.pak_ops.list_pak_contents(pak_file)
            
            if not files:
                QMessageBox.warning(self.tab, "Empty PAK", "No files found in PAK")
                return
            
            # Show file selection dialog
            dialog = FileSelectionDialog(self.tab, files, pak_file)
            
            if dialog.exec():
                selected_files = dialog.get_selected_files()
                
                if not selected_files:
                    QMessageBox.information(self.tab, "No Selection", "No files selected")
                    return
                
                # Get output directory
                dest_dir = QFileDialog.getExistingDirectory(
                    self.tab, "Select Destination Folder",
                    os.path.dirname(pak_file)
                )
                
                if not dest_dir:
                    return
                
                self._start_individual_extraction(pak_file, selected_files, dest_dir)
        
        except Exception as e:
            self.tab.add_result_text(f"❌ Error listing PAK: {e}")
    
    def _start_individual_extraction(self, pak_file, selected_files, dest_dir):
        """Start individual file extraction in thread"""
        self.tab.add_result_text(f"Extracting {len(selected_files)} files...")
        self.tab.set_pak_buttons_enabled(False)
        
        self.tab.progress_dialog = ProgressDialog(
            self.tab,
            "Extracting Files",
            f"Extracting {len(selected_files)} files..."
        )
        self.tab.progress_dialog.show()
        
        self.current_thread = IndividualExtractionThread(
            self.wine_wrapper, pak_file, selected_files, dest_dir
        )
        self.current_thread.progress_updated.connect(self.on_operation_progress)
        self.current_thread.extraction_finished.connect(self._on_individual_extraction_finished)
        self.current_thread.start()
    
    def _on_individual_extraction_finished(self, results):
        """Handle individual extraction completion"""
        if self.tab.progress_dialog:
            try:
                self.tab.progress_dialog.close()
            except RuntimeError:
                pass
            finally:
                self.tab.progress_dialog = None
        
        self.tab.set_pak_buttons_enabled(True)
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        self.tab.add_result_text(f"✅ Extracted {successful} files successfully")
        if failed > 0:
            self.tab.add_result_text(f"❌ Failed: {failed} files")
        self.tab.add_result_text("-" * 60)
        
        if self.current_thread:
            self.current_thread.deleteLater()
            self.current_thread = None
    
    def on_operation_progress(self, percentage, message):
        """Handle progress updates"""
        if self.tab.progress_dialog and not self.tab.progress_dialog.wasCanceled():
            try:
                self.tab.progress_dialog.setValue(percentage)
                self.tab.progress_dialog.setLabelText(message)
            except RuntimeError:
                pass
    
    def cancel_current_operation(self):
        """Cancel current operation"""
        if self.current_monitor:
            self.current_monitor.cancel()
            self.tab.add_result_text("Operation cancelled by user")
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.terminate()