from PySide6 import QtCore
import asyncio
import queue
import time
import threading

class WebsocketWorker(QtCore.QThread):
    update_signal = QtCore.Signal(list, bool)  

    def __init__(self, parallel_type=None, ws_transport_method=None, price_generator=None,
                 start_ws_func_name="", q=None, multiple_levels=False,
                 timer_ws_response=2, bulk_response=False):
        super().__init__()
        self._is_running = True  
        self.parallel_type=parallel_type
        self._should_stop = False
        self.price_generator = price_generator
        self.start_ws_func_name=start_ws_func_name
        self.all_response = []
        self._should_stop = False
        self.bulk_response = bulk_response
        self.q=q
        self.loop=None
        self.task=None
        self.timer_ws_response=timer_ws_response
        self.multiple_levels=multiple_levels
        self.ws_transport_method=ws_transport_method
        self.generator_call = getattr(self.price_generator, start_ws_func_name)            
        
        if self.ws_transport_method == "queue":
            self.queue_timer = QtCore.QTimer()
            self.queue_timer.timeout.connect(self.get_queue)
            self.queue_timer.start(self.timer_ws_response * 1000)
    
    def get_queue(self):
        all_responses = []
        while True:
            try:
                response = self.q.get_nowait()
                all_responses.append(response)
            except queue.Empty:
                break 
        if len(all_responses) > 0:
            #print(f"WebsocketWorker: {threading.current_thread()}")
            self.update_signal.emit(all_responses, True)
            
    def run_threading(self,):
        self.generator_call()

    async def run_async(self,):
        async for message in self.generator_call():
            if self._should_stop:  
                break
            self.update_signal.emit([message], False)

    def run(self):
        match self.parallel_type:
            case "async":
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.run_async())
            case "threading":
                self.run_threading()
                            
    def stop(self):
        self._should_stop = True
        self._is_running = False
        self.quit()
        self.wait()

class PriceProcessor:
    def __init__(self, main_window, axis_transformer, normalisation_engine, instrument_manager, data_container_manager, websocket_json_format, 
                 interest_rate_config, dividend_rate_config, timer_process_data):
        self.main_window = main_window
        self.axis_transformer=axis_transformer
        self.normalisation_engine=normalisation_engine
        self.instrument_manager=instrument_manager
        self.data_container_manager=data_container_manager
        self.interest_rate_config=interest_rate_config
        self.dividend_rate_config=dividend_rate_config
        self.last_buffer_responses={}
        self.last_process_update=time.time()
        self.timer_process_data=timer_process_data
        self.ws_instrument_key = websocket_json_format["instrument_key"]
        self.ws_bid_key = websocket_json_format["bid_key"]
        self.ws_ask_key = websocket_json_format["ask_key"]
        self.ws_timestamp_key = websocket_json_format["timestamp_key"]
        self._last_update_checker_timer=time.time()
    
    def update_price(self, websocket_response,):
        instrument_name = websocket_response[self.ws_instrument_key]
        
        bid = websocket_response[self.ws_bid_key]
        ask = websocket_response[self.ws_ask_key]
        timestamp = websocket_response[self.ws_timestamp_key]
        asset_type = self.instrument_manager.name_to_instrument_type[instrument_name]
        
        if asset_type == "options":
            instrument_object = self.instrument_manager.options[instrument_name]
            instrument_object.update_price(bid, ask)

            for price_type, data_object in self.data_container_manager.objects.items():
                    idx = self.instrument_manager.options_maps.name_index_map[instrument_name]
                    jdx = instrument_object.price_type_idx_map[price_type]
                    data_object.raw.update_all_metrics(idx, jdx, *instrument_object.get_all_metrics(), instrument_object.valid_price)
                    self.instrument_manager.ensure_pair_OTM_flag(instrument_name, instrument_object.OTM)

        elif asset_type == "futures":
            instrument_object = self.instrument_manager.futures[instrument_name]
            instrument_object.update_price(bid, ask)
        else:
            instrument_object = self.instrument_manager.spot[instrument_name]
            instrument_object.update_price(bid, ask)

        if time.time() - self._last_update_checker_timer > 20:
            for option_object in self.instrument_manager.options.values():
                if time.time() - option_object.last_update_time > 20:
                    option_object.update_price()

    def check_enough_time(self, ):
        if time.time() - self.last_process_update > self.timer_process_data:            
            return True
        else:
            return False
    
    def bulk_response(self, websocket_responses):
        for websocket_response in websocket_responses:
            instrument_name = websocket_response[self.ws_instrument_key]
            self.last_buffer_responses[instrument_name] = websocket_response
                
    def update_response_buffer(self, websocket_response):
        instrument_name = websocket_response[self.ws_instrument_key]
        self.last_buffer_responses[instrument_name] = websocket_response

    def _update_term_structure_engine(self, term_structure_config):
        if term_structure_config["use_ws_response"]:
            coupled = set(self.last_buffer_responses.keys()) & set(term_structure_config["instrument_list"])
                        
            if len(coupled) > 0:
                filtered_responses = {ins_name : self.last_buffer_responses[ins_name] for ins_name in coupled}
                term_structure_config["engine"].update_data(filtered_responses)
                term_structure_config["engine"].fit()
                
    def update_price_with_buffer(self):
        self._update_term_structure_engine(self.interest_rate_config)
        self._update_term_structure_engine(self.dividend_rate_config)

        for instrument_name, websocket_response in self.last_buffer_responses.copy().items():
            self.update_price(websocket_response)
            del self.last_buffer_responses[instrument_name]

        self.last_buffer_responses.clear()        

        for data_object in self.data_container_manager.objects.values():
            x, y, z = self.axis_transformer.transform_data(data_object.raw)
            data_object.update_dataclasses(x, y, z)
        
        self.data_container_manager.process_update()        
        self.last_process_update=time.time()

