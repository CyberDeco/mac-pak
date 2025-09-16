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