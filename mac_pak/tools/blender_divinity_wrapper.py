#!/usr/bin/env python3
"""
Divine.exe wrapper adapted for Wine-based execution on macOS
Replaces direct subprocess calls with WineWrapper integration

Adaptation of:
https://github.com/Norbyte/dos2de_collada_exporter/blob/master/io_scene_dos2de/divine.py
"""

from pathlib import Path
import bpy
from . import helpers

# Import wine wrapper utilities
try:
    from mac_pak.tools.wine_wrapper import get_wine_wrapper, is_wine_available
    WINE_AVAILABLE = True
except ImportError:
    WINE_AVAILABLE = False
    print("Warning: Wine wrapper not available")

class DivineInvoker:
    def __init__(self, addon_prefs, divine_prefs):
        self.addon_prefs = addon_prefs
        self.divine_prefs = divine_prefs
        self.wine_wrapper = None
        
        # Initialize wine wrapper if available
        if WINE_AVAILABLE:
            try:
                self.wine_wrapper = get_wine_wrapper()
                # Update lslib path in wine wrapper if set in prefs
                if self.addon_prefs.lslib_path:
                    self.wine_wrapper.lslib_path = self.addon_prefs.lslib_path
            except Exception as e:
                print(f"Warning: Failed to initialize wine wrapper: {e}")
                self.wine_wrapper = None

    def check_lslib(self):
        """Validate LSLib/Divine.exe path"""
        if self.addon_prefs.lslib_path is None or self.addon_prefs.lslib_path == "":
            helpers.report("LSLib path was not set up in addon preferences. Cannot convert to GR2.", "ERROR")
            return False
            
        lslib_path = Path(self.addon_prefs.lslib_path)
        
        # On macOS with Wine, check if path exists (might be Windows path format)
        if not lslib_path.is_file():
            # Try stripping Wine Z: prefix if present
            path_str = str(lslib_path)
            if path_str.startswith("Z:"):
                mac_path = path_str[2:].replace('\\', '/')
                if not Path(mac_path).is_file():
                    helpers.report("The LSLib path set in addon preferences is invalid. Cannot convert to GR2.", "ERROR")
                    return False
            else:
                helpers.report("The LSLib path set in addon preferences is invalid. Cannot convert to GR2.", "ERROR")
                return False
        
        # Check wine availability on macOS
        if WINE_AVAILABLE and not is_wine_available():
            helpers.report("Wine is not available. Cannot run Divine.exe on macOS.", "ERROR")
            return False
        
        return True

    def build_export_options(self):
        """Build export options string for divine.exe"""
        export_str = ""
        # Possible args:
        #"export-normals;export-tangents;export-uvs;export-colors;deduplicate-vertices;
        # deduplicate-uvs;recalculate-normals;recalculate-tangents;recalculate-iwt;flip-uvs;
        # force-legacy-version;compact-tris;build-dummy-skeleton;apply-basis-transforms;conform"

        divine_args = {
            "ignore_uv_nan" : "ignore-uv-nan",
            "x_flip_meshes": "x-flip-meshes",
            "mirror_skeletons": "mirror-skeletons"
        }

        gr2_args = {
            "yup_conversion" : "apply-basis-transforms",
            #"conform" : "conform"
        }

        for prop, arg in divine_args.items():
            val = getattr(self.divine_prefs, prop, False)
            if val == True:
                export_str += "-e " + arg + " "

        gr2_settings = self.divine_prefs.gr2_settings

        for prop, arg in gr2_args.items():
            val = getattr(gr2_settings, prop, False)
            if val == True:
                export_str += "-e " + arg + " "

        return export_str

    def build_import_options(self):
        """Build import options string for divine.exe"""
        args = ""
        divine_args = {
            "x_flip_meshes": "x-flip-meshes",
            "mirror_skeletons": "mirror-skeletons"
        }

        for prop, arg in divine_args.items():
            val = getattr(self.divine_prefs, prop, False)
            if val == True:
                args += "-e " + arg + " "

        return args
    
    def invoke_lslib(self, args_list):
        """
        Invoke LSLib through Wine wrapper instead of direct subprocess
        
        Args:
            args_list: List of arguments for divine.exe (already parsed)
        """
        print("[DOS2DE-Collada] Starting GR2 conversion using divine.exe via Wine.")
        print(f"[DOS2DE-Collada] Sending command: {' '.join(args_list)}")

        if not self.wine_wrapper:
            helpers.report("Wine wrapper not initialized. Cannot run Divine.exe on macOS.", "ERROR")
            return False

        try:
            # Use wine wrapper's run_lslib_command
            from mac_pak.tools.wine_wrapper import run_lslib_command
            
            result = run_lslib_command(
                lslib_path=self.wine_wrapper.lslib_path,
                args=args_list,
                timeout=300,
                settings_manager=self.wine_wrapper.settings_manager
            )
            
            # Process results
            stdout = result.stdout if result.stdout else ""
            stderr = result.stderr if result.stderr else ""
            
            print("STDERR: ", stderr)
            print("STDOUT: ", stdout)

            err = stderr
            if len(err):
                err += '\n'
            err += '\n'.join(stdout.splitlines()[-1:])
            
            if result.returncode != 0 or stdout.startswith('[FATAL] '):
                if stdout.startswith('[FATAL] Value glb is not allowed'):
                    error_message = "LSLib v1.20 or later is required for glTF support"
                else:
                    error_message = "Failed to convert GR2 (see the message log for more details). " + err
                helpers.report(error_message, "ERROR")
                return False
            else:
                return True
                
        except Exception as e:
            helpers.report(f"Failed to launch lslib via Wine: {str(e)}", "ERROR")
            return False

    def _convert_path_to_wine(self, path):
        """Convert macOS path to Wine path format if using wine wrapper"""
        if self.wine_wrapper:
            return self.wine_wrapper.mac_to_wine_path(str(path))
        return str(path)

    def export_gr2(self, collada_path, gr2_path, format):
        """Export COLLADA to GR2 format using Wine"""
        if not self.check_lslib():
            return False
        
        gr2_options_str = self.build_export_options()
        game_ver = bpy.context.scene.ls_properties.game
        
        # Convert paths to Wine format
        wine_collada = self._convert_path_to_wine(collada_path)
        wine_gr2 = self._convert_path_to_wine(gr2_path)
        
        # Build argument list (no shell quoting needed)
        args_list = [
            "--loglevel", "all",
            "-g", game_ver,
            "-s", wine_collada,
            "-d", wine_gr2,
            "-i", format,
            "-o", "gr2",
            "-a", "convert-model"
        ]
        
        # Add export options
        if gr2_options_str.strip():
            for opt in gr2_options_str.strip().split():
                args_list.append(opt)
        
        return self.invoke_lslib(args_list)

    def import_gr2(self, gr2_path, collada_path, format):
        """Import GR2 to COLLADA format using Wine"""
        if not self.check_lslib():
            return False
        
        gr2_options_str = self.build_import_options()
        
        # Convert paths to Wine format
        wine_gr2 = self._convert_path_to_wine(gr2_path)
        wine_collada = self._convert_path_to_wine(collada_path)
        
        # Build argument list
        args_list = [
            "--loglevel", "all",
            "-g", "bg3",
            "-s", wine_gr2,
            "-d", wine_collada,
            "-i", "gr2",
            "-o", format,
            "-a", "convert-model",
            "-e", "flip-uvs"
        ]
        
        # Add import options
        if gr2_options_str.strip():
            for opt in gr2_options_str.strip().split():
                args_list.append(opt)
        
        return self.invoke_lslib(args_list)