#!/usr/bin/env python3
"""
BG3 LSX Tools - PyQt6 Version
Universal editor supporting LSX, LSJ, and LSF formats with syntax highlighting
"""

import xml.etree.ElementTree as ET
import json
import os
import re
import threading
from pathlib import Path
from collections import defaultdict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QFileDialog, QMessageBox, QTabWidget, QListWidget,
    QSplitter, QFrame, QGroupBox, QComboBox, QProgressBar,
    QFormLayout, QLineEdit, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter, QTextDocument

# Import your existing backend
from ...data.parsers.larian_parser import UniversalBG3Parser

class LSXSyntaxHighlighter(QSyntaxHighlighter):
    """PyQt6 syntax highlighter for LSX/JSON files - OPTIMIZED"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_format = 'lsx'
        self.setup_highlighting_rules()
        self.precompile_patterns()  # NEW: Precompile all regex patterns
    
    def setup_highlighting_rules(self):
        """Setup highlighting formats"""
        # XML/LSX formats
        self.xml_tag_format = QTextCharFormat()
        self.xml_tag_format.setForeground(QColor("#0066CC"))
        self.xml_tag_format.setFontWeight(QFont.Weight.Bold)
        
        self.xml_attribute_format = QTextCharFormat()
        self.xml_attribute_format.setForeground(QColor("#006600"))
        
        self.xml_value_format = QTextCharFormat()
        self.xml_value_format.setForeground(QColor("#CC0000"))
        
        # JSON/LSJ formats
        self.json_key_format = QTextCharFormat()
        self.json_key_format.setForeground(QColor("#0066CC"))
        self.json_key_format.setFontWeight(QFont.Weight.Bold)
        
        self.json_string_format = QTextCharFormat()
        self.json_string_format.setForeground(QColor("#CC0000"))
        
        self.json_number_format = QTextCharFormat()
        self.json_number_format.setForeground(QColor("#FF6600"))
        
        self.json_bool_format = QTextCharFormat()
        self.json_bool_format.setForeground(QColor("#9900CC"))
        self.json_bool_format.setFontWeight(QFont.Weight.Bold)
        
        # Common formats
        self.bg3_important_format = QTextCharFormat()
        self.bg3_important_format.setForeground(QColor("#9900CC"))
        self.bg3_important_format.setFontWeight(QFont.Weight.Bold)
        
        self.uuid_format = QTextCharFormat()
        self.uuid_format.setForeground(QColor("#FF6600"))
        self.uuid_format.setFontWeight(QFont.Weight.Bold)
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#666666"))
        self.comment_format.setFontItalic(True)
    
    def precompile_patterns(self):
        """Precompile all regex patterns - CRITICAL OPTIMIZATION"""
        # XML patterns
        self.xml_comment_pattern = re.compile(r'<!--.*?-->')
        self.xml_tag_pattern = re.compile(r'<[^>]+>')
        self.xml_attr_pattern = re.compile(r'(\w+)="([^"]*)"')
        
        # JSON patterns
        self.json_key_pattern = re.compile(r'"([^"]+)"\s*:')
        self.json_string_pattern = re.compile(r':\s*"([^"]*)"')
        self.json_number_pattern = re.compile(r':\s*(-?\d+\.?\d*)')
        self.json_bool_pattern = re.compile(r':\s*(true|false|null)')
        
        # UUID pattern (shared)
        self.uuid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        
        # BG3 important attributes set for O(1) lookup
        self.bg3_important_attrs = {"UUID", "Author", "Name", "Description", "Version64", "MD5", "Folder"}
    
    def set_format(self, file_format):
        """Set the current file format"""
        self.current_format = file_format
        self.rehighlight()
    
    def highlightBlock(self, text):
        """Highlight a block of text"""
        if self.current_format == 'lsx':
            self.highlight_xml(text)
        elif self.current_format == 'lsj':
            self.highlight_json(text)
    
    def highlight_xml(self, text):
        """Highlight XML/LSX syntax - OPTIMIZED"""
        # Comments
        for match in self.xml_comment_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.comment_format)
        
        # XML tags
        for match in self.xml_tag_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.xml_tag_format)
        
        # Attributes and values
        for match in self.xml_attr_pattern.finditer(text):
            attr_name, attr_value = match.groups()
            
            # Attribute name
            attr_start = match.start(1)
            attr_length = len(attr_name)
            
            # Check if it's BG3-important (O(1) lookup)
            if attr_name in self.bg3_important_attrs:
                self.setFormat(attr_start, attr_length, self.bg3_important_format)
            else:
                self.setFormat(attr_start, attr_length, self.xml_attribute_format)
            
            # Attribute value
            value_start = match.start(2)
            value_length = len(attr_value)
            
            # Check if it's a UUID
            if self.uuid_pattern.match(attr_value):
                self.setFormat(value_start, value_length, self.uuid_format)
            else:
                self.setFormat(value_start, value_length, self.xml_value_format)
    
    def highlight_json(self, text):
        """Highlight JSON/LSJ syntax - OPTIMIZED"""
        # JSON string keys
        for match in self.json_key_pattern.finditer(text):
            key_start = match.start(1)
            key_length = len(match.group(1))
            self.setFormat(key_start, key_length, self.json_key_format)
        
        # JSON string values
        for match in self.json_string_pattern.finditer(text):
            value = match.group(1)
            value_start = match.start(1)
            value_length = len(value)
            
            # Check if it's a UUID
            if self.uuid_pattern.match(value):
                self.setFormat(value_start, value_length, self.uuid_format)
            else:
                self.setFormat(value_start, value_length, self.json_string_format)
        
        # JSON numbers
        for match in self.json_number_pattern.finditer(text):
            num_start = match.start(1)
            num_length = len(match.group(1))
            self.setFormat(num_start, num_length, self.json_number_format)
        
        # JSON booleans and null
        for match in self.json_bool_pattern.finditer(text):
            bool_start = match.start(1)
            bool_length = len(match.group(1))
            self.setFormat(bool_start, bool_length, self.json_bool_format)


