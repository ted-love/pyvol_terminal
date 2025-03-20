#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 10 21:09:24 2025

@author: ted
"""
import asyncio
import websockets
import json
import nest_asyncio
nest_asyncio.apply()
import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone
from typing import Dict
import requests
import warnings
from websockets.asyncio.client import connect

warnings.simplefilter(action='ignore', category=FutureWarning)

def generate_option_channels():
    channels = []
    
    url = "https://www.deribit.com/api/v2/public/get_instruments"

    params = {"currency": "BTC",  
              "kind": "option",
              }
            
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data['result']:
            options = data['result']
    
    df_options = pd.DataFrame.from_dict(options)
    df_options["bid"] = np.nan
    df_options["ask"] = np.nan
    
    df_options = df_options.rename(columns={"option_type" : "flag",
                                            "expiration_timestamp" : "expiry"})
    
    df_options["flag"] = ["c" if flag == "call" else "p" for flag in df_options["flag"]]
    
    S_0 = requests.get("https://www.deribit.com/api/v2/public/get_index_price", params={"index_name" : "btc_usd"}).json()["result"]["index_price"]
    S_0 = float(S_0)
    
    df_options = df_options.loc[(df_options["strike"] >= S_0 - 0.5*S_0) & (df_options["strike"] <= S_0 + 0.5*S_0)]
    
    df_options["expiry"] = df_options["expiry"]/1000
    
    channels = [f"ticker.{instrument_name}.100ms" for instrument_name in df_options["instrument_name"]]
    
    
    df_options = df_options[["bid","ask", "strike", "expiry", "flag", "instrument_name"]]
    
    params = {"currency": "BTC",
              "kind": "future", 
             }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data['result']:
            options = data['result']
    
    df_futures = pd.DataFrame.from_dict(options)
    df_futures["bid"] = np.nan
    df_futures["ask"] = np.nan
    
    df_futures = df_futures.rename(columns={"expiration_timestamp" : "expiry"})
    
    df_futures = df_futures[~df_futures["instrument_name"].str.contains("PERPETUAL")]
    df_futures["expiry"] = df_futures["expiry"]/1000

    channels_futures = [f"ticker.{instrument_name}.100ms" for instrument_name in df_futures["instrument_name"]]
    
    channels = channels + channels_futures
    
    df_futures['rfq'] = df_futures['rfq'].astype(bool)
    option_underlying_name_map = {}

    for option_name in df_options["instrument_name"]:
        fut_name=option_name.rsplit("-", 2)[0]

        if fut_name in df_futures["instrument_name"].to_list():
            option_underlying_name_map[option_name] = fut_name
        else:
            syn_name = "SYN." + fut_name

            option_underlying_name_map[option_name] = syn_name
            
            if not syn_name in df_futures["instrument_name"].to_list():
            
                df_futures_last = df_futures.iloc[-1,:].to_frame().T
                df_futures_last.index = [df_futures_last.index[0]+1]
                df_futures_last["instrument_name"] = syn_name

                df_futures = pd.concat([df_futures, df_futures_last],axis=0)
                
                expiry = fut_name.split("-")[1]

                dt = datetime.strptime(expiry, "%d%b%y")
                dt = dt.replace(hour=8, minute=0, second=0, microsecond=0)
                dt = dt.replace(tzinfo=timezone.utc)
                epoch_timestamp = dt.timestamp()
                
                df_futures_last["expiry"] = epoch_timestamp
                
            
    spot_instrument_name = "BTC_USDC"
    underlying_channel = f"book.{spot_instrument_name}.none.1.100ms"

    channels.append(underlying_channel) 

    df_spot = pd.DataFrame([spot_instrument_name], columns=["instrument_name"])

    future_underlying_name_map = {future_name : spot_instrument_name for future_name in df_futures["instrument_name"]}    
    return channels, df_options, df_futures, df_spot, option_underlying_name_map, future_underlying_name_map, 


class Streamer:
    def __init__(self, ws_connection_url: str, channels : list, spot_flag: str=True, future_flag: str=True) -> None:

        self.channels = channels
        self.ws_connection_url: str = ws_connection_url
        self.spot_flag=spot_flag
        self.future_flag=future_flag        
        self.option_names = []
        self.future_names = []
        self._reformat_data(channels)
        
        self.websocket_client: websockets.WebSocketClientProtocol = None
        self.refresh_token: str = None
        self.refresh_token_expiry_time: int = None
    
    def _reformat_data(self, channels):
        if self.spot_flag:
            self.spot_name = channels[-1].split(".")[1]
        
        if self.future_flag:
            for channel in channels:
                if "SYN" in channel:
                    instrument_name = channel.split(".")[1] +"."+ channel.split(".")[2]
                    self.future_names.append(instrument_name)
                else:
                    instrument_name = channel.split(".")[1]
                    n = instrument_name.count("-")                    
                    if n == 1:
                        self.future_names.append(instrument_name)
                    elif n == 3:
                        self.option_names.append(instrument_name)

    async def ws_manager(self): 
        async with connect(self.ws_connection_url,
                            ping_interval=None,
                            compression=None,
                            close_timeout=60,
                            max_size=3000000
                          ) as self.websocket_client:
                                                                
            self.loop = asyncio.get_event_loop()
            await self.establish_heartbeat()

            self.loop.create_task(self.ws_refresh_auth())
            self.loop.create_task(self.ws_operation(operation='subscribe',))
            while True:
                try:
                    message: bytes = await self.websocket_client.recv()
                except websockets.ConnectionClosed as e:
                    print(f"Connection closed with error: {e}")
                    break
                    
                message: Dict = json.loads(message)
                
                if "id" in message and message['id'] == 42:
                    continue
                if "params" in message:
                    params = message["params"]
                    if "data" in params:
                        data=params["data"]
                        
                        instrument_name = data["instrument_name"]
                        if self.spot_flag:
                            if instrument_name == self.spot_name:
                                data["best_bid_price"] = data["bids"][0][0]
                                data["best_ask_price"] = data["asks"][0][0]
                                
                                yield data
                                continue
                            
                        if self.future_flag and not instrument_name in self.future_names:
                            underlying_index = data["underlying_index"]
                            if "SYN." in underlying_index:
                            
                                data_synth = {}
                                
                                data_synth["instrument_name"]= data["underlying_index"]
                                data_synth["best_bid_price"] = data["underlying_price"] - 2.5
                                data_synth["best_ask_price"] = data["underlying_price"] + 2.5
                                data_synth["timestamp"] = data["timestamp"]
                                
                                if data_synth["instrument_name"] == "SYN.EXPIRY":
                                    data_synth["instrument_name"] = "SYN." + data["instrument_name"].rsplit("-", 2)[0]
                                    
                                yield data
                                continue

                        yield data
                        continue
                        
                if 'id' in list(message):
                    if message["id"] == 9900:
                        if "error" in message:
                            error_message = message["error"]
                            print(error_message)
                    
                    if message['id'] == 9929:

                        if 'result' in message:
                            self.refresh_token = message['result']['refresh_token']

                        # Refresh Authentication well before the required datetime
                        if message['testnet']:
                            expires_in: int = 300
                        else:
                            expires_in: int = message['result']['expires_in'] - 240

                    elif message['id'] == 8212:
                        continue

                elif 'method' in list(message):
                    # Respond to Heartbeat Message
                    if message['method'] == 'heartbeat':
                        await self.heartbeat_response()
           
    async def establish_heartbeat(self) -> None:
        msg: Dict = {
                    "jsonrpc": "2.0",
                    "id": 9098,
                    "method": "public/set_heartbeat",
                    "params": {
                              "interval": 10
                               }
                    }

        await self.websocket_client.send(json.dumps(msg))

    async def heartbeat_response(self) -> None:
        msg: Dict = {"jsonrpc": "2.0",
                    "id": 8212,
                    "method": "public/test",
                    "params": {}
                    }

        await self.websocket_client.send(json.dumps(msg))

    async def close(self):
        for task in self.tasks:
            task.cancel()
        if self.websocket_client:
            await self.websocket_client.close()
            self.websocket_client = None

    async def ws_refresh_auth(self) -> None:
        while True:
            if self.refresh_token_expiry_time is not None:
                if time.time() > self.refresh_token_expiry_time:
                    msg: Dict = {
                                "jsonrpc": "2.0",
                                "id": 9929,
                                "method": "public/auth",
                                "params": {
                                          "grant_type": "refresh_token",
                                          "refresh_token": self.refresh_token
                                            }
                                }

                    await self.websocket_client.send(json.dumps(msg))

            await asyncio.sleep(150)

    async def ws_operation(self, operation: str,) -> None:
        await asyncio.sleep(2)

        msg: Dict = {
                    "jsonrpc": "2.0",
                    "method": f"public/{operation}",
                    "id": 42,
                    "params": {
                        "channels": self.channels
                        }
                    }
        
        await self.websocket_client.send(json.dumps(msg))

