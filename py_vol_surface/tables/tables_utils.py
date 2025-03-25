from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt


class CustomDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if option.state & QtWidgets.QStyle.State_Selected:
            # Retrieve the item's foreground color
            color_brush = index.data(QtCore.Qt.ForegroundRole)
            if color_brush is not None:
                color = color_brush.color()
                option.palette.setColor(QtGui.QPalette.HighlightedText, color)


class OptionMetricCellItem(QtWidgets.QTableWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlags(self.flags() | Qt.ItemIsSelectable)
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)
        self.setBackground(QtGui.QBrush("black"))
        self.setForeground(QtGui.QBrush(QtGui.QColor("#fb8b1e")))
        self.setTextAlignment(Qt.AlignRight)
        font = QtGui.QFont("Neue Haas Grotesk", 12)
        self.setFont(font)
        
        
class BlankCellItem(QtWidgets.QTableWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlags(self.flags() & ~Qt.ItemIsSelectable)
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)
        self.setBackground(QtGui.QBrush("grey"))
        self.setForeground(QtGui.QBrush(QtGui.QColor("#fb8b1e")))
        self.setTextAlignment(Qt.AlignRight)


class OptionNameCellItem(QtWidgets.QTableWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlags(self.flags() |  Qt.ItemIsEnabled)
        self.setBackground(QtGui.QBrush("black"))
        self.setForeground(QtGui.QBrush(QtGui.QColor("#fb8b1e")))
        self.setTextAlignment(Qt.AlignLeft)
        self.setFlags(self.flags() | Qt.ItemIsSelectable)
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)
        font = QtGui.QFont("Neue Haas Grotesk", 12)
        self.setFont(font)

        
class OptionExpiryCellItem(QtWidgets.QTableWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.setBackground(QtGui.QBrush("grey"))
        self.setForeground(QtGui.QBrush(QtGui.QColor("white")))
        self.setTextAlignment(Qt.AlignLeft)
        font = QtGui.QFont("Neue Haas Grotesk", 12)
        self.setFont(font)

    
class TableColumnItem(QtWidgets.QTableWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlags(self.flags() | Qt.ItemIsEnabled)
        self.setBackground(QtGui.QBrush(QtGui.QColor("#414141")))
        self.setForeground(QtGui.QBrush("white"))
        self.setTextAlignment(Qt.AlignCenter)
        font = QtGui.QFont("Neue Haas Grotesk", 14)
        font.setBold(True)
        self.setFont(font) 
        
def get_style_sheets():
    
    QLabel = """background-color : #232323; color : white"""

    style_sheet_dict = {"QLabel" : QLabel,
                        }


    
    return style_sheet_dict


class StrikeOptionsComboBox(QtWidgets.QComboBox):
    def __init__(self, strikes=None, default_n_strike=None, expiry=None, table_idx=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.strikes=strikes
        self.expiry=expiry
        self.table_idx=table_idx  
        self.default_n_strike=default_n_strike
        self.current_n_strikes=default_n_strike

        self.view().setAutoScroll(False)
                
        self.setStyleSheet("""
                            QComboBox {
                                background-color: #fb8b1e;
                                color: black;
                                border: 1px solid black;
                                text-align: right;
                            }
                            QComboBox:focus {
                                background-color: #fb8b1e;
                                border: 2px solid black;
                                text-align: right;
                            }
                            QComboBox::drop-down {
                                border-color: black;
                                background-color: #fb8b1e;
                                text-align: right;
                            }
                            QComboBox::item {
                                background-color: #fb8b1e;
                                color: black;
                                text-align: right;
                            }
                            QComboBox::item:selected {
                                background-color: #d97d1a; 
                                color: black;
                                text-align: right;
                            }
                            QComboBox QAbstractItemView {
                                background-color: #fb8b1e;
                                color: black;
                                border: 1px solid black;
                                text-align: right;
                            }
                        """)        
        
        font = QtGui.QFont("Neue Haas Grotesk", 12)
        self.setFont(font)

    def wheelEvent(self, event):
        if self.view().isVisible():
            super().wheelEvent(event)