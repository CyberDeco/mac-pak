#!/usr/bin/env python3
"""
ZIP and Metadata Generator for BG3 Mods
Automatically generates distributable ZIP files with proper metadata
"""

import os
import json
import zipfile
import uuid
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QTextEdit, QPushButton, QLabel, QFileDialog,
    QGroupBox, QCheckBox, QMessageBox
)

# Import custom progress dialog
from ...ui.dialogs.progress_dialog import ProgressDialog


class ModMetadataGenerator:
    """Generates metadata files for BG3 mods"""
    
    def __init__(self):
        self.metadata_template = {
            "Mods": [
                {
                    "Author": "",
                    "Name": "",
                    "Folder": "",
                    "Version": "",
                    "Description": "",
                    "UUID": "",
                    "Created": "",
                    "Dependencies": [],
                    "Group": ""
                }
            ]
        }
    
    def generate_mod_metadata(self, mod_info):
        """Generate metadata JSON for mod"""
        metadata = self.metadata_template.copy()
        
        mod_entry = {
            "Author": mod_info.get("author", "Unknown"),
            "Name": mod_info.get("name", "Untitled Mod"),
            "Folder": mod_info.get("folder", mod_info.get("name", "UntitledMod")),
            "Version": mod_info.get("version", "1.0.0"),
            "Description": mod_info.get("description", ""),
            "UUID": mod_info.get("uuid", str(uuid.uuid4())),
            "Created": mod_info.get("created", datetime.now().isoformat()),
            "Dependencies": mod_info.get("dependencies", []),
            "Group": mod_info.get("group", str(uuid.uuid4()))
        }
        
        metadata["Mods"][0] = mod_entry
        return metadata
    
    def extract_mod_info_from_pak(self, pak_file, wine_wrapper=None):
        """Extract mod information from PAK filename and structure"""
        pak_name = Path(pak_file).stem
        
        mod_info = {
            "name": pak_name,
            "folder": pak_name,
            "version": "1.0.0",
            "author": "Unknown",
            "description": f"BG3 mod: {pak_name}",
            "uuid": str(uuid.uuid4()),
            "created": datetime.now().isoformat(),
            "dependencies": [],
            "group": str(uuid.uuid4())
        }
        
        return mod_info
    
    def _generate_modsettings_lsx(self, mod_info):
        """Generate basic modsettings.lsx file"""
        template = f'''<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="0" revision="9" build="331"/>
    <region id="ModuleSettings">
        <node id="root">
            <children>
                <node id="ModOrder">
                    <children>
                        <node id="Module">
                            <attribute id="UUID" type="FixedString" value="{mod_info['uuid']}"/>
                        </node>
                    </children>
                </node>
                <node id="Mods">
                    <children>
                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="{mod_info['folder']}"/>
                            <attribute id="MD5" type="LSString" value=""/>
                            <attribute id="Name" type="LSString" value="{mod_info['name']}"/>
                            <attribute id="UUID" type="FixedString" value="{mod_info['uuid']}"/>
                            <attribute id="Version64" type="int64" value="36028797018963968"/>
                        </node>
                    </children>
                </node>
            </children>
        </node>
    </region>
</save>'''
        return template


class ZipGeneratorThread(QThread):
    """Thread for generating ZIP files with metadata"""
    
    progress_updated = pyqtSignal(int, str)
    zip_completed = pyqtSignal(bool, dict)
    
    def __init__(self, pak_file, output_dir, mod_info=None, wine_wrapper=None):
        super().__init__()
        self.pak_file = pak_file
        self.output_dir = output_dir
        self.mod_info = mod_info
        self.wine_wrapper = wine_wrapper
        self.metadata_generator = ModMetadataGenerator()
    
    def run(self):
        """Generate ZIP file with PAK and metadata"""
        try:
            self.progress_updated.emit(10, "Analyzing PAK file...")
            
            # Extract or use provided mod info
            if not self.mod_info:
                self.mod_info = self.metadata_generator.extract_mod_info_from_pak(
                    self.pak_file, self.wine_wrapper
                )
            
            self.progress_updated.emit(30, "Generating metadata...")
            
            # Generate metadata
            metadata = self.metadata_generator.generate_mod_metadata(self.mod_info)
            
            # Create output ZIP filename
            mod_name = self.mod_info.get("name", Path(self.pak_file).stem)
            version = self.mod_info.get("version", "1.0.0")
            zip_filename = f"{mod_name}_v{version}.zip"
            zip_path = os.path.join(self.output_dir, zip_filename)
            
            self.progress_updated.emit(50, "Creating ZIP file...")
            
            # Create ZIP file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add PAK file
                pak_filename = Path(self.pak_file).name
                zipf.write(self.pak_file, pak_filename)
                
                self.progress_updated.emit(70, "Adding metadata...")
                
                # Add metadata.json
                metadata_json = json.dumps(metadata, indent=2)
                zipf.writestr("metadata.json", metadata_json)
                
                # Add modsettings.lsx if we have enough info
                if self.mod_info.get("uuid"):
                    modsettings = self.metadata_generator._generate_modsettings_lsx(self.mod_info)
                    zipf.writestr("modsettings.lsx", modsettings)
                
                self.progress_updated.emit(90, "Finalizing...")
            
            result = {
                "zip_path": zip_path,
                "pak_file": pak_filename,
                "metadata": metadata,
                "size": os.path.getsize(zip_path)
            }
            
            self.progress_updated.emit(100, "ZIP generation complete!")
            self.zip_completed.emit(True, result)
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "pak_file": self.pak_file
            }
            self.zip_completed.emit(False, error_result)


class ZipMetadataWidget:
    """Widget for ZIP generation with metadata input"""
    
    def __init__(self, parent, wine_wrapper, settings_manager):
        self.parent = parent
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.zip_thread = None
        self.progress_dialog = None
    
    def show_zip_dialog(self, pak_file):
        """Show dialog for ZIP generation with metadata input"""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Generate Distributable ZIP")
        dialog.setModal(True)
        dialog.resize(500, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Mod info section
        info_group = QGroupBox("Mod Information")
        info_layout = QFormLayout(info_group)
        
        # Extract basic info from PAK filename
        pak_name = Path(pak_file).stem
        
        name_edit = QLineEdit(pak_name)
        info_layout.addRow("Mod Name:", name_edit)
        
        version_edit = QLineEdit("1.0.0")
        info_layout.addRow("Version:", version_edit)
        
        author_edit = QLineEdit()
        info_layout.addRow("Author:", author_edit)
        
        folder_edit = QLineEdit(pak_name)
        info_layout.addRow("Folder Name:", folder_edit)
        
        desc_edit = QTextEdit()
        desc_edit.setMaximumHeight(100)
        desc_edit.setPlainText(f"BG3 mod: {pak_name}")
        info_layout.addRow("Description:", desc_edit)
        
        layout.addWidget(info_group)
        
        # Options section
        options_group = QGroupBox("ZIP Options")
        options_layout = QFormLayout(options_group)
        
        include_modsettings = QCheckBox()
        include_modsettings.setChecked(True)
        options_layout.addRow("Include modsettings.lsx:", include_modsettings)
        
        include_readme = QCheckBox()
        include_readme.setChecked(True)
        options_layout.addRow("Generate README.txt:", include_readme)
        
        layout.addWidget(options_group)
        
        # Output section
        output_group = QGroupBox("Output Location")
        output_layout = QHBoxLayout(output_group)
        
        output_edit = QLineEdit(self.settings_manager.get("working_directory", ""))
        output_layout.addWidget(output_edit)
        
        browse_btn = QPushButton("Browse...")
        def browse_output():
            directory = QFileDialog.getExistingDirectory(
                dialog, "Select Output Directory", output_edit.text()
            )
            if directory:
                output_edit.setText(directory)
        
        browse_btn.clicked.connect(browse_output)
        output_layout.addWidget(browse_btn)
        
        layout.addWidget(output_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        generate_btn = QPushButton("Generate ZIP")
        generate_btn.setDefault(True)
        
        def start_generation():
            mod_info = {
                "name": name_edit.text() or pak_name,
                "version": version_edit.text() or "1.0.0", 
                "author": author_edit.text() or "Unknown",
                "folder": folder_edit.text() or pak_name,
                "description": desc_edit.toPlainText(),
                "uuid": str(uuid.uuid4()),
                "created": datetime.now().isoformat(),
                "dependencies": [],
                "group": str(uuid.uuid4())
            }
            
            output_dir = output_edit.text()
            if not output_dir or not os.path.exists(output_dir):
                QMessageBox.warning(dialog, "Error", "Please select a valid output directory.")
                return
            
            self._start_zip_generation(pak_file, output_dir, mod_info, dialog)
        
        generate_btn.clicked.connect(start_generation)
        button_layout.addWidget(generate_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _start_zip_generation(self, pak_file, output_dir, mod_info, parent_dialog):
        """Start ZIP generation in background thread - STANDARDIZED with custom ProgressDialog"""
        
        # Create CUSTOM progress dialog (not QProgressDialog!)
        self.progress_dialog = ProgressDialog(
            parent_dialog,
            message="Generating ZIP file...",
            cancel_text="Cancel",
            min_val=0,
            max_val=100
        )
        
        # Set file info
        self.progress_dialog.set_file_info(pak_file)
        
        # Connect cancellation
        self.progress_dialog.canceled.connect(self._cancel_zip_generation)
        
        # Show dialog
        self.progress_dialog.show()
        
        # Start generation thread
        self.zip_thread = ZipGeneratorThread(pak_file, output_dir, mod_info, self.wine_wrapper)
        
        # Connect signals - using update_progress() method
        self.zip_thread.progress_updated.connect(self.progress_dialog.update_progress)
        self.zip_thread.zip_completed.connect(
            lambda success, result: self._on_zip_completed(success, result, parent_dialog)
        )
        
        self.zip_thread.start()
    
    def _on_zip_completed(self, success, result, parent_dialog):
        """Handle ZIP generation completion"""
        # Disconnect signals first
        if self.progress_dialog:
            try:
                self.progress_dialog.canceled.disconnect(self._cancel_zip_generation)
            except TypeError:
                pass
        
        if self.zip_thread:
            try:
                self.zip_thread.progress_updated.disconnect(self.progress_dialog.update_progress)
            except TypeError:
                pass
        
        # Close progress dialog
        if self.progress_dialog:
            try:
                self.progress_dialog.close()
            except RuntimeError:
                pass
            finally:
                self.progress_dialog = None
        
        # Show results
        if success:
            zip_path = result["zip_path"]
            size_mb = result["size"] / (1024 * 1024)
            
            msg = QMessageBox(parent_dialog)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("ZIP Generated Successfully")
            msg.setText(f"Mod ZIP file created successfully!")
            msg.setInformativeText(
                f"File: {Path(zip_path).name}\n"
                f"Size: {size_mb:.1f} MB\n"
                f"Location: {zip_path}"
            )
            msg.exec()
            
            parent_dialog.accept()
        else:
            error = result.get("error", "Unknown error")
            QMessageBox.critical(parent_dialog, "ZIP Generation Failed", f"Failed to generate ZIP:\n{error}")
        
        # Cleanup thread
        if self.zip_thread:
            self.zip_thread.deleteLater()
            self.zip_thread = None
    
    def _cancel_zip_generation(self):
        """Cancel ZIP generation"""
        if self.zip_thread and self.zip_thread.isRunning():
            self.zip_thread.terminate()
            self.zip_thread.wait()
        
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None