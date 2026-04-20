"""
core/root_cause.py
------------------
Root-cause analysis engine.
Analyses per-process trends to identify aging causes, assigns severity
levels, and persists results to the root_cause table.
"""

import logging
import time
from typing import Dict, List, Optional

from config.settings import (
    MEMORY_SLOPE_THRESHOLD,
    CPU_SLOPE_THRESHOLD,
    THREAD_SLOPE_THRESHOLD,
    DISK_SLOPE_THRESHOLD,
    NET_SLOPE_THRESHOLD,
    IGNORE_PROCESS_NAMES,
)
from core.analyzer import TrendAnalyzer
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

# Cause classifications
CAUSE_MEMORY_LEAK    = "Memory Leak"
CAUSE_CPU_RUNAWAY    = "CPU Runaway"
CAUSE_THREAD_LEAK    = "Thread Leak"
CAUSE_RESOURCE_EXHAUST = "Resource Exhaustion"
CAUSE_DISK_BOTTLENECK  = "Disk Bottleneck"
CAUSE_NET_BOTTLENECK   = "Network Bottleneck"
CAUSE_NORMAL           = "Normal Operation"

# (multiplier beyond threshold) → severity
SEVERITY_THRESHOLDS = [
    (5.0, "CRITICAL"),
    (2.5, "HIGH"),
    (1.0, "MEDIUM"),
    (0.0, "LOW"),
]


def _severity(slope: float, threshold: float) -> str:
    ratio = slope / threshold if threshold else 0
    for mult, sev in SEVERITY_THRESHOLDS:
        if ratio >= mult:
            return sev
    return "LOW"


class RootCauseEngine:
    """
    Determines the dominant aging cause from process and system trends.
    Results are written to the root_cause table.
    """

    def __init__(self, db: DatabaseManager, analyzer: TrendAnalyzer):
        self.db       = db
        self.analyzer = analyzer

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(self) -> List[Dict]:
        """
        Perform a full root-cause pass and return list of cause dicts.
        """
        causes: List[Dict] = []

        # 1. Process-level causes
        proc_causes = self._analyze_processes()
        causes.extend(proc_causes)

        # 2. System-level causes (disk, network)
        sys_causes = self._analyze_system()
        causes.extend(sys_causes)

        # 3. Persist all detected causes
        now = time.time()
        for c in causes:
            c["timestamp"] = now
            self.db.insert_root_cause(c)

        if causes:
            logger.info("Root-cause run: %d cause(s) found", len(causes))
        else:
            # Record normal operation
            self.db.insert_root_cause({
                "timestamp": now,
                "pid":       0,
                "name":      "system",
                "cause":     CAUSE_NORMAL,
                "severity":  "LOW",
                "detail":    "All metrics within normal bounds.",
            })

        return causes

    # ── Process analysis ──────────────────────────────────────────────────────

    def _analyze_processes(self) -> List[Dict]:
        proc_trends = self.analyzer.analyze_all_processes()
        causes      = []
        ignore = {n.lower() for n in IGNORE_PROCESS_NAMES}

        for trend in proc_trends:
            name      = trend["name"]
            if name and name.lower() in ignore:
                continue
            pid       = 0  # lookup not critical for display
            detected  = []

            if trend["memory_leak"]:
                sev    = _severity(trend["mem_slope"], MEMORY_SLOPE_THRESHOLD)
                detail = (
                    f"Memory slope={trend['mem_slope']:.4f}%/sample "
                    f"(R²={trend['mem_r2']:.2f})"
                )
                detected.append({
                    "pid":      pid,
                    "name":     name,
                    "cause":    CAUSE_MEMORY_LEAK,
                    "severity": sev,
                    "detail":   detail,
                })

            if trend["cpu_runaway"]:
                sev    = _severity(trend["cpu_slope"], CPU_SLOPE_THRESHOLD)
                detail = (
                    f"CPU slope={trend['cpu_slope']:.4f}%/sample "
                    f"(R²={trend['cpu_r2']:.2f})"
                )
                detected.append({
                    "pid":      pid,
                    "name":     name,
                    "cause":    CAUSE_CPU_RUNAWAY,
                    "severity": sev,
                    "detail":   detail,
                })

            if trend["thread_leak"]:
                sev    = _severity(trend["thread_slope"], THREAD_SLOPE_THRESHOLD)
                detail = (
                    f"Thread slope={trend['thread_slope']:.4f}/sample "
                    f"(R²={trend['thread_r2']:.2f})"
                )
                detected.append({
                    "pid":      pid,
                    "name":     name,
                    "cause":    CAUSE_THREAD_LEAK,
                    "severity": sev,
                    "detail":   detail,
                })

            causes.extend(detected)

        return causes

    # ── System-level analysis ─────────────────────────────────────────────────

    def _analyze_system(self) -> List[Dict]:
        sys_trend = self.analyzer.analyze_system()
        causes    = []
        now       = time.time()

        if sys_trend.get("disk_bottleneck"):
            sev = _severity(sys_trend["disk_slope"], DISK_SLOPE_THRESHOLD)
            causes.append({
                "pid":      0,
                "name":     "system",
                "cause":    CAUSE_DISK_BOTTLENECK,
                "severity": sev,
                "detail":   f"Disk usage slope={sys_trend['disk_slope']:.4f}%/sample",
            })

        if sys_trend.get("net_bottleneck"):
            sev = _severity(sys_trend["net_slope"], NET_SLOPE_THRESHOLD)
            causes.append({
                "pid":      0,
                "name":     "system",
                "cause":    CAUSE_NET_BOTTLENECK,
                "severity": sev,
                "detail":   f"Network slope={sys_trend['net_slope']:.2f} bytes/s/sample",
            })

        return causes

    # ── Convenience: dominant cause ───────────────────────────────────────────

    def dominant_cause(self) -> Optional[Dict]:
        """Return the most severe recent cause from the DB."""
        causes = self.db.get_root_causes(limit=20)
        if not causes:
            return None
        sev_map = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return max(causes, key=lambda c: sev_map.get(c["severity"], 0))
