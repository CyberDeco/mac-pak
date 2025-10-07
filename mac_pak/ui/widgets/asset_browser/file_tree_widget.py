#!/usr/bin/env python3
"""
Enhanced file tree widget with size, date columns and context menu
"""

import os
from datetime import datetime
from PyQt6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QFrame, QMenu, 
                            QApplication, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QDesktopServices, QColor

from ....data.file_preview import get_file_icon


class FileTreeWidget(QTreeWidget):
    """Enhanced tree widget with size, date, and context menu"""
    
    # Signals
    file_selected = pyqtSignal(str)
    directory_changed = pyqtSignal(str)
    stats_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_directory = None
        self._filter_func = None
        self._file_count = 0
        self._folder_count = 0
        self._total_size = 0
        self._filtered_count = 0
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup enhanced tree widget UI"""
        self.setHeaderLabels(["Name", "Type", "Size", "Modified"])
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.setAlternatingRowColors(True)  # Zebra striping
        
        # Set column widths
        self.setColumnWidth(0, 450)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 100)
        self.setColumnWidth(3, 150)
        
        # Remove grid lines
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.header().setHighlightSections(False)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Apply Mac-style styling with zebra stripes
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: white;
                outline: none;
            }
            QTreeWidget::item {
                padding: 4px;
                border: none;
            }
            QTreeWidget::item:hover {
                background-color: #e8f4fd;
            }
            QTreeWidget::item:selected {
                background-color: #007AFF;
                color: white;
            }
            QTreeWidget::item:alternate {
                background-color: #f9f9f9;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 6px;
                border: none;
                border-right: 1px solid #e0e0e0;
                border-bottom: 1px solid #d0d0d0;
                font-weight: 600;
            }
            QHeaderView::section:first {
                border-top-left-radius: 8px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 8px;
                border-right: none;
            }
        """)
    
    def connect_signals(self):
        """Connect widget signals"""
        self.itemClicked.connect(self.on_item_clicked)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def load_directory(self, directory):
        """Load directory contents"""
        if not directory or not os.path.exists(directory):
            return
        
        self.current_directory = directory
        self.clear()
        
        # Reset stats
        self._file_count = 0
        self._folder_count = 0
        self._total_size = 0
        self._filtered_count = 0
        
        try:
            items = []
            for entry in os.scandir(directory):
                try:
                    # Get file info
                    stat_info = entry.stat()
                    size = stat_info.st_size
                    mod_time = datetime.fromtimestamp(stat_info.st_mtime)
                    
                    # Create tree item
                    item = QTreeWidgetItem()
                    item.setText(0, entry.name)
                    item.setData(0, Qt.ItemDataRole.UserRole, entry.path)
                    
                    if entry.is_dir():
                        item.setText(1, "Folder")
                        item.setText(2, "--")
                        # Use text icon for folder instead of QIcon
                        item.setText(0, f"📁 {entry.name}")
                        # Set folder text color
                        item.setForeground(0, QColor("#007AFF"))
                        font = item.font(0)
                        font.setBold(True)
                        item.setFont(0, font)
                        self._folder_count += 1
                    else:
                        file_ext = os.path.splitext(entry.name)[1].upper()
                        item.setText(1, file_ext[1:] if file_ext else "File")
                        item.setText(2, self._format_size(size))
                        # Use emoji icon in the text instead of QIcon
                        icon_emoji = get_file_icon(entry.path)
                        item.setText(0, f"{icon_emoji} {entry.name}")
                        self._file_count += 1
                        self._total_size += size
                    
                    item.setText(3, mod_time.strftime("%Y-%m-%d %H:%M"))
                    
                    items.append(item)
                except (PermissionError, OSError):
                    continue
            
            # Add all items
            self.addTopLevelItems(items)
            
            # Apply filter if set
            if self._filter_func:
                self.apply_current_filter()
            else:
                self._filtered_count = self._file_count + self._folder_count
            
            # Emit stats changed
            self.stats_changed.emit()
            
        except PermissionError:
            QMessageBox.warning(self, "Permission Denied", 
                              f"Cannot access directory: {directory}")
    
    def refresh(self):
        """Refresh current directory"""
        if self.current_directory:
            self.load_directory(self.current_directory)
    
    def set_filter(self, filter_func):
        """Set filter function"""
        self._filter_func = filter_func
        self.apply_current_filter()
    
    def apply_current_filter(self):
        """Apply current filter to items"""
        if not self._filter_func:
            # Show all items
            for i in range(self.topLevelItemCount()):
                self.topLevelItem(i).setHidden(False)
            self._filtered_count = self._file_count + self._folder_count
        else:
            # Apply filter
            visible_count = 0
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                file_path = item.data(0, Qt.ItemDataRole.UserRole)
                is_dir = item.text(1) == "Folder"
                
                should_show = self._filter_func(file_path, is_dir)
                item.setHidden(not should_show)
                
                if should_show:
                    visible_count += 1
            
            self._filtered_count = visible_count
        
        self.stats_changed.emit()
    
    def on_item_clicked(self, item, column):
        """Handle item click"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path and os.path.isfile(file_path):
            self.file_selected.emit(file_path)
    
    def on_item_double_clicked(self, item, column):
        """Handle item double click"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path and os.path.isdir(file_path):
            self.directory_changed.emit(file_path)
    
    def show_context_menu(self, position):
        """Show context menu for selected item"""
        item = self.itemAt(position)
        if not item:
            return
        
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        is_dir = item.text(1) == "Folder"
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #007AFF;
                color: white;
            }
        """)
        
        # Copy path action
        copy_action = menu.addAction("📋 Copy Path")
        copy_action.triggered.connect(lambda: self.copy_path(file_path))
        
        # Show in Finder
        finder_action = menu.addAction("📁 Show in Finder")
        finder_action.triggered.connect(lambda: self.show_in_finder(file_path))
        
        if not is_dir:
            menu.addSeparator()
            
            # Quick convert actions for LSF/LSX files
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in ['.lsf', '.lsx', '.lsj']:
                convert_menu = menu.addMenu("🔄 Quick Convert")
                
                if file_ext != '.lsx':
                    convert_lsx = convert_menu.addAction("To LSX")
                    convert_lsx.triggered.connect(
                        lambda: self.quick_convert(file_path, 'lsx'))
                
                if file_ext != '.lsj':
                    convert_lsj = convert_menu.addAction("To LSJ")
                    convert_lsj.triggered.connect(
                        lambda: self.quick_convert(file_path, 'lsj'))
                
                if file_ext != '.lsf':
                    convert_lsf = convert_menu.addAction("To LSF")
                    convert_lsf.triggered.connect(
                        lambda: self.quick_convert(file_path, 'lsf'))
            
            # Open in external editor
            menu.addSeparator()
            external_action = menu.addAction("📝 Open in External Editor")
            external_action.triggered.connect(lambda: self.open_external(file_path))
        
        menu.exec(self.viewport().mapToGlobal(position))
    
    def copy_path(self, file_path):
        """Copy file path to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(file_path)
        # Could show a temporary tooltip here
    
    def show_in_finder(self, file_path):
        """Show file in Finder"""
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            else:
                # Show parent directory and select file
                parent_dir = os.path.dirname(file_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(parent_dir))
    
    def open_external(self, file_path):
        """Open file in external editor"""
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
    
    def quick_convert(self, file_path, target_format):
        """Quick convert file (placeholder - would integrate with conversion tools)"""
        QMessageBox.information(
            self, 
            "Quick Convert", 
            f"Would convert:\n{os.path.basename(file_path)}\n\nTo format: {target_format.upper()}\n\n"
            f"(This feature requires integration with the Universal Editor tab)"
        )
    
    def get_stats(self):
        """Get current file tree statistics"""
        return {
            'file_count': self._file_count,
            'folder_count': self._folder_count,
            'total_size': self._total_size,
            'filtered_count': self._filtered_count
        }
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"