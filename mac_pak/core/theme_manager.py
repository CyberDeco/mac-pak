#!/usr/bin/env python3
"""
Theme manager 
"""

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTextEdit, 
    QTreeWidget, QTabWidget, QTabBar, QGroupBox, QPushButton
    )

from PyQt6.QtGui import QIcon, QFont, QAction

def apply_button_styles(self):
    """Apply consistent button styling across the application"""
    button_style = """
    QPushButton {
        padding: 8px 16px;
        border-radius: 6px;
        border: 1px solid #ccc;
        background: white;
        min-height: 20px;
    }
    QPushButton:hover {
        background: #f0f0f0;
        border-color: #999;
    }
    QPushButton:pressed {
        background: #e0e0e0;
    }
    QPushButton:disabled {
        background: #f5f5f5;
        color: #999;
    }
    """
    self.setStyleSheet(button_style)

class ThemeManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
    
    def setup_theme_toggle(self):
        """Add theme switching capability"""
        # Add to the View menu (or create it if it doesn't exist)
        view_menu = None
        for action in self.menuBar().actions():
            if action.text() == "View":
                view_menu = action.menu()
                break
        
        if not view_menu:
            view_menu = self.menuBar().addMenu("View")
        
        self.dark_mode_action = QAction("Dark Mode", self)
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(self.dark_mode_action)
        
        # Load saved theme preference
        is_dark = self.settings_manager.get("dark_mode", False)
        self.dark_mode_action.setChecked(is_dark)
        if is_dark:
            self.apply_dark_theme()
    
    def toggle_dark_mode(self, checked):
        """Toggle between light and dark themes"""
        if checked:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
        
        # Save preference
        self.settings_manager.set("dark_mode", checked)
    
    def apply_dark_theme(self):
        """Apply dark theme stylesheet"""
        dark_style = """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QTextEdit {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #555;
        }
        QTreeWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #555;
        }
        QTabWidget::pane {
            background-color: #2b2b2b;
            border: 1px solid #555;
        }
        QTabBar::tab {
            background-color: #3c3c3c;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #007AFF;
        }
        QGroupBox {
            color: #ffffff;
            border: 1px solid #555;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            color: #ffffff;
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555;
            padding: 8px 16px;
            border-radius: 6px;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
            border-color: #777;
        }
        QPushButton:pressed {
            background-color: #2a2a2a;
        }
        """
        self.setStyleSheet(dark_style)
    
    def apply_light_theme(self):
        """Apply light theme (system default)"""
        self.setStyleSheet("")  # Reset to system theme