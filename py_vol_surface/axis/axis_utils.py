from datetime import datetime
import numpy as np
from . import axis_widgets
from .. import utils

def i_axis_labels(label_metric):
    match label_metric:
        case "Strike":
            label = "Strike"
        case  "Moneyness":
            label = "Strike/Spot"
        case "Log-Moneyness":
            label = "log(Strike/Spot)"
        case "Delta":
            label = "Delta"
    return label

def j_axis_labels(label_metric):
    match label_metric:
        case "Expiry":
            label = "Expiry"
        case "Years":
            label = "Maturity (Years)"
    return label

def k_axis_labels(label_metric):
    match label_metric:
        case "Implied Volatility":
            label = "Implied Volatility (%)"
        case "Total Volatility":
            label = "Total Volatility"
    return label

def get_axis_label(i_label_metric, j_label_metric, k_label_metric):
    i_label = i_axis_labels(i_label_metric)
    j_label = j_axis_labels(j_label_metric)
    k_label = k_axis_labels(k_label_metric)
    
    axis_labes = {"i" : i_label,
                  "j" : j_label,
                  "k" : k_label}

    return axis_labes

def get_label_types():
    label_metric_types = {"i_label_metrics" : ["Strike", "Moneyness", "Log-Moneyness", "Delta"],
                          "j_label_metrics" : ["Expiry", "Years"],
                          "k_label_metrics" : ["Implied Volatility", "Total Volatility"]
                          }
    
    return label_metric_types

def get_attributes_labels():
    metric_label_map = {"delta" : "Delta",
                        "IVOL" : "Implied Volatility",
                        "IVOL_perc" : "Implied Volatility (%)",
                        "TVAR" : "Total Volatility",
                        "expiry" : "Expiry",
                        "years" : "Years",
                        "strike" : "Strike",
                        "moneyness" : "Moneyness",
                        "log_moneyness" : "Log-Moneyness" ,
                        "standardised_moneyness" : "Standardised-Moneyness" 
                        }
    
    label_metric_map = {label : metric for metric, label in metric_label_map.items()}
    return metric_label_map, label_metric_map


class VisualTickGenerator:
    def __init__(self):
        self._null = lambda x: f"{x:,.2f}"
        self.tick_functions = {
                            "Expiry": self.Expiry_function,
                            "Years": self._null,
                            "Delta": self.Delta_function,
                            "Strike": self._null,
                            "Moneyness": self._null,
                            "Log-Moneyness": self._null,
                            "Implied Volatility": self._null,
                            }
        self.metric_label_map, self.label_metric_map = get_attributes_labels()
    
    def get_function(self, axis_label):
        if axis_label in self.tick_functions:
            return self.tick_functions[axis_label]
        else:
            return self._null
    
    def get_tick_functions(self):
        return self.tick_functions
    
    @staticmethod
    def null_visualise(values):
        return [f"{val:,.2f}" for val in values]
    
    @staticmethod
    def rounder(tick_labels):
        rounded = np.round(tick_labels)
        can_be_integer = np.all(np.isclose(tick_labels, rounded))
        if can_be_integer:
            return rounded.astype(int).astype(str).tolist()
        else:
            round_val = int(abs(np.floor(np.log10(abs(np.diff(tick_labels)).min()))))
            return np.round(tick_labels, round_val).astype(str).tolist()
    
    @staticmethod
    def Delta_function(value):
        return f"{round(100 * value, 1)}P" if value < 0.5 else f"{round(100 * (1 - value), 2)}C"
    
    @staticmethod
    def Expiry_function(value):
        return datetime.fromtimestamp(value).strftime("%d-%b").upper()
    
    @staticmethod
    def Years_function(values):
        return [f"{val:,.2f}" for val in values]


def get_metric_maps():    
    metric_maps = {"delta" : ["OTM", "delta", "call_flag", "delta_mag"],
                   "moneyness" : ["moneyness"],
                   "log_moneyness" : ["log_moneyness"],
                   "standardised_moneyness" : ["standardised_moneyness"],
                   "strike" : [],
                   "expiry" : [],
                   "years" : [],
                   "IVOL" : [],
                   "IVOL_perc" :[],
                   "TVAR" : []}
    
    return metric_maps

def get_metric_functions():
    metric_functions = {"expiry" : null_metric,
                        "years" : years_metric_func,
                        "delta" : delta_metric_mask_sorter,
                        "strike" : null_metric,
                        "moneyness" : moneyness_mask_sorter,
                        "log_moneyness": moneyness_mask_sorter,
                        "standardised_moneyness" : moneyness_mask_sorter,
                        "IVOL": null_metric,
                        "IVOL_perc" : null_metric,
                        "null" : null_metric,
                        "TVAR" : TVAR_function,
                        }
    
    return  metric_functions

def null_metric(raw_object, x, y, z):
    return x, y, z, [True]*z.size, np.arange(z.size)

def get_spot_metric_functions():
    metric_functions = get_metric_functions()
    metric_functions["moneyness"] = moneyness_spot
    metric_functions["log_moneyness"] = log_moneyness_spot
    return metric_functions

def _base_money_sorter(raw_object, x, y, z):
    mask_removal = raw_object.OTM
    x = x[mask_removal]
    y = y[mask_removal]
    z = z[mask_removal]
    
    mask_rearrange = np.lexsort((x, y))
    
    x = x[mask_rearrange]
    y = y[mask_rearrange]
    z = z[mask_rearrange]
    return x, y, z, mask_removal, mask_rearrange

def TVAR_function(raw_object, x, y, z):
    return x, y, z*utils.convert_unix_maturity_to_years(y), [True]*z.size, np.arange(z.size)

def IVOL_perc_function(raw_object, x, y, z):
    return x, y, 100*z, [True]*z.size, np.arange(z.size)

def moneyness_mask_sorter(raw_object, x, y, z):
    x=raw_object.moneyness
    return _base_money_sorter(raw_object, x, y, z)

def log_moneyness_mask_sorter(raw_object, x, y, z):
    x=raw_object.log_moneyness
    return _base_money_sorter(raw_object, x, y, z)

def standardised_moneyness_sorter(raw_object, x, y, z):
    x=raw_object.standardised_moneyness
    return _base_money_sorter(raw_object, x, y, z)

def years_metric_func(raw_object, x, y, z):
    return x, utils.convert_unix_maturity_to_years(y), z, [True]*z.size, np.arange(z.size)

def moneyness_spot(raw_object, x, y, z):
    return raw_object.moneyness, y, z, [True]*z.size, np.arange(z.size)

def log_moneyness_spot(raw_object, x, y, z):
    return raw_object.log_moneyness, y, z, [True]*z.size, np.arange(z.size)

def delta_metric_mask_sorter(raw_object, x, y, z):
    mask_removal = raw_object.OTM & (raw_object.delta_mag < 0.5)
    x = raw_object.delta
    x_masked = x[mask_removal] 
    y_masked = y[mask_removal]  
    z_masked = z[mask_removal]
    
    put_indices = np.where(~raw_object.call_flag[mask_removal])[0]
    call_indices = np.where(raw_object.call_flag[mask_removal])[0]

    if put_indices.size > 0:
        sorted_put_indices = put_indices[np.lexsort((y_masked[put_indices], -x_masked[put_indices]))]
    else:
        sorted_put_indices = np.array([], dtype=int)
    if call_indices.size > 0:
        sorted_call_indices = call_indices[np.lexsort((y_masked[call_indices], -x_masked[call_indices]))]
    else:
        sorted_call_indices = np.array([], dtype=int)

    mask_rearrange = np.concatenate([sorted_put_indices, sorted_call_indices])
    
    x_sorted = x_masked[mask_rearrange]
    y_sorted = y_masked[mask_rearrange]
    z_sorted = z_masked[mask_rearrange]        
    mask = x_sorted > 0
    x_sorted[~mask] = -1 * x_sorted[~mask]  
    x_sorted[mask] = 1 - x_sorted[mask]  
    return x_sorted, y_sorted, z_sorted, mask_removal, mask_rearrange
        

class MetricFunctionGenerator:
    def __init__(self, only_1_underyling):
        self.only_1_underyling=only_1_underyling
        self.metric_functions = {"expiry": self.null_metric,
                                "years": self.years_metric_func,
                                "delta": self.delta_metric_mask_sorter,
                                "strike": self.null_metric,
                                "moneyness": self.moneyness_mask_sorter,
                                "log_moneyness": self.moneyness_mask_sorter,
                                "standardised_moneyness": self.moneyness_mask_sorter,
                                "IVOL": self.null_metric,
                                "IVOL_perc": self.IVOL_perc_function,
                                "TVAR": self.TVAR_function,
                               }
        
        self.metric_label_map, self.label_metric_map = get_attributes_labels()

        if self.only_1_underyling:
            self.metric_functions["moneyness"] = self.moneyness_spot
            self.metric_functions["log_moneyness"] = self.log_moneyness_spot
            
                            
    def get_function(self, axis_metric):
        return self.metric_functions[axis_metric]
    
    def get_spot_metric_functions(self):
        spot_metric_functions = self.get_metric_functions()
        return spot_metric_functions
    
    @staticmethod
    def null_metric(raw_object, x, y, z):
        return x, y, z, [True] * z.size, np.arange(z.size)
    
    @staticmethod
    def _base_money_sorter(raw_object, x, y, z):
        mask_removal = raw_object.OTM
        x, y, z = x[mask_removal], y[mask_removal], z[mask_removal]
        mask_rearrange = np.lexsort((x, y))
        return x[mask_rearrange], y[mask_rearrange], z[mask_rearrange], mask_removal, mask_rearrange
    
    @staticmethod
    def TVAR_function(raw_object, x, y, z):
        return x, y, z * utils.convert_unix_maturity_to_years(y), [True] * z.size, np.arange(z.size)
    
    @staticmethod
    def IVOL_perc_function(raw_object, x, y, z):
        return x, y, 100 * z, [True] * z.size, np.arange(z.size)
    
    def moneyness_mask_sorter(self, raw_object, x, y, z):
        x = raw_object.moneyness
        return self._base_money_sorter(raw_object, x, y, z)
    
    def log_moneyness_mask_sorter(self, raw_object, x, y, z):
        x = raw_object.log_moneyness
        return self._base_money_sorter(raw_object, x, y, z)
    
    def standardised_moneyness_sorter(self, raw_object, x, y, z):
        x = raw_object.standardised_moneyness
        return self._base_money_sorter(raw_object, x, y, z)
    
    @staticmethod
    def years_metric_func(raw_object, x, y, z):
        return x, utils.convert_unix_maturity_to_years(y), z, [True] * z.size, np.arange(z.size)
    
    @staticmethod
    def moneyness_spot(raw_object, x, y, z):
        return raw_object.moneyness, y, z, [True] * z.size, np.arange(z.size)
    
    @staticmethod
    def log_moneyness_spot(raw_object, x, y, z):
        return raw_object.log_moneyness, y, z, [True] * z.size, np.arange(z.size)
    
    def delta_metric_mask_sorter(self, raw_object, x, y, z):
        mask_removal = raw_object.OTM & (raw_object.delta_mag < 0.5)
        x, x_masked, y_masked, z_masked = raw_object.delta, raw_object.delta[mask_removal], y[mask_removal], z[mask_removal]
        put_indices = np.where(~raw_object.call_flag[mask_removal])[0]
        call_indices = np.where(raw_object.call_flag[mask_removal])[0]
        
        sorted_put_indices = put_indices[np.lexsort((y_masked[put_indices], -x_masked[put_indices]))] if put_indices.size > 0 else np.array([], dtype=int)
        sorted_call_indices = call_indices[np.lexsort((y_masked[call_indices], -x_masked[call_indices]))] if call_indices.size > 0 else np.array([], dtype=int)
        
        mask_rearrange = np.concatenate([sorted_put_indices, sorted_call_indices])
        x_sorted, y_sorted, z_sorted = x_masked[mask_rearrange], y_masked[mask_rearrange], z_masked[mask_rearrange]
        mask = x_sorted > 0
        x_sorted[~mask] = -x_sorted[~mask]
        x_sorted[mask] = 1 - x_sorted[mask]
        return x_sorted, y_sorted, z_sorted, mask_removal, mask_rearrange
    
    
def create_axis_items(widget=None, n_ticks=None):    
    def _create_add_2D_axis_item(ax_manager, title, orientation, axis_3D_direction):
        axis_item = axis_widgets.CustomAxisItem(axis_3D_direction=axis_3D_direction, orientation=orientation) 
        axis_item.setTitle(title)
        ax_manager.add_2D_axis_item(axis_item, axis_3D_direction)
        
    axis_manager = axis_widgets.AxisManager(widget, n_ticks)

    _create_add_2D_axis_item(axis_manager, "Strike", "bottom", "x")
    _create_add_2D_axis_item(axis_manager, "Expiry", "bottom", "y")
    
    _create_add_2D_axis_item(axis_manager, "Implied Volatility", "left", "z")
    _create_add_2D_axis_item(axis_manager, "Implied Volatility", "left", "z")
    
    grid_manager = axis_widgets.GridManager(widget)
    return axis_manager, grid_manager
