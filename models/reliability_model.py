"""
models/reliability_model.py
---------------------------
MRGP-inspired stochastic exponential failure model.

P(failure before time t) = 1 − exp(−λ · t)

λ (failure rate) is derived from the system degradation slope so that
steeper degradation → sooner predicted failure.
"""

import math
import logging
from typing import Optional

from config.settings import MIN_LAMBDA, FAILURE_THRESHOLD

logger = logging.getLogger(__name__)


class ReliabilityModel:
    """
    Exponential reliability model parameterised by a degradation slope.

    Methods
    -------
    estimate_lambda(slope)
        Map a positive degradation slope to a failure rate λ.
    failure_probability(t, lambda_val)
        Return P(crash) at horizon t minutes.
    critical_time(lambda_val, threshold)
        Solve for T where P(T) == threshold (minutes).
    """

    # Scaling constant: tunes how fast P grows with slope
    # Increase to make the model more aggressive, decrease to be conservative.
    LAMBDA_SCALE = 0.01

    # ── Core model functions ─────────────────────────────────────────────────

    def estimate_lambda(self, slope: float) -> float:
        """
        Convert a degradation slope (% or absolute per sample) to λ.
        λ = max(slope * LAMBDA_SCALE, MIN_LAMBDA)
        """
        raw = slope * self.LAMBDA_SCALE
        lam = max(raw, MIN_LAMBDA)
        logger.debug("estimate_lambda(slope=%.6f) -> λ=%.8f", slope, lam)
        return lam

    def failure_probability(self, t: float, lambda_val: float) -> float:
        """
        P(failure before t minutes) = 1 − exp(−λ · t).
        Returns a value in [0, 1].
        """
        if t <= 0 or lambda_val <= 0:
            return 0.0
        prob = 1.0 - math.exp(-lambda_val * t)
        return min(max(prob, 0.0), 1.0)

    def critical_time(
        self,
        lambda_val: float,
        threshold: float = FAILURE_THRESHOLD,
    ) -> Optional[float]:
        """
        Solve 1 − exp(−λ · T) = threshold  →  T = −ln(1 − threshold) / λ
        Returns T in minutes, or None if λ equals zero.
        """
        if lambda_val <= 0 or threshold <= 0 or threshold >= 1:
            return None
        try:
            t = -math.log(1.0 - threshold) / lambda_val
            return round(t, 2)
        except (ValueError, ZeroDivisionError):
            return None

    def failure_curve(
        self,
        lambda_val: float,
        horizon_minutes: int = 120,
        points: int = 60,
    ) -> list:
        """
        Return a list of (t, P(t)) pairs suitable for plotting.
        t is in minutes; horizon defaults to 2 hours.
        """
        step = max(horizon_minutes / points, 1)
        curve = []
        for i in range(points + 1):
            t    = i * step
            prob = self.failure_probability(t, lambda_val)
            curve.append({"t": round(t, 2), "p": round(prob, 4)})
        return curve

    # ── Convenience wrapper ───────────────────────────────────────────────────

    def analyze(
        self,
        degradation_slope: float,
        threshold: float = FAILURE_THRESHOLD,
        horizon_minutes: int = 120,
    ) -> dict:
        """
        One-call analysis: given a slope, return λ, curve, critical_time,
        and optimal_restart_time (15 % safety margin).
        """
        from config.settings import RESTART_SAFETY_MARGIN

        lam          = self.estimate_lambda(degradation_slope)
        t_critical   = self.critical_time(lam, threshold)
        t_restart    = None
        if t_critical is not None:
            t_restart = round(t_critical * (1.0 - RESTART_SAFETY_MARGIN), 2)

        p_now = self.failure_probability(0, lam)  # always 0 but kept for symmetry

        return {
            "lambda_val":             lam,
            "failure_probability_now": p_now,
            "critical_time_minutes":  t_critical,
            "optimal_restart_minutes": t_restart,
            "curve": self.failure_curve(lam, horizon_minutes),
        }
