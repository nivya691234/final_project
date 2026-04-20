"""
core/predictor.py
-----------------
Failure prediction engine.
Combines the TrendAnalyzer slope with the ReliabilityModel to:
 1. Estimate failure probability right now.
 2. Compute time-to-crash (T_critical) and optimal restart time.
 3. Persist prediction to the database.
"""

import logging
import time
from typing import Dict, Optional

from config.settings import FAILURE_THRESHOLD, RESTART_SAFETY_MARGIN
from core.analyzer import TrendAnalyzer
from database.db_manager import DatabaseManager
from models.reliability_model import ReliabilityModel

logger = logging.getLogger(__name__)

# Mapping of failure probability → restart priority label
PRIORITY_MAP = [
    (0.85, "CRITICAL"),
    (0.65, "HIGH"),
    (0.40, "MEDIUM"),
    (0.15, "LOW"),
    (0.00, "NORMAL"),
]


def _priority_label(prob: float) -> str:
    for threshold, label in PRIORITY_MAP:
        if prob >= threshold:
            return label
    return "NORMAL"


class FailurePredictor:
    """
    Orchestrates slope → λ → P(failure) → restart time pipeline.
    """

    def __init__(
        self,
        db: DatabaseManager,
        analyzer: TrendAnalyzer,
        model: ReliabilityModel,
        failure_threshold: float = FAILURE_THRESHOLD,
    ):
        self.db        = db
        self.analyzer  = analyzer
        self.model     = model
        self.threshold = failure_threshold

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(self) -> Dict:
        """
        Execute one prediction cycle.
        Returns the prediction dict that was stored.
        """
        system_trend = self.analyzer.analyze_system()

        # Use degradation_score as the primary slope driver;
        # also incorporate raw RAM slope (strongest aging indicator)
        deg_score  = system_trend.get("degradation_score", 0)
        ram_slope  = max(system_trend.get("ram_slope", 0), 0)
        cpu_slope  = max(system_trend.get("cpu_slope", 0), 0)

        # Composite slope: weighted average of key signals
        composite_slope = (ram_slope * 0.5 + cpu_slope * 0.3 +
                           deg_score * 0.2)

        analysis = self.model.analyze(
            degradation_slope=composite_slope,
            threshold=self.threshold,
        )

        lam             = analysis["lambda_val"]
        t_crash         = analysis["critical_time_minutes"]
        t_restart       = analysis["optimal_restart_minutes"]
        now             = time.time()

        # Convert relative minutes to absolute epoch seconds
        abs_crash   = (now + t_crash   * 60) if t_crash   is not None else None
        abs_restart = (now + t_restart * 60) if t_restart is not None else None

        # Current failure probability (at minute=0 is 0; meaningful at t=30/60/…)
        # Use the 60-minute horizon probability as the "current risk"
        p_60 = self.model.failure_probability(60, lam)

        priority = _priority_label(p_60)

        prediction = {
            "timestamp":              now,
            "failure_probability":    round(p_60, 4),
            "predicted_restart_time": abs_restart,
            "predicted_crash_time":   abs_crash,
            "lambda_val":             lam,
            "priority":               priority,
        }

        self.db.insert_prediction(prediction)
        logger.info(
            "Prediction: P(60min)=%.2f%% priority=%s crash_in=%.1f min",
            p_60 * 100,
            priority,
            t_crash if t_crash else 0,
        )
        return prediction

    # ── Failure curve for dashboard ───────────────────────────────────────────

    def get_failure_curve(self, horizon_minutes: int = 120) -> list:
        """
        Return a time-series failure-probability curve for Chart.js.
        Uses the most recent prediction's lambda_val from the DB.
        """
        pred = self.db.get_latest_prediction()
        lam  = pred["lambda_val"] if pred else 1e-5
        return self.model.failure_curve(lam, horizon_minutes)
