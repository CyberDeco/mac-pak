


# from ...tools.blender import BlenderIntegration


# def run_blender_operation(self, script_path, args):
#     cmd = ["blender", "--background", "--python", script_path] + args
#     result = subprocess.run(cmd, capture_output=True, text=True)
#     return result.returncode == 0, result.stdout, result.stderr

class BlenderTab(QWidget):
    """Asset Browser tab for the main application"""
    
    def __init__(self, parent, settings_manager, wine_wrapper):
        super().__init__(parent)
        
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager
        self.parser = UniversalBG3Parser()
        
        if wine_wrapper:
            self.parser.set_wine_wrapper(wine_wrapper)
        
        # Initialize preview system
        self.preview_manager = FilePreviewManager(wine_wrapper, self.parser)
        
        self.current_directory = None
        self.setup_ui()
        
        # Load initial directory if available
        if settings_manager:
            working_dir = settings_manager.get("working_directory")
            if working_dir and os.path.exists(working_dir):
                self.current_directory = working_dir
                self.refresh_view()