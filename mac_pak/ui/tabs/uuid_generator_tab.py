import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QGroupBox, QFormLayout, QSpinBox, QComboBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QTabWidget,
    QSplitter, QFrame, QApplication, QFileDialog, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

# Import the separate widget classes
from ..widgets.uuid_generator.paired_generator import IDGeneratorWidget
from ..widgets.uuid_generator.individual_generator import IndividualGeneratorsWidget
from ..widgets.uuid_generator.output_json import HistoryWidget

class BG3IDGeneratorTab(QWidget):
    """Main container for UUID and handle generation with tabbed interface"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        
        self.settings_manager = settings_manager
        self.wine_wrapper = wine_wrapper
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup the main tabbed interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Title
        title_label = QLabel("UUID & TranslatedString Generator")
        title_label.setProperty("header", "h1")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create individual widgets
        self.id_generator_widget = IDGeneratorWidget(
            parent=self, 
            settings_manager=self.settings_manager,
            wine_wrapper=self.wine_wrapper
        )
        
        self.individual_generators_widget = IndividualGeneratorsWidget(
            parent=self,
            settings_manager=self.settings_manager,
            wine_wrapper=self.wine_wrapper
        )
        
        self.history_widget = HistoryWidget(
            parent=self,
            settings_manager=self.settings_manager,
            wine_wrapper=self.wine_wrapper
        )
        
        # Add tabs
        self.tab_widget.addTab(self.id_generator_widget, "ID Generator")
        self.tab_widget.addTab(self.individual_generators_widget, "Individual Generators")
        self.tab_widget.addTab(self.history_widget, "Generated Items")
        
        layout.addWidget(self.tab_widget)
    
    def connect_signals(self):
        """Connect signals between widgets"""
        # Note: This is a conceptual example. In practice, you might want to use 
        # proper PyQt signals or a more robust event system
        
        # Connect history updates from both generator widgets to history widget
        self.id_generator_widget.history_updated = self._create_history_updater()
        self.individual_generators_widget.history_updated = self._create_history_updater()
    
    def _create_history_updater(self):
        """Create a simple history updater function"""
        class HistoryUpdater:
            def __init__(self, history_widget):
                self.history_widget = history_widget
            
            def emit(self, item_type, value, content_type):
                self.history_widget.add_to_history(item_type, value, content_type)
        
        return HistoryUpdater(self.history_widget)
    
    def get_history_items(self):
        """Get all generated items from history"""
        return self.history_widget.get_history_items()
    
    def get_history_count(self):
        """Get count of generated items"""
        return self.history_widget.get_history_count()
    
    def clear_all_history(self):
        """Clear all generation history"""
        self.history_widget.clear_history()
    
    def export_history(self):
        """Export generation history"""
        self.history_widget.export_generated_items()

# Alternative implementation using proper PyQt signals
class BG3IDGeneratorTabWithSignals(QWidget):
    """Alternative implementation using proper PyQt signals"""
    
    # Define custom signals
    history_item_generated = pyqtSignal(str, str, str)  # type, value, content_type
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        
        self.settings_manager = settings_manager
        self.wine_wrapper = wine_wrapper
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup the main tabbed interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Title
        title_label = QLabel("BG3 ID Generator")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create individual widgets
        self.id_generator_widget = IDGeneratorWidget(
            parent=self, 
            settings_manager=self.settings_manager,
            wine_wrapper=self.wine_wrapper
        )
        
        self.individual_generators_widget = IndividualGeneratorsWidget(
            parent=self,
            settings_manager=self.settings_manager,
            wine_wrapper=self.wine_wrapper
        )
        
        self.history_widget = HistoryWidget(
            parent=self,
            settings_manager=self.settings_manager,
            wine_wrapper=self.wine_wrapper
        )
        
        # Add tabs
        self.tab_widget.addTab(self.id_generator_widget, "ID Generator")
        self.tab_widget.addTab(self.individual_generators_widget, "Individual Generators") 
        self.tab_widget.addTab(self.history_widget, "Generated Items")
        
        layout.addWidget(self.tab_widget)
    
    def connect_signals(self):
        """Connect PyQt signals between widgets"""
        # Connect the main signal to history widget
        self.history_item_generated.connect(self.history_widget.add_to_history)
        
        # You would need to modify the generator widgets to emit this signal
        # instead of using the history_updated attribute approach