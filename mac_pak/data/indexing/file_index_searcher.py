#!/usr/bin/env python3
"""
Index Search System for BG3 Files
Provides fast searching across PAK contents and extracted files
"""

import os
import json
import sqlite3
import threading
import fnmatch
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QLabel, QComboBox, QCheckBox,
    QSplitter, QTextEdit, QProgressBar, QGroupBox, QFormLayout,
    QTabWidget, QMessageBox, QMenu, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QAction

class FileIndexer:
    """Handles indexing of PAK files and extracted directories"""
    
    def __init__(self, wine_wrapper=None):
        self.wine_wrapper = wine_wrapper
        self.db_path = "bg3_file_index.db"
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for file indexing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indexed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_extension TEXT,
                file_size INTEGER,
                source_pak TEXT,
                source_type TEXT,  -- 'pak' or 'extracted'
                relative_path TEXT,
                last_modified TIMESTAMP,
                indexed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_hash TEXT,
                metadata TEXT  -- JSON string for additional data
            )
        ''')
        
        # Index for fast searching
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_name ON indexed_files(file_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_extension ON indexed_files(file_extension)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_pak ON indexed_files(source_pak)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relative_path ON indexed_files(relative_path)')
        
        # PAK info table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pak_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pak_path TEXT UNIQUE NOT NULL,
                pak_name TEXT NOT NULL,
                file_count INTEGER,
                total_size INTEGER,
                last_indexed TIMESTAMP,
                pak_hash TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def index_pak_file(self, pak_path, progress_callback=None):
        """Index contents of a PAK file"""
        if not self.wine_wrapper:
            raise Exception("Wine wrapper not available for PAK indexing")
        
        try:
            if progress_callback:
                progress_callback(10, f"Reading PAK contents: {Path(pak_path).name}")
            
            # Get PAK contents
            files = self.wine_wrapper.list_pak_contents(pak_path)
            
            if progress_callback:
                progress_callback(30, "Processing file list...")
            
            # Prepare database connection
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Remove existing entries for this PAK
            cursor.execute('DELETE FROM indexed_files WHERE source_pak = ?', (pak_path,))
            
            pak_name = Path(pak_path).name
            total_files = len(files)
            
            if progress_callback:
                progress_callback(50, f"Indexing {total_files} files...")
            
            # Index each file
            for i, file_info in enumerate(files):
                if isinstance(file_info, dict):
                    file_path = file_info.get('name', str(file_info))
                    file_size = file_info.get('size', 0)
                else:
                    file_path = str(file_info)
                    file_size = 0
                
                file_name = Path(file_path).name
                file_ext = Path(file_path).suffix.lower()
                
                # Insert file record
                cursor.execute('''
                    INSERT INTO indexed_files 
                    (file_path, file_name, file_extension, file_size, source_pak, 
                     source_type, relative_path, last_modified, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_path, file_name, file_ext, file_size, pak_path,
                    'pak', file_path, datetime.now(), 
                    json.dumps({'type': 'pak_file'})
                ))
                
                # Update progress
                if progress_callback and i % 100 == 0:
                    percent = 50 + int((i / total_files) * 40)
                    progress_callback(percent, f"Indexed {i}/{total_files} files")
            
            # Update PAK info
            pak_size = os.path.getsize(pak_path) if os.path.exists(pak_path) else 0
            cursor.execute('''
                INSERT OR REPLACE INTO pak_info 
                (pak_path, pak_name, file_count, total_size, last_indexed)
                VALUES (?, ?, ?, ?, ?)
            ''', (pak_path, pak_name, total_files, pak_size, datetime.now()))
            
            conn.commit()
            conn.close()
            
            if progress_callback:
                progress_callback(100, f"Indexed {total_files} files from {pak_name}")
            
            return {
                'success': True,
                'files_indexed': total_files,
                'pak_name': pak_name
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'pak_path': pak_path
            }
    
    def index_directory(self, directory_path, progress_callback=None):
        """Index extracted files in a directory"""
        try:
            if progress_callback:
                progress_callback(10, f"Scanning directory: {Path(directory_path).name}")
            
            # Find all files
            all_files = []
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, directory_path)
                    all_files.append((file_path, relative_path))
            
            if progress_callback:
                progress_callback(30, f"Found {len(all_files)} files")
            
            # Prepare database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Remove existing entries for this directory
            cursor.execute('DELETE FROM indexed_files WHERE source_pak = ? AND source_type = ?', 
                          (directory_path, 'extracted'))
            
            total_files = len(all_files)
            
            # Index each file
            for i, (file_path, relative_path) in enumerate(all_files):
                try:
                    stat = os.stat(file_path)
                    file_name = Path(file_path).name
                    file_ext = Path(file_path).suffix.lower()
                    
                    cursor.execute('''
                        INSERT INTO indexed_files 
                        (file_path, file_name, file_extension, file_size, source_pak, 
                         source_type, relative_path, last_modified, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        file_path, file_name, file_ext, stat.st_size, directory_path,
                        'extracted', relative_path, datetime.fromtimestamp(stat.st_mtime),
                        json.dumps({'type': 'extracted_file'})
                    ))
                    
                    # Update progress
                    if progress_callback and i % 50 == 0:
                        percent = 30 + int((i / total_files) * 60)
                        progress_callback(percent, f"Indexed {i}/{total_files} files")
                        
                except OSError:
                    continue  # Skip files that can't be accessed
            
            conn.commit()
            conn.close()
            
            if progress_callback:
                progress_callback(100, f"Indexed {total_files} extracted files")
            
            return {
                'success': True,
                'files_indexed': total_files,
                'directory': directory_path
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'directory': directory_path
            }

class IndexSearcher:
    """Handles searching through indexed files"""
    
    def __init__(self, db_path="bg3_file_index.db"):
        self.db_path = db_path
    
    def search_files(self, query, filters=None):
        """
        Search indexed files
        
        Args:
            query: Search query string
            filters: Dict with search filters
            
        Returns:
            List of matching file records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build search query
        where_conditions = []
        params = []
        
        if query:
            # Support wildcard search
            if '*' in query or '?' in query:
                where_conditions.append('file_name GLOB ?')
                params.append(query)
            else:
                where_conditions.append('file_name LIKE ?')
                params.append(f'%{query}%')
        
        # Apply filters
        if filters:
            if filters.get('extension'):
                where_conditions.append('file_extension = ?')
                params.append(filters['extension'])
            
            if filters.get('source_type'):
                where_conditions.append('source_type = ?')
                params.append(filters['source_type'])
            
            if filters.get('source_pak'):
                where_conditions.append('source_pak LIKE ?')
                params.append(f'%{filters["source_pak"]}%')
            
            if filters.get('min_size'):
                where_conditions.append('file_size >= ?')
                params.append(filters['min_size'])
            
            if filters.get('max_size'):
                where_conditions.append('file_size <= ?')
                params.append(filters['max_size'])
        
        # Build final query
        base_query = '''
            SELECT file_path, file_name, file_extension, file_size, 
                   source_pak, source_type, relative_path, last_modified
            FROM indexed_files
        '''
        
        if where_conditions:
            base_query += ' WHERE ' + ' AND '.join(where_conditions)
        
        base_query += ' ORDER BY file_name LIMIT 1000'  # Limit results
        
        cursor.execute(base_query, params)
        results = cursor.fetchall()
        
        conn.close()
        
        # Convert to dict format
        columns = ['file_path', 'file_name', 'extension', 'size', 
                  'source_pak', 'source_type', 'relative_path', 'last_modified']
        
        return [dict(zip(columns, row)) for row in results]
    
    def get_indexed_paks(self):
        """Get list of indexed PAK files"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT pak_name, file_count, last_indexed FROM pak_info ORDER BY pak_name')
        results = cursor.fetchall()
        
        conn.close()
        return results
    
    def get_index_stats(self):
        """Get indexing statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total files
        cursor.execute('SELECT COUNT(*) FROM indexed_files')
        total_files = cursor.fetchone()[0]
        
        # By source type
        cursor.execute('SELECT source_type, COUNT(*) FROM indexed_files GROUP BY source_type')
        by_type = dict(cursor.fetchall())
        
        # By extension
        cursor.execute('''
            SELECT file_extension, COUNT(*) 
            FROM indexed_files 
            GROUP BY file_extension 
            ORDER BY COUNT(*) DESC 
            LIMIT 10
        ''')
        top_extensions = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_files': total_files,
            'by_type': by_type,
            'top_extensions': top_extensions
        }