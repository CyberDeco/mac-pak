#!/usr/bin/env python3
"""
Entry point for BG3 Toolkit.
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import PyQt6.QtCore

def main():
    """Main application entry point"""
    print("Launching BG3 Mac Modding Toolkit (PyQt6)...")
    
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
        # Set Mac-specific environment variables
        os.environ["QT_MAC_WANTS_LAYER"] = "1"
    
    # Import and run the application
    try:
        # Create QApplication first
        app = QApplication(sys.argv)
        
        # Set application properties for Mac
        app.setApplicationName("BG3 Mac Modding Toolkit")
        app.setApplicationVersion("0.0")
        app.setOrganizationName("BG3ModToolkit")
        app.setOrganizationDomain("bg3modtoolkit.app")

        # Use native Mac file dialogs
        app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, False)
        
        # Import the main window class (using relative import since this is in the package)
        from .ui.main_window import BG3ModToolkitMainWindow
        
        # Create and show main window
        window = BG3ModToolkitMainWindow()
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