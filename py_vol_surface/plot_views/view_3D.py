import numpy as np
from PySide6.QtWidgets import QApplication
import pyqtgraph.opengl as gl
from PySide6 import QtCore, QtGui
from . import plot_views_utils

QApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)


class CustomGLViewWidget(gl.GLViewWidget):    
    right_click_signal = QtCore.Signal(float, float, float)
    surface_updated = QtCore.Signal()
    mouse_position_signal = QtCore.Signal(float, float, float)
    
    def __init__(self, main_window, price_type, instrument_manager, data_container_manager,
                 normalisation_engine=None, axis_manager=None, show_spot_text=None, devicePixelRatio=None, *args, **kwargs):
        super().__init__(*args, devicePixelRatio=devicePixelRatio, **kwargs)
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_Hover)
        self.setAttribute(QtCore.Qt.WA_DontCreateNativeAncestors) 
        self.main_window=main_window
        self.axis_manager=axis_manager 
        self.instrument_manager=instrument_manager
        self.normalisation_engine=normalisation_engine
        self.show_spot_text=show_spot_text
        self.top_price_type=price_type
        self.plotted_price_types=[price_type]
        self.cross_hairs_on=False
        self.text_color = (0, 0, 0, 255)
        self.bg_color = (255, 255, 255, 200)
        self.data_container_manager=data_container_manager
        self.cross_hairs_enabled=True
        near_clip, far_clip = self.compute_optimal_clipping()
        self.opts['near'] = near_clip
        self.opts['far'] = far_clip
        self.opts['azimuth'] = -50
        self.opts["distance"] = 4
        self.opts['center'] = QtGui.QVector3D(0, 1, 0)  
        self.interacting=False
        self.setup_mouse_interaction()
        self.init_crosshairs()
        self.plot_items={}
        self.mouse_position_signal.connect(self.update_crosshairs)
        self.first_plot=True
        self.mouse_released_callbacks=[]
        self.plot_interaction_buffer=[]
        self.add_mouse_release_callbacks(self.main_window.plot_buffered_plots)
        self.set_spot_text("")
        self.price_updated_callbacks=[]
        self.setMouseTracking(True)
        self.update()     

    def add_price_updated_callbacks(self, callback):
        self.price_updated_callbacks.append(callback)

    def add_mouse_release_callbacks(self, callback):
        self.mouse_released_callbacks.append(callback)

    def set_spot_text(self, text):
        self.spot_text = text
        self.update()
            
    def repaint_spot(self,):
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        
        margin = 10
        text_rect = painter.boundingRect(self.rect(), 
                                         QtCore.Qt.AlignTop | QtCore.Qt.AlignRight | QtCore.Qt.TextDontClip, 
                                         self.spot_text
                                        )
        text_rect.moveTopRight(self.rect().topRight() - QtCore.QPoint(margin, -margin))
        
        painter.setBrush(QtGui.QColor(*self.bg_color))
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 200), 1))
        painter.drawRect(text_rect.adjusted(-5, -2, 5, 2))
        
        painter.setPen(QtGui.QColor(*self.text_color))
        painter.drawText(text_rect, QtCore.Qt.AlignCenter, self.spot_text)
        painter.end()
    
    def get_top_price_type(self,):
        if "ask" in self.plotted_price_types:
            self.top_price_type="ask"
        elif "mid" in self.plotted_price_types:
            self.top_price_type="mid"
        elif "bid" in self.plotted_price_types:
            self.top_price_type="bid"

    def addPricePlots(self, price_type, surface, scatter):
        self.plot_items[price_type] = {"surface" : surface, "scatter" : scatter}
        if not price_type in self.plotted_price_types:
            self.plotted_price_types.append(price_type)
            
        self.get_top_price_type()
        super().addItem(self.plot_items[price_type]["surface"])
        super().addItem(self.plot_items[price_type]["scatter"])

        self._bring_item_to_front(self.line_xz)
        self._bring_item_to_front(self.line_yz)
        
    def removePricePlots(self, price_type):
        def _remove_item_price(price_type, plot_type):
            item = self.plot_items[price_type][plot_type]
            self.removeItem(item)
            item.hide()

        if self.main_window.surface_flag:
            _remove_item_price(price_type, "surface")
        if self.main_window.scatter_flag:
            _remove_item_price(price_type, "scatter")
            
        self.plotted_price_types.remove(price_type)
        self.get_top_price_type()

    def _bring_item_to_front(self, item):
        super().removeItem(item)
        super().addItem(item)

    def remove_spot_text(self):
        self.show_spot_text = False
        self.spot_text = ""
        self.update()
        
    def toggle_crosshairs(self,enable=True):
        self.cross_hairs_enabled=enable
        if not enable:
            self.line_xz.hide()
            self.line_yz.hide()
            
    def restore_spot_text(self, text=""):
        self.show_spot_text = True
        self.spot_text = text
        self.update()

    def paintGL(self, *args, **kwargs):
        super().paintGL(*args, **kwargs)
        if self.show_spot_text and self.spot_text:
            painter = QtGui.QPainter(self)
            self.repaint_spot()
            painter.end()

    def compute_optimal_clipping(self):
        largest_point_distance = np.sqrt(2)
        
        near_clip = max(0.0001, self.opts['distance'] - 1.01 * largest_point_distance) 
        far_clip = self.opts['distance'] 
        return near_clip, far_clip

    def init_crosshairs(self):
        self.line_yz = None
        self.line_xz = None
        self.cross_hairs_on = False
        line_xz, line_yz = np.column_stack([np.linspace(0,1,60)]*3) , np.column_stack([np.linspace(0,1,60)]*3)
        
        self.line_xz = gl.GLLinePlotItem(pos=line_xz,
                                    color=(1, 1, 1, 1),
                                    width=3,
                                    mode='line_strip',
                                    antialias=True)
    
        self.line_yz = gl.GLLinePlotItem(pos=line_yz,
                                        color=(1, 1, 1, 1),
                                        width=3,
                                        mode='line_strip',
                                        antialias=True)
            
        self.line_yz.setGLOptions('opaque')
        self.line_xz.setGLOptions('opaque')

        self.line_yz.hide()
        self.line_xz.hide()
        super().addItem(self.line_yz)
        super().addItem(self.line_xz)

    def setup_mouse_interaction(self):
        self.mouse_move_timer = QtCore.QTimer(self)
        self.mouse_move_timer.setInterval(100)
        self.mouse_move_timer.timeout.connect(self.process_mouse_move)
        self.mouse_move_timer.start()
        self.setMouseTracking(True)
        self.mouse_pos=None
        
    def mousePressEvent(self, event):
        match event.buttons().value :    
            case 2:
                self.mouse_pos = event.pos()  
                self.process_right_click(self.mouse_pos)
        super().mousePressEvent(event)

    def process_right_click(self, mouse_pos):
        world_x, world_y, world_z = self.get_mouse_pos(mouse_pos)
        if 0 <= world_x <= 1 and 0 <= world_y <= 1 and 0 <= world_z <= 1:        
            self.right_click_signal.emit(world_x, world_y, world_z)
    
    def mouseMoveEvent(self, event):
        self.mouse_pos = event.pos()
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        self.mouse_pos=None
        self.interacting=False
        self.cross_hairs_on=False
        self.line_yz.hide()
        self.line_xz.hide()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        self.interacting=False
        for callback in self.mouse_released_callbacks:
            callback()
        return super().mouseReleaseEvent(event)
    
    def get_mouse_pos(self, pos):
        self.makeCurrent() 
        world_x, world_y, world_z = plot_views_utils.map_2D_coords_to_3D(self, self.main_window.screen(), pos.x(), pos.y())
        return world_x, world_y, world_z
    
    def update_crosshairs(self, x, y):
        if not self.cross_hairs_on:
            self.cross_hairs_on = True
            self.line_yz.show()
            self.line_xz.show()

        gl_surface_item = self.plot_items[self.top_price_type]["surface"]
        if not gl_surface_item.z_norm is None:
            line_xz, line_yz = plot_views_utils.calculate_xy_lines(gl_surface_item.x_norm,
                                                                gl_surface_item.y_norm,
                                                                gl_surface_item.z_norm,
                                                                x_fixed=x,
                                                                y_fixed=y
                                                                )
            line_xz[:,2]+=0.005
            line_yz[:,2]+=0.005

            self.line_xz.setData(pos=line_xz)
            self.line_yz.setData(pos=line_yz)
    
    def process_mouse_move(self):
        if (self.cross_hairs_enabled
            and self.main_window.surface_flag
            and self.top_price_type in self.main_window.current_price_types
            and self.data_container_manager.objects[self.top_price_type].surface.valid_values
            and not self.mouse_pos is None
            ):
            
            world_x, world_y, world_z = self.get_mouse_pos(self.mouse_pos)
            if 0 <= world_x <= 1 and 0 <= world_y <= 1 and 0 <= world_z <= 1:
                self.mouse_position_signal.emit(world_x, world_y, world_z)
            else:
                self.cross_hairs_on=False
                self.line_yz.hide()
                self.line_xz.hide()
            self.mouse_pos = None
                
