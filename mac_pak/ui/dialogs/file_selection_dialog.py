import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt

class FileSelectionDialog(QDialog):
    """Dialog for selecting specific files from a PAK for extraction"""
    
    def __init__(self, parent, pak_file, wine_wrapper):
        super().__init__(parent)
        self.pak_file = pak_file
        self.wine_wrapper = wine_wrapper
        self.files_list = []
        self.selected_files = []
        
        self.setWindowTitle(f"Select Files to Extract - {Path(pak_file).name}")
        self.setModal(True)
        self.resize(600, 500)
        
        self.setup_ui()
        self.load_pak_contents()
    
    def setup_ui(self):
        """Setup dialog UI with better organization"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Header with PAK info
        header_group = QGroupBox()
        header_layout = QVBoxLayout(header_group)
        
        pak_name = Path(self.pak_file).name
        info_label = QLabel(f"📦 Select files to extract from: {pak_name}")
        info_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(info_label)
        
        # Add PAK stats
        self.stats_label = QLabel("Loading PAK information...")
        header_layout.addWidget(self.stats_label)
        
        layout.addWidget(header_group)
        
        # Search and filter section
        filter_group = QGroupBox("Filter Files")
        filter_layout = QVBoxLayout(filter_group)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Search:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter filename, extension, or path...")
        self.search_edit.textChanged.connect(self.filter_files)
        search_layout.addWidget(self.search_edit)
        
        filter_layout.addLayout(search_layout)
        
        # Quick selection buttons
        selection_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All Visible")
        select_all_btn.clicked.connect(self.select_all_files)
        selection_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self.select_no_files)
        selection_layout.addWidget(select_none_btn)
        
        select_by_type_btn = QPushButton("Select by Type...")
        select_by_type_btn.clicked.connect(self.select_by_type)
        selection_layout.addWidget(select_by_type_btn)
        
        # Add preset selections
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Quick select:"))
        
        select_lsx_btn = QPushButton("LSX Files")
        select_lsx_btn.clicked.connect(lambda: self.select_by_extension(['.lsx']))
        preset_layout.addWidget(select_lsx_btn)
        
        select_textures_btn = QPushButton("Textures")
        select_textures_btn.clicked.connect(lambda: self.select_by_extension(['.dds', '.png']))
        preset_layout.addWidget(select_textures_btn)
        
        filter_layout.addLayout(selection_layout)
        filter_layout.addLayout(preset_layout)
        
        layout.addWidget(filter_group)
    
    def load_pak_contents(self):
        """Load PAK contents into tree"""
        try:
            files = self.wine_wrapper.list_pak_contents(self.pak_file)
            self.files_list = files
            
            self.populate_file_tree(files)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read PAK contents: {e}")
    
    def populate_file_tree(self, files):
        """Populate file tree with files"""
        self.file_tree.clear()
        
        for file_info in files:
            # Handle different formats of file_info
            if isinstance(file_info, dict):
                file_path = file_info.get('name', str(file_info))
                file_size = file_info.get('size', 0)
            else:
                # If it's a string, split by whitespace to separate path from metadata
                file_str = str(file_info).strip()
                parts = file_str.split()
                
                # The file path is everything except the last few numeric parts
                # Look for where the numeric metadata starts
                path_parts = []
                for part in parts:
                    # If this part looks like a number, stop adding to path
                    if part.isdigit():
                        break
                    path_parts.append(part)
                
                file_path = ' '.join(path_parts) if path_parts else file_str
                file_size = 0
            
            # Skip directories for individual file extraction
            file_name = Path(file_path).name
            if '.' not in file_name or not file_path.strip():
                continue
            
            item = QTreeWidgetItem(self.file_tree)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)  # Start unchecked so user can select
            
            file_ext = Path(file_path).suffix.lower()
            
            # Set the correct columns
            item.setText(0, file_name)      # File Name column
            item.setText(1, file_ext)       # Type column  
            item.setText(2, file_path)      # Path column (clean path without metadata)
            
            # Store the clean path for extraction
            item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            
            print(f"Debug: Added file to tree: '{file_path}'")  # Debug output
        
        # Resize columns to content
        for i in range(3):
            self.file_tree.resizeColumnToContents(i)
    
    def filter_files(self):
        """Filter files based on search term"""
        search_term = self.search_edit.text().lower()
        
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            
            if not search_term:
                item.setHidden(False)
            else:
                # Check if search term matches filename, extension, or path
                file_name = item.text(0).lower()
                file_ext = item.text(1).lower()
                file_path = item.text(2).lower()
                
                matches = (search_term in file_name or 
                          search_term in file_ext or 
                          search_term in file_path)
                
                item.setHidden(not matches)
    
    def select_all_files(self):
        """Select all visible files"""
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            if not item.isHidden():
                item.setCheckState(0, Qt.CheckState.Checked)
    
    def select_no_files(self):
        """Deselect all files"""
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Unchecked)
    
    def select_by_type(self):
        """Select files by extension"""
        from PyQt6.QtWidgets import QInputDialog
        
        # Get all unique extensions
        extensions = set()
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            ext = item.text(1)
            if ext:
                extensions.add(ext)
        
        extensions = sorted(list(extensions))
        
        if not extensions:
            return
        
        extension, ok = QInputDialog.getItem(
            self, "Select by Type", 
            "Choose file type:", 
            extensions, 0, False
        )
        
        if ok:
            for i in range(self.file_tree.topLevelItemCount()):
                item = self.file_tree.topLevelItem(i)
                if item.text(1) == extension:
                    item.setCheckState(0, Qt.CheckState.Checked)
    
    def on_item_changed(self, item):
        """Handle item check state changes"""
        self.update_selection_info()
    
    def update_selection_info(self):
        """Update selection information"""
        selected_count = 0
        
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                selected_count += 1
        
        self.selection_info.setText(f"{selected_count} files selected")
        self.extract_btn.setEnabled(selected_count > 0 and bool(self.dest_edit.text()))
    
    def browse_destination(self):
        """Browse for extraction destination"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Extraction Destination"
        )
        
        if directory:
            self.dest_edit.setText(directory)
            self.update_selection_info()
    
    def start_extraction(self):
        """Start the extraction process"""
        # Get selected files
        selected_files = []
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                file_path = item.data(0, Qt.ItemDataRole.UserRole)
                selected_files.append(file_path)
        
        if not selected_files:
            QMessageBox.warning(self, "No Selection", "Please select files to extract.")
            return
        
        destination = self.dest_edit.text()
        if not destination:
            QMessageBox.warning(self, "No Destination", "Please select an extraction destination.")
            return
        
        self.selected_files = selected_files
        self.destination = destination
        self.accept()