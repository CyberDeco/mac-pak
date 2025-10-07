from PyQt6.QtWidgets import QComboBox, QStyledItemDelegate, QStyle, QStyleOptionComboBox, QStylePainter
from PyQt6.QtCore import Qt, QEvent, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPalette, QColor, QBrush, QPainter, QPen, QPainterPath

class ComboBoxHoverDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # Apply custom hover colors for macOS
        if option.state & QStyle.StateFlag.State_MouseOver:
            option.backgroundBrush = QBrush(QColor("#f2f2f7"))
            # Remove the selection state so it doesn't override hover
            option.state &= ~QStyle.StateFlag.State_Selected
        elif option.state & QStyle.StateFlag.State_Selected:
            option.backgroundBrush = QBrush(QColor("#007aff"))
            option.palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
        
        super().paint(painter, option, index)

class CheckableComboBox(QComboBox):
    itemsChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModel(QStandardItemModel())
        self.setItemDelegate(ComboBoxHoverDelegate())
        
        # Install event filter on the view itself
        self.view().viewport().installEventFilter(self)
        
    def paintEvent(self, event):
        # Let the default painting happen first
        super().paintEvent(event)
        
        # Now draw custom arrow with background
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate arrow button area (right side of combobox)
        button_width = 20  # Width of the arrow button area
        button_margin = 4  # Margin from edges
        
        arrow_bg_rect = QRect(
            self.width() - button_width - button_margin,
            button_margin,
            button_width,
            self.height() - (button_margin * 2)
        )
        
        # Draw rounded button background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#2683fe")))
        painter.drawRoundedRect(arrow_bg_rect, 6, 6)
        
        # Calculate arrow position (centered in the button)
        arrow_width = 6
        arrow_height = 4
        arrow_x = (arrow_bg_rect.center().x() - arrow_width // 2) + 1
        arrow_y = (arrow_bg_rect.center().y() - arrow_height // 2) + 1
        
        # Draw white chevron arrow
        path = QPainterPath()
        path.moveTo(arrow_x, arrow_y)  # Left point
        path.lineTo(arrow_x + arrow_width / 2, arrow_y + arrow_height)  # Bottom point
        path.lineTo(arrow_x + arrow_width, arrow_y)  # Right point
        
        # Set pen for chevron line (no fill)
        painter.setPen(QPen(QColor("#ffffff"), 2))  # White line, 2px thick
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
    
    def eventFilter(self, obj, event):
        if obj == self.view().viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                index = self.view().indexAt(event.pos())
                if index.isValid():
                    item = self.model().itemFromIndex(index)
                    if item and item.isCheckable():
                        current_state = item.checkState()
                        new_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
                        
                        # Check if this is "All Files"
                        if item.text() == "All Files":
                            # Toggle all items to match "All Files"
                            item.setCheckState(new_state)
                            for i in range(self.model().rowCount()):
                                other_item = self.model().item(i)
                                if other_item and other_item != item:
                                    other_item.setCheckState(new_state)
                        else:
                            # Toggle the individual item
                            item.setCheckState(new_state)
                            
                            # If unchecking an item, uncheck "All Files" too
                            if new_state == Qt.CheckState.Unchecked:
                                all_files_item = self.model().item(0)  # Assuming "All Files" is first
                                if all_files_item and all_files_item.text() == "All Files":
                                    all_files_item.setCheckState(Qt.CheckState.Unchecked)
                            # If all other items are checked, check "All Files"
                            elif new_state == Qt.CheckState.Checked:
                                all_checked = True
                                for i in range(1, self.model().rowCount()):  # Skip first item (All Files)
                                    other_item = self.model().item(i)
                                    if other_item and other_item.checkState() == Qt.CheckState.Unchecked:
                                        all_checked = False
                                        break
                                if all_checked:
                                    all_files_item = self.model().item(0)
                                    if all_files_item and all_files_item.text() == "All Files":
                                        all_files_item.setCheckState(Qt.CheckState.Checked)
                        
                        self.itemsChanged.emit()
                        return True  # Event handled
        return super().eventFilter(obj, event)
        
    def add_item(self, text, extensions, checked=False):
        item = QStandardItem(text)
        item.setCheckable(True)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        item.setData(extensions, Qt.ItemDataRole.UserRole)
        self.model().appendRow(item)
    
    def get_checked_items(self):
        checked = {}
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == Qt.CheckState.Checked:
                extensions = item.data(Qt.ItemDataRole.UserRole)
                checked[item.text()] = extensions
        return checked