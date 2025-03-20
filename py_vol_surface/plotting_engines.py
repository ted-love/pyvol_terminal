import numpy as np
from py_vol_surface.axis import axis_utils

class MetricEngine:
    def __init__(self, base_domain, options_1_underlying_flag=False, spot_object=None):
        self.base_domain = base_domain
        self._K = base_domain.strike.copy()
        self._T = base_domain.expiry.copy()
        
        self.generator=axis_utils.MetricFunctionGenerator(options_1_underlying_flag)
        self._change_metric_params("strike", "x")
        self._change_metric_params("expiry", "y")
        self._change_metric_params("IVOL", "z")

        self.spot_object=spot_object
            
    def _change_metric_params(self, metric, metric_direction):
        setattr(self, f"{metric_direction}_metric", metric)
        setattr(self, f"{metric_direction}_metric_function", self.generator.get_function(metric))
    
    def switch_axis(self, metric, metric_direction):
        self._change_metric_params(metric, metric_direction)
    
    def transform_data(self, raw_object, new_metric=None, metric_direction=None):
        if not new_metric is None and not metric_direction is None:
            self._change_metric_params(new_metric, metric_direction)
        
        if (new_metric is not None and metric_direction is None) or (new_metric is None and metric_direction is not None):
            raise ValueError("Must provide both 'new_metric' and 'metric_direction' together, or neither.")
        
        x_orig, y_orig = self._K.copy(), self._T.copy()
        z_orig = raw_object.IVOL.copy()

        x_metric, y, z, mask_removal_x, mask_rearrange_x = self.x_metric_function(raw_object, x_orig, y_orig, z_orig)
        
        x_new = x_orig[mask_removal_x][mask_rearrange_x]
        x_new, y_metric, z, mask_removal_y, mask_rearrange_y = self.y_metric_function(raw_object, x_new, y, z)
        
        x_metric = x_metric[mask_removal_y][mask_rearrange_y]
        y_new = y_orig[mask_removal_x][mask_rearrange_x][mask_removal_y][mask_rearrange_y]
        
        x, y, z_metric, mask_removal_z, mask_rearrange_z = self.z_metric_function(raw_object, x_new, y_new, z)
        
        x_metric = x_metric[mask_removal_z][mask_rearrange_z]
        y_metric = y_metric[mask_removal_z][mask_rearrange_z]
        return x_metric, y_metric, z_metric

class NormalisationEngine:
    def __init__(self, data_points=None):
        self.data_points=data_points
        self.scale=1
        self.shift=0
        self.min_surface_LB = None
        self.max_surface_UB = None
        self.surface_min = None
        self.surface_max = None
        self.normalised_min = None
        self.normalised_max = None
        self.offsets_x = [0.01, 0.01]
        self.offsets_y = [0, 0.01]
        self.offsets_z = [0.01, 0.01]
        self.min_UB_normalised=0.25
        self.max_LB_normalised=0.75

        self.current_data_max=0.
        self.current_data_min=1.
        self.x_min = np.nan
        self.x_max= np.nan
        self.y_min= np.nan
        self.y_max = np.nan
        self.z_min = np.nan
        self.z_max= np.nan
        
        self.x_UB=np.nan
        self.y_UB=np.nan
        self.z_UB=np.nan
        self.x_LB=np.nan
        self.y_LB=np.nan
        self.z_LB=np.nan
        
        self.first_plot=True
        self.scale_x=1
        self.shift_x=0
        self.scale_y=1
        self.shift_y=0
        self.scale_z=1
        self.shift_z=0
        self.ini_plot=True
        self.first_plot_x=True
        self.first_plot_y=True
        self.first_plot_z=True
        self.min_normalised_bounds = [0, 0.4]
        self.max_normalised_bounds = [0.6, 1]
        
    def _calc_norm_params(self, min_val, max_val, offsets):
        normalised_min = offsets[0]
        normalised_max = 1 - offsets[1]
        
        scale = (normalised_max - normalised_min) / (max_val - min_val)
        shift = normalised_min
        return scale, shift, min_val, max_val

    def _calc_normalisation_params(self, data_points, offsets):
        min_val = np.nanmin(data_points)
        max_val = np.nanmax(data_points)
        
        normalised_min = offsets[0]
        normalised_max = 1 - offsets[1]
        
        scale = (normalised_max - normalised_min) / (max_val - min_val)
        shift = normalised_min
        return scale, shift, min_val, max_val
    
    def create_truncated_x(self, data_points):
        self.scale_x, self.shift_x, self.x_min, self.x_max = self._calc_normalisation_params(data_points, [0,0])
        self.x_LB, self.x_UB, self.x_min_UB, self.x_max_LB = self._unnormalised_range_vals(self.scale_x, self.shift_x, self.x_min,)
        self.first_plot_x=False

    def create_truncated_y(self, data_points):
        self.scale_y, self.shift_y, self.y_min, self.y_max = self._calc_normalisation_params(data_points, [0,0])
        self.y_LB, self.y_UB, self.y_min_UB, self.y_max_LB = self._unnormalised_range_vals(self.scale_y, self.shift_y, self.y_min,)
        self.first_plot_y=False

    def create_truncated_z(self, data_points):
        self.scale_z, self.shift_z, self.z_min, self.z_max = self._calc_normalisation_params(data_points, [0,0])
        self.z_LB, self.z_UB, self.z_min_UB, self.z_max_LB = self._unnormalised_range_vals(self.scale_z, self.shift_z, self.z_min,)
        self.first_plot_z=False

    def normalise_x(self, x):
        return (x - self.x_min) * self.scale_x + self.shift_x
    
    def normalise_y(self, y):
        return (y - self.y_min) * self.scale_y + self.shift_y

    def normalise_z(self, z):
        return (z - self.z_min) * self.scale_z + self.shift_z
    
    def create_norm_x(self, data_points):
        self.scale_x, self.shift_x, self.x_min, self.x_max = self._calc_normalisation_params(data_points, self.offsets_x)
        self.x_LB, self.x_UB, self.x_min_UB, self.x_max_LB = self._unnormalised_range_vals(self.scale_x, self.shift_x, self.x_min)
        self.first_plot_x=False

    def create_norm_y(self, data_points):
        self.scale_y, self.shift_y, self.y_min, self.y_max = self._calc_normalisation_params(data_points, self.offsets_y)
        self.y_LB, self.y_UB, self.y_min_UB, self.y_max_LB = self._unnormalised_range_vals(self.scale_y, self.shift_y, self.y_min,)
        self.first_plot_y=False

    def create_norm_z(self, data_points):
        self.scale_z, self.shift_z, self.z_min, self.z_max = self._calc_normalisation_params(data_points, self.offsets_z)
        self.z_LB, self.z_UB, self.z_min_UB, self.z_max_LB = self._unnormalised_range_vals(self.scale_z, self.shift_z, self.z_min,)
        self.first_plot_z=False
        
    def create_x_norm(self, x_min, x_max):
        self.scale_x, self.shift_x, self.x_min, self.x_max = self._calc_norm_params(x_min, x_max, self.offsets_x)
        self.x_LB, self.x_UB, self.x_min_UB, self.x_max_LB = self._unnormalised_range_vals(self.scale_x, self.shift_x, self.x_min)

    def create_y_norm(self, y_min, y_max):
        self.scale_y, self.shift_y, self.y_min, self.y_max = self._calc_norm_params(y_min, y_max, self.offsets_y)
        self.y_LB, self.y_UB, self.y_min_UB, self.y_max_LB = self._unnormalised_range_vals(self.scale_y, self.shift_y, self.y_min)

    def create_z_norm(self, z_min, z_max):
        self.scale_z, self.shift_z, self.z_min, self.z_max = self._calc_norm_params(z_min, z_max, self.offsets_z)
        self.z_LB, self.z_UB, self.z_min_UB, self.z_max_LB = self._unnormalised_range_vals(self.scale_z, self.shift_z, self.z_min)

    def calculate_params(self, x_min, x_max, y_min, y_max, z_min, z_max):
        self.create_x_norm(x_min, x_max)
        self.create_y_norm(y_min, y_max)
        self.create_z_norm(z_min, z_max)
        
    def normalise_xyz(self, x, y, z):
        return self.normalise_x(x), self.normalise_y(y), self.normalise_z(z)    

    def check_value_bounds(self, x_min, x_max, y_min, y_max, z_min, z_max):
        axes_requiring_normalisation = []
        if x_min < self.x_LB or x_max > self.x_UB or x_min > self.x_min_UB or x_max < self.x_max_LB:
            axes_requiring_normalisation.append("x")
        if y_min < self.y_LB or y_max > self.y_UB or y_min > self.y_min_UB or y_max < self.y_max_LB:
            axes_requiring_normalisation.append("y")
        if z_min < self.z_LB or z_max > self.z_UB or z_min > self.z_min_UB or z_max < self.z_max_LB:
            axes_requiring_normalisation.append("z")
        return axes_requiring_normalisation

    def _unnormalised_range_vals(self, scale, shift, min_val):
        lower_bound = - shift / scale + min_val
        upper_bound = (1 - shift) / scale + min_val
        
        diff = upper_bound - lower_bound
        min_UB = lower_bound + diff * (1 + self.min_UB_normalised)
        max_LB = lower_bound + diff * (self.max_LB_normalised)
        return lower_bound, upper_bound, min_UB, max_LB

    def _unnormalise_values(self, values):
        return (values - self.shift ) / self.scale + self.surface_min

    def out_of_bounds_checker(self, x_min, x_max, y_min, y_max, z_min, z_max):
        if x_min < self.x_LB or x_max > self.x_UB:
            self.create_norm_x([x_min, x_max])
            
        if y_min < self.y_LB or y_max > self.y_UB:
            self.create_norm_y([y_min, y_max])

        if z_min < self.z_LB or z_max > self.z_UB:
            self.create_norm_z([z_min, z_max])

    def out_of_bounds_check(self, values):
        if not np.all(self.min_normalised_bounds[0] <= values.min() < self.min_normalised_bounds[1]):
            return True
        elif not np.all(self.max_normalised_bounds[0] < values.max() < self.max_normalised_bounds[1]):
            return True
        else:
            return False
    
    def values_out_of_bounds(self, values):
        if any(values < 0) or any(values > 0):
            return True
    
    def create_norm_domain(self, x, y, z, z_valid):
        if z_valid:
            self.create_norm_z(z)
            self.process_limits(x, y, z)
        else:
            self.create_norm_x(x)
            self.create_norm_y(y)
            self.process_limits(x, y)
    
    def recalculate_parameters(self, limits, axis_direction):
        if axis_direction == "x":
            self.scale_x, self.shift_x, self.x_min, self.x_max = self._calc_normalisation_params(limits, self.offsets_x)
            self.x_LB, self.x_UB, self.x_min_UB, self.x_max_LB = self._unnormalised_range_vals(self.scale_x, self.shift_x, self.x_min,)
            
        if axis_direction == "y":
            self.scale_y, self.shift_y, self.y_min, self.y_max = self._calc_normalisation_params(limits, self.offsets_y)
            self.y_LB, self.y_UB, self.y_min_UB, self.y_max_LB = self._unnormalised_range_vals(self.scale_y, self.shift_y, self.y_min,)

        if axis_direction == "z":
            self.scale_z, self.shift_z, self.z_min, self.z_max = self._calc_normalisation_params(limits, self.offsets_z)
            self.z_LB, self.z_UB, self.z_min_UB, self.z_max_LB = self._unnormalised_range_vals(self.scale_z, self.shift_z, self.z_min,)

    def check_and_update_normaliser(self, x_min=None, x_max=None, y_min=None, y_max=None, z_min=None, z_max=None):
        axes_requiring_normalisation = self.check_value_bounds2(x_min, x_max, y_min, y_max, z_min, z_max)
        for axis in axes_requiring_normalisation:
            getattr(self, f"create_norm_{axis}")([locals().get(f"{axis}_min"), locals().get(f"{axis}_max")])
        return axes_requiring_normalisation







    def check_value_bounds2(self, x_min=None, x_max=None, y_min=None, y_max=None, z_min=None, z_max=None):
        axes_requiring_normalisation = []
        if not x_min is None and not x_max is None:
            if x_min < self.x_LB or x_max > self.x_UB or x_min > self.x_min_UB or x_max < self.x_max_LB:
                axes_requiring_normalisation.append("x")
        if not y_min is None and not y_max is None:
            if y_min < self.y_LB or y_max > self.y_UB or y_min > self.y_min_UB or y_max < self.y_max_LB:
                axes_requiring_normalisation.append("y")
        if not z_min is None and not z_max is None:
            if np.isnan(self.z_LB):
                if not np.isnan(z_min):
                    axes_requiring_normalisation.append("z")
            else:            
                if z_min < self.z_LB or z_max > self.z_UB or z_min > self.z_min_UB or z_max < self.z_max_LB:
                    axes_requiring_normalisation.append("z")
        return axes_requiring_normalisation
    
    def normalise_domain(self, x=None, y=None, z=None):
        self.process_limits(x, y, z)
        if not z is None:
            axes_requiring_normalisation = self.check_value_bounds2(self.x_min, self.x_max, self.y_min, self.y_max, self.z_min, self.z_max)
        else:
            axes_requiring_normalisation=[]
        
        for axis in axes_requiring_normalisation:
            getattr(self, f"create_norm_{axis}")(locals().get(axis))
        
        if not x is None:
            x_norm=self.normalise_x(x)
        else:
            x_norm=None
            
        if not y is None:
            y_norm=self.normalise_y(y)
        else:
            y_norm=None
            
        if not z is None:
            z_norm=self.normalise_z(z)
        else:
            z_norm=None
        return x_norm, y_norm, z_norm, axes_requiring_normalisation

    def first_plot_normaliser(self, x, y, z, z_valid):    
        x_norm=self.normalise_x(x)
        y_norm=self.normalise_y(y)  
        if z_valid:
            z_norm=self.normalise_z(z)
        else:
            z_norm=np.nan * z
        return x_norm, y_norm, z_norm    
    
    def process_limits(self, x=None, y=None, z=None):
        if not x is None:
            x_min, x_max = np.nanmin(x), np.nanmax(x)
            if np.isnan(self.x_max):
                self.x_min = x_min
                self.x_max = x_max
            else:
                if x_min < self.x_min:
                    self.x_min = x_min
                if x_max > self.x_max:
                    self.x_max = x_max
                
        if not y is None:
            y_min, y_max = np.nanmin(y), np.nanmax(y)
            if np.isnan(self.y_max):
                self.y_min = y_min
                self.y_max = y_max
            else:
                if y_min < self.y_min:
                    self.y_min = y_min
                if y_max > self.y_max:
                    self.y_max = y_max

        if not z is None:
            z_min, z_max = np.nanmin(z), np.nanmax(z)
            if np.isnan(self.z_max):
                self.z_min = z_min
                self.z_max = z_max
            else:
                if z_min < self.z_min:
                    self.z_min = z_min
                if z_max > self.z_max:
                    self.z_max = z_max
