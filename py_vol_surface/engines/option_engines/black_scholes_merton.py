from . import base
import numpy as np
from scipy.stats import norm
import py_vollib_vectorized

class Engine(base.BaseEngine):
    def __init__(self, strike, expiry, flag, flag_int=None,
                 interest_rate_engine=None, dividend_rate_engine=None):
        super().__init__(strike, expiry, flag, flag_int, interest_rate_engine=interest_rate_engine, dividend_rate_engine=dividend_rate_engine)
        self.dividend_rate_engine = dividend_rate_engine
        self.IVOL_engine = self.IVOL
        self.greek_engine_all = self.get_all_greeks
        self.greeks_engines = {"delta": self.delta,
                               "gamma": self.gamma,
                               "vega": self.vega,
                               "rho" : self.rho,
                               "theta" : self.theta
                              }
    @staticmethod
    def IVOL(price, S, K, t, r, flag, q=0, return_as='numpy', **kwargs):
        return py_vollib_vectorized.vectorized_implied_volatility(price, S, K, t, r, flag, q=q, model='black_scholes_merton',return_as=return_as)

    @staticmethod
    def delta(sigma, S, K, t, r, flag, q=0, return_as='numpy', **kwargs):
        d1 = (np.log(S/K) + (r - q + 0.5 * sigma**2) * t) / sigma / np.sqrt(t)
        return flag * np.exp(-q*t) * norm.cdf(-flag*d1, 0, 1)

    @staticmethod
    def gamma(sigma, S, K, t, r, flag, q=0, return_as='numpy', **kwargs):
        d1 = (np.log(S/K) + (r - q + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
        return np.exp(-q * t) * norm.pdf(d1) / (S * sigma * np.sqrt(t))

    @staticmethod
    def vega(sigma, S, K, t, r, flag, q=0, return_as='numpy', **kwargs):
        d1 = (np.log(S/K) + (r - q + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
        return S * np.exp(-q * t) * norm.pdf(d1) * np.sqrt(t)

    @staticmethod
    def theta(sigma, S, K, t, r, flag, q=0, return_as='numpy', **kwargs):
        d1 = (np.log(S/K) + (r - q + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
        d2 = d1 - sigma * np.sqrt(t)
        term1 = - (S * np.exp(-q * t) * norm.pdf(d1) * sigma) / (2 * np.sqrt(t))
        term2 = flag * q * S * np.exp(-q * t) * norm.cdf(flag * d1)
        term3 = - flag * r * K * np.exp(-r * t) * norm.cdf(flag * d2)
        return term1 + term2 + term3

    @staticmethod
    def rho(sigma, S, K, t, r, flag, q=0, return_as='numpy', **kwargs):
        d1 = (np.log(S/K) + (r - q + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
        d2 = d1 - sigma * np.sqrt(t)
        return flag * K * t * np.exp(-r * t) * norm.cdf(flag * d2)

    @staticmethod
    def PC_parity(S, K, t, r, C=None, P=None, q=0, **kwargs):
        if P is not None:
            return P + S * np.exp(-q * t) - K * np.exp(-r * t)
        elif C is not None:
            return C - (S * np.exp(-q * t) - K * np.exp(-r * t))
        else:
            raise ValueError("Either C or P must be provided")

    @staticmethod
    def get_all_greeks(sigma, S, K, t, r, flag, q=0, **kwargs):
        d1 = (np.log(S/K) + (r - q + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
        d2 = d1 - sigma * np.sqrt(t)
        
        delta = flag * np.exp(-q * t) * norm.cdf(flag * d1)
        gamma = np.exp(-q * t) * norm.pdf(d1) / (S * sigma * np.sqrt(t))
        vega = S * np.exp(-q * t) * norm.pdf(d1) * np.sqrt(t)
        theta = - (S * np.exp(-q * t) * norm.pdf(d1) * sigma) / (2 * np.sqrt(t)) \
                + flag * q * S * np.exp(-q * t) * norm.cdf(flag * d1)\
                - flag * r * K * np.exp(-r * t) * norm.cdf(flag * d2)\
                
        rho = flag * K * t * np.exp(-r * t) * norm.cdf(flag * d2)
        return delta, gamma, vega, theta, rho