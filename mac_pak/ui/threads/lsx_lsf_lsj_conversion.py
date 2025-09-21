import os
import shutil
from PyQt6.QtCore import QThread, pyqtSignal

from ...data.parsers.larian_parser import ProgressUpdate, ParseResult
from typing import List

class FileConversionThread(QThread):
    """Thread for file conversions"""
    
    progress_updated = pyqtSignal(int, str)
    conversion_finished = pyqtSignal(bool, dict)
    
    def __init__(self, wine_wrapper, source_path, target_path, source_format, target_format):
        super().__init__()
        self.wine_wrapper = wine_wrapper
        self.source_path = source_path
        self.target_path = target_path
        self.source_format = source_format
        self.target_format = target_format
    
    def run(self):
        """Run the conversion"""
        try:
            self.progress_updated.emit(20, "Starting conversion...")
            
            if self.source_format == self.target_format:
                # Just copy the file
                shutil.copy2(self.source_path, self.target_path)
                self.conversion_finished.emit(True, {"message": "File copied (same format)"})
                return
            
            self.progress_updated.emit(40, "Converting file...")
            
            # Use divine.exe for conversions
            success, output = self.wine_wrapper.run_divine_command(
                action="convert-resource",
                source=self.wine_wrapper.mac_to_wine_path(self.source_path),
                destination=self.wine_wrapper.mac_to_wine_path(self.target_path),
                input_format=self.source_format,
                output_format=self.target_format
            )
            
            self.progress_updated.emit(100, "Conversion complete!")
            
            result_data = {
                "success": success,
                "output": output,
                "source_path": self.source_path,
                "target_path": self.target_path
            }
            
            self.conversion_finished.emit(success, result_data)
            
        except Exception as e:
            self.conversion_finished.emit(False, {"error": str(e)})

class BatchConversionThread(QThread):
    """Thread for batch conversions"""
    
    progress_updated = pyqtSignal(int, str)
    conversion_finished = pyqtSignal(list)
    
    def __init__(self, wine_wrapper, file_list, target_format, output_dir=None):
        super().__init__()
        self.wine_wrapper = wine_wrapper
        self.file_list = file_list
        self.target_format = target_format
        self.output_dir = output_dir
    
    def run(self):
        """Run batch conversion"""
        results = []
        total_files = len(self.file_list)
        
        for i, source_file in enumerate(self.file_list):
            percentage = int((i / total_files) * 100)
            self.progress_updated.emit(percentage, f"Converting {os.path.basename(source_file)}...")
            
            try:
                # Determine output path
                if self.output_dir:
                    basename = os.path.splitext(os.path.basename(source_file))[0]
                    target_file = os.path.join(self.output_dir, f"{basename}.{self.target_format}")
                else:
                    target_file = os.path.splitext(source_file)[0] + f".{self.target_format}"
                
                # Detect source format
                source_format = self.detect_format(source_file)
                
                # Convert
                if source_format == self.target_format:
                    import shutil
                    shutil.copy2(source_file, target_file)
                    success, output = True, "File copied (same format)"
                else:
                    success, output = self.wine_wrapper.run_divine_command(
                        action="convert-resource",
                        source=self.wine_wrapper.mac_to_wine_path(source_file),
                        destination=self.wine_wrapper.mac_to_wine_path(target_file),
                        input_format=source_format,
                        output_format=self.target_format
                    )
                
                results.append({
                    'source': source_file,
                    'target': target_file,
                    'success': success,
                    'output': output
                })
                
            except Exception as e:
                results.append({
                    'source': source_file,
                    'target': '',
                    'success': False,
                    'output': str(e)
                })
        
        self.progress_updated.emit(100, "Batch conversion complete!")
        self.conversion_finished.emit(results)
    
    def detect_format(self, file_path):
        """Detect file format from extension"""
        ext = os.path.splitext(file_path)[1].lower()
        format_map = {'.lsx': 'lsx', '.lsj': 'lsj', '.lsf': 'lsf'}
        return format_map.get(ext, 'lsx')

class BatchParserThread(QThread):
    """Thread for batch processing multiple files"""
    
    # Signals
    progress_updated = pyqtSignal(ProgressUpdate)
    file_completed = pyqtSignal(ParseResult)
    batch_completed = pyqtSignal(list, list)  # results, errors
    
    def __init__(self, parser_instance, file_paths: List[str], max_workers: int = 4):
        super().__init__()
        self.parser = parser_instance
        self.file_paths = file_paths
        self.max_workers = max_workers
        self.should_stop = False
        self.results = []
        self.errors = []
        self._mutex = QMutex()
        self.completed_counter = ThreadSafeCounter()
    
    def run(self):
        """Execute batch parsing in thread pool"""
        try:
            total_files = len(self.file_paths)
            
            self.progress_updated.emit(ProgressUpdate(
                current=0, total=total_files,
                message=f"Starting batch parse of {total_files} files",
                stage="batch_starting"
            ))
            
            # Use ThreadPoolExecutor for concurrent parsing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all parsing tasks
                future_to_file = {
                    executor.submit(self._parse_single_file, file_path): file_path
                    for file_path in self.file_paths
                }
                
                # Process completed tasks
                for future in as_completed(future_to_file):
                    with QMutexLocker(self._mutex):
                        if self.should_stop:
                            break
                    
                    file_path = future_to_file[future]
                    
                    try:
                        result = future.result()
                        
                        if result.success:
                            self.results.append(result)
                        else:
                            self.errors.append(result)
                        
                        # Emit individual file completion
                        self.file_completed.emit(result)
                        
                        # Update progress
                        completed = self.completed_counter.increment()
                        self.progress_updated.emit(ProgressUpdate(
                            current=completed, total=total_files,
                            message=f"Processed {completed}/{total_files}: {os.path.basename(file_path)}",
                            stage="processing"
                        ))
                        
                    except Exception as e:
                        error_result = ParseResult(
                            success=False,
                            error=f"Future execution error: {str(e)}",
                            file_path=file_path
                        )
                        self.errors.append(error_result)
                        self.file_completed.emit(error_result)
            
            # Emit final completion
            self.batch_completed.emit(self.results, self.errors)
            
            self.progress_updated.emit(ProgressUpdate(
                current=total_files, total=total_files,
                message=f"Batch complete: {len(self.results)} successful, {len(self.errors)} errors",
                stage="completed"
            ))
            
        except Exception as e:
            logger.error(f"Batch parsing thread error: {e}")
            self.progress_updated.emit(ProgressUpdate(
                current=0, total=len(self.file_paths),
                message="Batch parsing failed",
                error=str(e)
            ))
    
    def _parse_single_file(self, file_path: str) -> ParseResult:
        """Parse a single file (called from thread pool)"""
        start_time = time.time()
        
        try:
            # Check if we should stop
            with QMutexLocker(self._mutex):
                if self.should_stop:
                    return ParseResult(
                        success=False,
                        error="Parsing cancelled",
                        file_path=file_path
                    )
            
            # Create a new parser instance for thread safety
            thread_parser = UniversalBG3Parser()
            if hasattr(self.parser, 'wine_wrapper'):
                thread_parser.set_wine_wrapper(self.parser.wine_wrapper)
            
            result_data = thread_parser.parse_file(file_path)
            processing_time = time.time() - start_time
            
            if result_data and not isinstance(result_data, str):
                return ParseResult(
                    success=True,
                    data=result_data,
                    file_path=file_path,
                    processing_time=processing_time
                )
            else:
                error_msg = result_data if isinstance(result_data, str) else "Unknown parsing error"
                return ParseResult(
                    success=False,
                    error=error_msg,
                    file_path=file_path,
                    processing_time=processing_time
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            return ParseResult(
                success=False,
                error=f"Exception: {str(e)}",
                file_path=file_path,
                processing_time=processing_time
            )
    
    def stop_parsing(self):
        """Signal the thread to stop processing"""
        with QMutexLocker(self._mutex):
            self.should_stop = True
        
        # Request thread interruption
        self.requestInterruption()