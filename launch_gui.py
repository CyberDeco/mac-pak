from toolkit_gui import BG3ModToolkitGUI
#from lslib_divine import BG3MacTool


# In your main() function, after the CLI demo:
if __name__ == "__main__":
    
    # Then launch GUI
    print("\nLaunching GUI...")
    wine_path = "/opt/homebrew/bin/wine"
    divine_exe = "Z:/Users/corrine/Desktop/code/repos/bg3/lslib/ExportTool/Packed/Tools/Divine.exe"  
    gui = BG3ModToolkitGUI(wine_path=wine_path, divine_path=divine_exe)
    gui.run()