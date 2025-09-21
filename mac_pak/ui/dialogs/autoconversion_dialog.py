import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QTextEdit
)

from PyQt6.QtCore import (
    QThread, QObject, pyqtSlot
)

from ...data.parsers.larian_parser import ProgressUpdate

class AutoConversionDialog(QDialog):
    """Dialog for showing conversion progress and results with threading"""
    
    def __init__(self, parent=None, processor=None, workspace_path=None):
        super().__init__(parent)
        self.processor = processor
        self.workspace_path = workspace_path
        self.conversion_thread = None
        self.conversion_worker = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the conversion dialog UI"""
        self.setWindowTitle("Auto-Conversion Progress")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Progress section
        self.progress_label = QLabel("Preparing workspace conversion...")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Results section
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_conversion)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setEnabled(False)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def start_conversion(self):
        """Start the conversion process in a separate thread"""
        if not self.processor or not self.workspace_path:
            QMessageBox.warning(self, "Error", "No processor or workspace path specified.")
            return
        
        # Create worker thread
        self.conversion_thread = QThread()
        self.conversion_worker = ConversionWorker(self.processor, self.workspace_path)
        self.conversion_worker.moveToThread(self.conversion_thread)
        
        # Connect signals
        self.conversion_worker.progress_updated.connect(self.update_progress)
        self.conversion_worker.conversion_completed.connect(self.conversion_completed)
        self.conversion_thread.started.connect(self.conversion_worker.prepare_workspace)
        self.conversion_thread.finished.connect(self.conversion_thread.deleteLater)
        self.conversion_worker.conversion_completed.connect(self.conversion_thread.quit)
        
        # Start thread
        self.conversion_thread.start()
        
        self.results_text.append("Conversion started...")
    
    @pyqtSlot(ProgressUpdate)
    def update_progress(self, progress: ProgressUpdate):
        """Update progress display"""
        self.progress_bar.setValue(progress.current)
        self.progress_label.setText(progress.message)
        self.results_text.append(f"[{progress.current}%] {progress.message}")
    
    @pyqtSlot(dict)
    def conversion_completed(self, result: dict):
        """Handle conversion completion"""
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        if result.get('errors'):
            self.results_text.append("\nConversion completed with errors:")
            for error in result['errors']:
                self.results_text.append(f"  • {error}")
        else:
            self.results_text.append("\nConversion completed successfully!")
        
        conversions = result.get('conversions', [])
        if conversions:
            self.results_text.append(f"\nConverted {len(conversions)} files:")
            for conv in conversions:
                status = "✓" if conv['success'] else "✗"
                self.results_text.append(f"  {status} {conv['conversion_type']}")
        
        # Store result for parent
        self.conversion_result = result
    
    def cancel_conversion(self):
        """Cancel the conversion process"""
        if self.conversion_worker:
            self.conversion_worker.stop_conversion()
        
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.quit()
            self.conversion_thread.wait(3000)
        
        self.results_text.append("\nConversion cancelled.")
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
    
    @staticmethod
    def show_conversion_preview(parent, conversion_files):
        """Show preview of files that will be converted"""
        dialog = QDialog(parent)
        dialog.setWindowTitle("Auto-Conversion Preview")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Info
        total_files = sum(len(files) for files in conversion_files.values())
        info_label = QLabel(f"Found {total_files} files that will be automatically converted:")
        layout.addWidget(info_label)
        
        # File tree
        tree = QTreeWidget()
        tree.setHeaderLabels(['File', 'Conversion', 'Location'])
        
        for conversion_type, files in conversion_files.items():
            if not files:
                continue
                
            # Create category item
            category_item = QTreeWidgetItem(tree)
            category_item.setText(0, conversion_type.replace('_', ' ').title())
            category_item.setText(1, f"{len(files)} files")
            
            for file_info in files:
                file_item = QTreeWidgetItem(category_item)
                file_name = os.path.basename(file_info['source'])
                file_item.setText(0, file_name)
                file_item.setText(1, f"→ {file_info['target_ext']}")
                file_item.setText(2, file_info['relative_path'])
        
        tree.expandAll()
        layout.addWidget(tree)
        
        # Info text
        info_text = QTextEdit()
        info_text.setMaximumHeight(100)
        info_text.setPlainText(
            "These files will be converted during PAK creation:\n"
            "• .lsf.lsx files will become .lsf files\n"
            "• .lsb.lsx files will become .lsb files\n"
            "• Original .lsx files will be preserved in your workspace"
        )
        layout.addWidget(info_text)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        return dialog.exec() == QDialog.DialogCode.Accepted