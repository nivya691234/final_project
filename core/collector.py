"""
core/collector.py
-----------------
Continuous system and per-process metric collection using psutil.
Runs in a background daemon thread and writes to the database on every tick.
"""

import logging
import os
import threading
import time
from typing import Optional

import psutil

from config.settings import SAMPLING_INTERVAL
from database.db_manager import DatabaseManager
from core.pid_registry import get_registered_pids

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Periodically samples system and process metrics via psutil and
    persists them to SQLite through DatabaseManager.
    """

    def __init__(
        self,
        db: DatabaseManager,
        interval: float = SAMPLING_INTERVAL,
    ):
        self.db       = db
        self.interval = interval
        self._stop    = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # State for computing per-tick deltas (disk I/O, network)
        self._prev_disk_io = psutil.disk_io_counters()
        self._prev_net_io  = psutil.net_io_counters()
        self._prev_time    = time.time()

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Launch the background collection loop."""
        self._thread = threading.Thread(
            target=self._loop, name="DataCollector", daemon=True
        )
        self._thread.start()
        logger.info("DataCollector started (interval=%ss)", self.interval)

    def stop(self) -> None:
        """Signal the collection loop to stop."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 2)
        logger.info("DataCollector stopped.")

    # ── Internal loop ─────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._collect_system()
                self._collect_processes()
            except Exception as exc:
                logger.exception("Collector error: %s", exc)
            self._stop.wait(timeout=self.interval)

    # ── System-level snapshot ─────────────────────────────────────────────────

    def _collect_system(self) -> None:
        now  = time.time()
        dt   = max(now - self._prev_time, 1e-3)

        cpu  = psutil.cpu_percent(interval=None)
        vm   = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Disk I/O rates (bytes/s)
        disk_io      = psutil.disk_io_counters()
        disk_read_r  = 0.0
        disk_write_r = 0.0
        if self._prev_disk_io and disk_io:
            disk_read_r  = (disk_io.read_bytes  - self._prev_disk_io.read_bytes)  / dt
            disk_write_r = (disk_io.write_bytes - self._prev_disk_io.write_bytes) / dt
        self._prev_disk_io = disk_io

        # Network I/O rates (bytes/s)
        net_io      = psutil.net_io_counters()
        net_send_r  = 0.0
        net_recv_r  = 0.0
        if self._prev_net_io and net_io:
            net_send_r = (net_io.bytes_sent - self._prev_net_io.bytes_sent) / dt
            net_recv_r = (net_io.bytes_recv - self._prev_net_io.bytes_recv) / dt
        self._prev_net_io = net_io

        # Load average (1‑min) — fallback 0 on Windows
        try:
            load_avg = psutil.getloadavg()[0]
        except AttributeError:
            load_avg = 0.0

        # CPU stats
        try:
            cpu_stats   = psutil.cpu_stats()
            ctx_sw      = float(cpu_stats.ctx_switches)
            interrupts  = float(cpu_stats.interrupts)
            interrupt_r = interrupts / dt
        except Exception:
            ctx_sw      = 0.0
            interrupt_r = 0.0

        self._prev_time = now

        self.db.insert_system_metrics({
            "timestamp":        now,
            "cpu":              cpu,
            "ram":              vm.percent,
            "ram_used":         vm.used,
            "ram_available":    vm.available,
            "disk":             disk.percent,
            "disk_read_rate":   max(disk_read_r,  0),
            "disk_write_rate":  max(disk_write_r, 0),
            "net_send_rate":    max(net_send_r,   0),
            "net_recv_rate":    max(net_recv_r,   0),
            "load_avg":         load_avg,
            "context_switches": ctx_sw,
            "interrupt_rate":   interrupt_r,
        })

    # ── Per-process snapshot ──────────────────────────────────────────────────

    def _collect_processes(self) -> None:
        now = time.time()
        ignore_pids = set(get_registered_pids())
        ignore_pids.add(os.getpid())
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent",
             "memory_info", "num_threads", "create_time"]
        ):
            try:
                info = proc.info
                pid  = info["pid"]
                if pid in ignore_pids:
                    continue
                name = info["name"] or "unknown"

                cpu    = info.get("cpu_percent") or 0.0
                mem_p  = info.get("memory_percent") or 0.0
                mi     = info.get("memory_info")
                mem_b  = mi.rss if mi else 0
                threads = info.get("num_threads") or 0

                # File descriptors (Linux/Mac only; 0 on Windows)
                try:
                    fds = proc.num_fds()
                except (AttributeError, psutil.AccessDenied, psutil.NoSuchProcess):
                    fds = 0

                self.db.insert_process_metrics({
                    "timestamp":    now,
                    "pid":          pid,
                    "name":         name,
                    "cpu":          cpu,
                    "memory":       mem_p,
                    "memory_bytes": mem_b,
                    "threads":      threads,
                    "fds":          fds,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception as exc:
                logger.debug("Process collection error (pid=%s): %s",
                             getattr(proc, "pid", "?"), exc)

    # ── Baseline helper ───────────────────────────────────────────────────────

    def capture_baseline(self) -> None:
        """Store a one-time baseline of current system state."""
        cpu  = psutil.cpu_percent(interval=1)
        vm   = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        self.db.upsert_baseline(cpu, vm.percent, disk.percent)
        logger.info(
            "Baseline captured: CPU=%.1f%% RAM=%.1f%% Disk=%.1f%%",
            cpu, vm.percent, disk.percent,
        )
