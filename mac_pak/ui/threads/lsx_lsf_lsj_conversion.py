import os
import shutil
from PyQt6.QtCore import QThread, pyqtSignal

class FileConversionThread(QThread):
    """Thread for file conversions"""
    
    progress_updated = pyqtSignal(int, str)
    conversion_finished = pyqtSignal(bool, dict)
    
    def __init__(self, bg3_tool, source_path, target_path, source_format, target_format):
        super().__init__()
        self.bg3_tool = bg3_tool
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
                import shutil
                shutil.copy2(self.source_path, self.target_path)
                self.conversion_finished.emit(True, {"message": "File copied (same format)"})
                return
            
            self.progress_updated.emit(40, "Converting file...")
            
            # Use divine.exe for conversions
            success, output = self.bg3_tool.run_divine_command(
                action="convert-resource",
                source=self.bg3_tool.mac_to_wine_path(self.source_path),
                destination=self.bg3_tool.mac_to_wine_path(self.target_path),
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
    
    def __init__(self, bg3_tool, file_list, target_format, output_dir=None):
        super().__init__()
        self.bg3_tool = bg3_tool
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
                    success, output = self.bg3_tool.run_divine_command(
                        action="convert-resource",
                        source=self.bg3_tool.mac_to_wine_path(source_file),
                        destination=self.bg3_tool.mac_to_wine_path(target_file),
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
