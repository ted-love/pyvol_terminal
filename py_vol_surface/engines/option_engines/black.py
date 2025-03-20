from . import base
import numpy as np
from scipy.stats import norm
import py_vollib_vectorized

class Engine(base.BaseEngine):
    def __init__(self, strike, expiry, flag, flag_int=None, interest_rate_engine=None, **kwargs):
        super().__init__(strike, expiry, flag, flag_int, interest_rate_engine)
        self.IVOL_engine = self.IVOL
        
        self.greek_engine_all = self.get_all_greeks
        self.greeks_engines = {"delta": self.delta,
                               "gamma": self.gamma,
                               "vega": self.vega,
                               "rho" : self.rho,
                               "theta" : self.theta
                              }

    @staticmethod
    def IVOL(price, F, K, t, r, flag, return_as='numpy', **kwargs):
            return py_vollib_vectorized.vectorized_implied_volatility_black(price, F, K, r, t, flag, return_as=return_as)

    @staticmethod
    def delta(sigma, F, K, t, r, flag, **kwargs):
        d1 =  1/(sigma*np.sqrt(t)) * (np.log(F/K) + (0.5*sigma**2)*t)
        return flag * np.exp(-r*t)*norm.cdf(flag*d1, 0, 1)

    @staticmethod
    def gamma(sigma, F, K, t, r, flag, **kwargs):
        d1 =  1/(sigma*np.sqrt(t)) * (np.log(F/K) + (0.5*sigma**2)*t)
        return np.exp(-r * t) * norm.cdf(d1, 0, 1) / (F * sigma * np.sqrt(t))

    @staticmethod
    def vega(sigma, F, K, t, r, flag, **kwargs):
        d1 =  1/(sigma*np.sqrt(t)) * (np.log(F/K) + (0.5*sigma**2)*t)
        return F * np.exp(-r*t) * norm.cdf(d1, 0, 1) * np.sqrt(t)

    @staticmethod
    def theta(sigma, F, K, t, r, flag, **kwargs):
        d1 =  1/(sigma*np.sqrt(t)) * (np.log(F/K) + (0.5*sigma**2)*t)
        d2 = d1 - np.sqrt(t)
        t1 = - F * np.exp(-r*t) * norm.pdf(d1, 0, 1) * sigma / (2 * np.sqrt(t))
        t2 = - flag * r * K *np.exp(-r*t) * norm.cdf(flag*d2) + flag* r * F * np.exp(-r*t) * norm.cdf(flag*d1, 0, 1)
        return t1 + t2

    @staticmethod
    def rho(sigma, F, K, t, r, flag, **kwargs):
        d1 =  1/(sigma*np.sqrt(t)) * (np.log(F/K) + (0.5*sigma**2)*t)
        d2 = d1 - np.sqrt(t)
        return -t * flag * (F * norm.cdf(flag *sigma, 0,) - K * norm.cdf(flag*d2, 0, 1))

    @staticmethod
    def PC_parity(F, K, t, r, C=None, P=None, **kwargs):
        if P:
            return P + (F - K) * np.exp(- r*t)
        else:
            return C - (F - K) * np.exp(- r*t)

    @staticmethod
    def get_all_greeks(sigma, F, K, t, r, flag, **kwargs):
        d1 = (np.log(F/K) + 0.5 * t * sigma**2) / (sigma*np.sqrt(t))
        d2 = d1 - np.sqrt(t)
        
        delta=flag * np.exp(-r*t)*norm.cdf(flag*d1, 0, 1)
        gamma=np.exp(-r * t) * norm.cdf(d1, 0, 1) / (F * sigma * np.sqrt(t))
        vega=F * np.exp(-r*t) * norm.cdf(d1, 0, 1) * np.sqrt(t)
        theta= - F * np.exp(-r*t) * norm.pdf(d1, 0, 1) * sigma / (2 * np.sqrt(t)) \
                - flag * r * K *np.exp(-r*t) * norm.cdf(flag*d2) + flag* r * F * np.exp(-r*t) * norm.cdf(flag*d1, 0, 1)
        rho = -t * flag * (F * norm.cdf(flag *sigma, 0,) - K * norm.cdf(flag*d2, 0, 1))
        return delta, gamma, vega, theta, rho

