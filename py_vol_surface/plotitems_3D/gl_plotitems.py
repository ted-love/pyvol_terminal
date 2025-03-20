import pyqtgraph.opengl as gl
import numpy as np
import time
class glSurface(gl.GLSurfacePlotItem):
    def __init__(self, price_type, data_object, normalisation_engine, parent_widget=None,**kwargs):
        self.data_object=data_object
        self.init=True
        self.parent_widget=parent_widget
        self.normalisation_engine=normalisation_engine
        self.type="surface"
        self.x=data_object.x
        self.y=data_object.y
        self.z=data_object.z
        self.x_norm = None
        self.y_norm = None
        self.z_norm = None 
        self.plot_name = f"{self.type}_{price_type}"
        self.colormap=data_object.colourmap
        self.colors = self.colormap.map(self.z, mode='float')
        super().__init__(x=self.x, y=self.y, z=self.z, **kwargs)    

    def setData(self, x=None, y=None, z=None, colors=None, **kwargs):
        if self.init:
            self.colors = self.data_object.colourmap.map(self.z, mode='float')
            self.init=False
            self.x_norm, self.y_norm, self.z_norm = self.normalisation_engine.normalise_xyz(x, y, z)
            return super().setData(x=self.x_norm, y=self.y_norm, z=self.z_norm, colors=self.colors, **kwargs)
        else:
            if not x is None:
                self.x=x
            if not y is None:
                self.y=y
            if not z is None:
                self.z=z   
            if self.data_object.valid_values:
                self.x_norm, self.y_norm, self.z_norm = self.normalisation_engine.normalise_xyz(self.x, self.y, self.z)
                self.colors = self.data_object.colourmap.map(self.z_norm, mode='float')
                return super().setData(x=self.x_norm, y=self.y_norm, z=self.z_norm, colors=self.colors, **kwargs)


class glScatter(gl.GLScatterPlotItem):
    def __init__(self, price_type, data_object, normalisation_engine, parent_widget=None, **kwargs):
        self.parent_widget=parent_widget
        self.data_object=data_object
        self.first_plot=True
        self.normalisation_engine=normalisation_engine
        self.type="scatter"

        self.x=data_object.x
        self.y=data_object.y
        self.z=data_object.z
        self.init=True
        self.plot_name = f"{self.type}_{price_type}"

        self.x_norm = self.normalisation_engine.normalise_x(self.x)
        self.y_norm = self.normalisation_engine.normalise_y(self.y)
        self.z_norm = self.normalisation_engine.normalise_z(self.z)
        pos = np.column_stack((self.x_norm, self.y_norm, self.z_norm))
        super().__init__(pos=pos, color=self.data_object.colour, **kwargs)        
        self.color = self.data_object.colour
    
    def setData(self, x=None, y=None, z=None, pos=None, color=None, **kwargs):
        if self.init:
            
            self.init=False
            #self.x_norm, self.y_norm, self.z_norm = self.normalisation_engine.normalise_xyz(pos[:,0], pos[:,1], pos[:,2])
            pos = np.column_stack((self.x_norm, self.y_norm, self.z_norm))
            self.timer = time.time()
            
            return super().setData(pos=pos, color=self.color, **kwargs)
        else:           
            if self.data_object.valid_values:
                if not pos is None:
                    self.x = pos[:,0]
                    self.y = pos[:,1]
                    self.z = pos[:,2]
                else:                    
                    if not x is None:
                        self.x=x
                    if not y is None:
                        self.y=y
                    if not z is None:
                        self.z=z
                    self.x_norm, self.y_norm, self.z_norm = self.normalisation_engine.normalise_xyz(self.x, self.y, self.z)
                    pos = np.column_stack((self.x_norm, self.y_norm, self.z_norm))
                    return super().setData(pos=pos, color=self.color, **kwargs)
    
    