#!/usr/bin/env python3
"""
Assets Browser tab - Refactored with separated widget components
"""

import os
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QSplitter, QFrame, QMessageBox)
from PyQt6.QtCore import Qt

from ..widgets.asset_browser.preview_widget import PreviewWidget
from ..widgets.asset_browser.navigation_bar import NavigationBar
from ..widgets.asset_browser.filter_bar import FilterBar
from ..widgets.asset_browser.file_tree_widget import FileTreeWidget
from ...data.parsers.larian_parser import UniversalBG3Parser
from ...data.file_preview import FilePreviewManager

class AssetBrowserTab(QWidget):
    """Asset Browser tab for the main application - orchestrates widget components"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.parser = UniversalBG3Parser()
        
        if wine_wrapper:
            self.parser.set_wine_wrapper(wine_wrapper)

        # Initialize preview manager (for cache clearing)
        self.preview_manager = FilePreviewManager(self.wine_wrapper, self.parser)
        
        # Create widget components
        self.navigation_bar = NavigationBar(self, settings_manager)
        self.filter_bar = FilterBar(self)
        self.file_tree = FileTreeWidget(self)
        self.preview_widget = PreviewWidget(parent, self.wine_wrapper, self.parser)
        
        self.setup_ui()
        self.connect_signals()
        
        # Load initial directory if available
        if settings_manager:
            working_dir = settings_manager.get("working_directory")
            if working_dir and os.path.exists(working_dir):
                self.load_directory(working_dir)
    
    def setup_ui(self):
        """Setup the asset browser interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Asset Browser")
        title_label.setProperty("header", "h1")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Navigation bar
        layout.addWidget(self.navigation_bar)
        
        # Filter bar
        layout.addWidget(self.filter_bar)
        
        # Main content - horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: File tree
        tree_frame = QFrame()
        tree_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(10, 10, 10, 10)
        tree_layout.addWidget(self.file_tree)
        splitter.addWidget(tree_frame)
        
        # Right: Preview pane
        splitter.addWidget(self.preview_widget)
        
        splitter.setSizes([750, 250])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter, 1)
    
    def connect_signals(self):
        """Connect signals between widget components"""
        # Navigation bar signals
        self.navigation_bar.directory_changed.connect(self.load_directory)
        self.navigation_bar.refresh_requested.connect(self.refresh)
        self.navigation_bar.clear_cache_requested.connect(self.clear_cache)
        
        # Filter bar signals
        self.filter_bar.filters_changed.connect(self.file_tree.set_filter)
        
        # File tree signals
        self.file_tree.file_selected.connect(self.preview_widget.preview_file)
        self.file_tree.directory_changed.connect(self.load_directory)
    
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
    
    def refresh(self):
        """Refresh the current view"""
        self.file_tree.refresh()
        self.preview_widget.clear_preview()
    
    def clear_cache(self):
        """Clear the preview cache"""
        self.preview_manager.clear_cache()
        QMessageBox.information(self, "Cache Cleared", "Preview cache has been cleared.")