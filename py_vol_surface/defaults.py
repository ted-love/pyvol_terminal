from py_vol_surface.engines.option_engines import base
from py_vol_surface.engines.yield_engines import implied_engines


def update_config(config):
    _check_data_config(config)
    
    if not "starting_price_type" in config: 
        config["starting_price_type"]="mid"
    
    if "df_spot" in config["data_config"]:
        config["spot_flag"]=True
    else:
        config["spot_flag"]=False
    
    if not "colour_styles_config" in config:
        config["colour_styles_config"] = {"scatter" : {"bid" : (1,0,0,1), "ask" : (0, 0, 1, 1), "mid" : (1, 1, 1, 1)},
                                          "surface" : {"bid" : "inferno", "ask" : "inferno", "mid" : "inferno"},
                                         }
    _check_option_config(config)
    _check_yield_configs(config)


def _check_data_config(config):
    data_config = config["data_config"]
    
    if not "df_options" in data_config and not "df_futures" in data_config:
        raise
    
def _check_yield_configs(config):
    if not "interest_rate_config" in config:
        config["interest_rate_config"] = {"engine" : implied_engines.DummyYieldClass(),
                                          "use_ws_response" : False}
    else:
        if not "engine" in config["interest_rate_config"]:
            config["interest_rate_config"] = {"engine" : implied_engines.DummyYieldClass(),
                                               "use_ws_response" : False}
            
    if not "dividend_rate_config" in config:
        config["dividend_rate_config"] = {"engine" : implied_engines.DummyYieldClass(),
                                          "use_ws_response" : False}
    else:
        if not "engine" in config["dividend_rate_config"]:
            config["dividend_rate_config"] = {"engine" : implied_engines.DummyYieldClass(),
                                              "use_ws_response" : False}

    
def _check_option_config(config):
    pass


