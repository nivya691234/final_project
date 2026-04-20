"""
core/analyzer.py
----------------
Linear-regression–based trend analysis for system and process metrics.
Uses scipy (or numpy fallback) to compute per-metric slopes and detect
aging symptoms: memory leaks, CPU runaway, thread leaks, etc.
"""

import logging
import time
from typing import Dict, List, Optional

import numpy as np

try:
    from scipy.stats import linregress as _linregress
    def _slope_r2(x, y):
        if len(x) < 3 or len(set(x)) < 2:
            return 0.0, 0.0
        try:
            res = _linregress(x, y)
            return res.slope, (res.rvalue ** 2) if res.rvalue else 0.0
        except Exception:
            return 0.0, 0.0
except ImportError:
    def _slope_r2(x, y):
        if len(x) < 3 or len(set(x)) < 2:
            return 0.0, 0.0
        try:
            coeffs = np.polyfit(x, y, 1)
            y_pred = np.polyval(coeffs, x)
            ss_res = np.sum((np.array(y) - y_pred) ** 2)
            ss_tot = np.sum((np.array(y) - np.mean(y)) ** 2)
            r2     = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            return float(coeffs[0]), float(r2)
        except Exception:
            return 0.0, 0.0

from config.settings import (
    TREND_WINDOW,
    MEMORY_SLOPE_THRESHOLD,
    CPU_SLOPE_THRESHOLD,
    THREAD_SLOPE_THRESHOLD,
    DISK_SLOPE_THRESHOLD,
    NET_SLOPE_THRESHOLD,
    RSQUARED_THRESHOLD,
)
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    Fetches recent metric windows from the database and computes
    linear-regression slopes for each metric.
    """

    def __init__(self, db: DatabaseManager, window: int = TREND_WINDOW):
        self.db     = db
        self.window = window

    # ── System-level trend ────────────────────────────────────────────────────

    def analyze_system(self) -> Dict:
        """
        Returns a dict with slope/r2 for each system metric, plus boolean
        flags for detected aging symptoms.
        """
        rows = self.db.get_system_metrics(limit=self.window)
        if len(rows) < 3:
            return self._empty_system_result()

        ts   = np.array([r["timestamp"] for r in rows])
        # Normalise time axis to seconds-since-first-sample
        t    = ts - ts[0]

        def sr(field):
            vals = np.array([r[field] for r in rows], dtype=float)
            return _slope_r2(t, vals)

        cpu_s,  cpu_r2  = sr("cpu")
        ram_s,  ram_r2  = sr("ram")
        disk_s, disk_r2 = sr("disk")
        net_sr  = sr("net_recv_rate")
        net_ss  = sr("net_send_rate")
        net_s   = (net_sr[0] + net_ss[0]) / 2

        # Aging rules: 1. At least ``window`` samples (configurable)
        has_50 = len(rows) >= self.window

        # Aging rules: 2. Monotonic increase of 80 percent
        def mono80(vals):
            if len(vals) < 2: return False
            inc = sum(1 for i in range(1, len(vals)) if vals[i] >= vals[i-1])
            return (inc / (len(vals) - 1)) >= 0.80
            
        c_vals = np.array([r["cpu"] for r in rows])[::-1]
        r_vals = np.array([r["ram"] for r in rows])[::-1]
        d_vals = np.array([r["disk"] for r in rows])[::-1]
        n_vals = np.array([r["net_recv_rate"] + r["net_send_rate"] for r in rows])[::-1]

        # Aging rules: 3. Windows average compare baseline
        baseline = self.db.get_baseline() or {}
        b_cpu = baseline.get("cpu_baseline", 0)
        b_ram = baseline.get("ram_baseline", 0)
        b_disk = baseline.get("disk_baseline", 0)
        b_net = 0  # No net baseline, so assume always true
        
        avg_cpu = np.mean(c_vals) if len(c_vals) else 0
        avg_ram = np.mean(r_vals) if len(r_vals) else 0
        avg_disk = np.mean(d_vals) if len(d_vals) else 0
        avg_net = np.mean(n_vals) if len(n_vals) else 0
        
        mem_aging = has_50 and mono80(r_vals) and (avg_ram > b_ram)
        cpu_aging = has_50 and mono80(c_vals) and (avg_cpu > b_cpu)
        disk_aging = has_50 and mono80(d_vals) and (avg_disk > b_disk)
        net_aging = has_50 and mono80(n_vals) and (avg_net > b_net)

        result = {
            "cpu_slope":    cpu_s,
            "cpu_r2":       cpu_r2,
            "ram_slope":    ram_s,
            "ram_r2":       ram_r2,
            "disk_slope":   disk_s,
            "disk_r2":      disk_r2,
            "net_slope":    net_s,
            # Symptom flags
            "memory_leak":  (ram_s > MEMORY_SLOPE_THRESHOLD) and (ram_r2 >= RSQUARED_THRESHOLD) and mem_aging,
            "cpu_runaway":  (cpu_s > CPU_SLOPE_THRESHOLD) and (cpu_r2 >= RSQUARED_THRESHOLD) and cpu_aging,
            "disk_bottleneck":  (disk_s > DISK_SLOPE_THRESHOLD) and (disk_r2 >= RSQUARED_THRESHOLD) and disk_aging,
            "net_bottleneck":   (net_s > NET_SLOPE_THRESHOLD) and net_aging,
            # Overall degradation score (0-1 normalised)
            "degradation_score": self._degradation_score(cpu_s, ram_s, disk_s),
        }
        logger.debug("System trend: %s", result)
        return result

    def _degradation_score(self, cpu_s: float, ram_s: float, disk_s: float) -> float:
        """
        Weighted composite degradation metric normalised to ~[0, 1].
        Higher = worse system health.
        """
        w_cpu  = min(max(cpu_s  / CPU_SLOPE_THRESHOLD,  0), 1) * 0.4
        w_ram  = min(max(ram_s  / MEMORY_SLOPE_THRESHOLD, 0), 1) * 0.45
        w_disk = min(max(disk_s / DISK_SLOPE_THRESHOLD,  0), 1) * 0.15
        return round(w_cpu + w_ram + w_disk, 4)

    # ── Per-process trend ─────────────────────────────────────────────────────

    def analyze_process(self, name: str, limit: int = None) -> Dict:
        """Return slope info for a specific process by name."""
        lim  = limit or self.window
        rows = self.db.get_process_metrics_by_name(name, limit=lim)
        if len(rows) < 3:
            return self._empty_process_result(name)

        # Chronological order
        chron_rows = list(reversed(rows))
        ts = np.array([r["timestamp"] for r in chron_rows])
        t  = ts - ts[0]

        m_vals = [r["memory"]  for r in chron_rows]
        c_vals = [r["cpu"]     for r in chron_rows]
        t_vals = [r["threads"] for r in chron_rows]

        mem_s, mem_r2  = _slope_r2(t, m_vals)
        cpu_s, cpu_r2  = _slope_r2(t, c_vals)
        thr_s, thr_r2  = _slope_r2(t, t_vals)

        # Aging rules: 1. At least ``window`` samples (configurable)
        has_50 = len(rows) >= self.window

        # Aging rules: 2. Monotonic increase of 80 percent
        def mono80(vals):
            if len(vals) < 2: return False
            inc = sum(1 for i in range(1, len(vals)) if vals[i] >= vals[i-1])
            return (inc / (len(vals) - 1)) >= 0.80

        # Aging rules: 3. Windows average compare baseline
        baseline = self.db.get_baseline() or {}
        b_ram = baseline.get("ram_baseline", 0)
        b_cpu = baseline.get("cpu_baseline", 0)
        
        avg_mem = sum(m_vals) / len(m_vals) if m_vals else 0
        avg_cpu = sum(c_vals) / len(c_vals) if c_vals else 0
        
        # Combined checks for strict software aging validation
        mem_aging = has_50 and mono80(m_vals) and (avg_mem > b_ram)
        cpu_aging = has_50 and mono80(c_vals) and (avg_cpu > b_cpu)
        thr_aging = has_50 and mono80(t_vals)

        return {
            "name":         name,
            "samples":      len(rows),
            "mem_slope":    mem_s,
            "mem_r2":       mem_r2,
            "cpu_slope":    cpu_s,
            "cpu_r2":       cpu_r2,
            "thread_slope": thr_s,
            "thread_r2":    thr_r2,
            # Symptom flags
            "memory_leak":  (mem_s > MEMORY_SLOPE_THRESHOLD) and (mem_r2 >= RSQUARED_THRESHOLD) and mem_aging,
            "cpu_runaway":  (cpu_s > CPU_SLOPE_THRESHOLD) and (cpu_r2 >= RSQUARED_THRESHOLD) and cpu_aging,
            "thread_leak":  (thr_s > THREAD_SLOPE_THRESHOLD) and (thr_r2 >= RSQUARED_THRESHOLD) and thr_aging,
        }

    def analyze_all_processes(self) -> List[Dict]:
        """Analyze every distinct process present in the DB."""
        names   = self.db.get_distinct_process_names()
        results = []
        for name in names:
            r = self.analyze_process(name)
            if r["samples"] >= 3:
                results.append(r)
        # Sort by worst memory slope first
        results.sort(key=lambda x: x["mem_slope"], reverse=True)
        return results

    # ── Helper: empty result skeletons ────────────────────────────────────────

    @staticmethod
    def _empty_system_result() -> Dict:
        return {
            "cpu_slope": 0, "cpu_r2": 0,
            "ram_slope": 0, "ram_r2": 0,
            "disk_slope": 0, "disk_r2": 0,
            "net_slope": 0,
            "memory_leak": False, "cpu_runaway": False,
            "disk_bottleneck": False, "net_bottleneck": False,
            "degradation_score": 0,
        }

    @staticmethod
    def _empty_process_result(name: str) -> Dict:
        return {
            "name": name, "samples": 0,
            "mem_slope": 0, "mem_r2": 0,
            "cpu_slope": 0, "cpu_r2": 0,
            "thread_slope": 0, "thread_r2": 0,
            "memory_leak": False, "cpu_runaway": False, "thread_leak": False,
        }
