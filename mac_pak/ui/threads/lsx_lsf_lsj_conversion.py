import os
import shutil
from PyQt6.QtCore import QThread, pyqtSignal

from ...data.parsers.larian_parser import ProgressUpdate, ParseResult
from typing import List

# class FileConversionThread(QThread):
#     """Thread for file conversions - uses async WineProcessMonitor"""
    
#     progress_updated = pyqtSignal(int, str)
#     conversion_finished = pyqtSignal(bool, dict)
    
#     def __init__(self, wine_wrapper, source_path, target_path, source_format, target_format):
#         super().__init__()
#         self.wine_wrapper = wine_wrapper
#         self.source_path = source_path
#         self.target_path = target_path
#         self.source_format = source_format
#         self.target_format = target_format
#         self.monitor = None
    
#     def run(self):
#         """Run the conversion using subprocess (thread-safe)"""
#         try:
#             self.progress_updated.emit(20, "Starting conversion...")
            
#             if self.source_format == self.target_format:
#                 shutil.copy2(self.source_path, self.target_path)
#                 self.conversion_finished.emit(True, {"message": "File copied (same format)"})
#                 return
            
#             self.progress_updated.emit(40, "Converting file...")
            
#             # Use subprocess directly (thread-safe, unlike QProcess from thread)
#             import subprocess
            
#             cmd = [
#                 self.wine_wrapper.wine_env.wine_path,
#                 self.wine_wrapper.lslib_path,
#                 "--action", "convert-resource",
#                 "--game", "bg3",
#                 "--source", self.wine_wrapper.mac_to_wine_path(self.source_path),
#                 "--destination", self.wine_wrapper.mac_to_wine_path(self.target_path)
#             ]
            
#             env = os.environ.copy()
#             env["WINEPREFIX"] = self.wine_wrapper.wine_env.wine_prefix
            
#             # Run subprocess - blocks this thread but not UI
#             result = subprocess.run(
#                 cmd,
#                 env=env,
#                 capture_output=True,
#                 text=True,
#                 timeout=120
#             )
            
#             success = (result.returncode == 0)
#             output = result.stdout if result.stdout else result.stderr
            
#             self.progress_updated.emit(100, "Conversion complete!")
            
#             result_data = {
#                 "success": success,
#                 "output": output,
#                 "source_path": self.source_path,
#                 "target_path": self.target_path
#             }
            
#             self.conversion_finished.emit(success, result_data)
            
#         except subprocess.TimeoutExpired:
#             self.conversion_finished.emit(False, {"error": "Conversion timed out after 2 minutes"})
#         except Exception as e:
#             self.conversion_finished.emit(False, {"error": str(e)})

#     def cancel_operation(self):
#         """Cancel the current conversion operation"""
#         self.requestInterruption()
#         if hasattr(self, 'wine_wrapper') and self.wine_wrapper:
#             # Cancel the wine wrapper operation
#             self.wine_wrapper.cancel_current_operation()
        
#         # Terminate the thread if it doesn't stop gracefully
#         if self.isRunning():
#             self.terminate()
#             if not self.wait(3000):  # Wait 3 seconds
#                 self.quit()


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
                source_format = self._detect_format(source_file)
                
                if source_format == self.target_format:
                    shutil.copy2(source_file, target_file)
                    results.append({
                        "source": source_file,
                        "target": target_file,
                        "success": True,
                        "message": "File copied (same format)"
                    })
                    continue
                
                # Use the synchronous binary converter method
                # Divine.exe auto-detects format from file extensions
                success, output = self.wine_wrapper.binary_converter.run_divine_command(
                    action="convert-resource",
                    source=self.wine_wrapper.mac_to_wine_path(source_file),
                    destination=self.wine_wrapper.mac_to_wine_path(target_file)
                )
                
                results.append({
                    "source": source_file,
                    "target": target_file,
                    "success": success,
                    "message": output if not success else "Conversion successful"
                })
                
            except Exception as e:
                results.append({
                    "source": source_file,
                    "target": None,
                    "success": False,
                    "message": str(e)
                })
        
        self.progress_updated.emit(100, "Batch conversion complete")
        self.conversion_finished.emit(results)
    
    def _detect_format(self, file_path):
        """Detect file format from extension"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.lsx':
            return 'lsx'
        elif ext == '.lsf':
            return 'lsf'
        elif ext == '.lsj':
            return 'lsj'
        else:
            return 'lsx'  # Default to LSX


class BatchParserThread(QThread):
    """Thread for batch parsing operations"""
    
    progress_updated = pyqtSignal(int, str)
    parse_completed = pyqtSignal(ParseResult)
    batch_finished = pyqtSignal()
    
    def __init__(self, parser, file_list):
        super().__init__()
        self.parser = parser
        self.file_list = file_list
    
    def run(self):
        """Run batch parsing"""
        total_files = len(self.file_list)
        
        for i, file_path in enumerate(self.file_list):
            percentage = int(((i + 1) / total_files) * 100)
            self.progress_updated.emit(percentage, f"Parsing {os.path.basename(file_path)}...")
            
            # Parse file
            result = self.parser.parse_file(file_path)
            self.parse_completed.emit(result)
        
        self.progress_updated.emit(100, "Batch parsing complete")
        self.batch_finished.emit()