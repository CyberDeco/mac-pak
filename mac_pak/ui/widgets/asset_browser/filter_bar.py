#!/usr/bin/env python3
"""
Filter bar widget for the asset browser - handles file type and search filtering
"""

import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal

from ....core.combo_box import CheckableComboBox


class FilterBar(QWidget):
    """Filter bar for file type and search filtering"""
    
    # Signals
    filters_changed = pyqtSignal(object)  # Emits filter function when filters change
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Filter state
        self.show_all_types = True
        self.enabled_extensions = set()
        self.search_term = ""
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup filter bar UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # File type filter combo
        self.filter_combo = CheckableComboBox(self)
        self.filter_combo.setMinimumWidth(200)
        
        # Common BG3 file types
        file_types = [
            ("All Files", []),
            ("PAK Files", [".pak"]),
            ("LSF Files", [".lsf"]),
            ("LSX Files", [".lsx"]),
            ("LSJ Files", [".lsj"]),
            ("DDS Images", [".dds"]),
            ("Models", [".gr2"]),
            ("Textures", [".dds", ".png", ".jpg"]),
            ("Audio", [".wem", ".wav"]),
            ("Scripts", [".lua", ".script"]),
            ("Localization", [".loca"]),
        ]
        
        for label, extensions in file_types:
            self.filter_combo.add_item(label, extensions, checked=True)
        
        layout.addWidget(self.filter_combo)
        
        # Search filter
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search files...")
        self.search_edit.setMinimumWidth(200)
        layout.addWidget(self.search_edit)
        
        layout.addStretch()
    
    def connect_signals(self):
        """Connect widget signals"""
        self.filter_combo.itemsChanged.connect(self.update_filters)
        self.search_edit.textChanged.connect(self.update_filters)
    
    def update_filters(self):
        """Update filter state and emit filter function"""
        # Update type filter state
        enabled_extensions = set()
        show_all = False
        
        checked_items = self.filter_combo.get_checked_items()
        
        # If nothing is checked, hide everything
        if not checked_items:
            self.show_all_types = False
            self.enabled_extensions = set()
        else:
            # Process all checked items
            for label, extensions in checked_items.items():
                if not extensions:  # "All Files" option
                    show_all = True
                else:
                    enabled_extensions.update(extensions)
            
            self.show_all_types = show_all
            self.enabled_extensions = enabled_extensions
        
        # Update search term
        self.search_term = self.search_edit.text().lower()
        
        # Emit the filter function
        self.filters_changed.emit(self.get_filter_func())
    
    def get_filter_func(self):
        """Get the current filter function"""
        search_term = self.search_term
        show_all_types = self.show_all_types
        enabled_extensions = self.enabled_extensions
        
        def filter_func(item):
            """Check if item matches both type and search filters"""
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            item_text = item.text(0).lower()
            
            if not item_path or item_path == "placeholder":
                return True
            
            # Check search match
            search_matches = not search_term or search_term in item_text
            
            # Directories always pass type filter
            if os.path.isdir(item_path):
                return search_matches
            
            # Check type match
            if show_all_types:
                type_matches = True
            else:
                file_ext = os.path.splitext(item_path)[1].lower()
                type_matches = file_ext in enabled_extensions
            
            return search_matches and type_matches
        
        return filter_func
    
    def reset_filters(self):
        """Reset all filters to default state"""
        # Check all items in combo
        for i in range(self.filter_combo.count()):
            self.filter_combo.set_item_checked(i, True)
        
        # Clear search
        self.search_edit.clear()