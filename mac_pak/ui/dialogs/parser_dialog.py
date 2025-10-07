import os
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QTextEdit, QProgressBar,
    QDialogButtonBox, QTabWidget, QWidget, 
    QMessageBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from ...data.larian_parser import ProgressUpdate, ParseResult, ConversionWorker
from ..threads.lsf_conversion  import BatchParserThread

class BatchParsingDialog(QDialog):
    """Dialog for batch parsing operations with threading support"""
    
    def __init__(self, parent=None, parser_instance=None):
        super().__init__(parent)
        self.parser = parser_instance
        self.batch_thread = None
        self.setup_ui()
        self.results = []
        self.errors = []
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Batch File Parser")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Progress section
        progress_group = QWidget()
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_label = QLabel("Ready to start batch parsing...")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_group)
        
        # Results section
        self.results_tabs = QTabWidget()
        
        # Success tab
        self.success_widget = QWidget()
        success_layout = QVBoxLayout(self.success_widget)
        self.success_tree = QTreeWidget()
        self.success_tree.setHeaderLabels(['File', 'Format', 'Processing Time', 'Details'])
        success_layout.addWidget(self.success_tree)
        self.results_tabs.addTab(self.success_widget, "Successful Parses")
        
        # Errors tab
        self.error_widget = QWidget()
        error_layout = QVBoxLayout(self.error_widget)
        self.error_tree = QTreeWidget()
        self.error_tree.setHeaderLabels(['File', 'Error'])
        error_layout.addWidget(self.error_tree)
        self.results_tabs.addTab(self.error_widget, "Errors")
        
        # Log tab
        self.log_widget = QWidget()
        log_layout = QVBoxLayout(self.log_widget)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        self.results_tabs.addTab(self.log_widget, "Processing Log")
        
        layout.addWidget(self.results_tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Batch Parse")
        self.start_button.clicked.connect(self.start_batch_parsing)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_parsing)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def set_file_list(self, file_paths: List[str]):
        """Set the list of files to parse"""
        self.file_paths = file_paths
        self.progress_label.setText(f"Ready to parse {len(file_paths)} files")
    
    def start_batch_parsing(self):
        """Start the batch parsing process"""
        if not hasattr(self, 'file_paths') or not self.file_paths:
            QMessageBox.warning(self, "No Files", "No files selected for parsing.")
            return
        
        # Clear previous results
        self.results.clear()
        self.errors.clear()
        self.success_tree.clear()
        self.error_tree.clear()
        self.log_text.clear()
        
        # Setup UI for processing
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.file_paths))
        self.progress_bar.setValue(0)
        
        # Create and start batch parsing thread
        max_workers = min(4, len(self.file_paths))  # Limit concurrent threads
        self.batch_thread = BatchParserThread(self.parser, self.file_paths, max_workers)
        
        # Connect signals
        self.batch_thread.progress_updated.connect(self.update_progress)
        self.batch_thread.file_completed.connect(self.file_completed)
        self.batch_thread.batch_completed.connect(self.batch_completed)
        self.batch_thread.finished.connect(self.parsing_finished)
        
        # Start the thread
        self.batch_thread.start()
        
        self.log_message("Batch parsing started...")
    
    def stop_parsing(self):
        """Stop the batch parsing process"""
        if self.batch_thread and self.batch_thread.isRunning():
            self.log_message("Stopping batch parsing...")
            self.batch_thread.stop_parsing()
            self.batch_thread.wait(5000)  # Wait up to 5 seconds
            
            if self.batch_thread.isRunning():
                self.batch_thread.terminate()
                self.batch_thread.wait()
            
            self.log_message("Batch parsing stopped.")
        
        self.parsing_finished()
    
    @pyqtSlot(ProgressUpdate)
    def update_progress(self, progress: ProgressUpdate):
        """Update progress display"""
        self.progress_bar.setValue(progress.current)
        self.progress_label.setText(progress.message)
        
        if progress.error:
            self.log_message(f"ERROR: {progress.error}")
        else:
            self.log_message(f"[{progress.stage}] {progress.message}")
    
    @pyqtSlot(ParseResult)
    def file_completed(self, result: ParseResult):
        """Handle individual file completion"""
        if result.success:
            self.results.append(result)
            self.add_success_item(result)
            self.log_message(f"✓ Parsed: {os.path.basename(result.file_path)} ({result.processing_time:.2f}s)")
        else:
            self.errors.append(result)
            self.add_error_item(result)
            self.log_message(f"✗ Failed: {os.path.basename(result.file_path)} - {result.error}")
    
    @pyqtSlot(list, list)
    def batch_completed(self, results: List[ParseResult], errors: List[ParseResult]):
        """Handle batch completion"""
        self.log_message(f"Batch parsing completed: {len(results)} successful, {len(errors)} errors")
        
        # Update tab titles with counts
        self.results_tabs.setTabText(0, f"Successful Parses ({len(results)})")
        self.results_tabs.setTabText(1, f"Errors ({len(errors)})")
    
    def parsing_finished(self):
        """Clean up after parsing is finished"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"Completed: {len(self.results)} successful, {len(self.errors)} errors")
        
        if self.batch_thread:
            self.batch_thread = None
    
    def add_success_item(self, result: ParseResult):
        """Add successful parse result to tree"""
        item = QTreeWidgetItem(self.success_tree)
        item.setText(0, os.path.basename(result.file_path))
        
        if result.data:
            item.setText(1, result.data.get('format', 'unknown'))
            item.setText(2, f"{result.processing_time:.2f}s")
            
            # Add details
            details = []
            if 'regions' in result.data:
                details.append(f"{len(result.data['regions'])} regions")
            if 'version' in result.data:
                details.append(f"v{result.data['version']}")
            
            item.setText(3, ", ".join(details))
        else:
            item.setText(1, "unknown")
            item.setText(2, f"{result.processing_time:.2f}s")
    
    def add_error_item(self, result: ParseResult):
        """Add error result to tree"""
        item = QTreeWidgetItem(self.error_tree)
        item.setText(0, os.path.basename(result.file_path))
        item.setText(1, result.error or "Unknown error")
    
    def log_message(self, message: str):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        if self.batch_thread and self.batch_thread.isRunning():
            reply = QMessageBox.question(
                self, "Parsing in Progress",
                "Batch parsing is still running. Do you want to stop it and close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_parsing()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

