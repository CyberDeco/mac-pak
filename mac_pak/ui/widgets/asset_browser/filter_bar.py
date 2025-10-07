#!/usr/bin/env python3
"""
Enhanced filter bar with active filter indicators and quick filter buttons
"""

import os
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, 
                            QPushButton, QLabel, QFrame, QStyle)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from ....core.combo_box import CheckableComboBox


class FilterBadge(QLabel):
    """Badge showing active filter count"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #007AFF;
                color: white;
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
                min-width: 20px;
            }
        """)
        self.hide()
    
    def set_count(self, count):
        """Update badge count"""
        if count > 0:
            self.setText(str(count))
            self.show()
        else:
            self.hide()


class QuickFilterButton(QPushButton):
    """Quick filter button with toggle state"""
    
    def __init__(self, text, extensions, parent=None):
        super().__init__(text, parent)
        self.extensions = extensions
        self.setCheckable(True)
        self.setMinimumWidth(80)

class FilterBar(QWidget):
    """Enhanced filter bar with active indicators and quick filters"""
    
    # Signals
    filters_changed = pyqtSignal(object)  # Emits filter function when filters change
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Filter state
        self.show_all_types = True
        self.enabled_extensions = set()
        self.search_term = ""
        self.quick_filter_buttons = {}
        
        # Search debounce timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filters)
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup enhanced filter bar UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        
        # Top row: Search and type filter
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        # Search box with icon
        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 16px;")
        top_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search files...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 6px 12px;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #007AFF;
            }
        """)
        top_layout.addWidget(self.search_box, 1)
        
        # Active filter badge
        self.filter_badge = FilterBadge(self)
        top_layout.addWidget(self.filter_badge)
        
        # File type filter combo
        type_label = QLabel("Type:")
        type_label.setStyleSheet("font-weight: 600; color: #666;")
        top_layout.addWidget(type_label)
        
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
        
        for label, exts in file_types:
            self.filter_combo.add_item(label, exts)
        
        top_layout.addWidget(self.filter_combo)
        
        # Clear filters button
        self.clear_btn = QPushButton(" Clear")
        self.clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_LineEditClearButton))
        self.clear_btn.setProperty("destructive", "true")
        
        self.clear_btn.setToolTip("Clear all filters")
        top_layout.addWidget(self.clear_btn)
        
        main_layout.addLayout(top_layout)
        
        # Bottom row: Quick filter buttons
        quick_filter_frame = QFrame()
        quick_filter_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f8f8;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        quick_layout = QHBoxLayout(quick_filter_frame)
        quick_layout.setContentsMargins(8, 4, 8, 4)
        quick_layout.setSpacing(8)
        
        quick_label = QLabel("Quick:")
        quick_label.setStyleSheet("font-weight: 600; color: #666; font-size: 11px;")
        quick_layout.addWidget(quick_label)
        
        # Define quick filter buttons
        quick_filters = [
            ("📦 PAK", [".pak"]),
            ("📄 Binary Files", [".lsf", ".lsx", ".lsj", ".lsb", ".lsbc", ".lsbs"]),
            ("🖼️ Images", [".dds", ".png", ".jpg", ".jpeg"]),
            ("🖌️ Models", [".gr2"]),
            ("📜 Scripts", [".lua", ".script"]),
            ("🔊 Audio", [".wem", ".wav"]),
            ("✨ Effects", [".lsfx"]),
        ]
        
        for label, exts in quick_filters:
            btn = QuickFilterButton(label, exts, self)
            btn.toggled.connect(lambda checked, e=exts: self.toggle_quick_filter(e, checked))
            quick_layout.addWidget(btn)
            self.quick_filter_buttons[tuple(exts)] = btn
        
        quick_layout.addStretch()
        
        main_layout.addWidget(quick_filter_frame)
    
    def connect_signals(self):
        """Connect widget signals"""
        self.search_box.textChanged.connect(self.on_search_changed)
        self.filter_combo.itemsChanged.connect(self.on_type_filter_changed)
        self.clear_btn.clicked.connect(self.clear_all_filters)
    
    def on_search_changed(self, text):
        """Handle search text change with debouncing"""
        self.search_term = text.strip()
        # Debounce search to avoid filtering on every keystroke
        self.search_timer.start(300)  # 300ms delay
    
    def on_type_filter_changed(self):
        """Handle file type filter change"""
        self.enabled_extensions.clear()
        self.show_all_types = False
        
        checked_items = self.filter_combo.get_checked_items()
        
        for label, exts in checked_items.items():
            if label == "All Files" or not exts:
                self.show_all_types = True
                self.enabled_extensions.clear()
                break
            else:
                self.enabled_extensions.update(exts)
        
        if not checked_items:
            self.show_all_types = True
        
        self.apply_filters()
    
    def toggle_quick_filter(self, extensions, checked):
        """Handle quick filter button toggle"""
        if checked:
            # Add extensions to filter
            self.enabled_extensions.update(extensions)
            self.show_all_types = False
        else:
            # Remove extensions from filter
            self.enabled_extensions.difference_update(extensions)
            if not self.enabled_extensions:
                self.show_all_types = True
        
        # Update the main combo box to reflect quick filter state
        self.sync_combo_with_extensions()
        self.apply_filters()
    
    def sync_combo_with_extensions(self):
        """Sync combo box state with current extension set"""
        # This would need to iterate through items and check/uncheck them
        # For now, we'll skip this since the CheckableComboBox handles its own state
        pass
    
    def apply_filters(self):
        """Apply current filters and emit filter function"""
        self.update_filter_badge()
        
        # Create filter function
        def filter_func(file_path, is_dir):
            # Directories always pass
            if is_dir:
                return True
            
            # Type filter
            if not self.show_all_types:
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext not in self.enabled_extensions:
                    return False
            
            # Search filter
            if self.search_term:
                file_name = os.path.basename(file_path).lower()
                if self.search_term.lower() not in file_name:
                    return False
            
            return True
        
        self.filters_changed.emit(filter_func)
    
    def update_filter_badge(self):
        """Update the active filter count badge"""
        count = 0
        
        if self.search_term:
            count += 1
        
        if not self.show_all_types and self.enabled_extensions:
            count += 1
        
        self.filter_badge.set_count(count)
    
    def clear_all_filters(self):
        """Clear all active filters"""
        # Clear search
        self.search_box.clear()
        self.search_term = ""
        
        # Clear type filters - uncheck all items and check "All Files"
        self.show_all_types = True
        self.enabled_extensions.clear()
        
        # Manually set all items to checked (since CheckableComboBox checks all when "All Files" is checked)
        for i in range(self.filter_combo.model().rowCount()):
            item = self.filter_combo.model().item(i)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        
        # Clear quick filters
        for btn in self.quick_filter_buttons.values():
            btn.setChecked(False)
        
        self.apply_filters()
    
    def get_active_filter_summary(self):
        """Get summary of active filters for status bar"""
        parts = []
        
        if self.search_term:
            parts.append(f"Search: '{self.search_term}'")
        
        if not self.show_all_types and self.enabled_extensions:
            ext_list = ", ".join(sorted(self.enabled_extensions))
            parts.append(f"Types: {ext_list}")
        
        return " | ".join(parts) if parts else ""