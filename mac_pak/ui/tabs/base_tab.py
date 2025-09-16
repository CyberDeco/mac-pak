from PyQt6.QtWidgets import QWidget

class BaseTab(QWidget):
    def __init__(self, parent=None, wine_wrapper=None, settings_manager=None):
        super().__init__(parent)
        self.wine_wrapper = wine_wrapper
        self.settings_manager = settings_manager