#!/usr/bin/env python3
"""
BG3 ID Generator - UUID and TranslatedString Handle Generator
Generates unique identifiers and handles for BG3 mod development
"""

import uuid
import random
import string
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

class UUIDGenerator:
    """Generates various types of UUIDs for BG3 modding"""
    
    @staticmethod
    def generate_uuid4():
        """Generate standard UUID4"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_bg3_uuid():
        """Generate BG3-style UUID (same as UUID4 but formatted for BG3)"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_multiple_uuids(count):
        """Generate multiple UUIDs"""
        return [str(uuid.uuid4()) for _ in range(count)]
    
    @staticmethod
    def validate_uuid(uuid_string):
        """Validate if string is a valid UUID"""
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False

class TranslatedStringGenerator:
    """Generates TranslatedString handles for BG3 localization"""
    
    def __init__(self):
        # BG3 uses specific handle ranges for different content types
        self.handle_ranges = {
            'custom_mod': (0x10000000, 0x1FFFFFFF),  # Custom mod range
            'dialog': (0x20000000, 0x2FFFFFFF),      # Dialog content
            'items': (0x30000000, 0x3FFFFFFF),       # Items and equipment
            'spells': (0x40000000, 0x4FFFFFFF),      # Spells and abilities
            'characters': (0x50000000, 0x5FFFFFFF),  # Character names/descriptions
            'general': (0x60000000, 0x6FFFFFFF),     # General content
        }
    
    def generate_handle(self, content_type='custom_mod'):
        """Generate a TranslatedString handle for specific content type"""
        if content_type not in self.handle_ranges:
            content_type = 'custom_mod'
        
        min_val, max_val = self.handle_ranges[content_type]
        handle = random.randint(min_val, max_val)
        
        # Format as hex string with 'h' prefix (BG3 format)
        return f"h{handle:08x}"
    
    def generate_multiple_handles(self, count, content_type='custom_mod'):
        """Generate multiple unique handles"""
        handles = set()
        
        while len(handles) < count:
            handles.add(self.generate_handle(content_type))
        
        return list(handles)
    
    def validate_handle(self, handle_string):
        """Validate TranslatedString handle format"""
        if not handle_string.startswith('h'):
            return False, "Handle must start with 'h'"
        
        try:
            hex_part = handle_string[1:]
            int(hex_part, 16)
            return True, "Valid handle"
        except ValueError:
            return False, "Invalid hexadecimal format"
    
    def get_content_type_from_handle(self, handle_string):
        """Determine content type from handle value"""
        try:
            hex_part = handle_string[1:]
            value = int(hex_part, 16)
            
            for content_type, (min_val, max_val) in self.handle_ranges.items():
                if min_val <= value <= max_val:
                    return content_type
            
            return 'unknown'
        except:
            return 'invalid'

class BG3IDGeneratorWidget(QWidget):
    """Combined widget for UUID and handle generation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.uuid_generator = UUIDGenerator()
        self.handle_generator = TranslatedStringGenerator()
        self.generated_items = []  # Store generated items
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the generator interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Title
        title_label = QLabel("BG3 ID Generator")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Combined ID Generator tab
        id_tab = self.create_id_generator_tab()
        self.tab_widget.addTab(id_tab, "ID Generator")
        
        # Individual generators tab
        individual_tab = self.create_individual_generators_tab()
        self.tab_widget.addTab(individual_tab, "Individual Generators")
        
        # History tab
        history_tab = self.create_history_tab()
        self.tab_widget.addTab(history_tab, "Generated Items")
        
        layout.addWidget(self.tab_widget)
    
    def create_id_generator_tab(self):
        """Create combined UUID and Handle generation tab"""
        tab = QWidget()
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Content widget
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(25)
        
        # Combined Generator section at top
        combined_group = self.create_styled_group("Generate Paired UUIDs & Handles", 18)
        combined_layout = QVBoxLayout(combined_group)
        
        # Options for paired generation
        paired_options = QFormLayout()
        
        self.paired_count_spin = QSpinBox()
        self.paired_count_spin.setMinimum(1)
        self.paired_count_spin.setMaximum(100)
        self.paired_count_spin.setValue(5)
        paired_options.addRow("Number of Pairs:", self.paired_count_spin)
        
        self.paired_content_type = QComboBox()
        self.paired_content_type.addItems(['custom_mod', 'dialog', 'items', 'spells', 'characters', 'general'])
        paired_options.addRow("Content Type:", self.paired_content_type)
        
        combined_layout.addLayout(paired_options)
        
        generate_pairs_btn = QPushButton("Generate UUID/Handle Pairs")
        generate_pairs_btn.clicked.connect(self.generate_paired_ids)
        combined_layout.addWidget(generate_pairs_btn)
        
        # Results table for pairs
        self.pairs_table = QTableWidget()
        self.pairs_table.setColumnCount(2)
        self.pairs_table.setHorizontalHeaderLabels(['UUID', 'TranslatedString Handle'])
        self.pairs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pairs_table.setMaximumHeight(250)
        combined_layout.addWidget(self.pairs_table)
        
        copy_pairs_btn = QPushButton("Copy All Pairs to Clipboard")
        copy_pairs_btn.clicked.connect(self.copy_paired_ids)
        combined_layout.addWidget(copy_pairs_btn)
        
        main_layout.addWidget(combined_group)
        
        # Validation section (full width)
        validation_group = self.create_styled_group("Validation", 16)
        validation_layout = QVBoxLayout(validation_group)
        
        # UUID validation
        uuid_val_layout = QHBoxLayout()
        uuid_val_layout.addWidget(QLabel("UUID:"))
        self.uuid_validation_input = QLineEdit()
        self.uuid_validation_input.setPlaceholderText("Enter UUID to validate")
        self.uuid_validation_input.textChanged.connect(self.validate_uuid_input)
        uuid_val_layout.addWidget(self.uuid_validation_input)
        validation_layout.addLayout(uuid_val_layout)
        
        self.uuid_validation_result = QLabel("Enter a UUID to validate")
        validation_layout.addWidget(self.uuid_validation_result)
        
        # Handle validation
        handle_val_layout = QHBoxLayout()
        handle_val_layout.addWidget(QLabel("Handle:"))
        self.handle_validation_input = QLineEdit()
        self.handle_validation_input.setPlaceholderText("Enter handle to validate (e.g., h12345678)")
        self.handle_validation_input.textChanged.connect(self.validate_handle_input)
        handle_val_layout.addWidget(self.handle_validation_input)
        validation_layout.addLayout(handle_val_layout)
        
        self.handle_validation_result = QLabel("Enter a handle to validate")
        validation_layout.addWidget(self.handle_validation_result)
        
        main_layout.addWidget(validation_group)
        
        # Handle Information at bottom
        info_group = self.create_styled_group("Handle Information", 16)
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel("""
<b>TranslatedString Handle Ranges:</b> Custom Mod: h10000000-h1FFFFFFF, Dialog: h20000000-h2FFFFFFF, Items: h30000000-h3FFFFFFF, Spells: h40000000-h4FFFFFFF, Characters: h50000000-h5FFFFFFF, General: h60000000-h6FFFFFFF<br>
<b>Usage:</b> UUIDs identify unique objects, while handles reference localized text entries in LSX files.
        """)
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        main_layout.addWidget(info_group)
        
        # Setup scroll
        scroll.setWidget(content_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        
        return tab
    
    def create_individual_generators_tab(self):
        """Create individual UUID and handle generators tab"""
        tab = QWidget()
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Content widget
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(25)
        
        # Grid for individual generators
        grid = QGridLayout()
        grid.setSpacing(20)
        
        # Individual UUID section
        uuid_group = self.create_styled_group("UUID Generator", 16)
        uuid_layout = QVBoxLayout(uuid_group)
        
        # Single UUID
        generate_uuid_btn = QPushButton("Generate Single UUID")
        generate_uuid_btn.clicked.connect(self.generate_single_uuid)
        uuid_layout.addWidget(generate_uuid_btn)
        
        self.single_uuid_result = QLineEdit()
        self.single_uuid_result.setReadOnly(True)
        self.single_uuid_result.setPlaceholderText("Generated UUID will appear here")
        uuid_layout.addWidget(self.single_uuid_result)
        
        copy_uuid_btn = QPushButton("Copy UUID")
        copy_uuid_btn.clicked.connect(self.copy_single_uuid)
        uuid_layout.addWidget(copy_uuid_btn)
        
        # Multiple UUIDs
        uuid_count_layout = QFormLayout()
        self.uuid_count_spin = QSpinBox()
        self.uuid_count_spin.setMinimum(1)
        self.uuid_count_spin.setMaximum(100)
        self.uuid_count_spin.setValue(5)
        uuid_count_layout.addRow("Count:", self.uuid_count_spin)
        uuid_layout.addLayout(uuid_count_layout)
        
        generate_multiple_uuids_btn = QPushButton("Generate Multiple UUIDs")
        generate_multiple_uuids_btn.clicked.connect(self.generate_multiple_uuids)
        uuid_layout.addWidget(generate_multiple_uuids_btn)
        
        self.batch_uuid_results = QTextEdit()
        self.batch_uuid_results.setMaximumHeight(150)
        self.batch_uuid_results.setPlaceholderText("Generated UUIDs will appear here")
        uuid_layout.addWidget(self.batch_uuid_results)
        
        copy_multiple_uuids_btn = QPushButton("Copy All UUIDs")
        copy_multiple_uuids_btn.clicked.connect(self.copy_batch_uuids)
        uuid_layout.addWidget(copy_multiple_uuids_btn)
        
        # Individual Handle section
        handle_group = self.create_styled_group("TranslatedString Handle Generator", 16)
        handle_layout = QVBoxLayout(handle_group)
        
        # Single handle
        handle_type_layout = QFormLayout()
        self.single_content_type = QComboBox()
        self.single_content_type.addItems(['custom_mod', 'dialog', 'items', 'spells', 'characters', 'general'])
        handle_type_layout.addRow("Content Type:", self.single_content_type)
        handle_layout.addLayout(handle_type_layout)
        
        generate_handle_btn = QPushButton("Generate Single Handle")
        generate_handle_btn.clicked.connect(self.generate_single_handle)
        handle_layout.addWidget(generate_handle_btn)
        
        self.single_handle_result = QLineEdit()
        self.single_handle_result.setReadOnly(True)
        self.single_handle_result.setPlaceholderText("Generated handle will appear here")
        handle_layout.addWidget(self.single_handle_result)
        
        copy_handle_btn = QPushButton("Copy Handle")
        copy_handle_btn.clicked.connect(self.copy_single_handle)
        handle_layout.addWidget(copy_handle_btn)
        
        # Multiple handles
        handle_count_layout = QFormLayout()
        self.handle_count_spin = QSpinBox()
        self.handle_count_spin.setMinimum(1)
        self.handle_count_spin.setMaximum(100)
        self.handle_count_spin.setValue(10)
        handle_count_layout.addRow("Count:", self.handle_count_spin)
        
        self.batch_content_type = QComboBox()
        self.batch_content_type.addItems(['custom_mod', 'dialog', 'items', 'spells', 'characters', 'general'])
        handle_count_layout.addRow("Content Type:", self.batch_content_type)
        handle_layout.addLayout(handle_count_layout)
        
        generate_multiple_handles_btn = QPushButton("Generate Multiple Handles")
        generate_multiple_handles_btn.clicked.connect(self.generate_multiple_handles)
        handle_layout.addWidget(generate_multiple_handles_btn)
        
        self.batch_handle_results = QTextEdit()
        self.batch_handle_results.setMaximumHeight(150)
        self.batch_handle_results.setPlaceholderText("Generated handles will appear here")
        handle_layout.addWidget(self.batch_handle_results)
        
        copy_multiple_handles_btn = QPushButton("Copy All Handles")
        copy_multiple_handles_btn.clicked.connect(self.copy_batch_handles)
        handle_layout.addWidget(copy_multiple_handles_btn)
        
        grid.addWidget(uuid_group, 0, 0)
        grid.addWidget(handle_group, 0, 1)
        
        # Make columns equal width
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        
        main_layout.addLayout(grid)
        
        # Setup scroll
        scroll.setWidget(content_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        
        return tab
    
    def create_history_tab(self):
        """Create history/generated items tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
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
        
        return tab
    
    def create_styled_group(self, title, font_size=16):
        """Create a styled QGroupBox with custom font size"""
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {font_size}px;
                font-weight: bold;
                margin-top: 10px;
                padding-top: 20px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        return group
    
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
            
            # Add to history
            self.add_to_history('UUID', uuid_val, 'N/A')
            self.add_to_history('Handle', handle_val, content_type)
        
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
    
    def generate_single_uuid(self):
        """Generate a single UUID"""
        new_uuid = self.uuid_generator.generate_uuid4()
        self.single_uuid_result.setText(new_uuid)
        
        # Add to history
        self.add_to_history('UUID', new_uuid, 'N/A')
    
    def generate_multiple_uuids(self):
        """Generate multiple UUIDs"""
        count = self.uuid_count_spin.value()
        uuids = self.uuid_generator.generate_multiple_uuids(count)
        
        # Display results
        result_text = '\n'.join(uuids)
        self.batch_uuid_results.setPlainText(result_text)
        
        # Add to history
        for uuid_val in uuids:
            self.add_to_history('UUID', uuid_val, 'N/A')
    
    def generate_single_handle(self):
        """Generate a single TranslatedString handle"""
        content_type = self.single_content_type.currentText()
        handle = self.handle_generator.generate_handle(content_type)
        self.single_handle_result.setText(handle)
        
        # Add to history
        self.add_to_history('Handle', handle, content_type)
    
    def generate_multiple_handles(self):
        """Generate multiple TranslatedString handles"""
        count = self.handle_count_spin.value()
        content_type = self.batch_content_type.currentText()
        handles = self.handle_generator.generate_multiple_handles(count, content_type)
        
        # Display results
        result_text = '\n'.join(handles)
        self.batch_handle_results.setPlainText(result_text)
        
        # Add to history
        for handle in handles:
            self.add_to_history('Handle', handle, content_type)
    
    def copy_single_uuid(self):
        """Copy single UUID to clipboard"""
        uuid_text = self.single_uuid_result.text()
        if uuid_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(uuid_text)
            self.show_copy_message("UUID copied to clipboard")
    
    def copy_batch_uuids(self):
        """Copy batch UUIDs to clipboard"""
        uuids_text = self.batch_uuid_results.toPlainText()
        if uuids_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(uuids_text)
            self.show_copy_message("UUIDs copied to clipboard")
    
    def copy_single_handle(self):
        """Copy single handle to clipboard"""
        handle_text = self.single_handle_result.text()
        if handle_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(handle_text)
            self.show_copy_message("Handle copied to clipboard")
    
    def copy_batch_handles(self):
        """Copy batch handles to clipboard"""
        handles_text = self.batch_handle_results.toPlainText()
        if handles_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(handles_text)
            self.show_copy_message("Handles copied to clipboard")
#!/usr/bin/env python3
"""
BG3 ID Generator - UUID and TranslatedString Handle Generator
Generates unique identifiers and handles for BG3 mod development
"""

import uuid
import random
import string
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

class UUIDGenerator:
    """Generates various types of UUIDs for BG3 modding"""
    
    @staticmethod
    def generate_uuid4():
        """Generate standard UUID4"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_bg3_uuid():
        """Generate BG3-style UUID (same as UUID4 but formatted for BG3)"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_multiple_uuids(count):
        """Generate multiple UUIDs"""
        return [str(uuid.uuid4()) for _ in range(count)]
    
    @staticmethod
    def validate_uuid(uuid_string):
        """Validate if string is a valid UUID"""
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False

class TranslatedStringGenerator:
    """Generates TranslatedString handles for BG3 localization"""
    
    def __init__(self):
        # BG3 uses specific handle ranges for different content types
        self.handle_ranges = {
            'custom_mod': (0x10000000, 0x1FFFFFFF),  # Custom mod range
            'dialog': (0x20000000, 0x2FFFFFFF),      # Dialog content
            'items': (0x30000000, 0x3FFFFFFF),       # Items and equipment
            'spells': (0x40000000, 0x4FFFFFFF),      # Spells and abilities
            'characters': (0x50000000, 0x5FFFFFFF),  # Character names/descriptions
            'general': (0x60000000, 0x6FFFFFFF),     # General content
        }
    
    def generate_handle(self, content_type='custom_mod'):
        """Generate a TranslatedString handle for specific content type"""
        if content_type not in self.handle_ranges:
            content_type = 'custom_mod'
        
        min_val, max_val = self.handle_ranges[content_type]
        handle = random.randint(min_val, max_val)
        
        # Format as hex string with 'h' prefix (BG3 format)
        return f"h{handle:08x}"
    
    def generate_multiple_handles(self, count, content_type='custom_mod'):
        """Generate multiple unique handles"""
        handles = set()
        
        while len(handles) < count:
            handles.add(self.generate_handle(content_type))
        
        return list(handles)
    
    def validate_handle(self, handle_string):
        """Validate TranslatedString handle format"""
        if not handle_string.startswith('h'):
            return False, "Handle must start with 'h'"
        
        try:
            hex_part = handle_string[1:]
            int(hex_part, 16)
            return True, "Valid handle"
        except ValueError:
            return False, "Invalid hexadecimal format"
    
    def get_content_type_from_handle(self, handle_string):
        """Determine content type from handle value"""
        try:
            hex_part = handle_string[1:]
            value = int(hex_part, 16)
            
            for content_type, (min_val, max_val) in self.handle_ranges.items():
                if min_val <= value <= max_val:
                    return content_type
            
            return 'unknown'
        except:
            return 'invalid'

class BG3IDGeneratorWidget(QWidget):
    """Combined widget for UUID and handle generation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.uuid_generator = UUIDGenerator()
        self.handle_generator = TranslatedStringGenerator()
        self.generated_items = []  # Store generated items
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the generator interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Title
        title_label = QLabel("BG3 ID Generator")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Combined ID Generator tab
        id_tab = self.create_id_generator_tab()
        self.tab_widget.addTab(id_tab, "ID Generator")
        
        # Individual generators tab
        individual_tab = self.create_individual_generators_tab()
        self.tab_widget.addTab(individual_tab, "Individual Generators")
        
        # History tab
        history_tab = self.create_history_tab()
        self.tab_widget.addTab(history_tab, "Generated Items")
        
        layout.addWidget(self.tab_widget)
    
    def create_id_generator_tab(self):
        """Create combined UUID and Handle generation tab"""
        tab = QWidget()
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Content widget
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(25)
        
        # Combined Generator section at top
        combined_group = self.create_styled_group("Generate Paired UUIDs + TranslatedString Handles", 18)
        combined_layout = QVBoxLayout(combined_group)
        
        # Options for paired generation
        paired_options = QFormLayout()
        
        self.paired_count_spin = QSpinBox()
        self.paired_count_spin.setMinimum(1)
        self.paired_count_spin.setMaximum(100)
        self.paired_count_spin.setValue(5)
        paired_options.addRow("Number of Pairs:", self.paired_count_spin)
        
        self.paired_content_type = QComboBox()
        self.paired_content_type.addItems(['custom_mod', 'dialog', 'items', 'spells', 'characters', 'general'])
        paired_options.addRow("Content Type:", self.paired_content_type)
        
        combined_layout.addLayout(paired_options)
        
        generate_pairs_btn = QPushButton("Generate UUID/Handle Pairs")
        generate_pairs_btn.clicked.connect(self.generate_paired_ids)
        combined_layout.addWidget(generate_pairs_btn)
        
        # Results table for pairs
        self.pairs_table = QTableWidget()
        self.pairs_table.setColumnCount(2)
        self.pairs_table.setHorizontalHeaderLabels(['UUID', 'TranslatedString Handle'])
        self.pairs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pairs_table.setMaximumHeight(250)
        combined_layout.addWidget(self.pairs_table)
        
        copy_pairs_btn = QPushButton("Copy All Pairs to Clipboard")
        copy_pairs_btn.clicked.connect(self.copy_paired_ids)
        combined_layout.addWidget(copy_pairs_btn)
        
        main_layout.addWidget(combined_group)
        
        # Three-column layout: UUID Validation + Handle Validation (stacked) | Handle Information
        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(15)
        
        # Left column: Stacked validation sections
        left_column = QVBoxLayout()
        left_column.setSpacing(15)
        
        # UUID Validation
        uuid_validation_group = self.create_styled_group("UUID Validation", 16)
        uuid_validation_layout = QVBoxLayout(uuid_validation_group)
        
        self.uuid_validation_input = QLineEdit()
        self.uuid_validation_input.setPlaceholderText("Enter UUID to validate")
        self.uuid_validation_input.textChanged.connect(self.validate_uuid_input)
        uuid_validation_layout.addWidget(self.uuid_validation_input)
        
        self.uuid_validation_result = QLabel("Enter a UUID to validate")
        uuid_validation_layout.addWidget(self.uuid_validation_result)
        
        left_column.addWidget(uuid_validation_group)
        
        # Handle Validation  
        handle_validation_group = self.create_styled_group("Handle Validation", 16)
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
        
        # Right column: Handle Information
        info_group = self.create_styled_group("Handle Information", 16)
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
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        
        return tab
    
    def create_individual_generators_tab(self):
        """Create individual UUID and handle generators tab"""
        tab = QWidget()
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Content widget
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(25)
        
        # Grid for individual generators
        grid = QGridLayout()
        grid.setSpacing(20)
        
        # Individual UUID section
        uuid_group = self.create_styled_group("UUID Generator", 16)
        uuid_layout = QVBoxLayout(uuid_group)
        
        # Single UUID
        generate_uuid_btn = QPushButton("Generate Single UUID")
        generate_uuid_btn.clicked.connect(self.generate_single_uuid)
        uuid_layout.addWidget(generate_uuid_btn)
        
        self.single_uuid_result = QLineEdit()
        self.single_uuid_result.setReadOnly(True)
        self.single_uuid_result.setPlaceholderText("Generated UUID will appear here")
        uuid_layout.addWidget(self.single_uuid_result)
        
        copy_uuid_btn = QPushButton("Copy UUID")
        copy_uuid_btn.clicked.connect(self.copy_single_uuid)
        uuid_layout.addWidget(copy_uuid_btn)
        
        # Multiple UUIDs
        uuid_count_layout = QFormLayout()
        self.uuid_count_spin = QSpinBox()
        self.uuid_count_spin.setMinimum(1)
        self.uuid_count_spin.setMaximum(100)
        self.uuid_count_spin.setValue(5)
        uuid_count_layout.addRow("Count:", self.uuid_count_spin)
        uuid_layout.addLayout(uuid_count_layout)
        
        generate_multiple_uuids_btn = QPushButton("Generate Multiple UUIDs")
        generate_multiple_uuids_btn.clicked.connect(self.generate_multiple_uuids)
        uuid_layout.addWidget(generate_multiple_uuids_btn)
        
        self.batch_uuid_results = QTextEdit()
        self.batch_uuid_results.setMaximumHeight(150)
        self.batch_uuid_results.setPlaceholderText("Generated UUIDs will appear here")
        uuid_layout.addWidget(self.batch_uuid_results)
        
        copy_multiple_uuids_btn = QPushButton("Copy All UUIDs")
        copy_multiple_uuids_btn.clicked.connect(self.copy_batch_uuids)
        uuid_layout.addWidget(copy_multiple_uuids_btn)
        
        # Individual Handle section
        handle_group = self.create_styled_group("TranslatedString Handle Generator", 16)
        handle_layout = QVBoxLayout(handle_group)
        
        # Single handle
        handle_type_layout = QFormLayout()
        self.single_content_type = QComboBox()
        self.single_content_type.addItems(['custom_mod', 'dialog', 'items', 'spells', 'characters', 'general'])
        handle_type_layout.addRow("Content Type:", self.single_content_type)
        handle_layout.addLayout(handle_type_layout)
        
        generate_handle_btn = QPushButton("Generate Single Handle")
        generate_handle_btn.clicked.connect(self.generate_single_handle)
        handle_layout.addWidget(generate_handle_btn)
        
        self.single_handle_result = QLineEdit()
        self.single_handle_result.setReadOnly(True)
        self.single_handle_result.setPlaceholderText("Generated handle will appear here")
        handle_layout.addWidget(self.single_handle_result)
        
        copy_handle_btn = QPushButton("Copy Handle")
        copy_handle_btn.clicked.connect(self.copy_single_handle)
        handle_layout.addWidget(copy_handle_btn)
        
        # Multiple handles
        handle_count_layout = QFormLayout()
        self.handle_count_spin = QSpinBox()
        self.handle_count_spin.setMinimum(1)
        self.handle_count_spin.setMaximum(100)
        self.handle_count_spin.setValue(10)
        handle_count_layout.addRow("Count:", self.handle_count_spin)
        
        self.batch_content_type = QComboBox()
        self.batch_content_type.addItems(['custom_mod', 'dialog', 'items', 'spells', 'characters', 'general'])
        handle_count_layout.addRow("Content Type:", self.batch_content_type)
        handle_layout.addLayout(handle_count_layout)
        
        generate_multiple_handles_btn = QPushButton("Generate Multiple Handles")
        generate_multiple_handles_btn.clicked.connect(self.generate_multiple_handles)
        handle_layout.addWidget(generate_multiple_handles_btn)
        
        self.batch_handle_results = QTextEdit()
        self.batch_handle_results.setMaximumHeight(150)
        self.batch_handle_results.setPlaceholderText("Generated handles will appear here")
        handle_layout.addWidget(self.batch_handle_results)
        
        copy_multiple_handles_btn = QPushButton("Copy All Handles")
        copy_multiple_handles_btn.clicked.connect(self.copy_batch_handles)
        handle_layout.addWidget(copy_multiple_handles_btn)
        
        grid.addWidget(uuid_group, 0, 0)
        grid.addWidget(handle_group, 0, 1)
        
        # Make columns equal width
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        
        main_layout.addLayout(grid)
        
        # Setup scroll
        scroll.setWidget(content_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        
        return tab
    
    def create_history_tab(self):
        """Create history/generated items tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
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
        
        return tab
    
    def create_styled_group(self, title, font_size=16):
        """Create a styled QGroupBox with custom font size"""
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {font_size}px;
                font-weight: bold;
                margin-top: 10px;
                padding-top: 20px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        return group
    
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
            
            # Add to history
            self.add_to_history('UUID', uuid_val, 'N/A')
            self.add_to_history('Handle', handle_val, content_type)
        
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
    
    def generate_single_uuid(self):
        """Generate a single UUID"""
        new_uuid = self.uuid_generator.generate_uuid4()
        self.single_uuid_result.setText(new_uuid)
        
        # Add to history
        self.add_to_history('UUID', new_uuid, 'N/A')
    
    def generate_multiple_uuids(self):
        """Generate multiple UUIDs"""
        count = self.uuid_count_spin.value()
        uuids = self.uuid_generator.generate_multiple_uuids(count)
        
        # Display results
        result_text = '\n'.join(uuids)
        self.batch_uuid_results.setPlainText(result_text)
        
        # Add to history
        for uuid_val in uuids:
            self.add_to_history('UUID', uuid_val, 'N/A')
    
    def generate_single_handle(self):
        """Generate a single TranslatedString handle"""
        content_type = self.single_content_type.currentText()
        handle = self.handle_generator.generate_handle(content_type)
        self.single_handle_result.setText(handle)
        
        # Add to history
        self.add_to_history('Handle', handle, content_type)
    
    def generate_multiple_handles(self):
        """Generate multiple TranslatedString handles"""
        count = self.handle_count_spin.value()
        content_type = self.batch_content_type.currentText()
        handles = self.handle_generator.generate_multiple_handles(count, content_type)
        
        # Display results
        result_text = '\n'.join(handles)
        self.batch_handle_results.setPlainText(result_text)
        
        # Add to history
        for handle in handles:
            self.add_to_history('Handle', handle, content_type)
    
    def copy_single_uuid(self):
        """Copy single UUID to clipboard"""
        uuid_text = self.single_uuid_result.text()
        if uuid_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(uuid_text)
            self.show_copy_message("UUID copied to clipboard")
    
    def copy_batch_uuids(self):
        """Copy batch UUIDs to clipboard"""
        uuids_text = self.batch_uuid_results.toPlainText()
        if uuids_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(uuids_text)
            self.show_copy_message("UUIDs copied to clipboard")
    
    def copy_single_handle(self):
        """Copy single handle to clipboard"""
        handle_text = self.single_handle_result.text()
        if handle_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(handle_text)
            self.show_copy_message("Handle copied to clipboard")
    
    def copy_batch_handles(self):
        """Copy batch handles to clipboard"""
        handles_text = self.batch_handle_results.toPlainText()
        if handles_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(handles_text)
            self.show_copy_message("Handles copied to clipboard")
    
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
        
        if not uuid_text:
            self.uuid_validation_result.setText("Enter a UUID to validate")
            self.uuid_validation_result.setStyleSheet("")
            return
        
        is_valid = self.uuid_generator.validate_uuid(uuid_text)
        
        if is_valid:
            self.uuid_validation_result.setText("✅ Valid UUID format")
            self.uuid_validation_result.setStyleSheet("color: green;")
        else:
            self.uuid_validation_result.setText("❌ Invalid UUID format")
            self.uuid_validation_result.setStyleSheet("color: red;")
    
    def validate_handle_input(self):
        """Validate handle input in real-time"""
        handle_text = self.handle_validation_input.text()
        
        if not handle_text:
            self.handle_validation_result.setText("Enter a handle to validate")
            self.handle_validation_result.setStyleSheet("")
            return
        
        is_valid, message = self.handle_generator.validate_handle(handle_text)
        content_type = self.handle_generator.get_content_type_from_handle(handle_text)
        
        if is_valid:
            self.handle_validation_result.setText(f"✅ {message} (Type: {content_type})")
            self.handle_validation_result.setStyleSheet("color: green;")
        else:
            self.handle_validation_result.setText(f"❌ {message}")
            self.handle_validation_result.setStyleSheet("color: red;")
    
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


# Alias for backwards compatibility
UUIDHandleWidget = BG3IDGeneratorWidget

# Test the widget if run directly
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    
    widget = BG3IDGeneratorWidget()
    widget.setWindowTitle("BG3 ID Generator")
    widget.resize(900, 700)
    widget.show()
    
    sys.exit(app.exec())