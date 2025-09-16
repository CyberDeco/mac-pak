#!/usr/bin/env python3
"""
mac-pak: BG3 Modding Toolkit for Mac
Entry point for the application.
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Don't create __pycache__ files
sys.dont_write_bytecode = True

if __name__ == "__main__":
    from mac_pak.launch import main
    main()