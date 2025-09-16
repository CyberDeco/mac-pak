from PyQt6.QtCore import QThread, pyqtSignal

class IndexingThread(QThread):
    """Thread for background indexing operations"""
    
    progress_updated = pyqtSignal(int, str)
    indexing_finished = pyqtSignal(list)
    
    def __init__(self, files, file_type, indexer):
        super().__init__()
        self.files = files
        self.file_type = file_type
        self.indexer = indexer
    
    def run(self):
        """Run indexing operations"""
        results = []
        total_files = len(self.files)
        
        for i, file_path in enumerate(self.files):
            overall_progress = int((i / total_files) * 100)
            
            def progress_callback(percent, message):
                # Adjust progress to account for multiple files
                adjusted_percent = overall_progress + int((percent / total_files))
                self.progress_updated.emit(adjusted_percent, message)
            
            try:
                if self.file_type == 'pak':
                    result = self.indexer.index_pak_file(file_path, progress_callback)
                elif self.file_type == 'directory':
                    result = self.indexer.index_directory(file_path, progress_callback)
                else:
                    result = {'success': False, 'error': f'Unknown file type: {self.file_type}'}
                
                results.append(result)
                
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e),
                    'file_path': file_path
                })
        
        self.indexing_finished.emit(results)