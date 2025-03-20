from py_vol_surface import surface_plotter
from py_vol_surface import utils
from py_vol_surface import instruments
from py_vol_surface.engines.option_engines import black_scholes_merton
from py_vol_surface.engines.yield_engines import implied_engines
from py_vol_surface import interpolation_engines
from examples.bybit import websocket_streamer
import queue


def main():
    ws_option_url = "wss://stream.bybit.com/v5/public/option"
    ws_spot_url = "wss://stream.bybit.com/v5/public/spot"

    websocket_json_format = utils.create_websocket_json_formatter("symbol",
                                                                  "bidPrice",
                                                                  "askPrice",
                                                                  "ts"
                                                                  )
    
    channels, df_options, df_spot, option_underlying_name_map = websocket_streamer.get_bybit_tickers()

    q = queue.Queue()
    ws = websocket_streamer.Streamer(ws_option_url, ws_spot_url, channels, q)

    starting_price_type="mid"
    
    data_config = {"df_options" : df_options,
                   "df_spot" : df_spot
                  }
    
    plotting_config = {"timer_update_plot" : 0 # set to 0 since we want plot as soon as timer_ws_response is completed. If websocket_config["timer_ws_response"] = 0, then there will be no buffering in the plotting after each ws response
                      }
    
    data_processing_config = {"websocket_json_format" : websocket_json_format,
                              "timer_process_data" : 0,  # set to 0 since we want process data as soon as timer_ws_response is completed. If websocket_config["timer_ws_response"] = 0, then there will be no buffering in the data processing after each ws response
                             }
    
    websocket_config = {"parallel_type": "threading",
                        "ws_transport_method" : "queue",
                        "start_ws_func_name": "start_websocket",
                        "price_generator": ws,
                        "multiple_levels": False,
                        "timer_ws_response" : 2,
                        "bulk_response" : False,
                        "q" : q,
                       }

    option_config = {"object" : instruments.Option,
                    "underlying_map": option_underlying_name_map,
                    "engine": black_scholes_merton.Engine,
                    "valid_price_checker" : utils.ValidPriceChecker(30).check
                    }
    
    colour_styles_config = {"scatter" : {"bid" : (1,0,0,1), "ask" : (0, 0, 1, 1), "mid" : (1, 1, 1, 1)},
                            "surface" :  {"bid" : "inferno", "ask" : "inferno", "mid" : "inferno"},
                            }
    
    interpolation_config = {"engine" : interpolation_engines.CustomBSplineInterpolator(),
                            "n_x": 40,
                            "n_y": 30,
                            }    
        
    interest_rate_config = {}  # Do not require as inputs, will force r=0
    dividend_rate_config = {}  # Do not require as inputs, will force q=0
    
    surface_plotter.plot_surface(starting_price_type=starting_price_type,
                                 plotting_config=plotting_config,
                                 data_config=data_config,
                                 websocket_config=websocket_config,
                                 data_processing_config=data_processing_config,
                                 option_config=option_config,
                                 interpolation_config=interpolation_config,
                                 colour_styles_config=colour_styles_config,
                                )
if __name__ == '__main__':
    main()