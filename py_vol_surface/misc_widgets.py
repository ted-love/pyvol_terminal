import pyqtgraph as pg
import numpy as np
from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QColor, QPixmap, QPainter

    
class CustomColorMap(pg.ColorMap):
    def __init__(self, colourmap_style: str):
        pos = np.linspace(0, 1, 500)          
        try:
            colourmap = pg.colormap.get(colourmap_style)
        except:
            print(f"{colourmap_style} is not in pyqtgraph, using default inferno")
            colourmap = pg.colormap.get("inferno")

        colors = colourmap.map(pos, mode='byte')        
        super().__init__(pos=pos, color=colors, mode='byte')
        
     
class ColorSquare(QtWidgets.QLabel):
    def __init__(self, color, size=50):
        super().__init__()
        self.color = color
        self.color_width = size
        self.color_height = size /2
        self.setFixedSize(self.color_width, self.color_height)

        self.update_color()

    def update_color(self):
        pixmap = QPixmap(self.color_width, self.color_height)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QPainter(pixmap)
        
        qcol_rgb = QColor.fromRgbF(*self.color)
        painter.setBrush(qcol_rgb)
        painter.drawRect(0, 0, self.color_width, self.color_height)
        painter.end()
        self.setPixmap(pixmap)
        self.setStyleSheet("border: 2px solid black;")


class Legend(QtWidgets.QWidget):
    def __init__(self, colourmap={}, parent=None):
        self.colourmap=colourmap
        super().__init__(parent)
        self.setStyleSheet("background: transparent; color: white;")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.legend_items={}
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding
                           )

    def remove_legend_item(self, legend_name):
        inner_widget=self.legend_items[legend_name]
        self.layout.removeWidget(inner_widget)
                    
    def add_legend_item(self, legend_name):
        colour = self.colourmap[legend_name]
        hbox_layout = QtWidgets.QHBoxLayout()
        hbox_layout.setAlignment(QtCore.Qt.AlignLeft)
        hbox_layout.setContentsMargins(0, 0, 0, 0)
        hbox_layout.setSpacing(5)

        square_colour = ColorSquare(colour)
        hbox_layout.addWidget(square_colour)

        # Label (expand horizontally)
        square_label = QtWidgets.QLabel(legend_name)
        square_label.setStyleSheet("border: 1px solid white; padding: 3px; background-color: white; color: black")
        #square_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
        #                           QtWidgets.QSizePolicy.Fixed)
        
        hbox_layout.addWidget(square_label)
        inner_widget = QtWidgets.QWidget()
        inner_widget.setLayout(hbox_layout)

        self.legend_items[legend_name] = inner_widget        
        self.layout.addWidget(inner_widget)
        self.adjustSize()
        self.update()
    
