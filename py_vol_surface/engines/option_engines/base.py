from ... import utils

class BaseEngine:
    def __init__(self, strike, expiry, flag_str, flag_int=None, interest_rate_engine=None, dividend_rate_engine=None):
        self.strike = strike
        self.expiry = expiry
        self.flag_str = flag_str
        self.interest_rate_engine = interest_rate_engine
        self.dividend_rate_engine=dividend_rate_engine
        self.IVOL_engine = None
        self.greek_engine_all = None
        self.greeks_engines = {}
        if self.dividend_rate_engine is None:
            self._dividend_off=True
        else:
            self._dividend_off=False
        
        if not flag_int is None:
            self.flag_int = flag_int
        else:
            self.flag_int = 1 if flag_str.lower() == "c" else -1

    def calculate_IVOL(self, option_prices, underlying_price):
        yte = utils.convert_unix_maturity_to_years(self.expiry)       
        r = self.interest_rate_engine.evaluate(yte)
        if not self._dividend_off:
            q = self.dividend_rate_engine.evaluate(yte)
        else:
            q = 0
        return self.IVOL_engine(option_prices,
                               underlying_price,
                               self.strike,
                               yte,
                               r,
                               self.flag_str,
                               q=q
                               )

    def calculate_all_greeks(self, IVOL, underlying_price):
        yte = utils.convert_unix_maturity_to_years(self.expiry)
        r = self.interest_rate_engine.evaluate(yte)
        if not self._dividend_off:
            q = self.dividend_rate_engine.evaluate(yte)
        else:
            q = None
        return self.greek_engine_all(IVOL,
                                     underlying_price,
                                     self.strike,
                                     yte,
                                     r,
                                     self.flag_int,
                                     q=q
                                    )
