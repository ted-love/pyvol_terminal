import numpy as np
from OpenGL import GL as opengl
from OpenGL import GLU
import pyqtgraph as pg
from PySide6 import QtGui

def map_2D_coords_to_3D(widget, screen, x, y):
    
    widget_height = widget.height()
    widget_width = widget.width()
    ratio = screen.devicePixelRatio()
    mouse_x_logical = x
    mouse_y_logical = y
    mouse_x_normalized = mouse_x_logical / widget_width
    mouse_y_normalized = mouse_y_logical / widget_height

    viewport = opengl.glGetIntegerv(opengl.GL_VIEWPORT)
    _, _, viewport_width, viewport_height = viewport

    mouse_x_physical = mouse_x_normalized * viewport_width
    mouse_y_physical = mouse_y_normalized * viewport_height
    mouse_y_physical = viewport_height - mouse_y_physical 
    
    depth = opengl.glReadPixels(int(mouse_x_physical), int(mouse_y_physical),  1, 1, opengl.GL_DEPTH_COMPONENT, opengl.GL_FLOAT)[0][0]

    modelview = np.array(widget.viewMatrix().data()).reshape(4, 4)
    projection = np.array(widget.projectionMatrix(viewport, (0, 0, ratio * widget_width, ratio* widget_height)).data()).reshape(4, 4)
   
    world_x, world_y, world_z = GLU.gluUnProject(mouse_x_physical, mouse_y_physical, depth, modelview, projection, viewport)

    return world_x, world_y, world_z

def calculate_xy_lines(X, Y, Z, x_fixed, y_fixed):
    x_index = np.argmin(np.abs(X - x_fixed)) 
    y_index = np.argmin(np.abs(Y - y_fixed))  

    line_xz = np.column_stack(([x_fixed] * Y.size, Y, Z[x_index,: ]))  
    line_yz = np.column_stack((X, [y_fixed]*X.size, Z[:,y_index])) 
    return line_xz, line_yz

def initialise_plotdataitems(price_types, colours):
    vol_smiles = {}
    vol_terms = {}
    for price_type in price_types:
        r, g, b, a = [int(c * 255) for c in colours[price_type]]
        pen = pg.mkPen(QtGui.QColor(r, g, b, a))
        vol_s = pg.PlotDataItem(x=[], y=[], pen=pen)
        vol_t = pg.PlotDataItem(x=[], y=[], pen=pen)
        vol_smiles[price_type]=vol_s
        vol_terms[price_type]=vol_t
    
    return vol_smiles, vol_terms
