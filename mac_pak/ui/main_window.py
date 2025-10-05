#!/usr/bin/env python3
"""
BG3 MacPak Modding Toolkit - PyQt6 Version
A native macOS application for modding Baldur's Gate 3 using Wine and divine.exe
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QTextEdit, QTabWidget, QGroupBox, 
    QFileDialog, QMessageBox, QStatusBar, QMenuBar
)
from PyQt6.QtCore import Qt, QSettings, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont

# Import core components with correct paths
from ..core.settings import SettingsManager
from ..core.update_checker import UpdateChecker
from .dialogs.update_dialog import UpdateDialog
from ..tools.wine_wrapper import WineWrapper
from .tabs.pak_tools_tab import PakToolsTab
from .tabs.assets_browser_tab import AssetBrowserTab
from .tabs.universal_editor_tab import UniversalEditorTab
from .tabs.index_search_tab import IndexSearchTab
from .tabs.uuid_generator_tab import BG3IDGeneratorTab
from .dialogs.settings_dialog import SettingsDialog

class UpdateCheckThread(QThread):
    """Proper QThread subclass for update checking"""
    
    update_result = pyqtSignal(dict)
    
    def run(self):
        """Run update check in background"""
        try:
            checker = UpdateChecker()
            result = checker.check_for_updates()
            self.update_result.emit(result)
        except Exception as e:
            self.update_result.emit({'error': str(e)})


class MacPakMainWindow(QMainWindow):
    """Main application window with native Mac styling and threading support"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize settings first
        self.settings_manager = SettingsManager()
        self.wine_wrapper = None
        self.update_thread = None
        
        # UI setup
        self.setup_window_properties()
        self.setup_menubar()
        self.setup_status_bar()
        
        # Initialize backend FIRST
        self.initialize_backend()
        
        # THEN setup interface with the wine_wrapper available
        self.setup_main_interface()
        
        # Restore window state
        self.restore_window_state()

        # Check for updates on startup (optional)
        QTimer.singleShot(3000, self.check_for_updates)  # Check after 3 seconds
    
    def check_for_updates(self, show_no_update_message=False):
        """Check for updates using proper threading"""
        # Don't start new check if one is already running
        if self.update_thread and self.update_thread.isRunning():
            return
        
        # Clean up any previous thread
        if self.update_thread:
            self.update_thread.deleteLater()
        
        # Create and start new update thread
        self.update_thread = UpdateCheckThread(self)
        self.update_thread.update_result.connect(
            lambda result: self.handle_update_result(result, show_no_update_message)
        )
        self.update_thread.finished.connect(self.on_update_check_finished)
        self.update_thread.start()
    
    def handle_update_result(self, result, show_no_update_message):
        """Handle update check result"""
        if result.get('error'):
            if show_no_update_message:
                QMessageBox.warning(self, "Update Check", f"Failed to check for updates: {result['error']}")
            return
        
        if result['update_available']:
            # Check if user already skipped this version
            skipped_version = self.settings_manager.get("skipped_version", "")
            
            if skipped_version != result['latest_version']:
                dialog = UpdateDialog(result, self)
                dialog.exec()
        elif show_no_update_message:
            QMessageBox.information(self, "No Updates", "You're running the latest version!")
    
    def on_update_check_finished(self):
        """Clean up update thread when finished"""
        if self.update_thread:
            self.update_thread.deleteLater()
            self.update_thread = None
    
    def setup_window_properties(self):
        """Setup main window properties with Mac styling"""
        self.setWindowTitle("MacPak")
        self.setMinimumSize(1000, 600)
        
        # Set up Mac-style window
        self.setUnifiedTitleAndToolBarOnMac(True)
        
        # Apply Mac-style theme
        self.apply_mac_styling()
    
    def apply_mac_styling(self):
        """Apply Mac-native styling"""
        app = QApplication.instance()
        if app:
            app.setApplicationName("MacPak")
            app.setApplicationVersion("0.1.0")
            app.setOrganizationName("CyberDeco")
            app.setOrganizationDomain("MacPak.app")
    
    def setup_menubar(self):
        """Setup native Mac menubar"""
        menubar = self.menuBar()
        
        # Application menu
        app_menu = menubar.addMenu("MacPak")
        
        about_action = QAction("About MacPak", self)
        about_action.triggered.connect(self.show_about)
        app_menu.addAction(about_action)
        
        app_menu.addSeparator()
        
        prefs_action = QAction("Preferences...", self)
        prefs_action.setShortcut("Cmd+,")
        prefs_action.triggered.connect(self.open_preferences)
        app_menu.addAction(prefs_action)
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open PAK...", self)
        open_action.setShortcut("Cmd+O")
        open_action.triggered.connect(self.open_pak_file)
        file_menu.addAction(open_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        reinit_action = QAction("Reinitialize Backend", self)
        reinit_action.triggered.connect(self.reinitialize_backend)
        tools_menu.addAction(reinit_action)
        
        # Add manual update check
        check_updates_action = QAction("Check for Updates...", self)
        check_updates_action.triggered.connect(lambda: self.check_for_updates(True))
        tools_menu.addAction(check_updates_action)
    
    def setup_main_interface(self):
        """Setup the main interface with tabs"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tab_widget, 1)
        
        # Add tabs with wine_wrapper (might be None if backend failed)
        self.setup_tabs()
    
    def setup_tabs(self):
        """Setup all tabs with proper error handling"""
        try:
            # Create tabs - pass whatever wine_wrapper we have (could be None)
            asset_tab = AssetBrowserTab(self, self.settings_manager, self.wine_wrapper)
            editor_tab = UniversalEditorTab(self, self.settings_manager, self.wine_wrapper)
            pak_tab = PakToolsTab(self, self.settings_manager, self.wine_wrapper)
            index_search_tab = IndexSearchTab(self, self.settings_manager, self.wine_wrapper)
            id_generator_tab = BG3IDGeneratorTab(self, self.settings_manager, self.wine_wrapper)

            # Add tabs to the widget
            self.tab_widget.addTab(asset_tab, "Asset Browser")
            self.tab_widget.addTab(editor_tab, "Universal Editor")
            self.tab_widget.addTab(pak_tab, "PAK Tools")
            self.tab_widget.addTab(index_search_tab, "Index Search")
            self.tab_widget.addTab(id_generator_tab, "BG3 ID Generator")
            
        except Exception as e:
            print(f"Error creating tabs: {e}")
            # Create a simple error tab if tab imports fail
            error_widget = QWidget()
            error_layout = QVBoxLayout(error_widget)
            error_label = QLabel(f"Error loading tabs: {e}")
            error_label.setWordWrap(True)
            error_layout.addWidget(error_label)
            self.tab_widget.addTab(error_widget, "Error")
    
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create status widgets
        self.backend_status = QLabel("Backend: Not initialized")
        self.backend_status.setStyleSheet("color: orange; font-weight: bold;")
        
        self.file_info = QLabel("")
        
        # Add widgets to status bar
        self.status_bar.addWidget(self.backend_status)
        self.status_bar.addPermanentWidget(self.file_info)
    
    def initialize_backend(self):
        """Initialize the Wine wrapper backend"""
        try:
            wine_path = self.settings_manager.get("wine_path")
            divine_path = self.settings_manager.get("divine_path")

            if not wine_path or not divine_path:
                self.backend_status.setText("Backend: Needs configuration")
                self.backend_status.setStyleSheet("color: orange; font-weight: bold;")
                # Don't show setup dialog during init - let user open preferences manually
                return
            
            # Validate paths exist
            if not os.path.exists(wine_path):
                raise FileNotFoundError(f"Wine executable not found: {wine_path}")
            
            if not os.path.exists(divine_path.split(':')[-1]):
                raise FileNotFoundError(f"Divine.exe not found: {divine_path}")

            self.wine_wrapper = WineWrapper(wine_path, divine_path)
            
            self.backend_status.setText("Backend: Initialized")
            self.backend_status.setStyleSheet("color: green; font-weight: bold;")
            self.status_bar.showMessage("Backend initialized successfully")
            
        except Exception as e:
            self.backend_status.setText("Backend: Error")
            self.backend_status.setStyleSheet("color: red; font-weight: bold;")
            print(f"Backend initialization failed: {e}")
            # Don't show error dialog during init - just log it
    
    def reinitialize_backend(self):
        """Manually reinitialize the backend"""
        old_wine_wrapper = self.wine_wrapper
        self.wine_wrapper = None
        
        # Try to reinitialize
        self.initialize_backend()
        
        # If successful and we have tabs, recreate them with new backend
        if self.wine_wrapper and self.wine_wrapper != old_wine_wrapper:
            if hasattr(self, 'tab_widget'):
                # Clear existing tabs
                self.tab_widget.clear()
                # Recreate with new wine_wrapper
                self.setup_tabs()
    
    def restore_window_state(self):
        """Restore window geometry and state"""
        geometry = self.settings_manager.get("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1200, 800)
            self.center_window()
    
    def center_window(self):
        """Center window on screen"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Clean up update thread
        if self.update_thread and self.update_thread.isRunning():
            self.update_thread.quit()
            self.update_thread.wait(1000)
        
        self.settings_manager.set("window_geometry", self.saveGeometry())
        self.settings_manager.sync()
        event.accept()
    
    # Menu actions
    def open_pak_file(self):
        """Open PAK file from menu"""
        pak_file, _ = QFileDialog.getOpenFileName(
            self, "Open PAK File",
            self.settings_manager.get("working_directory", ""),
            "PAK Files (*.pak);;All Files (*)"
        )
        
        if pak_file:
            # Switch to PAK Tools tab and load the file
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "PAK Tools":
                    self.tab_widget.setCurrentIndex(i)
                    # Try to load the file in the PAK tools tab
                    pak_tab = self.tab_widget.currentWidget()
                    if hasattr(pak_tab, 'load_pak_file'):
                        pak_tab.load_pak_file(pak_file)
                    break
    
    def open_preferences(self):
        """Open preferences dialog"""
        try:
            settings_dialog = SettingsDialog(self, self.settings_manager)
            if settings_dialog.exec():
                # If settings were changed, offer to reinitialize
                reply = QMessageBox.question(
                    self, "Reinitialize Backend",
                    "Settings have been updated. Would you like to reinitialize the backend now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.reinitialize_backend()
        except Exception as e:
            QMessageBox.information(
                self, "Preferences", 
                f"Error opening preferences: {e}\n\n"
                "You can manually edit settings in your system preferences."
            )
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About MacPak",
            """
            <h3>MacPak</h3>
            <p>A native macOS application for modding Baldur's Gate 3.</p>
            
            <p><b>Status:</b> Connected - PAK Tools now functional</p>
            
            <p><b>Features:</b></p>
            <ul>
            <li>Extract and create PAK files</li>
            <li>Browse game assets</li>
            <li>Edit LSX files with syntax highlighting</li>
            <li>Validate mod structures</li>
            <li>Native Mac file dialogs and styling</li>
            </ul>
            
            <p>Built with PyQt6 and divine.exe via Wine.</p>
            """
        )