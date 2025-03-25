from py_vol_surface import surface_plotter
from py_vol_surface import utils
from py_vol_surface import instruments
from py_vol_surface.engines.option_engines import black
from py_vol_surface.engines.yield_engines import implied_engines
from py_vol_surface import interpolation_engines
from examples.deribit import websocket_streamer


def main():
    url = "wss://www.deribit.com/ws/api/v2"
    
    websocket_json_format = utils.create_websocket_json_formatter("instrument_name",
                                                                  "best_bid_price",
                                                                  "best_ask_price",
                                                                  "timestamp")
    channels, df_options, df_futures, df_spot, option_underlying_name_map, future_underlying_name_map = websocket_streamer.generate_option_channels()
    
    ws = websocket_streamer.Streamer(url, channels, spot_flag=True, future_flag=True)
        
    starting_price_type="mid"
    
    data_config = {"df_options" : df_options,
                   "df_futures" : df_futures,
                   "df_spot" : df_spot,
                   }
    
    plotting_config = {"timer_update_plot" : 2 # set to 2 since ws_transport_method is yield and therefore no wait time between plots unless specified with timer_update_plot
                      }
    
    data_processing_config = {"websocket_json_format" : websocket_json_format,
                              "timer_process_data" : 2,  # set to 2 since ws_transport_method is yield and therefore no buffer unless specified with timer_process_data
                             }
    
    websocket_config = {"parallel_type": "async",
                        "ws_transport_method" : "yield",
                        "start_ws_func_name": "start_websocket",
                        "price_generator": ws,
                        "multiple_levels": False,
                        "timer_ws_response" : 2,
                        "bulk_response" : False
                        }

    option_config = {"object" : instruments.OptionInverted,
                     "underlying_map": option_underlying_name_map,
                     "engine": black.Engine,
                     "valid_price_checker" : utils.ValidPriceChecker(50).check
                    }
    
    future_config = {"object" : instruments.Future,
                     "underlying_map" : future_underlying_name_map}
    

    colour_styles_config = {"scatter" : {"bid" : (1,0,0,1), "ask" : (0, 0, 1, 1), "mid" : (1, 1, 1, 1)},
                            "surface" : {"bid" : "inferno", "ask" : "inferno", "mid" : "inferno"},
                            }
    
    interpolation_config = {"engine" : interpolation_engines.CustomBSplineInterpolator(),
                            "n_x": 40,
                            "n_y": 30,
                            }  
      
    interest_rate_config = {}  # Do not require as inputs, will force r=0
    dividend_rate_config = {}  # Do not require as inputs, will force q=0
    
    """
    instrument_manager, _, _, _ = instruments.create_instrument_objects(data_config, option_config, future_config)
    
    interest_rate_config = {"engine" : implied_engines.ImpliedFromOption("black", instrument_manager, "best_bid_price", "best_ask_price"),
                            "use_ws_response" : True,
                            "instrument_list" : df_options["instrument_name"].to_list() + df_futures["instrument_name"].to_list(),
                            }
    
    interest_rate_config = {"engine" : implied_engines.ImpliedFromFuture("black", instrument_manager, "best_bid_price", "best_ask_price"),
                            "use_ws_response" : True,
                            "instrument_list" : df_futures["instrument_name"].to_list() + df_spot["instrument_name"].to_list(),
                            }
    """
    surface_plotter.plot_surface(starting_price_type=starting_price_type,
                                 plotting_config=plotting_config,
                                 data_config=data_config,
                                 websocket_config=websocket_config,
                                 data_processing_config=data_processing_config,
                                 option_config=option_config,
                                 future_config=future_config,
                                 interpolation_config=interpolation_config,
                                 colour_styles_config=colour_styles_config,
                                )
if __name__ == '__main__':
    main()