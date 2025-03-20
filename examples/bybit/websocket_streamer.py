import requests
import pandas as pd
import time
import threading
import json
import websockets
from websockets.sync.client import connect
from typing import Dict
import queue


def get_bybit_tickers():
    url = "https://api.bybit.com/v5/market/instruments-info"
    
    response = requests.get(url, params={"category" : "option"})
    
    json_reponse = response.json()
    L = json_reponse["result"]["list"]

    df_options = pd.DataFrame(L)    
    df_options["strike"] = [float(sym.split("-")[2]) for sym in df_options["symbol"]]
    df_options = df_options.rename(columns={"optionsType" : "flag",
                                            "deliveryTime" : "expiry",
                                            "symbol" : "instrument_name"})    
    
    df_options["flag"] = ["c" if flag == "Call" else "p" for flag in df_options["flag"]]
    df_options["expiry"] = df_options["expiry"].values.astype(float)/1000

    df_options = df_options.drop_duplicates(subset=["expiry", "flag", "strike"])
    
    S_0 = requests.get("https://api.bybit.com/v5/market/tickers", params={"category" : "spot", "symbol" : "BTCUSDT"}).json()["result"]["list"][0]["lastPrice"]
    S_0 = float(S_0)
    
    df_options = df_options.loc[(df_options["strike"] >= S_0 - 0.5*S_0) & (df_options["strike"] <= S_0 + 0.5*S_0)]
    channels = [f"tickers.{name}" for name in df_options["instrument_name"]]
    
    spot_instrument_name = "BTCUSDT"
    underlying_channel = f"orderbook.1.{spot_instrument_name}"

    channels.append(underlying_channel) 
    
    df_spot = pd.DataFrame([spot_instrument_name], columns=["instrument_name"])
    
    option_underlying_name_map = {option_name : spot_instrument_name for option_name in df_options["instrument_name"]} 
    return channels, df_options, df_spot, option_underlying_name_map


class Streamer:
    def __init__(self, ws_option_url: str, ws_spot_url: str, channels : list, queue: queue.Queue) -> None:
        super().__init__()
        self.channels = channels
        self.ws_option_url: str = ws_option_url
        self.refresh_token: str = None
        self.refresh_token_expiry_time: int = None
        self.ws_spot_url=ws_spot_url
        self.ws_option_channels = channels[:-1]
        self.ws_spot_channels = channels[-1:]  
        self.running = False  
        self.last_print = time.time()
        self.spot_orderbook = {}
        self.queue=queue

    def _initialise_local_data(self, topic):
        try:
            self.spot_orderbook[topic]
        except KeyError:
            self.spot_orderbook[topic] = []

    def _process_delta_orderbook(self, message, topic):
        self._initialise_local_data(topic)
        if "snapshot" in message["type"]:
            self.spot_orderbook[topic] = message["data"]
            return

        book_sides = {"b": message["data"]["b"], "a": message["data"]["a"]}
        self.spot_orderbook[topic]["u"]=message["data"]["u"]
        self.spot_orderbook[topic]["seq"]=message["data"]["seq"]

        for side, entries in book_sides.items():
            for entry in entries:
                if float(entry[1]) == 0:
                    index = _find_index(self.spot_orderbook[topic][side], entry, 0)
                    self.spot_orderbook[topic][side].pop(index)
                    continue

                price_level_exists = entry[0] in [
                    level[0] for level in self.spot_orderbook[topic][side]
                ]
                if not price_level_exists:
                    self.spot_orderbook[topic][side].append(entry)
                    continue

                qty_changed = entry[1] != next(
                    level[1]
                    for level in self.spot_orderbook[topic][side]
                    if level[0] == entry[0]
                )
                if price_level_exists and qty_changed:
                    index = _find_index(self.spot_orderbook[topic][side], entry, 0)
                    self.spot_orderbook[topic][side][index] = entry
                    continue

    def start_websocket(self):
        print("Starting websocket connections")
        self._running = True
        for channel_type, channels, url in zip(["spot","option"],
                                            [self.ws_spot_channels, self.ws_option_channels],
                                            [self.ws_spot_url, self.ws_option_url]):
            
            threading.Thread(target=self._setup_websocket, args=(channels, channel_type, url), daemon=True).start()

            
    def _setup_websocket(self, channels, channel_type, url):
        with connect(url) as websocket:
            websocket.send(json.dumps({"op" : "subscribe",
                                       "args" : channels}))
                        
            websocket.send(json.dumps({"req_id": "100001", "op": "ping"}))
            last_heartbeat = time.time()
            while True:
                try:
                    message: bytes = websocket.recv()
                except websockets.ConnectionClosed as e:
                    print(f"Connection closed with error: {e}")
                    break
                
                if time.time() - last_heartbeat > 15:
                    websocket.send(json.dumps({"req_id": "100001", "op": "ping"}))
                
                message: Dict = json.loads(message)
                
                if "op" in message:
                    if message["op"] == "pong":
                        last_heartbeat = time.time()
                        continue
                                
                if not "success" in message:
                    processed_data = self._process_message(message, channel_type)
                    self.queue.put(processed_data)
                
    def _process_message(self, message: dict, channel_type: str) -> dict:
        if channel_type == "spot":
            self._process_delta_orderbook(message, message["topic"])
            return self.process_orderbook_message(message)
        else:
            return self.process_ticker_message(message)
        
    async def _subscribe(self, websocket, channel_type: str, channels: list) -> None:
        if channel_type == "spot":
            for channel in channels:
                symbol = channel.split(".")[-1]
                sub_msg = json.dumps({"op": "subscribe", "args": [channel]})
                await websocket.send(sub_msg)
        else:
            for channel in channels:
                symbol = channel.split(".")[-1]
                sub_msg = json.dumps({"op": "subscribe", "args": [channel]})
                await websocket.send(sub_msg)

    def process_orderbook_message(self, message):
        data= list(self.spot_orderbook.values())[0]
        if not "symbol" in data:
            data["symbol"] = data.pop("s")
        data["ts"] = message["ts"] / 1000
        data["bidPrice"] = float(data["b"][0][0])
        data["askPrice"] = float(data["a"][0][0])
        return data
    
    def process_ticker_message(self, message):
        data=message["data"]    
        data["ts"] = message["ts"]
        data["bidPrice"] = float(data["bidPrice"])
        data["askPrice"] = float(data["askPrice"])
        return data
    
    def _sending_heartbeat(self, ws):
        while True:
            time.sleep(15)
        
    def stop(self):
        print("Stopping WebSocket connections...")
        self.running = False
        if self.ws_spot:
            self.ws_spot.exit() 
        if self.ws_option:
            self.ws_option.exit() 
        self.quit()  
        self.wait(2000) 

def _find_index(source, target, key):
    return next(i for i, j in enumerate(source) if j[key] == target[key])