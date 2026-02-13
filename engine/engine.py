
import numpy as np
import math

class Engine:
    def __init__(self, config):
        self.config = config

    def generate_return(self):
        return np.random.normal(
            self.config["mu_expansion"],
            self.config["sigma_expansion"]
        )

    def adjusted_return(self, L, r):
        return L * r - self.config["alpha_leverage"] * (L - 1)**2

    def shock_impact(self, week, capital, exposure, coverage, shock_week, severity):
        if week == shock_week:
            impact = capital * exposure * severity
            return impact * (1 - self.config["beta_coverage"] * coverage)
        return 0

    def calculate_ic(self, history):
        D = history[-1]
        sigma = np.std(history)
        return (
            self.config["weight_money"] * math.log(1 + D)
            - self.config["lambda_volatility"] * sigma
        )
