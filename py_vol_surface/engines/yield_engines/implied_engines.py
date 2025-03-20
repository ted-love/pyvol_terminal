import numpy as np
from scipy.interpolate import PchipInterpolator, make_interp_spline
from ... import utils
import math
from pprint import pprint


def implied_q_from_PC_BSM(C,P,r,T,S,K):
    q = math.log((C - P + K*np.exp(-r*T))/S)/-T
    return q

def implied_forward_rate(F_1, F_2, T_1, T_2):
    return math.log(F_2 / F_1) / (T_2 - T_1)

def implied_q_from_futures(F, S, T, r):
    return r - math.log(F / S)/T

def implied_r_from_futures(F, S, T, q):
    return q + math.log(F / S)/T

def get_implied_from_PC_black(C, P, F, K, T):
    return - math.log((C-P) / (F - K)) / T

class ImpliedFromFuture:
    def __init__(self, model_type, instrument_manager, bid_key="bid", ask_key="ask", given_rate_engine=None):
        self.bid_key=bid_key
        self.ask_key=ask_key
        self.instrument_manager=instrument_manager
        self.model_type=model_type
        self.given_rate_engine=given_rate_engine
        self.instrument_to_idx_map={}
        self.spot_future_name_map={}
        self.mean_discretisation_steps=20
        self._null_arr = np.array([0] * self.mean_discretisation_steps)
        self.interpolator = lambda x: self._null_arr 
        self._expiry_min = None

        if self.model_type == "black":
            self.calculate_implied_yield = implied_r_from_futures
        elif self.model_type == "black_scholes_merton":
            self.calculate_implied_yield = implied_q_from_PC_BSM    
        
        if given_rate_engine is None:
            self.given_rate_engine=DummyYieldClass()
        
        self._setup()
    
    def _setup(self):        
        self._n_future = len(self.instrument_manager.futures)
        self.expiry_arr = np.nan * np.empty(self._n_future)
        self.bid_arr = np.nan * np.empty(self._n_future)
        self.ask_arr = np.nan * np.empty(self._n_future)
        self.mid_arr = np.nan * np.empty(self._n_future)
        self.imp_rate = np.nan * np.empty(self._n_future)   
        self.spot_arr = np.nan * np.empty(self._n_future)   
        
        for idx, (instrument_name, instrument_object) in enumerate(self.instrument_manager.futures.items()):
            self.instrument_to_idx_map[instrument_name] = idx
            spot_name = instrument_object.underlying_object.instrument_name
            if spot_name in self.spot_future_name_map:
                self.spot_future_name_map[spot_name].append(instrument_name)
            else:
                self.spot_future_name_map[spot_name] = [instrument_name]
            self.expiry_arr[idx] = float(instrument_object.expiry)
            if self._expiry_min is None:
                self._expiry_min = instrument_object.expiry
            else:
                if instrument_object.expiry < self._expiry_min:
                    self._expiry_min=instrument_object.expiry
                    
    def update_data(self, websocket_responses):
        for instrument_name, price_dict in websocket_responses.items():
            self._internal_updater(instrument_name, price_dict[self.bid_key], price_dict[self.ask_key])

    def _internal_updater(self, instrument_name, bid_price, ask_price):
        
        asset_object=self.instrument_manager.all_instrument_objects[instrument_name]
        asset_object.update_price(bid_price, ask_price, callbacks=False)
        if instrument_name in self.instrument_to_idx_map:
            idx = self.instrument_to_idx_map[instrument_name]
            yte = utils.convert_unix_maturity_to_years(asset_object.expiry)
            self.imp_rate[idx] = self.calculate_implied_yield(asset_object.mid,
                                                            asset_object.underlying_object.mid,
                                                            yte,
                                                            self.given_rate_engine.evaluate(yte))
        if instrument_name in self.spot_future_name_map:
            for future_names in self.spot_future_name_map[instrument_name]:
                future_object=self.instrument_manager.all_instrument_objects[future_names]
                idx = self.instrument_to_idx_map[future_names]
                yte = utils.convert_unix_maturity_to_years(future_object.expiry)
                self.imp_rate[idx] = self.calculate_implied_yield(future_object.mid,
                                                                future_object.underlying_object.mid,
                                                                yte,
                                                                self.given_rate_engine.evaluate(yte))

                
                
                
    def fit(self):
        yte = utils.convert_unix_maturity_to_years(self.expiry_arr)
        x, y = utils.filter_nans_2D(yte, self.imp_rate)
        if x.size > 2:
            if np.all(np.diff(self.imp_rate) >= 0):
                self.interpolator = PchipInterpolator(x, y)
            else:
                self.interpolator = make_interp_spline(x, y, k=2)
        else:
            self.interpolator = lambda x: self._null_arr
        
    def evaluate(self, yte):
        xi = np.linspace(utils.convert_unix_maturity_to_years(self._expiry_min), yte, 20)
        return self.interpolator(xi).sum() / 20
        

class ImpliedFromOption:
    def __init__(self, model_type, instrument_manager=None, bid_key="bid", ask_key="ask"):
        if model_type == "black":
            self.calculate_implied_yield = get_implied_from_PC_black
        elif model_type == "black_scholes_merton":
            self.calculate_implied_yield = implied_q_from_PC_BSM

        self.instrument_manager=instrument_manager        
        self.exp_yield = {}
        self.expiry_option_pair_map = {}
        self.expiry_opt_list_map = {}
        self.bid_key=bid_key
        self.ask_key=ask_key
        self._find_mid_strike()
        self.mean_discretisation_steps=20
        self._null_arr = np.array([0] * self.mean_discretisation_steps)
    
    def _find_mid_strike(self,):
        strikes = []
        for option_object in self.instrument_manager.options.values():
            strikes.append(option_object.strike)
        self._median_strike = np.median(strikes)
    
    def _find_closest_option(self, option_name_list):
        def _finding(option_name_list, default_val=None):
            smallest_abs_diff = 1e10
            smallest_diff_instrument_name = None
            for option_name in option_name_list:
                option_object = self.instrument_manager.options[option_name]
                if default_val:
                    abs_diff = abs(option_object.strike - default_val)
                else: 
                    abs_diff = abs(option_object.strike - option_object.underlying_object.mid) 
                if abs_diff < smallest_abs_diff:
                    smallest_abs_diff = abs_diff 
                    smallest_diff_instrument_name = option_name
            return smallest_diff_instrument_name
        smallest_diff_instrument_name = _finding(option_name_list)
        if smallest_diff_instrument_name is None:
            smallest_diff_instrument_name = _finding(option_name_list, self._median_strike)
        return smallest_diff_instrument_name
    
    def _create_constructor(self):
        for opt1_name, opt2_name in self.instrument_manager.options_maps.put_call_map.items():
            option_object1 = self.instrument_manager.options[opt1_name]
            expiry = option_object1.expiry
            
            if expiry in self.expiry_opt_list_map:
                list_for_specific_expiry = self.expiry_opt_list_map[expiry]
                if not opt2_name in list_for_specific_expiry:    # checking if the put or call with same expiry and maturity is already in dict.
                    self.expiry_opt_list_map[expiry].append(opt1_name)
            else:
                self.expiry_opt_list_map[expiry] = [opt1_name]
        
        self.expiry_opt_list_map = {key: self.expiry_opt_list_map[key] for key in sorted(self.expiry_opt_list_map)}
        
        for expiry, option_name_list in self.expiry_opt_list_map.items():
            smallest_diff_instrument_name = self._find_closest_option(option_name_list)
            
            if not smallest_diff_instrument_name is None:
                smallest_option_object = self.instrument_manager.options[smallest_diff_instrument_name]
                
                if smallest_option_object.flag_int == 1:
                    call_object = smallest_option_object
                    put_name = self.instrument_manager.options_maps.put_call_map[call_object.instrument_name]
                    put_object = self.instrument_manager.options[put_name]
                else:
                    put_object = smallest_option_object
                    call_name = self.instrument_manager.options_maps.put_call_map[put_object.instrument_name]
                    call_object = self.instrument_manager.options[call_name]

                temp_dict = {"call" : call_object,
                             "put" : put_object}

                self.expiry_option_pair_map[expiry] = temp_dict
        
    def _create_yield_curve(self,):
        yte_arr = []
        yield_arr = []
        print(f"\n_create_yield_curve")
        for expiry, object_dict in self.expiry_option_pair_map.items():
            call_object = object_dict["call"]
            put_object = object_dict["put"]
            yte = utils.convert_unix_maturity_to_years(expiry)
            dividend = get_implied_from_PC_black(call_object.mid,
                                                 put_object.mid,
                                                 call_object.underlying_object.mid,
                                                 call_object.strike,
                                                 yte)
            if not np.isnan(dividend):
                print(np.array((call_object.mid,
                                                 put_object.mid,
                                                 call_object.underlying_object.mid,
                                                 call_object.strike,
                                                 yte)))
                print(f"\ndividend: {dividend}")
                self.exp_yield[expiry] = dividend
                yte_arr.append(yte)
                yield_arr.append(dividend)
                
        return np.array(yte_arr), np.array(yield_arr)   

    def update_data(self, websocket_responses):
        for instrument_name, price_dict in websocket_responses.items():
            self._internal_updater(instrument_name, price_dict[self.bid_key], price_dict[self.ask_key])
                    
    def _internal_updater(self, instrument_name, bid_price, ask_price):
        option_object=self.instrument_manager.all_instrument_objects[instrument_name]
        option_object.update_price(bid_price, ask_price, callbacks=False)
            
    def fit(self):
        self._create_constructor()
        yte_arr, yield_arr = self._create_yield_curve()        
        if len(self.exp_yield) > 2:
            if np.all(np.diff(yield_arr) >= 0):
                self.interpolator = PchipInterpolator(yte_arr, yield_arr)
            else:
                self.interpolator = make_interp_spline(yte_arr, yield_arr, k=2)
        else:
            self.interpolator = lambda x: self._null_arr 
        xi = np.linspace(0, 1, 20)
        print("\nevaluate")
        print(np.round(self.interpolator(xi), 3))

    def evaluate(self, yte):
        xi = np.linspace(0, yte, 20)
        return self.interpolator(xi).sum() / 20


class DummyYieldClass:
    def __init__(self):
        pass
    
    def evaluate(self, x):
        return 0