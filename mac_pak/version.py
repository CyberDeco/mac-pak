# mac_pak/version.py
__version__ = "0.1.0"
__build__ = "2025.09.21"
__author__ = "CyberDeco"
__name__ = "MacPak"

def get_version_info():
    return {
        "version": __version__,
        "build": __build__,
        "github_repo": f"{__author__}/mac-pak",
        "version": __version__,
        "name": __name__,
        "author": __author__,
    }