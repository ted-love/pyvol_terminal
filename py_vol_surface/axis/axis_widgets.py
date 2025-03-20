import pyqtgraph as pg
from PySide6 import QtGui 
import pyqtgraph.opengl as gl
import numpy as np
from typing import List, Optional
from . import axis_utils

class CustomAxisItem(pg.AxisItem):
    def __init__(self, axis_3D_direction=None, *args, **kwargs):
        self.axis_3D_direction=axis_3D_direction
        self.title=None
        self.visual_tick_generator = axis_utils.VisualTickGenerator()
        self.display_tick_gen = self.visual_tick_generator.get_function(self.title)
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def setTitle(self, title):
        self.title = title
        self.display_tick_gen = self.visual_tick_generator.get_function(title)
        super().setLabel(title)
        
    def updateRange(self, limits):
        self.setRange(limits[0], limits[1])
    
    def tickStrings(self, values, scale, spacing):
        return [self.display_tick_gen(val) for val in values]


class _Axis3DLabel:
    def __init__(self, widget, axis_label, axis_direction, colour, offset):
        self.widget=widget
        self.axis_label=axis_label
        self.axis_direction=axis_direction
        self.colour=colour
        self.offset=offset
        self.label_position = self._create_label_position()
        self.gl_object = self.create_label_object(axis_label)
        self.widget.addItem(self.gl_object)
    
    def create_label_object(self, axis_label):
        self.axis_label=axis_label
        return gl.GLTextItem(pos=self.label_position, text=self.axis_label, font=QtGui.QFont('Arial', 10), color=self.colour)
    
    def _create_label_position(self, ):
        if self.axis_direction=="x":
            return (0.5, self.offset, 0)
        elif self.axis_direction=="y":
            return (1 + self.offset, 0.5, 0)
        else:
            return (1, 1, 0.5)

    def switch(self, new_label):
        self.axis_label=new_label
        self.gl_object.setData(text=new_label)
        

class _Axis3DTicks:
    def __init__(self, widget, axis_label, axis_direction, axis_limits,
                 n_ticks, colour, offset_tick):
        self.widget=widget        
        self.axis_label = axis_label
        self.axis_direction=axis_direction
        self.offset_tick=offset_tick
        self.n_ticks = n_ticks
        self.base_tick_coords = self._calculate_base_axis_pos(n_ticks)
        self.generator = axis_utils.VisualTickGenerator()
        self.display_tick_gen = self.generator.get_function(axis_label)

        self.colour=colour
        self.tick_coords = self._create_tick_positions()
        self.min = axis_limits[0]
        self.max = axis_limits[1]
        self.tick_nums = self._create_tick_nums(self.min, self.max, n_ticks)
        self.gl_objects = self.create_tick_objects(self.tick_nums)
         
    def _calculate_base_axis_pos(self,n_ticks,):
            if self.axis_label == "Delta":
                return [0.10, 0.30, 0.45, 0.55, 0.70, 0.90]
            else:    
                return np.linspace(0, 1, n_ticks)
    
    def _create_tick_nums(self, min_val, max_val, n_ticks):
        values = np.linspace(min_val, max_val, n_ticks)
        return [self.display_tick_gen(val) for val in values]
        
    def _create_tick_positions(self):
        if self.axis_direction=="x":
            return [(pos, 0 + self.offset_tick, 0) for pos in self.base_tick_coords]
        elif self.axis_direction=="y":
            return [(1 + self.offset_tick, pos, 0) for pos in self.base_tick_coords]
        else:
            return [(1, 1, pos) for pos in self.base_tick_coords] \
        
    def switch(self, axis_limits, axis_label):        
        if axis_label is None:
            axis_label = self.axis_label
        else:
            self.axis_label = axis_label
        self.display_tick_gen = self.generator.get_function(axis_label)
        self.update_values(axis_limits)
        
    def update_values(self, axis_limits):
        self.min, self.max = axis_limits[0] ,axis_limits[1]
        self.tick_nums = self._create_tick_nums(self.min, self.max, self.n_ticks)
        for idx, tick_nums in enumerate(self.tick_nums):
            self.gl_objects[idx].setData(text=tick_nums)      
                    
    def create_tick_objects(self, tick_nums):
        gl_objects = []
        for pos, tick in zip(self.tick_coords, tick_nums):
            gl_object = gl.GLTextItem(pos=pos, text=tick, font=QtGui.QFont('Arial', 10), color=self.colour)
            self.widget.addItem(gl_object)
            gl_objects.append(gl_object)
        return gl_objects
    
    
class Axis3D:
    def __init__(self, widget, label, axis_direction, axis_limits, n_ticks, colour, offset_ticks, offset_labels):
        self.widget=widget
        self.ticks = _Axis3DTicks(widget, label, axis_direction, axis_limits, n_ticks, colour, offset_ticks)
        self.label = _Axis3DLabel(widget, label, axis_direction, colour, offset_labels)

    def switch(self, axis_limits, label):
        self.ticks.switch(axis_limits, label)
        self.label.switch(label)
        
    def update_ticks(self, axis_limits):
        self.ticks.update_values(axis_limits)
        

class AxisManager:
    def __init__(self, widget=None, n_ticks=[6,6,6]):
        self.widget=widget
        self.n_ticks_dict={"x" : n_ticks[0],
                           "y" : n_ticks[1],
                           "z" : n_ticks[2]
                          }
        self.axis_2D_items: dict[str, List[CustomAxisItem]] = {"x" : [],
                                                               "y" : [],
                                                               "z" : []}              
        self.axis_3D_items: dict[str, Optional[Axis3D]] = {"x" : None,
                                                           "y" : None,
                                                           "z" : None}
        self.colours = {"x" : "yellow",
                        "y" : "white",
                        "z" : "cyan",
                        }
        self.axis_x = None  
        self.axis_y = None
        self.axis_z = None        
        self.offset_ticks = {"x" : -0.2,
                             "y" : 0.1,
                             "z" : 0.2
                             }
        self.offset_labels = {"x" : -0.4,
                              "y" : 0.3,
                              "z" : 0.3}
        if not widget is None:
            self.create_default()
            self.initialised_default=True
        else:\
            self.initialised_default=False
    
    def create_default(self):
        self.axis_3D_items["x"] = Axis3D(self.widget, "Strike", "x", [0, 1], self.n_ticks_dict["x"], self.colours["x"], self.offset_ticks["x"], self.offset_labels["x"])
        self.axis_3D_items["y"] = Axis3D(self.widget, "Expiry", "y", [0, 1], self.n_ticks_dict["y"], self.colours["y"], self.offset_ticks["y"], self.offset_labels["y"])
        self.axis_3D_items["z"] = Axis3D(self.widget, "Implied Volatility", "z", [0, 1], self.n_ticks_dict["z"], self.colours["z"], self.offset_ticks["z"], self.offset_labels["z"])
        
        for axis in ["x", "y", "z"]:
            setattr(self, f"{axis}_min", getattr(self.axis_3D_items[axis].ticks, "min"))
            setattr(self, f"{axis}_max", getattr(self.axis_3D_items[axis].ticks, "max"))

    def update_ticks(self, axis_limits, axis_direction):        
        axis_ticks = self.axis_3D_items[axis_direction].ticks
        axis_ticks.update_values(axis_limits)

        setattr(self, f"{axis_direction}_min", getattr(self.axis_3D_items[axis_direction].ticks, "min"))
        setattr(self, f"{axis_direction}_max", getattr(self.axis_3D_items[axis_direction].ticks, "max"))

    def switch_axis(self, axis_limits, new_label_metric, axis_direction):
        self.axis_3D_items[axis_direction].switch(axis_limits, new_label_metric)  

        for axis_item in self.axis_2D_items[axis_direction]:
            axis_item.setTitle(new_label_metric)
            
    def add_2D_axis_item(self, axis_item, axis_direction):
        self.axis_2D_items[axis_direction].append(axis_item)
        
    def addWidget(self, widget):
        self.widget=widget
        if not self.initialised_default:
            self.create_default()
        
        
class GridManager:
    def __init__(self, widget=None):
        self.widget=widget
        self.grid_xy, self.grid_yz, self.grid_xz = self._create_grids()
        if not widget is None:
            self._addGrids(widget)
    
    def addWidget(self, widget):
        self.widget=widget
        self._addGrids(self.widget)
    
    def _addGrids(self, widget):
        widget.addItem(self.grid_xy)
        widget.addItem(self.grid_yz)
        widget.addItem(self.grid_xz)
        self.widget=widget
        
    def _create_grid(self, size=(1, 1, 1), spacing=(0.1, 0.1, 0.1), rotation=None, translation=None):
        grid = gl.GLGridItem()
        grid.setSize(*size)
        grid.setSpacing(*spacing)
        if rotation:
            grid.rotate(*rotation)
        
        if translation:
            grid.translate(*translation)
        return grid

    def _create_grids(self):
        self.grid_xy = self._create_grid(
            size=(1, 1, 1),
            spacing=(0.1, 0.1, 0.1),
            translation=(0.5, 0.5, 0)
        )
        
        self.grid_yz = self._create_grid(
            size=(1, 1, 1),
            spacing=(0.1, 0.1, 0.1),
            rotation=(90, 0, 1, 0),
            translation=(0, 0.5, 0.5)
        )
                        
        self.grid_xz = self._create_grid(
            size=(1, 1, 1),
            spacing=(0.1, 0.1, 0.1),
            rotation=(90, 1, 0, 0),
            translation=(0.5, 1, 0.5)
        )
        return self.grid_xy, self.grid_yz, self.grid_xz
