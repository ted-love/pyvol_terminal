import pyqtgraph as pg
from PySide6 import QtCore, QtGui
from datetime import datetime

class SubPlot(pg.PlotWidget):
    def __init__(self, main_window=None, data_container_manager=None, normalisation_engine=None,
                 axis_3D_directions=None, line_dataitems=None, right_click_signal=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_window=main_window
        self.data_container_manager=data_container_manager
        self.normalisation_engine=normalisation_engine
        self.axis_3D_directions=axis_3D_directions
        self.other_axis_direction = "yz" if axis_3D_directions=="xz" else "xz"
        self.current_price_types=[]
        self.line_dataitems=line_dataitems
        self.text=""
        self.show_text=False
        self.text_color = (0, 0, 0, 255)
        self.bg_color = (255, 255, 255, 200)
        self.prev_x=None
        self.prev_y=None
        right_click_signal.connect(self.update_plots)
        self.interacting=False
        
    def add_line(self, price_type):
        self.current_price_types.append(price_type)
        curve = self.line_dataitems[price_type]
        self.update_plot(price_type)
        self.addItem(curve)
        curve.show()
        self.update_plots()        
        
    def remove_line(self, price_type):
        curve = self.line_dataitems[price_type]
        self.current_price_types.remove(price_type)
        curve.hide()
        self.removeItem(curve)
        if len(self.current_price_types) == 0:
            self.prev_x=None
            self.prev_y=None

    def update_plots(self, x=None, y=None):
        if x:
            self.prev_x=x
        else:
            x=self.prev_x
        if y:
            self.prev_y=y
        else:
            y=self.prev_y
        for price_type in self.current_price_types:
            self.update_plot(price_type, x, y)
    
    def update_plot(self, price_type, x=None, y=None):
        if self.main_window.subplots_flag and not self.interacting:
            if not x:
                x=self.prev_x
            if not y:
                y=self.prev_y  
            
            if x and y:
                data_container = self.data_container_manager.objects[price_type]
                if data_container.surface.valid_values:
                    xi, yi = data_container.surface.x, data_container.surface.y

                    if self.axis_3D_directions=="xz": 
                        other_axis_pos = self.normalisation_engine.y_LB + y * (self.normalisation_engine.y_UB - self.normalisation_engine.y_LB)

                        x_vals = xi
                        y_vals = [other_axis_pos] * xi.size
                        x_vals_plotting = x_vals
                    else:
                        other_axis_pos = self.normalisation_engine.x_LB + x * (self.normalisation_engine.x_UB - self.normalisation_engine.x_LB)
                        y_vals = yi
                        x_vals = [other_axis_pos] * yi.size
                        x_vals_plotting = y_vals
                        
                    z_vals = data_container.surface.interpolator.evaluate(x_vals, y_vals)

                    if z_vals.ndim == 1:
                        y_vals_plotting = z_vals
                    else:
                        if z_vals.shape[1] == 1 or z_vals.shape[0] == 1:
                            y_vals_plotting = z_vals.flatten()
                        else:
                            if self.axis_3D_directions=="yz":
                                y_vals_plotting = z_vals[0,:]
                            else:
                                y_vals_plotting = z_vals[:,0]
                    self.line_dataitems[price_type].setData(x_vals_plotting, y_vals_plotting)
                    
                    self.show_text=True
                    self.set_text(other_axis_pos)
                    self.getPlotItem().autoBtnClicked()
    
    def mousePressEvent(self, ev):
        self.interacting=True
        return super().mousePressEvent(ev)
    
    def mouseReleaseEvent(self, ev):
        self.interacting=False
        return super().mouseReleaseEvent(ev)
    
    def set_text(self, text):
        if self.other_axis_direction=="xz":
            text = f"{text:,.2f}"
        else:
            text = datetime.fromtimestamp(text).strftime("%d-%b-%Y").upper()
            
        self.text = str(text)
        self.viewport().update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.show_text and self.text:
            painter = QtGui.QPainter(self.viewport())
            painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
            self._draw_text(painter)
            painter.end()

    def _draw_text(self, painter):
        viewport_rect = self.viewport().rect()
        text_rect = painter.boundingRect(viewport_rect, 
                                       QtCore.Qt.AlignTop | QtCore.Qt.AlignRight | QtCore.Qt.TextDontClip, 
                                       self.text)
        text_rect.moveTopRight(viewport_rect.topRight() - QtCore.QPoint(10, -10))
        
        painter.setBrush(QtGui.QColor(*self.bg_color))
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 200), 1))
        painter.drawRect(text_rect.adjusted(-5, -2, 5, 2))
        
        painter.setPen(QtGui.QColor(*self.text_color))
        painter.drawText(text_rect, QtCore.Qt.AlignCenter, self.text)