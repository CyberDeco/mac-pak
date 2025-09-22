#!/usr/bin/env python3
"""
Entry point for MacPak.
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import PyQt6.QtCore
from .version import *

def main():
    """Main application entry point"""
    print("Launching MacPak (PyQt6)...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    # Check for PyQt6
    try:
        print(f"Using PyQt6 version: {PyQt6.QtCore.PYQT_VERSION_STR}")
    except ImportError as e:
        print(f"Error: PyQt6 not found. Please install with: pip install PyQt6")
        print(f"Import error: {e}")
        sys.exit(1)
    
    # Set up environment for Mac
    if sys.platform == "darwin":
        os.environ["QT_MAC_WANTS_LAYER"] = "1"
    
    # Import and run the application
    try:
        # Create QApplication first
        app = QApplication(sys.argv)
        
        # Set application properties for Mac
        app.setApplicationName(get_version_info()['name'])
        app.setApplicationVersion(get_version_info()['build'])
        app.setOrganizationName(get_version_info()['author'])
        app.setOrganizationDomain(f"{get_version_info()['name']}.app")

        # Use native Mac file dialogs
        app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, False)

        # Fix stylesheet path for both development and bundled app
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            base_path = Path(sys._MEIPASS)
        else:
            # Running in development
            base_path = Path(__file__).parent
            print(base_path)
        
        style_path = base_path / "resources" / "styles" / "main.qss"
        
        # Load stylesheet if it exists
        if style_path.exists():
            with open(style_path, 'r') as f:
                qss = f.read()
            app.setStyleSheet(qss)
        else:
            print(f"Warning: Stylesheet not found at {style_path}")
        
        # Import the main window class
        from .ui.main_window import MacPakMainWindow
        
        # Create and show main window
        window = MacPakMainWindow()
        window.show()
        
        # Run the application
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"Error importing application components: {e}")
        print("Make sure all required files are in the correct package structure")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()