from . import utils
import numpy as np
import time
import math
import pandas as pd
from dataclasses import dataclass
from typing import Dict


class _BaseInstrument:
    def __init__(self, instrument_name, valid_price_checker=utils.ValidPriceChecker(20).check):
        self.instrument_name = instrument_name
        self.bid = np.nan
        self.ask = np.nan
        self.mid = np.nan
        self.spread_perc=np.nan
        self._metric_callbacks=[]
        self.last_update_time=time.time()
        self.valid_price=False
        self.valid_price_checker=valid_price_checker
            
    def add_metric_callback(self, callback):
        self._metric_callbacks.append(callback)
        
    def update_price(self, bid=None, ask=None, callbacks=True): 
        if bid != None and ask != None:
            self.bid = np.nan if bid==0. else bid
            self.ask = np.nan if ask==0. else ask
            self.mid = 0.5 * (self.bid + self.ask)
            self.spread_perc = 100 * (self.ask - self.bid) / self.mid
            
            if self.valid_price_checker(bid, ask):
                self.valid_price=True
            else:
                self.valid_price=False
            if callbacks:
                for callback in self._metric_callbacks:
                    callback()
        self.last_update_time = time.time()
        

class Spot(_BaseInstrument):
    def __init__(self, *args):
        self.category="spot"
        super().__init__(*args)


class Future(_BaseInstrument):
    def __init__(self, instrument_name, underlying_object, expiry,
                 interest_rate_engine=None, dividend_rate_engine=None, **kwargs):
        super().__init__(instrument_name)
        self.underlying_object=underlying_object
        self.expiry=expiry
        self.interest_rate_engine=interest_rate_engine
        self.dividend_rate_engine=dividend_rate_engine
        self.category="future"
    
    def get_forward_rate(self,):
        yte = utils.convert_unix_maturity_to_years(self.expiry)         
        self.forward_rate = np.log(self.mid / self.underlying_object.mid) / yte
        

class Option(_BaseInstrument):
    def __init__(self, instrument_name, underlying_object, strike, expiry, flag, flag_int, option_engine,
                 valid_price_checker=utils.ValidPriceChecker(20).check, **kwargs):
        super().__init__(instrument_name, valid_price_checker)
        self.underlying_object=underlying_object
        self.category="option"
        self.strike=strike
        self.expiry=expiry
        self.flag=flag
        self.flag_int=flag_int
        self.IVOL= np.nan*np.zeros(3)
        self.delta= np.nan* np.zeros(3)
        self.delta_mag= np.nan * np.zeros(3)
        self.gamma=np.nan* np.zeros(3)
        self.vega=np.nan*np.zeros(3)
        self.rho=np.nan*np.zeros(3)
        self.theta=np.nan*np.zeros(3)
        self.moneyness=np.nan
        self.log_moneyness=np.nan
        self.standardised_moneyness=np.nan* np.zeros(3)
        self.OTM=np.nan
        self.option_engine=option_engine
        self._nan_3_numpy = np.nan * np.empty(3)
        self.call_flag= True if flag_int == 1 else False
        
        self.price_type_idx_map = {"bid" : 0,
                                   "ask" : 1,
                                   "mid" : 2}
        
        self.add_metric_callback(self._OTM_checker)
        self.add_metric_callback(self.calculate_implied_volatility)
        self.add_metric_callback(self.calculate_all_greeks)
        self.add_metric_callback(self.calculate_all_moneyness)
    
    def _OTM_checker(self,):
        if self.underlying_object.valid_price:
            if self.flag_int == 1:
                if self.underlying_object.mid < self.strike:
                    self.OTM=True
                else:
                    self.OTM=False
            else:
                if self.underlying_object.mid < self.strike:
                    self.OTM=False
                else:
                    self.OTM=True

    def get_all_metrics(self):
        return self.IVOL, self.delta, self.delta_mag, self.gamma, self.vega, self.moneyness, self.log_moneyness,\
                self.standardised_moneyness, self.OTM, self.call_flag
        
    def calculate_implied_volatility(self,):
        if self.underlying_object.valid_price:
            if self.valid_price and self.OTM==True:
                self.IVOL = self.option_engine.calculate_IVOL([self.bid, self.ask, self.mid],
                                                              self.underlying_object.mid,)

    def calculate_all_greeks(self):
        if self.valid_price and self.underlying_object.valid_price:
            self.delta, self.gamma, self.vega, self.theta, self.rho = self.option_engine.calculate_all_greeks(self.IVOL,
                                                                                                             self.underlying_object.mid)
            self.delta_mag = np.abs(self.delta)
        else:
            self.delta, self.gamma, self.vega, self.theta, self.rho, self.delta_mag = [self._nan_3_numpy] * 6

    def calculate_delta(self,):
        self.delta = self.option_engine.calculate_delta(self.IVOL,
                                                       self.underlying_object.mid,
                                                       )
        self.delta_mag = np.abs(self.delta)

    def calculate_gamma(self,):
        self.gamma = self.option_engine.calculate_gamma(self.IVOL,
                                                       self.underlying_object.mid,
                                                       )
    def calculate_vega(self,):
        self.vega = self.option_engine.calculate_vega(self.IVOL,
                                                     self.underlying_object.mid,
                                                    )
        
    def calculate_all_moneyness(self,):
        if self.underlying_object.valid_price:
            self.moneyness = self.strike / self.underlying_object.mid
            self.log_moneyness = np.log(self.moneyness)
            self.standardised_moneyness = self.log_moneyness / (self.IVOL * math.sqrt(utils.convert_unix_maturity_to_years(self.expiry)))
        else:
            self.moneyness=np.nan
            self.log_moneyness=np.nan
            self.standardised_moneyness = self._nan_3_numpy.copy()
            
    def calculate_standardised_moneyness(self,):
        self.standardised_moneyness = np.log(self.underlying_object.mid / self.strike) / (self.IVOL * math.sqrt(utils.convert_unix_maturity_to_years(self.expiry)))
        
    def calculate_log_moneyness(self,):
        self.log_moneyness = np.log(self.underlying_object.mid/ self.strike)

    def calculate_moneyness(self,):
        self.moneyness = self.strike / self.underlying_object.mid


class OptionInverted(Option):
    def update_price(self, bid=None, ask=None, **kwargs):
        if not np.isnan(self.underlying_object.mid):
            if bid != None and ask != None:
                super().update_price(bid * self.underlying_object.mid, ask * self.underlying_object.mid, **kwargs)  
            else:
                super().update_price(bid=bid, ask=ask, **kwargs)
    
        
@dataclass(slots=True, frozen=True)
class BaseMap:
    index_name_map: dict
    name_index_map: dict
    
    
@dataclass(slots=True, frozen=True)
class OptionMap(BaseMap):
    put_call_map: dict
    
    
class InstrumentManager:
    def __init__(self):
        self.futures = {}
        self.spot = {}
        self.options = {}
        self.maps = {}
        self.name_to_instrument_type = {}
        self.futures_maps: BaseMap
        self.options_maps: OptionMap
        self.all_instrument_objects = {}
        self.options_1_underlying_flag=False
        self.options_underlying_object=None
        
    def create_spot_object(self, df_spot):
        if not df_spot is None:
            obj = Spot(df_spot["instrument_name"].item())
            self.spot[df_spot["instrument_name"].item()] = obj
            self.name_to_instrument_type[df_spot["instrument_name"].item()] = "spot"
            self.all_instrument_objects[df_spot["instrument_name"].item()] = obj
            if len(self.spot) == 1:   
                self.options_1_underlying_flag=True
            else:
                self.options_1_underlying_flag=False

                        
    def create_future_objects(self, df_futures, future_config, interest_rate_engine=None, dividend_rate_engine=None):        
        for idx in df_futures.index:
            future_row = df_futures.loc[idx]
            instrument_name = future_row["instrument_name"]
            expiry = future_row["expiry"]
            self.name_to_instrument_type[instrument_name] = "futures"    

            if "underlying_map" in future_config:
                if isinstance(future_config["underlying_map"], str):
                    underlying_object = self.all_instrument_objects[future_config["underlying_map"]]
                elif isinstance(future_config["underlying_map"], Dict):
                    underlying_object = self.all_instrument_objects[future_config["underlying_map"][instrument_name]]
                else:
                    raise KeyError("You have specified an underyling map, but the underlying object has not been instantiated yet. Make sure underlying objects are instantiated first.")
            else:   
                underlying_object=None
            
            args = [instrument_name, underlying_object, expiry]
            if interest_rate_engine:
                args.append(interest_rate_engine)
            if dividend_rate_engine:
                args.append(dividend_rate_engine)
            
            future_object = future_config["object"](*args)
            
            self.futures[instrument_name]=future_object
            self.all_instrument_objects[instrument_name]=future_object
            
        self.futures_maps = self._create_maps(self.futures)
        
    def create_option_objects(self, df_options, option_config, interest_rate_engine, dividend_rate_engine):
        df_options["strike"] = pd.to_numeric(df_options["strike"], errors='coerce')
        df_options["expiry"] = pd.to_numeric(df_options["expiry"], errors='coerce')

        for idx in df_options.index:
            opt = df_options.loc[idx]
            instrument_name = opt["instrument_name"]
            
            if "underlying_map" in option_config:
                if isinstance(option_config["underlying_map"], str):
                    underlying_object = self.all_instrument_objects[option_config["underlying_map"]]
                    self.options_underlying_object = underlying_object
                    self.options_1_underlying_flag=True
                elif isinstance(option_config["underlying_map"], Dict):
                    underlying_object = self.all_instrument_objects[option_config["underlying_map"][instrument_name]]     
            else:
                underlying_object_list = list(self.spot.values())
                if len(underlying_object_list) != 1:
                    raise KeyError("You need to specify an underyling for the options if you have multiple spot objects")
                else:
                    underlying_object = underlying_object_list[0]
                    self.options_underlying_object=underlying_object
                    self.options_1_underlying_flag=True
                    
            self.name_to_instrument_type[instrument_name] = "options"    

            flag=opt["flag"]
            flag_int = 1 if flag=="c" else -1
            
            args = [opt["strike"], opt["expiry"], flag]
            kwargs = {"flag_int" : flag_int}
            kwargs["interest_rate_engine"]=interest_rate_engine
            kwargs["dividend_rate_engine"]=dividend_rate_engine

            opt_engine = option_config["engine"](*args, **kwargs)
            option = option_config["object"](instrument_name,
                                             underlying_object,
                                             opt["strike"],
                                             opt["expiry"],
                                             opt["flag"],
                                             flag_int,
                                             opt_engine,
                                             **option_config,
                                             )
            
            self.options[instrument_name]=option
            self.all_instrument_objects[instrument_name]=option
        
        put_call_pair_map = {}
        
        for opt_name1, object1 in self.options.items():
            for opt_name2, object2 in self.options.items():
                if object1.instrument_name != object2.instrument_name:
                    if object1.strike == object2.strike and object1.expiry==object2.expiry:
                        put_call_pair_map[opt_name1]=opt_name2
        
        temp_base = self._create_maps(self.options)
        self.options_maps = OptionMap(temp_base.index_name_map, temp_base.name_index_map, put_call_pair_map)
                
        if self.options_underlying_object is None:
            underlying_list = np.unique(list(option_config["underlying_map"].values()))
            if len(underlying_list) == 1:
                self.options_1_underlying_flag=True
                self.options_underlying_object=self.all_instrument_objects[underlying_list[0]]
            else:
                self.options_1_underlying_flag=False
            
    def _create_maps(self, instrument_object_dict):        
        index_name_map = {idx: name for idx, name in enumerate(instrument_object_dict)}
        name_index_map = {name: idx for idx, name in enumerate(instrument_object_dict)}
        return BaseMap(index_name_map, name_index_map)
    
    def ensure_pair_OTM_flag(self, instrument_name, OTM_flag):
        if instrument_name in self.options_maps.put_call_map:
            pair_object_name = self.options_maps.put_call_map[instrument_name]
            pair_object = self.options[pair_object_name]
            
            if OTM_flag == pair_object.OTM:
                pair_object.OTM = not OTM_flag
                
                
def create_instrument_objects(data_config, option_config, future_config=None, interest_rate_engine=None, dividend_rate_engine=None):
    instrument_manager = InstrumentManager()
    
    if "df_spot" in data_config:
        df_spot = _cleanup_dataframe(data_config["df_spot"], "spot")
        instrument_manager.create_spot_object(df_spot)
    else:
        df_spot=None
    
    if "df_futures" in data_config:
        df_futures = _cleanup_dataframe(data_config["df_futures"], "futures")        
        instrument_manager.create_future_objects(df_futures,
                                                 future_config,
                                                 interest_rate_engine=interest_rate_engine,
                                                 dividend_rate_engine=dividend_rate_engine,
                                                 )
    else:
        df_futures=None

    df_options = _cleanup_dataframe(data_config["df_options"], "options")
    instrument_manager.create_option_objects(df_options,
                                             option_config,
                                             interest_rate_engine=interest_rate_engine,
                                             dividend_rate_engine=dividend_rate_engine)
     
    return instrument_manager, df_options, df_futures, df_spot 

def _cleanup_dataframe(df, df_type):
    if df_type == "options":
        df = df.sort_values(by=["expiry", "strike", "flag"], ascending=[True, True, False])
        df.reset_index(drop=True, inplace=True)
    elif df_type == "futures" or df_type == "options":
        df = df.sort_values(by=["expiry"], ascending=[True])
    
    numeric_columns = ["strike", "expiry", "bid", "ask", "mid"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df    