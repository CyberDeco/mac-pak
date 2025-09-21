from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
import webbrowser

class UpdateDialog(QDialog):
    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.setWindowTitle("Update Available")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Version info
        version_label = QLabel(
            f"A new version of MacPak is available!\n\n"
            f"Current version: {self.update_info['current_version']}\n"
            f"Latest version: {self.update_info['latest_version']}"
        )
        layout.addWidget(version_label)
        
        # Release notes
        notes_label = QLabel("Release Notes:")
        layout.addWidget(notes_label)
        
        notes_text = QTextEdit()
        notes_text.setPlainText(self.update_info.get('release_notes', 'No release notes available.'))
        notes_text.setMaximumHeight(200)
        notes_text.setReadOnly(True)
        layout.addWidget(notes_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        skip_btn = QPushButton("Skip This Version")
        skip_btn.clicked.connect(self.skip_version)
        button_layout.addWidget(skip_btn)
        
        later_btn = QPushButton("Remind Me Later")
        later_btn.clicked.connect(self.remind_later)
        button_layout.addWidget(later_btn)
        
        download_btn = QPushButton("Download Update")
        download_btn.setDefault(True)
        download_btn.clicked.connect(self.download_update)
        button_layout.addWidget(download_btn)
        
        layout.addLayout(button_layout)
    
    def skip_version(self):
        # Save skipped version to settings
        from ...core.settings import SettingsManager
        settings = SettingsManager()
        settings.set("skipped_version", self.update_info['latest_version'])
        settings.sync()
        self.reject()
    
    def remind_later(self):
        self.reject()
    
    def download_update(self):
        download_url = self.update_info.get('download_url')
        if download_url:
            QDesktopServices.openUrl(QUrl(download_url))
        else:
            # Fallback to releases page
            repo_url = f"https://github.com/{self.update_info.get('github_repo', '')}/releases"
            QDesktopServices.openUrl(QUrl(repo_url))
        self.accept()