#!/usr/bin/env python3
"""
Assets Browser tab with improved UI features
"""

import os
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, 
                            QFrame, QMessageBox, QStatusBar)
from PyQt6.QtCore import Qt

from ..widgets.asset_browser.preview_widget import PreviewWidget
from ..widgets.asset_browser.navigation_bar import NavigationBar
from ..widgets.asset_browser.filter_bar import FilterBar
from ..widgets.asset_browser.file_tree_widget import FileTreeWidget
from ...data.parsers.larian_parser import UniversalBG3Parser
from ...data.file_preview import FilePreviewManager


class AssetBrowserTab(QWidget):
    """ Asset Browser tab with improved UI features"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.parser = UniversalBG3Parser()
        
        if wine_wrapper:
            self.parser.set_wine_wrapper(wine_wrapper)

        # Initialize preview manager (for cache clearing)
        self.preview_manager = FilePreviewManager(self.wine_wrapper, self.parser)
        
        # Create  widget components
        self.navigation_bar = NavigationBar(self, settings_manager)
        self.filter_bar = FilterBar(self)
        self.file_tree = FileTreeWidget(self)
        self.preview_widget = PreviewWidget(parent, self.wine_wrapper, self.parser)
        
        # Status bar for file count and size info
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                border-top: 1px solid #d0d0d0;
                background-color: #f8f8f8;
                padding: 4px 8px;
            }
        """)
        
        self.setup_ui()
        self.connect_signals()
        
        # Load initial directory if available
        if settings_manager:
            working_dir = settings_manager.get("working_directory")
            if working_dir and os.path.exists(working_dir):
                self.load_directory(working_dir)
            
            # Restore splitter position
            splitter_sizes = settings_manager.get("asset_browser_splitter", [800, 200])
            self.main_splitter.setSizes(splitter_sizes)
    
    def setup_ui(self):
        """Setup the  asset browser interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Asset Browser")
        title_label.setProperty("header", "h1")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Navigation bar with breadcrumbs
        layout.addWidget(self.navigation_bar)
        
        # Filter bar with active filter indicators
        layout.addWidget(self.filter_bar)
        
        # Main content - horizontal splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: File tree with size and date columns
        tree_frame = QFrame()
        tree_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(10, 10, 10, 10)
        tree_layout.addWidget(self.file_tree)
        self.main_splitter.addWidget(tree_frame)
        
        # Right:  preview pane with zoom and copy controls
        self.main_splitter.addWidget(self.preview_widget)
        
        self.main_splitter.setSizes([800, 200])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(self.main_splitter, 1)
        
        # Status bar at bottom
        layout.addWidget(self.status_bar)
    
    def connect_signals(self):
        """Connect signals between widget components"""
        # Navigation bar signals
        self.navigation_bar.directory_changed.connect(self.load_directory)
        self.navigation_bar.refresh_requested.connect(self.refresh)
        self.navigation_bar.clear_cache_requested.connect(self.clear_cache)
        
        # Filter bar signals
        self.filter_bar.filters_changed.connect(self.file_tree.set_filter)
        self.filter_bar.filters_changed.connect(self.update_status_bar)
        
        # File tree signals
        self.file_tree.file_selected.connect(self.preview_widget.preview_file)
        self.file_tree.directory_changed.connect(self.load_directory)
        self.file_tree.stats_changed.connect(self.update_status_bar)
        
        # Splitter position saving
        self.main_splitter.splitterMoved.connect(self.save_splitter_position)
    
    def load_directory(self, directory):
        """Load a new directory"""
        if not directory or not os.path.exists(directory):
            return
        
        # Update navigation bar
        self.navigation_bar.set_directory(directory)
        
        # Load into file tree
        self.file_tree.load_directory(directory)
        
        # Clear preview
        self.preview_widget.clear_preview()
        
        # Update status
        self.update_status_bar()
    
    def refresh(self):
        """Refresh the current view"""
        self.file_tree.refresh()
        self.preview_widget.clear_preview()
        self.update_status_bar()
    
    def clear_cache(self):
        """Clear the preview cache"""
        self.preview_manager.clear_cache()
        QMessageBox.information(self, "Cache Cleared", "Preview cache has been cleared.")
    
    def update_status_bar(self):
        """Update status bar with file count and size information"""
        stats = self.file_tree.get_stats()
        
        if stats:
            file_count = stats.get('file_count', 0)
            folder_count = stats.get('folder_count', 0)
            total_size = stats.get('total_size', 0)
            filtered_count = stats.get('filtered_count', 0)
            
            # Format size
            size_str = self._format_size(total_size)
            
            # Build status message
            status_parts = []
            
            if filtered_count > 0:
                status_parts.append(f"{filtered_count} items shown")
                if file_count + folder_count > filtered_count:
                    status_parts.append(f"({file_count + folder_count} total)")
            else:
                status_parts.append(f"{file_count} files, {folder_count} folders")
            
            if total_size > 0:
                status_parts.append(f"Total: {size_str}")
            
            # Show active filters
            active_filters = self.filter_bar.get_active_filter_summary()
            if active_filters:
                status_parts.append(f"• Filters: {active_filters}")
            
            self.status_bar.showMessage(" | ".join(status_parts))
        else:
            self.status_bar.showMessage("No directory loaded")
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def save_splitter_position(self):
        """Save splitter position to settings"""
        if self.settings_manager:
            sizes = self.main_splitter.sizes()
            self.settings_manager.set("asset_browser_splitter", sizes)
    
    def closeEvent(self, event):
        """Save state on close"""
        self.save_splitter_position()
        super().closeEvent(event)