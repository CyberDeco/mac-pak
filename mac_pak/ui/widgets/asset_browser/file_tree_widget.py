#!/usr/bin/env python3
"""
File tree widget for the asset browser - handles file/folder display and lazy loading
"""

import os
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QFrame
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ....data.file_preview import get_file_icon


class FileTreeWidget(QTreeWidget):
    """Custom tree widget for displaying file system with lazy loading"""
    
    # Signals
    file_selected = pyqtSignal(str)  # Emits file path when file is selected
    directory_changed = pyqtSignal(str)  # Emits new directory when navigating
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_directory = None
        self._filter_func = None
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup tree widget UI"""
        self.setHeaderLabels(["Name", "Type"])
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        
        # Set column widths
        self.setColumnWidth(0, 650)
        self.setColumnWidth(1, 50)
        
        # Remove grid lines
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.header().setHighlightSections(False)
        
        # Apply Mac-style styling
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: white;
                alternate-background-color: #f8f8f8;
                selection-background-color: #007AFF;
                outline: none;
            }
            QTreeWidget::item {
                height: 24px;
                padding: 2px;
                border: none;
            }
            QTreeWidget::item:selected {
                background-color: #007AFF;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #f2f2f7;
                color: black;
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
            QHeaderView::section {
                background-color: #f8f8f8;
                padding: 4px;
                border: none;
                border-right: 1px solid #d0d0d0;
                border-bottom: 1px solid #d0d0d0;
            }
            QHeaderView::section:last {
                border-right: none;
            }
        """)
    
    def connect_signals(self):
        """Connect internal signals"""
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
    
    def load_directory(self, directory):
        """Load a directory into the tree"""
        if not directory or not os.path.exists(directory):
            return
        
        self.current_directory = directory
        self.clear()
        self._populate_tree(directory, None)
        
        # Apply filter if one is set
        if self._filter_func:
            self.apply_filter(self._filter_func)
    
    def refresh(self):
        """Refresh the current directory"""
        if self.current_directory:
            self.load_directory(self.current_directory)
    
    def set_filter(self, filter_func):
        """Set a filter function and apply it"""
        self._filter_func = filter_func
        self.apply_filter(filter_func)
    
    def apply_filter(self, filter_func):
        """Apply filter function to all items"""
        if not filter_func:
            return
        
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            self._apply_filter_recursive(item, filter_func)
    
    def _apply_filter_recursive(self, item, filter_func):
        """Recursively apply filter to tree items"""
        visible_children = 0
        for i in range(item.childCount()):
            child = item.child(i)
            self._apply_filter_recursive(child, filter_func)
            if not child.isHidden():
                visible_children += 1
        
        item_visible = filter_func(item) or visible_children > 0
        item.setHidden(not item_visible)
    
    def _populate_tree(self, directory, parent_item):
        """Populate tree with directory contents"""
        try:
            # Temporarily disable sorting while populating
            sorting_enabled = self.isSortingEnabled()
            self.setSortingEnabled(False)
            
            for item_name in sorted(os.listdir(directory)):
                if item_name.startswith('.'):
                    continue
                
                item_path = os.path.join(directory, item_name)
                
                if parent_item:
                    tree_item = QTreeWidgetItem(parent_item)
                else:
                    tree_item = QTreeWidgetItem(self)
                
                tree_item.setData(0, Qt.ItemDataRole.UserRole, item_path)
                
                if os.path.isdir(item_path):
                    try:
                        item_count = len([f for f in os.listdir(item_path) if not f.startswith('.')])
                        tree_item.setText(0, f"📁 {item_name} ({item_count} items)")
                    except:
                        tree_item.setText(0, f"📁 {item_name}")
                    
                    tree_item.setText(1, "Folder")
                    tree_item.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                    )
                    
                    # Add placeholder for lazy loading
                    placeholder = QTreeWidgetItem(tree_item)
                    placeholder.setText(0, "Loading...")
                    placeholder.setData(0, Qt.ItemDataRole.UserRole, "placeholder")
                else:
                    try:
                        file_size = os.path.getsize(item_path)
                        size_str = self._format_file_size(file_size)
                        icon = get_file_icon(item_name)
                        tree_item.setText(0, f"{icon} {item_name} ({size_str})")
                    except:
                        icon = get_file_icon(item_name)
                        tree_item.setText(0, f"{icon} {item_name}")
                    
                    file_ext = os.path.splitext(item_path)[1].lower()
                    if file_ext:
                        tree_item.setText(1, file_ext[1:].upper())
                    else:
                        tree_item.setText(1, "File")
                    
                    tree_item.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
                    )
            
            self.setSortingEnabled(sorting_enabled)
        
        except PermissionError:
            if parent_item:
                error_item = QTreeWidgetItem(parent_item)
            else:
                error_item = QTreeWidgetItem(self)
            error_item.setText(0, "⚠️ Permission Denied")
            error_item.setText(1, "Error")
    
    def _format_file_size(self, size_bytes):
        """Format file size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def _on_item_expanded(self, item):
        """Handle lazy loading when item is expanded"""
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_path or not os.path.isdir(item_path):
            return
        
        # Check if this is the first expansion (has placeholder)
        if item.childCount() == 1:
            child = item.child(0)
            if child.data(0, Qt.ItemDataRole.UserRole) == "placeholder":
                item.removeChild(child)
                self._populate_tree(item_path, item)
                
                # Apply filter to newly loaded items
                if self._filter_func:
                    self._apply_filter_recursive(item, self._filter_func)
    
    def _on_selection_changed(self):
        """Handle selection changes"""
        selected_items = self.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if file_path and file_path != "placeholder" and os.path.isfile(file_path):
            self.file_selected.emit(file_path)
    
    def _on_item_double_clicked(self, item):
        """Handle double-click to navigate into directories"""
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if item_path and item_path != "placeholder" and os.path.isdir(item_path):
            self.directory_changed.emit(item_path)