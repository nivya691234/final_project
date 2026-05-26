"""
core/thresholds.py
------------------
Adaptive threshold learner for trend analysis.

Uses historical metric windows to derive dynamic slope thresholds.
Falls back to manual config values when history is insufficient.
"""

import logging
from typing import Dict, List

import numpy as np

from config.settings import (
    ADAPTIVE_HISTORY_SAMPLES,
    ADAPTIVE_MIN_HISTORY_SAMPLES,
    ADAPTIVE_PERCENTILE,
    ADAPTIVE_SCALE_FACTOR,
    ADAPTIVE_STD_MULTIPLIER,
    ADAPTIVE_THRESHOLDS_ENABLED,
    CPU_SLOPE_THRESHOLD,
    DISK_SLOPE_THRESHOLD,
    MEMORY_SLOPE_THRESHOLD,
    NET_SLOPE_THRESHOLD,
    THREAD_SLOPE_THRESHOLD,
)
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


def _slope_r2(x, y):
    if len(x) < 3 or len(set(x)) < 2:
        return 0.0, 0.0
    try:
        coeffs = np.polyfit(x, y, 1)
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((np.array(y) - y_pred) ** 2)
        ss_tot = np.sum((np.array(y) - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return float(coeffs[0]), float(r2)
    except Exception:
        return 0.0, 0.0


def _normalize_slope(slope: float) -> float:
    return float(abs(slope))


class ThresholdLearner:
    def __init__(self, db: DatabaseManager, window: int = 10):
        self.db = db
        self.window = window
        self.history_samples = ADAPTIVE_HISTORY_SAMPLES
        self.min_history = ADAPTIVE_MIN_HISTORY_SAMPLES
        self.percentile = ADAPTIVE_PERCENTILE
        self.std_multiplier = ADAPTIVE_STD_MULTIPLIER
        self.scale_factor = ADAPTIVE_SCALE_FACTOR
        self.enabled = ADAPTIVE_THRESHOLDS_ENABLED

    def get_system_thresholds(self) -> Dict[str, float]:
        if not self.enabled:
            return self._default_system_thresholds()

        rows = self.db.get_system_metrics(limit=self.history_samples)
        if len(rows) < self.min_history:
            return self._default_system_thresholds()

        ts = [r["timestamp"] for r in rows]
        return {
            "cpu": self._learn_threshold(ts, [r["cpu"] for r in rows], CPU_SLOPE_THRESHOLD, field="cpu"),
            "ram": self._learn_threshold(ts, [r["ram"] for r in rows], MEMORY_SLOPE_THRESHOLD, field="ram"),
            "disk": self._learn_threshold(ts, [r["disk"] for r in rows], DISK_SLOPE_THRESHOLD, field="disk"),
            "net": self._learn_threshold(
                ts,
                [r["net_recv_rate"] + r["net_send_rate"] for r in rows],
                NET_SLOPE_THRESHOLD,
                field="net",
            ),
        }

    def get_process_thresholds(self, name: str) -> Dict[str, float]:
        if not self.enabled:
            return self._default_process_thresholds()

        rows = self.db.get_process_metrics_by_name(name, limit=self.history_samples)
        if len(rows) < self.min_history:
            return self._default_process_thresholds()

        ts = [r["timestamp"] for r in rows]
        return {
            "memory": self._learn_threshold(ts, [r["memory"] for r in rows], MEMORY_SLOPE_THRESHOLD, field="process_memory"),
            "cpu": self._learn_threshold(ts, [r["cpu"] for r in rows], CPU_SLOPE_THRESHOLD, field="process_cpu"),
            "threads": self._learn_threshold(ts, [r["threads"] for r in rows], THREAD_SLOPE_THRESHOLD, field="process_threads"),
        }

    def _learn_threshold(self, ts: List[float], values: List[float], default: float, field: str = "metric") -> float:
        slopes = self._slopes_from_series(ts, values)
        if len(slopes) < self.min_history:
            return default

        normalized = np.array([_normalize_slope(s) for s in slopes], dtype=float)
        if normalized.size == 0:
            return default

        learned = np.percentile(normalized, self.percentile)
        mean = float(np.mean(normalized))
        std = float(np.std(normalized))
        auto_threshold = max(learned * self.scale_factor, mean + std * self.std_multiplier, default)
        logger.debug(
            "Adaptive threshold learned for %s: default=%.6f mean=%.6f std=%.6f p%d=%.6f -> result=%.6f",
            field, default, mean, std, self.percentile, learned, auto_threshold,
        )
        return float(max(default, auto_threshold))

    def _slopes_from_series(self, ts: List[float], values: List[float]) -> List[float]:
        if len(ts) < self.window or len(values) < self.window:
            return []

        slopes: List[float] = []
        for i in range(len(ts) - self.window + 1):
            window_ts = np.array(ts[i : i + self.window], dtype=float)
            window_vals = np.array(values[i : i + self.window], dtype=float)
            slope, _ = _slope_r2(window_ts, window_vals)
            slopes.append(slope)

        return slopes

    @staticmethod
    def _default_system_thresholds() -> Dict[str, float]:
        return {
            "cpu": CPU_SLOPE_THRESHOLD,
            "ram": MEMORY_SLOPE_THRESHOLD,
            "disk": DISK_SLOPE_THRESHOLD,
            "net": NET_SLOPE_THRESHOLD,
        }

    @staticmethod
    def _default_process_thresholds() -> Dict[str, float]:
        return {
            "memory": MEMORY_SLOPE_THRESHOLD,
            "cpu": CPU_SLOPE_THRESHOLD,
            "threads": THREAD_SLOPE_THRESHOLD,
        }
