import surface_plotter 
import utils
import ws_deribit
import sys
import traceback
import custom_interpolators
import option_engines
import term_structures
import instruments

def exception_handler(exc_type, exc_value, exc_tb):
    print("Uncaught exception:")
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = exception_handler

if __name__ == '__main__':
    url = "wss://www.deribit.com/ws/api/v2"
    
    websocket_json_format = utils.create_websocket_json_formatter("instrument_name",
                                                                  "best_bid_price",
                                                                  "best_ask_price",
                                                                  "timestamp"
                                                                  )
    
    channels, df_options, df_futures, df_spot, option_underlying_name_map, future_underlying_name_map = ws_deribit.generate_option_channels()
    
    spot_flag=True
    future_flag=True
    
    generator_args = []
    
    ws = ws_deribit.Streamer(url, channels, spot_flag, future_flag)
        
    timer_plot_update = 2
    
    surface_colour_style="inferno"

    price_generator=ws
    queue_flag=False
    multiple_levels=False
    
    def rate(_):return 0
    
    class interest_rate_engine:
        def __init__(self):
            pass
        def evaluate(x):
            return 0.
    
    interpolator_engine = custom_interpolators.CustomBSplineInterpolator()

    starting_price_type="mid"
    
    data_config = {"df_options" : df_options,
                   "df_futures" : df_futures,
                   "df_spot" : df_spot,
                   }

    data_processing_config = {"websocket_json_format" : websocket_json_format,
                              "timer_data_buffer" : 2,
                             }
    
    websocket_config = {"parallel_type": "async",
                        "ws_transport_method" : "yield",
                        "send_function_name": "ws_manager",
                        "price_generator": ws,
                        "multiple_levels": False,
                        "generator_args" : generator_args,
                        "timer_ws_transport" : 2,
                        "bulk_response" : False
                        }

    option_config = {"object" : instruments.OptionInverted,
                    "underlying_map": option_underlying_name_map,
                    "engine": option_engines.Black,
                    "valid_price_checker" : utils.ValidPriceChecker(20).check
                    }
    
    future_config = {"object" : instruments.Future,
                     "underlying_map" : future_underlying_name_map}
    

    colour_styles_config = {"scatter" : {"bid" : (1,0,0,1), "ask" : (0, 0, 1, 1), "mid" : (1, 1, 1, 1)},
                            "surface" : {"bid" : "inferno", "ask" : "inferno", "mid" : "inferno"},
                            }
    
    interpolation_config = {"engine" : interpolator_engine,
                            "n_x": 40,
                            "n_y": 30,
                            }    
    
    interest_rate_config = {"include_engine" : True,
                            "engine" : term_structures.YieldCurve(None, "best_bid_price", "best_ask_price"),
                            "use_ws_response" : True,
                            "instrument_list" : df_options["instrument_name"].to_list()
                            }
    
    interest_rate_config = {"include_engine" : False,
                            "engine" : rate,
                            "use_ws_response" : False}

    dividend_rate_config = {"include_engine" : False,
                            "engine" : rate,
                            "use_ws_response" : False}
    
    surface_plotter.plot_surface(starting_price_type=starting_price_type,
                                 data_config=data_config,
                                 websocket_config=websocket_config,
                                 data_processing_config=data_processing_config,
                                 option_config=option_config,
                                 future_config=future_config,
                                 interpolation_config=interpolation_config,
                                 interest_rate_config=interest_rate_config,
                                 dividend_rate_config=dividend_rate_config,
                                 colour_styles_config=colour_styles_config,
                                )