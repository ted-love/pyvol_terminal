from scipy.interpolate import RBFInterpolator, bisplrep, bisplev
import numpy as np

class CustomRBFInterpolator(RBFInterpolator):
    def __init__(self, n_x, n_y, kernel='linear', *args, **kwargs):
        self.n_x=n_x
        self.n_y=n_y
        self._initialized = False
        self.y = None
        self.z = None
        self.kernel = kernel
        self.args = args
        self.kwargs = kwargs

    def fit(self, x=None, y=None, z=None):
        x = x.flatten()
        y = y.flatten()
        self.y = np.column_stack((x, y))
        self.z = z.flatten()   
        super().__init__(self.y, self.z, kernel=self.kernel, *self.args, **self.kwargs)
        
    def evaluate(self, xi, yi):
        xi, yi = np.meshgrid(xi, yi)
        points = np.column_stack((xi.flatten(), yi.flatten()))
        new_vals = self(points).reshape(self.n_x, self.n_y)
        return new_vals
    
    
class CustomBSplineInterpolator:
    def __init__(self,):
        self.xy = None
        self.z=None
        self.kx=2
        self.ky=2  
    
    def fit(self, x, y, z):
        self.tck = bisplrep(x, y, z, s=len(x), kx=self.kx, ky=self.ky) 
        
    def evaluate(self, xi, yi):
        x_vals = np.unique(xi)
        y_vals = np.unique(yi)
        x_vals.sort()
        y_vals.sort()
        return bisplev(x_vals, y_vals, self.tck)
