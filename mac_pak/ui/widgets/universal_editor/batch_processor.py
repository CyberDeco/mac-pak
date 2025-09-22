import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, 
    QTextEdit, QLabel, QLineEdit, QComboBox, QProgressBar,
    QListWidget, QFileDialog, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...threads.lsx_lsf_lsj_conversion import BatchConversionThread

class BatchProcessor(QWidget):
    """Batch file processing interface"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.file_list = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup batch processing interface"""
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("Batch File Processing")
        title_label.setProperty("header", "h2")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_group.setProperty("header", "h3")
        file_layout = QVBoxLayout(file_group)
        
        # File list
        self.file_listbox = QListWidget()
        self.file_listbox.setMinimumHeight(200)
        file_layout.addWidget(self.file_listbox)
        
        # File buttons
        file_btn_layout = QHBoxLayout()
        
        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        file_btn_layout.addWidget(self.add_files_btn)
        
        self.add_dir_btn = QPushButton("Add Directory")
        self.add_dir_btn.clicked.connect(self.add_directory)
        file_btn_layout.addWidget(self.add_dir_btn)
        
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_selected)
        file_btn_layout.addWidget(self.remove_btn)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_files)
        file_btn_layout.addWidget(self.clear_btn)
        
        file_btn_layout.addStretch()
        file_layout.addLayout(file_btn_layout)
        
        layout.addWidget(file_group)
        
        # Operations group
        ops_group = QGroupBox("Batch Operations")
        ops_group.setProperty("header", "h3")
        ops_layout = QVBoxLayout(ops_group)
        
        # Format conversion
        combined_layout = QHBoxLayout()
        
        # Convert section
        combined_layout.addWidget(QLabel("Convert to:"))
        
        self.target_format_combo = QComboBox()
        self.target_format_combo.addItems(["lsx", "lsj", "lsf"])

        combined_layout.addWidget(self.target_format_combo)
        
        self.convert_btn = QPushButton("Convert All")
        self.convert_btn.clicked.connect(self.batch_convert)
        combined_layout.addWidget(self.convert_btn)
        
        # Add some spacing between sections
        combined_layout.addSpacing(30)
        
        # Output directory section
        combined_layout.addWidget(QLabel("Output Directory:"))
        
        self.output_dir_edit = QLineEdit()
        combined_layout.addWidget(self.output_dir_edit)
        
        self.browse_output_btn = QPushButton("Browse")
        self.browse_output_btn.clicked.connect(self.browse_output_dir)
        combined_layout.addWidget(self.browse_output_btn)
        
        combined_layout.addStretch()  # Push everything to the left
        ops_layout.addLayout(combined_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        ops_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready")
        ops_layout.addWidget(self.progress_label)
        
        layout.addWidget(ops_group)
        
        # Results
        results_group = QGroupBox("Results")
        results_group.setProperty("header", "h3")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
        self.update_button_states()
    
    def update_button_states(self):
        """Update button states based on current state"""
        has_files = len(self.file_list) > 0
        has_wine_wrapper = self.wine_wrapper is not None
        
        self.convert_btn.setEnabled(has_files and has_wine_wrapper)
        self.remove_btn.setEnabled(has_files)
        self.clear_btn.setEnabled(has_files)
    
    def add_files(self):
        """Add individual files to batch list"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select BG3 Files", initial_dir,
            "All BG3 Files (*.lsx *.lsj *.lsf);;LSX Files (*.lsx);;LSJ Files (*.lsj);;LSF Files (*.lsf);;All Files (*)"
        )
        
        for file_path in files:
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                self.file_listbox.addItem(os.path.basename(file_path))
        
        self.update_button_states()
    
    def add_directory(self):
        """Add all BG3 files from a directory"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", initial_dir)
        
        if directory:
            # Find all BG3 files in directory
            extensions = ['.lsx', '.lsj', '.lsf']
            found_files = []
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        file_path = os.path.join(root, file)
                        if file_path not in self.file_list:
                            found_files.append(file_path)
            
            # Add to list
            for file_path in found_files:
                self.file_list.append(file_path)
                rel_path = os.path.relpath(file_path, directory)
                self.file_listbox.addItem(rel_path)
            
            if found_files:
                self.results_text.append(f"Added {len(found_files)} files from {directory}")
            else:
                self.results_text.append(f"No BG3 files found in {directory}")
            
            self.update_button_states()
    
    def remove_selected(self):
        """Remove selected files from list"""
        current_row = self.file_listbox.currentRow()
        if current_row >= 0:
            del self.file_list[current_row]
            self.file_listbox.takeItem(current_row)
            self.update_button_states()
    
    def clear_files(self):
        """Clear all files from list"""
        self.file_list.clear()
        self.file_listbox.clear()
        self.update_button_states()
    
    def browse_output_dir(self):
        """Browse for output directory"""
        initial_dir = self.settings_manager.get("working_directory", str(Path.home())) if self.settings_manager else str(Path.home())
        
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", initial_dir)
        if directory:
            self.output_dir_edit.setText(directory)
    
    def batch_convert(self):
        """Perform batch conversion"""
        if not self.file_list:
            QMessageBox.warning(self, "Warning", "No files selected for conversion")
            return
        
        if not self.wine_wrapper:
            QMessageBox.critical(self, "Error", "Batch conversion requires divine.exe integration")
            return
        
        target_format = self.target_format_combo.currentText()
        output_dir = self.output_dir_edit.text() or None
        
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create output directory: {e}")
                return
        
        # Clear previous results
        self.results_text.clear()
        self.results_text.append(f"Starting batch conversion to {target_format.upper()}...")
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start conversion thread
        self.conversion_thread = BatchConversionThread(
            self.wine_wrapper, self.file_list, target_format, output_dir
        )
        self.conversion_thread.progress_updated.connect(self.update_progress)
        self.conversion_thread.conversion_finished.connect(self.batch_conversion_finished)
        self.conversion_thread.start()
        
        # Disable convert button during operation
        self.convert_btn.setEnabled(False)
    
    def update_progress(self, percentage, message):
        """Update progress display"""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
    
    def batch_conversion_finished(self, results):
        """Handle completed batch conversion"""
        # Hide progress bar
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Conversion complete!")
        
        # Display results
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        self.results_text.append(f"\nConversion complete!")
        self.results_text.append(f"Successful: {successful}")
        self.results_text.append(f"Failed: {failed}\n")
        
        # Show detailed results
        for result in results:
            status = "✅" if result['success'] else "❌"
            source_name = os.path.basename(result['source'])
            
            if result['success']:
                target_name = os.path.basename(result['target'])
                self.results_text.append(f"{status} {source_name} -> {target_name}")
            else:
                self.results_text.append(f"{status} {source_name}: {result['output']}")
        
        # Re-enable convert button
        self.convert_btn.setEnabled(True)