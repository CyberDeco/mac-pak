import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QGroupBox, QFormLayout, QSpinBox, QComboBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QTabWidget,
    QSplitter, QFrame, QApplication, QFileDialog, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# Import the backend classes
from ....data.generators.uuid_generator import UUIDGenerator, TranslatedStringGenerator

class IDGeneratorWidget(QWidget):
    """Combined UUID and Handle generation widget"""
    
    def __init__(self, parent=None, settings_manager=None, wine_wrapper=None):
        super().__init__(parent)
        
        self.uuid_generator = UUIDGenerator()
        self.handle_generator = TranslatedStringGenerator()
        self.settings_manager = settings_manager
        self.wine_wrapper = wine_wrapper
        
        # Signal for history updates
        self.history_updated = None  # Can be connected to history widget
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the generator interface"""
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Content widget
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Combined Generator section at top
        combined_group = QGroupBox("Generate Paired UUIDs + TranslatedString Handles")
        combined_group.setProperty("header", "h3")
        combined_layout = QVBoxLayout(combined_group)
        
        # Options for paired generation
        paired_options_container = QHBoxLayout()
        paired_options_container.addStretch()  # Left stretch
        
        paired_options = QHBoxLayout()
        paired_options.addWidget(QLabel("Number of Pairs:"))
        self.paired_count_spin = QSpinBox()
        self.paired_count_spin.setMinimum(1)
        self.paired_count_spin.setMaximum(100)
        self.paired_count_spin.setValue(5)
        paired_options.addWidget(self.paired_count_spin)
        
        paired_options.addSpacing(20)  # Space between controls
        
        paired_options.addWidget(QLabel("Content Type:"))
        self.paired_content_type = QComboBox()
        self.paired_content_type.addItems(['custom_mod', 'dialog', 'items', 'spells', 'characters', 'general'])
        paired_options.addWidget(self.paired_content_type)
        
        paired_options_container.addLayout(paired_options)
        paired_options_container.addStretch()  # Right stretch
        
        combined_layout.addLayout(paired_options_container)
    
        # Add the generate and copy buttons
        pairs_buttons = QHBoxLayout()
        
        generate_pairs_btn = QPushButton("Generate UUID/Handle Pairs")
        generate_pairs_btn.clicked.connect(self.generate_paired_ids)
        pairs_buttons.addWidget(generate_pairs_btn)
        pairs_buttons.addSpacing(30)
        
        copy_pairs_btn = QPushButton("Copy All Pairs to Clipboard")
        copy_pairs_btn.clicked.connect(self.copy_paired_ids)
        pairs_buttons.addWidget(copy_pairs_btn)
        combined_layout.addLayout(pairs_buttons)
        
        # Results table for pairs - MADE TALLER
        self.pairs_table = QTableWidget()
        self.pairs_table.setColumnCount(2)
        self.pairs_table.setHorizontalHeaderLabels(['UUID', 'TranslatedString Handle'])
        self.pairs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pairs_table.setMinimumHeight(300)  # Increased from 250 to 400
        combined_layout.addWidget(self.pairs_table)
        
        main_layout.addWidget(combined_group)
        
        # Three-column layout: UUID Validation + Handle Validation (stacked) | Handle Information
        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(10)
        
        # Left column: Stacked validation sections
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        
        # UUID Validation
        uuid_validation_group = QGroupBox("UUID Validation")
        uuid_validation_group.setProperty("header", "h3")
        uuid_validation_layout = QVBoxLayout(uuid_validation_group)
        
        self.uuid_validation_input = QLineEdit()
        self.uuid_validation_input.setPlaceholderText("Enter UUID to validate")
        self.uuid_validation_input.textChanged.connect(self.validate_uuid_input)
        uuid_validation_layout.addWidget(self.uuid_validation_input)
        
        self.uuid_validation_result = QLabel("Enter a UUID to validate")
        uuid_validation_layout.addWidget(self.uuid_validation_result)
        
        left_column.addWidget(uuid_validation_group)
        
        # Handle Validation  
        handle_validation_group = QGroupBox("TranslatedString Handle Validation")
        handle_validation_group.setProperty("header", "h3")
        handle_validation_layout = QVBoxLayout(handle_validation_group)
        
        self.handle_validation_input = QLineEdit()
        self.handle_validation_input.setPlaceholderText("Enter handle to validate (e.g., h12345678)")
        self.handle_validation_input.textChanged.connect(self.validate_handle_input)
        handle_validation_layout.addWidget(self.handle_validation_input)
        
        self.handle_validation_result = QLabel("Enter a handle to validate")
        handle_validation_layout.addWidget(self.handle_validation_result)
        
        left_column.addWidget(handle_validation_group)
        
        # Create left column widget
        left_widget = QWidget()
        left_widget.setLayout(left_column)
        
        # Right column: Handle Information - MADE SHORTER
        info_group = QGroupBox("Handle Information")
        info_group.setProperty("header", "h3")
        info_group.setMaximumHeight(280)  # Added height constraint to make it shorter
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel("""
        <b>Handle Ranges:</b><br>
        - Custom Mod: h10000000-h1FFFFFFF<br>
        - Dialog: h20000000-h2FFFFFFF<br>
        - Items: h30000000-h3FFFFFFF<br>
        - Spells: h40000000-h4FFFFFFF<br>
        - Characters: h50000000-h5FFFFFFF<br>
        - General: h60000000-h6FFFFFFF<br><br>
        <b>Usage:</b> UUIDs identify objects, handles reference localized text.
        """)
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        # Add to grid: 2 columns (left stacked validations, right info)
        bottom_grid.addWidget(left_widget, 0, 0)
        bottom_grid.addWidget(info_group, 0, 1)
        
        # Make columns equal width
        bottom_grid.setColumnStretch(0, 1)
        bottom_grid.setColumnStretch(1, 1)
        
        main_layout.addLayout(bottom_grid)
        
        # Setup scroll
        scroll.setWidget(content_widget)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
    
    def generate_paired_ids(self):
        """Generate UUID/Handle pairs"""
        count = self.paired_count_spin.value()
        content_type = self.paired_content_type.currentText()
        
        self.pairs_table.setRowCount(count)
        
        for i in range(count):
            uuid_val = self.uuid_generator.generate_uuid4()
            handle_val = self.handle_generator.generate_handle(content_type)
            
            self.pairs_table.setItem(i, 0, QTableWidgetItem(uuid_val))
            self.pairs_table.setItem(i, 1, QTableWidgetItem(handle_val))
            
            # Emit history updates if connected
            if self.history_updated:
                self.history_updated.emit('UUID', uuid_val, 'N/A')
                self.history_updated.emit('Handle', handle_val, content_type)
        
        self.show_copy_message(f"Generated {count} UUID/Handle pairs")
    
    def copy_paired_ids(self):
        """Copy all pairs to clipboard in a useful format"""
        rows = self.pairs_table.rowCount()
        if rows == 0:
            return
        
        text_lines = []
        for i in range(rows):
            uuid_item = self.pairs_table.item(i, 0)
            handle_item = self.pairs_table.item(i, 1)
            if uuid_item and handle_item:
                text_lines.append(f"UUID: {uuid_item.text()}, Handle: {handle_item.text()}")
        
        clipboard = QApplication.clipboard()
        clipboard.setText('\n'.join(text_lines))
        self.show_copy_message("Pairs copied to clipboard")
    
    def show_copy_message(self, message):
        """Show temporary copy confirmation"""
        # Create a temporary label to show copy confirmation
        if hasattr(self, 'copy_label') and self.copy_label is not None:
            try:
                self.copy_label.deleteLater()
            except RuntimeError:
                # Label already deleted, ignore
                pass
        
        self.copy_label = QLabel(message)
        self.copy_label.setStyleSheet("""
            QLabel {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 3px;
            }
        """)
        self.copy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.copy_label.setParent(self)
        self.copy_label.adjustSize()  # Auto-size based on content
        
        # Center horizontally
        x = (self.width() - self.copy_label.width()) // 2
        self.copy_label.move(x, 10)
        self.copy_label.show()
        
        # Hide after 2 seconds and clear reference
        def cleanup_label():
            if hasattr(self, 'copy_label') and self.copy_label is not None:
                try:
                    self.copy_label.deleteLater()
                except RuntimeError:
                    pass
                self.copy_label = None
        
        QTimer.singleShot(2000, cleanup_label)
    
    def validate_uuid_input(self):
        """Validate UUID input in real-time"""
        uuid_text = self.uuid_validation_input.text()
        self._update_uuid_validation(uuid_text, self.uuid_validation_result)
    
    def validate_handle_input(self):
        """Validate handle input in real-time"""
        handle_text = self.handle_validation_input.text()
        self._update_handle_validation(handle_text, self.handle_validation_result)
    
    def _update_uuid_validation(self, uuid_text, result_label):
        """Helper method to update UUID validation display"""
        if not uuid_text:
            result_label.setText("Enter a UUID to validate")
            result_label.setStyleSheet("")
            return
        
        is_valid = self.uuid_generator.validate_uuid(uuid_text)
        
        if is_valid:
            result_label.setText("✅ Valid UUID format")
            result_label.setStyleSheet("color: green;")
        else:
            result_label.setText("❌ Invalid UUID format")
            result_label.setStyleSheet("color: red;")
    
    def _update_handle_validation(self, handle_text, result_label):
        """Helper method to update handle validation display"""
        if not handle_text:
            result_label.setText("Enter a TranslatedString handle to validate")
            result_label.setStyleSheet("")
            return
        
        is_valid, message = self.handle_generator.validate_handle(handle_text)
        content_type = self.handle_generator.get_content_type_from_handle(handle_text)
        
        if is_valid:
            result_label.setText(f"✅ {message} (Type: {content_type})")
            result_label.setStyleSheet("color: green;")
        else:
            result_label.setText(f"❌ {message}")
            result_label.setStyleSheet("color: red;")