import os
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

# Database
DB_PATH = CONFIG_DIR / "bg3_file_index.db"

# Wine settings (if applicable)
WINE_PREFIX = os.getenv("WINE_PREFIX", "~/.wine")

class Settings:
    def __init__(self):
        self.db_path = DB_PATH
        self.wine_prefix = WINE_PREFIX
        # Add other settings as needed
