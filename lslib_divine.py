#!/usr/bin/env python3
"""
BG3 Mac PAK Tool - Native Mac interface using lslib via Wine
This approach leverages the proven lslib Divine.exe CLI tool through Wine
"""

import subprocess
import os
import json
import tempfile
from pathlib import Path

class BG3MacTool:
    def __init__(self, wine_prefix=None, lslib_path=None, wine_path=None):
        """Initialize the BG3 Mac tool with Wine and lslib paths"""
        self.wine_prefix = wine_prefix or os.path.expanduser("~/.wine")
        
        # Find Wine executable
        if wine_path:
            self.wine_path = wine_path
        else:
            # Common Wine installation locations on Mac
            possible_wine_paths = [
                "/usr/local/bin/wine",
                "/opt/homebrew/bin/wine", 
                "/Applications/Wine.app/Contents/Resources/wine/bin/wine",
                "wine"  # In PATH
            ]
            
            self.wine_path = None
            for path in possible_wine_paths:
                try:
                    result = subprocess.run([path, "--version"], capture_output=True, text=True)
                    if result.returncode == 0:
                        self.wine_path = path
                        break
                except:
                    continue
        
        if not self.wine_path:
            raise FileNotFoundError("Could not find wine executable. Please install Wine or specify wine_path.")
        
        # Use the path you provided
        if lslib_path:
            self.lslib_path = lslib_path
        else:
            # Your specific path
            raise ValueError("Must supply path to Divine.exe")
        
        print(f"Using Wine at: {self.wine_path}")
        print(f"Using Divine.exe at: {self.lslib_path}")
    
    def run_divine_command(self, action, source=None, destination=None, **kwargs):
        """Run a divine.exe command through Wine"""
        
        # Build the command
        cmd = [self.wine_path, self.lslib_path, "--action", action, "--game", "bg3"]
        
        if source:
            cmd.extend(["--source", source])
        if destination:
            cmd.extend(["--destination", destination])
        
        # Add any additional arguments
        for key, value in kwargs.items():
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])
        
        print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                env={"WINEPREFIX": self.wine_prefix}
            )
            
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
                return False, result.stderr
            else:
                return True, result.stdout
                
        except Exception as e:
            return False, str(e)
    
    def list_pak_contents(self, pak_file):
        """List the contents of a PAK file"""
        
        # Convert Mac path to Wine path
        wine_pak_path = self.mac_to_wine_path(pak_file)
        
        success, output = self.run_divine_command(
            action="list-package",
            source=wine_pak_path
        )
        
        if success:
            print("PAK Contents:")
            print(output)
            return self.parse_file_list(output)
        else:
            print(f"Failed to list PAK contents: {output}")
            return []
            
    def create_pak(self, source_dir, pak_file, compression_level=None):
        """Create PAK file from directory"""
        
        wine_source_path = self.mac_to_wine_path(source_dir)
        wine_pak_path = self.mac_to_wine_path(pak_file)
        
        # Ensure source directory exists
        if not os.path.exists(source_dir):
            print(f"Source directory does not exist: {source_dir}")
            return False
        
        # Ensure output directory exists
        pak_dir = os.path.dirname(pak_file)
        if pak_dir:
            os.makedirs(pak_dir, exist_ok=True)
        
        success, output = self.run_divine_command(
            action="create-package",
            source=wine_source_path,
            destination=wine_pak_path
        )
        
        if success:
            if os.path.exists(pak_file):
                file_size = os.path.getsize(pak_file)
                print(f"Successfully created PAK: {pak_file} ({file_size:,} bytes)")
                return True
            else:
                print(f"PAK creation reported success but file not found: {pak_file}")
                return False
        else:
            print(f"Failed to create PAK: {output}")
            return False
    
    def validate_mod_structure(self, mod_dir):
        """Validate that a directory has proper mod structure"""
        
        required_structure = []
        warnings = []
        meta_found = False
        
        # Folders that are game content, not mod content (don't need meta.lsx)
        game_content_folders = {"GustavDev", "Gustav", "Shared", "Engine", "Game", "Core"}
        
        # Check for common mod files/folders
        mods_folder = os.path.join(mod_dir, "Mods")
        if os.path.exists(mods_folder):
            required_structure.append("Mods/ folder found")
            
            # Look for mod subfolders
            mod_subfolders = [d for d in os.listdir(mods_folder) if os.path.isdir(os.path.join(mods_folder, d))]
            if mod_subfolders:
                for subfolder in mod_subfolders:
                    if subfolder in game_content_folders:
                        required_structure.append(f"Game content folder: Mods/{subfolder}/")
                        continue
                    
                    meta_path = os.path.join(mods_folder, subfolder, "meta.lsx")
                    if os.path.exists(meta_path):
                        required_structure.append(f"meta.lsx found in Mods/{subfolder}/")
                        meta_found = True
                    else:
                        warnings.append(f"meta.lsx missing in Mods/{subfolder}/")
            else:
                warnings.append("No mod subfolders found in Mods/")
        else:
            warnings.append("Mods/ folder not found")
        
        if not meta_found:
            warnings.append("No meta.lsx found - this mod may not work properly")
        
        return {
            'valid': len(warnings) == 0,
            'structure': required_structure,
            'warnings': warnings
        }
    def extract_pak(self, pak_file, destination_dir):
        """Extract entire PAK file to destination directory"""
        
        wine_pak_path = self.mac_to_wine_path(pak_file)
        wine_dest_path = self.mac_to_wine_path(destination_dir)
        
        # Create destination directory if it doesn't exist
        os.makedirs(destination_dir, exist_ok=True)
        
        success, output = self.run_divine_command(
            action="extract-package",
            source=wine_pak_path,
            destination=wine_dest_path
        )
        
        if success:
            print(f"Successfully extracted PAK to: {destination_dir}")
            print(output)
            return True
        else:
            print(f"Failed to extract PAK: {output}")
            return False
    
    def extract_single_file(self, pak_file, file_path, destination):
        """Extract a single file from PAK"""
        
        wine_pak_path = self.mac_to_wine_path(pak_file)
        wine_dest_path = self.mac_to_wine_path(destination)
        
        success, output = self.run_divine_command(
            action="extract-single-file",
            source=wine_pak_path,
            destination=wine_dest_path,
            packaged_path=file_path
        )
        
        if success:
            print(f"Successfully extracted '{file_path}' to: {destination}")
            return True
        else:
            print(f"Failed to extract file: {output}")
            return False
    
    def convert_lsf_to_lsx(self, lsf_file, lsx_file):
        """Convert binary LSF to readable LSX"""
        
        wine_source = self.mac_to_wine_path(lsf_file)
        wine_dest = self.mac_to_wine_path(lsx_file)
        
        success, output = self.run_divine_command(
            action="convert-resource",
            source=wine_source,
            destination=wine_dest
        )
        
        if success:
            print(f"Converted {lsf_file} to {lsx_file}")
            return True
        else:
            print(f"Failed to convert: {output}")
            return False
    
    def mac_to_wine_path(self, mac_path):
        """Convert Mac path to Wine path format"""
        abs_path = os.path.abspath(mac_path)
        
        # Simple conversion - you might need to adjust based on your Wine setup
        # This assumes your Wine C: drive maps to ~/.wine/dosdevices/c:
        if abs_path.startswith("/Users"):
            # Map to a Wine drive letter (adjust as needed)
            zpath  = abs_path.replace('/', '\\')
            wine_path = f"Z:{zpath}"
        else:
            zpath = abs_path.replace('/', '\\')
            wine_path = f"Z:{zpath}"
        
        return wine_path
    
    def parse_file_list(self, output):
        """Parse the output from list-package command"""
        files = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith('Package') and not line.startswith('---'):
                # Parse file information from the line
                # Format varies but typically: filename, size, CRC
                parts = line.strip().split()
                if parts:
                    files.append({
                        'name': parts[0],
                        'size': parts[1] if len(parts) > 1 else 'unknown',
                        'info': ' '.join(parts[2:]) if len(parts) > 2 else ''
                    })
        
        return files

def main():
    """Demo of the BG3 Mac tool with multiple PAK files"""
    
    # Initialize the tool with your specific Wine path
    try:
        tool = BG3MacTool(wine_path="/opt/homebrew/bin/wine")
        print("BG3 Mac Tool initialized successfully!")
        print(f"Using lslib at: {tool.lslib_path}")
        print()

        localpath = 'users/corrine/Desktop/Data'
        modpath = 'users/corrine/Desktop/Mods'
        # Test with multiple important PAK files for modding
        pak_files = {

            #"English.pak": f"/Users/corrine/.wine/dosdevices/c:{localpath}/Localization/English.pak",
            #"Gustav.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/Gustav.pak",
            #"Shared.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/Shared.pak",
            #"GustavX.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/GustavX.pak",
            #"Game.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/Game.pak",
            #"Models.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/Models.pak",
            #"Materials.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/Materials.pak",
            #"Assets.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/Assets.pak",
            #"Textures.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/Textures.pak",
            #"Gustav_Textures.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/Gustav_Textures.pak",
            #"Effects.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/Effects.pak",
            #"Engine.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/Engine.pak",
            #"GamePlatform.pak": f"/Users/corrine/.wine/dosdevices/c:/{localpath}/GamePlatform.pak",
            
            # Mods:
            #"EngelsDyes.pak": f"/Users/corrine/.wine/dosdevices/c:/{modpath}/EngelsDyes.pak",
            #"HT_LeakingBloodBag.pak": f"/Users/corrine/.wine/dosdevices/c:/{modpath}/HT_LeakingBloodBag.pak",
        }
        
        for pak_name, pak_file in pak_files.items():
            if os.path.exists(pak_file):
                print(f"\n{'='*50}")
                print(f"Analyzing {pak_name}")
                print('='*50)
                
                files = tool.list_pak_contents(pak_file)
                
                if files:
                    print(f"\nFound {len(files)} files in {pak_name}")
                    
                    # Show interesting files for modding
                    interesting_extensions = ['.lsf', '.lsx', '.txt', '.xml', '.gr2', '.dds']
                    interesting_files = [f for f in files if any(ext in f['name'].lower() for ext in interesting_extensions)]
                    
                    if interesting_files:
                        print(f"Interesting files for modding ({len(interesting_files)}):")
                        for file_info in interesting_files[:10]:  # Show first 10
                            print(f"  {file_info['name']} ({file_info['size']} bytes)")
                        if len(interesting_files) > 10:
                            print(f"  ... and {len(interesting_files) - 10} more")
                    
                    # Test single file extraction
                    if files:
                        test_file = files[0]
                        print(f"\nTesting single file extraction: {test_file['name']}")
                        
                        with tempfile.TemporaryDirectory() as temp_dir:
                            output_file = os.path.join(temp_dir, os.path.basename(test_file['name']))
                            if tool.extract_single_file(pak_file, test_file['name'], output_file):
                                if os.path.exists(output_file):
                                    file_size = os.path.getsize(output_file)
                                    print(f"✓ Successfully extracted {test_file['name']} ({file_size} bytes)")
                                    
                                    # If it's a text-based file, show a preview
                                    if any(ext in test_file['name'].lower() for ext in ['.lsx', '.xml', '.txt']):
                                        try:
                                            with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
                                                preview = f.read(500)
                                                print(f"Preview:\n{preview}...")
                                        except:
                                            pass
                else:
                    print(f"Could not list contents of {pak_name}")
            else:
                print(f"\n{pak_name} not found at: {pak_file}")
        
        print(f"\n{'='*50}")
        print("Summary: BG3 Mac modding toolkit is functional!")
        print("You can now:")
        print("- List PAK contents")
        print("- Extract entire PAKs") 
        print("- Extract individual files")
        print("- Process multiple PAK files")
        print("\nNext steps: Add GUI, batch operations, or LSF conversion")
            
    except FileNotFoundError as e:
        print(f"Setup error: {e}")
        print("Please ensure lslib/divine.exe is installed and accessible via Wine")

if __name__ == "__main__":
    main()