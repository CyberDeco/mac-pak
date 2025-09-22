import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QGroupBox, QFormLayout, QSpinBox, QComboBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QTabWidget,
    QSplitter, QFrame, QApplication, QFileDialog, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

class HistoryWidget(QWidget):
    """History/generated items widget"""
    
    def __init__(self, parent=None, settings_manager=None, wine_wrapper=None):
        super().__init__(parent)
        
        self.generated_items = []  # Store generated items
        self.settings_manager = settings_manager
        self.wine_wrapper = wine_wrapper
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the history interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export to JSON")
        export_btn.clicked.connect(self.export_generated_items)
        controls_layout.addWidget(export_btn)
        
        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self.clear_history)
        controls_layout.addWidget(clear_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Generated items table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(['Type', 'Value', 'Content Type', 'Generated At'])
        
        # Make table fill width
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.history_table)
    
    def add_to_history(self, item_type, value, content_type):
        """Add generated item to history"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        item = {
            'type': item_type,
            'value': value,
            'content_type': content_type,
            'timestamp': timestamp
        }
        
        self.generated_items.append(item)
        
        # Update table
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        
        self.history_table.setItem(row, 0, QTableWidgetItem(item_type))
        self.history_table.setItem(row, 1, QTableWidgetItem(value))
        self.history_table.setItem(row, 2, QTableWidgetItem(content_type))
        self.history_table.setItem(row, 3, QTableWidgetItem(timestamp))
        
        # Scroll to bottom
        self.history_table.scrollToBottom()
    
    def clear_history(self):
        """Clear generation history"""
        reply = QMessageBox.question(
            self, "Clear History",
            "This will clear all generated UUIDs and handles. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.generated_items.clear()
            self.history_table.setRowCount(0)
    
    def export_generated_items(self):
        """Export generated items to JSON"""
        if not self.generated_items:
            QMessageBox.information(self, "Export", "No generated items to export.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Generated Items",
            f"bg3_generated_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                export_data = {
                    'export_date': datetime.now().isoformat(),
                    'total_items': len(self.generated_items),
                    'items': self.generated_items
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
                
                QMessageBox.information(
                    self, "Export Complete", 
                    f"Successfully exported {len(self.generated_items)} items to {file_path}"
                )
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export items: {e}")
    
    def get_history_count(self):
        """Get the number of items in history"""
        return len(self.generated_items)
    
    def get_history_items(self):
        """Get all history items"""
        return self.generated_items.copy()
    
    def load_history_items(self, items):
        """Load history items from external source"""
        self.generated_items = items
        self._refresh_table()
    
    def _refresh_table(self):
        """Refresh the history table display"""
        self.history_table.setRowCount(0)
        
        for item in self.generated_items:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            
            self.history_table.setItem(row, 0, QTableWidgetItem(item['type']))
            self.history_table.setItem(row, 1, QTableWidgetItem(item['value']))
            self.history_table.setItem(row, 2, QTableWidgetItem(item['content_type']))
            self.history_table.setItem(row, 3, QTableWidgetItem(item['timestamp']))