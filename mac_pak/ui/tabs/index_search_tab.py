import os
import sqlite3
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QGroupBox,
    QLineEdit, QPushButton, QComboBox, QTreeWidget, QTreeWidgetItem,
    QFormLayout, QProgressBar, QFileDialog, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QAction

from ...data.indexing.file_index_searcher import FileIndexer, IndexSearcher
from ..threads.indexing_thread import IndexingThread

class IndexSearchTab(QWidget):
    """Widget for searching indexed files"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.indexer = FileIndexer(wine_wrapper)
        self.searcher = IndexSearcher()
        
        self.setup_ui()
        self.load_initial_data()
    
    def setup_ui(self):
        """Setup the search interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("File Index & Search")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Search tab
        search_tab = self.create_search_tab()
        self.tab_widget.addTab(search_tab, "Search Files")
        
        # Index management tab
        index_tab = self.create_index_tab()
        self.tab_widget.addTab(index_tab, "Manage Index")
        
        layout.addWidget(self.tab_widget)

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
    
    def create_search_tab(self):
        """Create the search tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Search controls
        search_group = self.create_styled_group("Search")
        search_layout = QVBoxLayout(search_group)
        
        # Search input
        search_input_layout = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter filename or pattern (* and ? wildcards supported)")
        self.search_edit.returnPressed.connect(self.perform_search)
        search_input_layout.addWidget(self.search_edit)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.perform_search)
        search_input_layout.addWidget(search_btn)
        
        search_layout.addLayout(search_input_layout)
        
        # Filters
        filters_layout = QHBoxLayout()
        
        # Extension filter
        filters_layout.addWidget(QLabel("Extension:"))
        self.ext_combo = QComboBox()
        self.ext_combo.setEditable(True)
        self.ext_combo.addItems(['', '.lsx', '.lsf', '.dds', '.gr2', '.txt', '.json'])
        filters_layout.addWidget(self.ext_combo)
        
        # Source type filter
        filters_layout.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(['All', 'PAK Files', 'Extracted'])
        filters_layout.addWidget(self.source_combo)
        
        filters_layout.addStretch()
        search_layout.addLayout(filters_layout)
        
        layout.addWidget(search_group)
        
        # Results area
        results_group = self.create_styled_group("Search Results")
        results_layout = QVBoxLayout(results_group)
        
        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(['File Name', 'Extension', 'Size', 'Source', 'Path'])
        self.results_tree.setRootIsDecorated(False)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.itemDoubleClicked.connect(self.open_file_from_results)
        
        # Context menu for results
        self.results_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_tree.customContextMenuRequested.connect(self.show_results_context_menu)
        
        results_layout.addWidget(self.results_tree)
        
        # Results info
        self.results_info = QLabel("Enter search terms to find files")
        results_layout.addWidget(self.results_info)
        
        layout.addWidget(results_group)
        
        return tab
    
    def create_index_tab(self):
        """Create the index management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Index statistics
        stats_group = QGroupBox("Index Statistics")
        stats_layout = QFormLayout(stats_group)
        
        self.stats_total_files = QLabel("0")
        stats_layout.addRow("Total Indexed Files:", self.stats_total_files)
        
        self.stats_pak_files = QLabel("0")
        stats_layout.addRow("PAK Files:", self.stats_pak_files)
        
        self.stats_extracted_files = QLabel("0")
        stats_layout.addRow("Extracted Files:", self.stats_extracted_files)
        
        layout.addWidget(stats_group)
        
        # Index operations
        ops_group = QGroupBox("Index Operations")
        ops_layout = QVBoxLayout(ops_group)
        
        # Add PAK files
        pak_layout = QHBoxLayout()
        pak_layout.addWidget(QLabel("Index PAK Files:"))
        
        select_pak_btn = QPushButton("Select PAK Files")
        select_pak_btn.clicked.connect(self.select_pak_files_to_index)
        pak_layout.addWidget(select_pak_btn)
        
        index_game_paks_btn = QPushButton("Index Game PAKs")
        index_game_paks_btn.clicked.connect(self.index_game_paks)
        pak_layout.addWidget(index_game_paks_btn)
        
        pak_layout.addStretch()
        ops_layout.addLayout(pak_layout)
        
        # Add directories
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Index Directories:"))
        
        select_dir_btn = QPushButton("Select Directory")
        select_dir_btn.clicked.connect(self.select_directory_to_index)
        dir_layout.addWidget(select_dir_btn)
        
        dir_layout.addStretch()
        ops_layout.addLayout(dir_layout)
        
        # Progress bar
        self.index_progress = QProgressBar()
        self.index_progress.setVisible(False)
        ops_layout.addWidget(self.index_progress)
        
        self.index_status = QLabel("")
        ops_layout.addWidget(self.index_status)
        
        layout.addWidget(ops_group)
        
        # Indexed PAKs list
        paks_group = QGroupBox("Indexed PAK Files")
        paks_layout = QVBoxLayout(paks_group)
        
        self.paks_tree = QTreeWidget()
        self.paks_tree.setHeaderLabels(['PAK Name', 'File Count', 'Last Indexed'])
        self.paks_tree.setRootIsDecorated(False)
        paks_layout.addWidget(self.paks_tree)
        
        # PAK operations
        pak_ops_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.load_indexed_paks)
        pak_ops_layout.addWidget(refresh_btn)
        
        clear_index_btn = QPushButton("Clear Index")
        clear_index_btn.clicked.connect(self.clear_index)
        pak_ops_layout.addWidget(clear_index_btn)
        
        pak_ops_layout.addStretch()
        paks_layout.addLayout(pak_ops_layout)
        
        layout.addWidget(paks_group)
        
        return tab
    
    def load_initial_data(self):
        """Load initial data for the interface"""
        self.load_index_stats()
        self.load_indexed_paks()
    
    def load_index_stats(self):
        """Load and display index statistics"""
        try:
            stats = self.searcher.get_index_stats()
            
            self.stats_total_files.setText(f"{stats['total_files']:,}")
            
            by_type = stats['by_type']
            self.stats_pak_files.setText(f"{by_type.get('pak', 0):,}")
            self.stats_extracted_files.setText(f"{by_type.get('extracted', 0):,}")
            
        except Exception as e:
            print(f"Error loading index stats: {e}")
    
    def load_indexed_paks(self):
        """Load list of indexed PAK files"""
        try:
            self.paks_tree.clear()
            
            paks = self.searcher.get_indexed_paks()
            
            for pak_name, file_count, last_indexed in paks:
                item = QTreeWidgetItem(self.paks_tree)
                item.setText(0, pak_name)
                item.setText(1, f"{file_count:,}")
                item.setText(2, last_indexed)
                
        except Exception as e:
            print(f"Error loading indexed PAKs: {e}")
    
    def perform_search(self):
        """Perform file search"""
        query = self.search_edit.text().strip()
        
        if not query:
            self.results_info.setText("Enter search terms to find files")
            return
        
        # Build filters
        filters = {}
        
        ext = self.ext_combo.currentText().strip()
        if ext:
            filters['extension'] = ext
        
        source = self.source_combo.currentText()
        if source == 'PAK Files':
            filters['source_type'] = 'pak'
        elif source == 'Extracted':
            filters['source_type'] = 'extracted'
        
        try:
            # Perform search
            results = self.searcher.search_files(query, filters)
            
            # Display results
            self.display_search_results(results)
            
            self.results_info.setText(f"Found {len(results)} files matching '{query}'")
            
        except Exception as e:
            self.results_info.setText(f"Search error: {e}")
    
    def display_search_results(self, results):
        """Display search results in the tree"""
        self.results_tree.clear()
        
        for result in results:
            item = QTreeWidgetItem(self.results_tree)
            item.setText(0, result['file_name'])
            item.setText(1, result['extension'])
            item.setText(2, self.format_file_size(result['size']))
            item.setText(3, 'PAK' if result['source_type'] == 'pak' else 'Extracted')
            item.setText(4, result['relative_path'])
            
            # Store full data for context menu
            item.setData(0, Qt.ItemDataRole.UserRole, result)
        
        # Resize columns
        for i in range(5):
            self.results_tree.resizeColumnToContents(i)
    
    def format_file_size(self, size):
        """Format file size for display"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        else:
            return f"{size/(1024*1024):.1f} MB"
    
    def show_results_context_menu(self, position):
        """Show context menu for search results"""
        item = self.results_tree.itemAt(position)
        if not item:
            return
        
        result_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not result_data:
            return
        
        menu = QMenu(self)
        
        # Extract file action
        if result_data['source_type'] == 'pak':
            extract_action = QAction("Extract File", self)
            extract_action.triggered.connect(lambda: self.extract_file_from_pak(result_data))
            menu.addAction(extract_action)
        
        # Open file action
        if result_data['source_type'] == 'extracted':
            open_action = QAction("Open File", self)
            open_action.triggered.connect(lambda: self.open_extracted_file(result_data))
            menu.addAction(open_action)
        
        # Copy path action
        copy_path_action = QAction("Copy Path", self)
        copy_path_action.triggered.connect(lambda: self.copy_file_path(result_data))
        menu.addAction(copy_path_action)
        
        menu.exec(self.results_tree.mapToGlobal(position))
    
    def open_file_from_results(self, item):
        """Handle double-click on search result"""
        result_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not result_data:
            return
        
        if result_data['source_type'] == 'extracted':
            self.open_extracted_file(result_data)
        else:
            self.extract_file_from_pak(result_data)
    
    def extract_file_from_pak(self, result_data):
        """Extract file from PAK"""
        # This would integrate with your existing PAK extraction system
        pak_path = result_data['source_pak']
        file_path = result_data['relative_path']
        
        # Show extraction dialog or use asset browser extraction
        QMessageBox.information(self, "Extract File", 
                               f"Would extract {file_path} from {Path(pak_path).name}")
    
    def open_extracted_file(self, result_data):
        """Open extracted file"""
        file_path = result_data['file_path']
        
        if os.path.exists(file_path):
            # Could open in preview or external editor
            QMessageBox.information(self, "Open File", f"Would open {file_path}")
        else:
            QMessageBox.warning(self, "File Not Found", f"File no longer exists: {file_path}")
    
    def copy_file_path(self, result_data):
        """Copy file path to clipboard"""
        from PyQt6.QtWidgets import QApplication
        
        path = result_data.get('file_path', result_data.get('relative_path', ''))
        clipboard = QApplication.clipboard()
        clipboard.setText(path)
    
    def select_pak_files_to_index(self):
        """Select PAK files to index"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PAK Files to Index",
            self.settings_manager.get("working_directory", "") if self.settings_manager else "",
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if files:
            self.index_files(files, 'pak')
    
    def select_directory_to_index(self):
        """Select directory to index"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Directory to Index",
            self.settings_manager.get("working_directory", "") if self.settings_manager else ""
        )
        
        if directory:
            self.index_files([directory], 'directory')
    
    def index_game_paks(self):
        """Index game PAK files (would need game path configuration)"""
        QMessageBox.information(self, "Index Game PAKs", 
                               "Game PAK indexing would scan the BG3 installation directory")
    
    def index_files(self, files, file_type):
        """Index files or directories"""
        if not files:
            return
        
        # Create indexing thread
        self.index_thread = IndexingThread(files, file_type, self.indexer)
        self.index_thread.progress_updated.connect(self.update_index_progress)
        self.index_thread.indexing_finished.connect(self.indexing_completed)
        
        # Show progress
        self.index_progress.setVisible(True)
        self.index_progress.setValue(0)
        self.index_status.setText("Starting indexing...")
        
        self.index_thread.start()
    
    def update_index_progress(self, percentage, message):
        """Update indexing progress"""
        self.index_progress.setValue(percentage)
        self.index_status.setText(message)
    
    def indexing_completed(self, results):
        """Handle indexing completion"""
        self.index_progress.setVisible(False)
        
        success_count = sum(1 for r in results if r.get('success'))
        total_count = len(results)
        
        if success_count == total_count:
            self.index_status.setText(f"Successfully indexed {success_count} items")
        else:
            self.index_status.setText(f"Indexed {success_count}/{total_count} items (some failed)")
        
        # Refresh data
        self.load_index_stats()
        self.load_indexed_paks()
        
        # Clear status after delay
        QTimer.singleShot(5000, lambda: self.index_status.setText(""))
    
    def clear_index(self):
        """Clear the entire index"""
        reply = QMessageBox.question(
            self, "Clear Index",
            "This will remove all indexed file data. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Clear database
                conn = sqlite3.connect(self.indexer.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM indexed_files')
                cursor.execute('DELETE FROM pak_info')
                conn.commit()
                conn.close()
                
                # Refresh interface
                self.load_index_stats()
                self.load_indexed_paks()
                self.results_tree.clear()
                self.results_info.setText("Index cleared")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear index: {e}")
