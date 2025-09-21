from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..editors.syntax_highlighter import LSXSyntaxHighlighter
from ..threads.lsx_lsf_lsj_conversion import FileConversionThread, BatchConversionThread
from ..widgets.universal_editor.lsx_editor import LSXEditor
from ..widgets.universal_editor.batch_processor import BatchProcessor

class UniversalEditorTab(QWidget):
    """Combined LSX Editor and Batch Processor in a tabbed interface"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.wine_wrapper = wine_wrapper
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the tabbed interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title_label = QLabel("LSX Editor and LSF/LSX/LSJ Converter")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # LSX Editor tab
        self.editor = LSXEditor(
            parent=self,
            settings_manager=self.settings_manager,
            wine_wrapper=self.wine_wrapper
        )
        self.tab_widget.addTab(self.editor, "File Editor")
        
        # Batch Processor tab
        self.batch_processor = BatchProcessor(
            parent=self,
            settings_manager=self.settings_manager,
            wine_wrapper=self.wine_wrapper
        )
        self.tab_widget.addTab(self.batch_processor, "Batch Processing")
        
        layout.addWidget(self.tab_widget)

       # Add a welcome message or recent files when no file is loaded
    def setup_universal_editor_placeholder(self):
        placeholder_widget = QWidget()
        layout = QVBoxLayout(placeholder_widget)
        
        # Center content vertically and horizontally
        layout.addStretch()
        
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        
        content_layout = QVBoxLayout()
        
        # Message
        message = QLabel("Universal Editor not available")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet("font-size: 18px; color: #666; margin: 10px;")
        
        hint = QLabel("Check that lsx_editor.py is in the same directory")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #888; margin-bottom: 20px;")
        
        content_layout.addWidget(message)
        content_layout.addWidget(hint)
        
        center_layout.addLayout(content_layout)
        center_layout.addStretch()
        layout.addLayout(center_layout)
        layout.addStretch()
        
        return placeholder_widget