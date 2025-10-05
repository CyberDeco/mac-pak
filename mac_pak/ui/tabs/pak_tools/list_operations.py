#!/usr/bin/env python3
"""
PAK List Operations
Handles all PAK listing and inspection functionality
"""

import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import QObject

from ...dialogs.progress_dialog import ProgressDialog


class ListOperations(QObject):
    """Handles all PAK listing operations"""
    
    def __init__(self, parent_tab, wine_wrapper, settings_manager):
        super().__init__()
        self.tab = parent_tab
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.current_monitor = None
    
    def list_pak_contents(self):
        """List PAK file contents - async"""
        if not self.wine_wrapper:
            QMessageBox.warning(self.tab, "Error", "Backend not initialized. Please check settings.")
            return
        
        pak_file, _ = QFileDialog.getOpenFileName(
            self.tab, "Select PAK File to List",
            self.settings_manager.get("working_directory", ""),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if not pak_file:
            return
        
        self.settings_manager.set("working_directory", os.path.dirname(pak_file))
        self._start_list_pak_async(pak_file)
    
    def _start_list_pak_async(self, pak_file):
        """Start async PAK listing"""
        self.tab.add_result_text(f"Listing contents of {os.path.basename(pak_file)}...")
        self.tab.set_pak_buttons_enabled(False)
        
        self.tab.progress_dialog = ProgressDialog(
            self.tab,
            "Listing PAK",
            f"Reading {os.path.basename(pak_file)}..."
        )
        self.tab.progress_dialog.canceled.connect(self.cancel_current_operation)
        self.tab.progress_dialog.show()
        
        self.current_monitor = self.wine_wrapper.pak_ops.list_pak_contents_async(pak_file)
        self.current_monitor.progress_updated.connect(self.on_operation_progress)
        self.current_monitor.process_finished.connect(
            lambda success, output: self._on_list_finished(success, output, pak_file)
        )
    
    def _on_list_finished(self, success, output, pak_file):
        """Handle listing completion"""
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
            files = self._parse_pak_listing(output)
            self.tab.add_result_text(f"✅ Found {len(files)} files in {os.path.basename(pak_file)}")
            self.tab.add_result_text("-" * 60)
            
            # Show first 20 files
            max_display = 20
            for i, file_path in enumerate(files[:max_display]):
                self.tab.add_result_text(f"  {file_path}")
            
            if len(files) > max_display:
                remaining = len(files) - max_display
                self.tab.add_result_text(f"\n  ... and {remaining} more files")
            
            self.tab.add_result_text("-" * 60)
        else:
            self.tab.add_result_text(f"❌ Failed to list PAK contents: {output}")
        
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