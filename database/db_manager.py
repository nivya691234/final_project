"""
database/db_manager.py
----------------------
Centralised SQLite data-access layer for the Software Aging Analyzer.
Provides a thread-safe DatabaseManager class with methods for every table.
"""

import json
import os
import sqlite3
import threading
import time
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from config.settings import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Thread-safe wrapper around SQLite.
    Uses a threading.Lock so multiple threads can safely call insert/query
    methods concurrently without WAL-mode conflicts.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock  = threading.Lock()

    # ── Internal helpers ──────────────────────────────────────────────────────

    @contextmanager
    def _get_conn(self):
        """Yield a connection with row_factory=sqlite3.Row and auto-commit."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _execute(self, sql: str, params: Tuple = ()) -> None:
        with self._lock, self._get_conn() as conn:
            conn.execute(sql, params)

    def _query(self, sql: str, params: Tuple = ()) -> List[sqlite3.Row]:
        with self._lock, self._get_conn() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    # ── Initialisation ────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Create all tables from schema.sql if they do not exist."""
        schema_path = os.path.join(
            os.path.dirname(__file__), "schema.sql"
        )
        with open(schema_path, "r") as f:
            schema_sql = f.read()

        with self._lock, self._get_conn() as conn:
            conn.executescript(schema_sql)
            self._ensure_column(conn, "action_queue", "executed_at", "REAL")
            self._ensure_column(conn, "action_queue", "severity", "TEXT")
        logger.info("Database initialised at %s", self.db_path)

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if any(c[1] == column for c in cols):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    # ── system_metrics ────────────────────────────────────────────────────────

    def insert_system_metrics(self, data: Dict[str, Any]) -> None:
        sql = """
        INSERT INTO system_metrics
            (timestamp, cpu, ram, ram_used, ram_available,
             disk, disk_read_rate, disk_write_rate,
             net_send_rate, net_recv_rate,
             load_avg, context_switches, interrupt_rate)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
        self._execute(sql, (
            data.get("timestamp",        time.time()),
            data.get("cpu",              0),
            data.get("ram",              0),
            data.get("ram_used",         0),
            data.get("ram_available",    0),
            data.get("disk",             0),
            data.get("disk_read_rate",   0),
            data.get("disk_write_rate",  0),
            data.get("net_send_rate",    0),
            data.get("net_recv_rate",    0),
            data.get("load_avg",         0),
            data.get("context_switches", 0),
            data.get("interrupt_rate",   0),
        ))

    def get_system_metrics(self, limit: int = 200) -> List[Dict]:
        rows = self._query(
            "SELECT * FROM system_metrics ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in reversed(rows)]

    def get_latest_system_metric(self) -> Optional[Dict]:
        rows = self._query(
            "SELECT * FROM system_metrics ORDER BY timestamp DESC LIMIT 1"
        )
        return dict(rows[0]) if rows else None

    # ── process_metrics ───────────────────────────────────────────────────────

    def insert_process_metrics(self, data: Dict[str, Any]) -> None:
        sql = """
        INSERT INTO process_metrics
            (timestamp, pid, name, cpu, memory, memory_bytes, threads, fds)
        VALUES (?,?,?,?,?,?,?,?)
        """
        self._execute(sql, (
            data.get("timestamp",    time.time()),
            data.get("pid",          0),
            data.get("name",         "unknown"),
            data.get("cpu",          0),
            data.get("memory",       0),
            data.get("memory_bytes", 0),
            data.get("threads",      0),
            data.get("fds",          0),
        ))

    def get_process_metrics(self, limit: int = 500) -> List[Dict]:
        rows = self._query(
            """
            SELECT * FROM process_metrics
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(r) for r in reversed(rows)]

    def get_process_metrics_by_name(self, name: str, limit: int = 100) -> List[Dict]:
        rows = self._query(
            """
            SELECT * FROM process_metrics
            WHERE name = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (name, limit)
        )
        return [dict(r) for r in reversed(rows)]

    def get_latest_process_by_name(self, name: str) -> Optional[Dict]:
        rows = self._query(
            """
            SELECT * FROM process_metrics
            WHERE name = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (name,)
        )
        return dict(rows[0]) if rows else None

    def get_top_processes(self, limit: int = 20) -> List[Dict]:
        """Return the most recent snapshot of top processes by memory % that are still running."""
        cutoff = time.time() - 60  # Only processes seen in the last 60 seconds
        rows = self._query(
            """
            WITH latest AS (
                SELECT pid, MAX(timestamp) AS max_ts
                FROM process_metrics
                GROUP BY pid
                HAVING max_ts >= ?
            )
            SELECT pm.*
            FROM process_metrics pm
            JOIN latest l ON pm.pid = l.pid AND pm.timestamp = l.max_ts
            ORDER BY pm.memory DESC
            LIMIT ?
            """,
            (cutoff, limit)
        )
        return [dict(r) for r in rows]

    def get_distinct_process_names(self) -> List[str]:
        cutoff = time.time() - 60
        rows = self._query(
            "SELECT DISTINCT name FROM process_metrics WHERE timestamp >= ? ORDER BY name",
            (cutoff,)
        )
        return [r[0] for r in rows]

    # ── baseline ──────────────────────────────────────────────────────────────

    def upsert_baseline(self, cpu: float, ram: float, disk: float) -> None:
        self._execute(
            """
            INSERT INTO baseline (id, cpu_baseline, ram_baseline, disk_baseline, captured_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                cpu_baseline  = excluded.cpu_baseline,
                ram_baseline  = excluded.ram_baseline,
                disk_baseline = excluded.disk_baseline,
                captured_at   = excluded.captured_at
            """,
            (cpu, ram, disk, time.time())
        )

    def get_baseline(self) -> Optional[Dict]:
        rows = self._query("SELECT * FROM baseline WHERE id = 1")
        return dict(rows[0]) if rows else None

    # ── predictions ───────────────────────────────────────────────────────────

    def insert_prediction(self, data: Dict[str, Any]) -> None:
        sql = """
        INSERT INTO predictions
            (timestamp, failure_probability, predicted_restart_time,
             predicted_crash_time, lambda_val, priority)
        VALUES (?,?,?,?,?,?)
        """
        self._execute(sql, (
            data.get("timestamp",             time.time()),
            data.get("failure_probability",   0),
            data.get("predicted_restart_time", None),
            data.get("predicted_crash_time",   None),
            data.get("lambda_val",            0),
            data.get("priority",              "LOW"),
        ))

    def get_predictions(self, limit: int = 100) -> List[Dict]:
        rows = self._query(
            "SELECT * FROM predictions ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in reversed(rows)]

    def get_latest_prediction(self) -> Optional[Dict]:
        rows = self._query(
            "SELECT * FROM predictions ORDER BY timestamp DESC LIMIT 1"
        )
        return dict(rows[0]) if rows else None

    # ── root_cause ────────────────────────────────────────────────────────────

    def insert_root_cause(self, data: Dict[str, Any]) -> None:
        sql = """
        INSERT INTO root_cause (timestamp, pid, name, cause, severity, detail)
        VALUES (?,?,?,?,?,?)
        """
        self._execute(sql, (
            data.get("timestamp", time.time()),
            data.get("pid",       0),
            data.get("name",      "system"),
            data.get("cause",     "Unknown"),
            data.get("severity",  "LOW"),
            data.get("detail",    ""),
        ))

    def get_root_causes(self, limit: int = 50) -> List[Dict]:
        rows = self._query(
            "SELECT * FROM root_cause ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in rows]

    def get_latest_root_cause(self) -> Optional[Dict]:
        rows = self._query(
            "SELECT * FROM root_cause ORDER BY timestamp DESC LIMIT 1"
        )
        return dict(rows[0]) if rows else None

    # ── recommendations ───────────────────────────────────────────────────────

    def insert_recommendation(self, data: Dict[str, Any]) -> None:
        sql = """
        INSERT INTO recommendations (timestamp, recommendation, priority, related_cause)
        VALUES (?,?,?,?)
        """
        self._execute(sql, (
            data.get("timestamp",      time.time()),
            data.get("recommendation", ""),
            data.get("priority",       "MEDIUM"),
            data.get("related_cause",  ""),
        ))

    def get_recommendations(self, limit: int = 50) -> List[Dict]:
        rows = self._query(
            "SELECT * FROM recommendations ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in rows]

    # ── action_queue ─────────────────────────────────────────────────────────

    def insert_action_item(self, data: Dict[str, Any]) -> int:
        sql = """
        INSERT INTO action_queue
            (timestamp, action, target, pid, params_json, source, reason, severity, status, message, executed_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """
        params_json = data.get("params_json")
        if params_json is None:
            params_json = json.dumps(data.get("params", {}))
        with self._lock, self._get_conn() as conn:
            cur = conn.execute(sql, (
                data.get("timestamp", time.time()),
                data.get("action", ""),
                data.get("target", ""),
                data.get("pid"),
                params_json,
                data.get("source", ""),
                data.get("reason", ""),
                data.get("severity", "LOW"),
                data.get("status", "PENDING"),
                data.get("message", ""),
                data.get("executed_at"),
            ))
            return cur.lastrowid

    def get_pending_actions(self, limit: int = 20) -> List[Dict]:
        rows = self._query(
            """
            SELECT * FROM action_queue
            WHERE status = 'PENDING'
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(r) for r in rows]

    def get_action_by_id(self, action_id: int) -> Optional[Dict]:
        rows = self._query(
            "SELECT * FROM action_queue WHERE id = ?",
            (action_id,)
        )
        return dict(rows[0]) if rows else None

    def update_action_status(self, action_id: int, status: str, message: str = "") -> None:
        executed_at = time.time() if status == "EXECUTED" else None
        self._execute(
            """
            UPDATE action_queue
            SET status = ?, message = ?, executed_at = COALESCE(?, executed_at)
            WHERE id = ?
            """,
            (status, message, executed_at, action_id),
        )

    def get_last_executed_action_time(self, target: str) -> Optional[float]:
        rows = self._query(
            """
            SELECT MAX(executed_at) AS ts
            FROM action_queue
            WHERE status = 'EXECUTED' AND target = ?
            """,
            (target,)
        )
        if not rows or rows[0]["ts"] is None:
            return None
        return float(rows[0]["ts"])

    def action_exists_recent(self, action: str, target: Optional[str], pid: Optional[int], within_sec: int) -> bool:
        cutoff = time.time() - within_sec
        rows = self._query(
            """
            SELECT id FROM action_queue
            WHERE action = ? AND (target = ? OR (target IS NULL AND ? IS NULL))
              AND (pid = ? OR (pid IS NULL AND ? IS NULL))
              AND timestamp >= ?
            LIMIT 1
            """,
            (action, target, target, pid, pid, cutoff),
        )
        return bool(rows)

    # ── Health / utility ──────────────────────────────────────────────────────

    def get_db_stats(self) -> Dict[str, int]:
        tables = [
            "system_metrics", "process_metrics", "baseline",
            "predictions", "root_cause", "recommendations", "action_queue"
        ]
        stats = {}
        for t in tables:
            rows = self._query(f"SELECT COUNT(*) AS cnt FROM {t}")
            stats[t] = rows[0]["cnt"] if rows else 0
        return stats

    # ── notification_log ──────────────────────────────────────────────────────

    def insert_notification(self, data: Dict[str, Any]) -> None:
        sql = """
        INSERT INTO notification_log
            (timestamp, category, severity, target, title, body, cooldown_key)
        VALUES (?,?,?,?,?,?,?)
        """
        self._execute(sql, (
            data.get("timestamp", time.time()),
            data.get("category", ""),
            data.get("severity", "LOW"),
            data.get("target", "system"),
            data.get("title", ""),
            data.get("body", ""),
            data.get("cooldown_key", ""),
        ))

    def notification_sent_recently(self, cooldown_key: str, within_sec: int) -> bool:
        """Return True if a notification with this key was sent within `within_sec`."""
        cutoff = time.time() - within_sec
        rows = self._query(
            """
            SELECT id FROM notification_log
            WHERE cooldown_key = ? AND timestamp >= ?
            LIMIT 1
            """,
            (cooldown_key, cutoff),
        )
        return bool(rows)

    def get_notification_history(self, limit: int = 50) -> List[Dict]:
        rows = self._query(
            "SELECT * FROM notification_log ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in rows]

    # ── notification_settings ─────────────────────────────────────────────────

    def upsert_notification_settings(self, settings: Dict[str, Any]) -> None:
        alert_types = settings.get("alert_types_json", "{}")
        if isinstance(alert_types, dict):
            alert_types = json.dumps(alert_types)
        self._execute(
            """
            INSERT INTO notification_settings (id, enabled, cooldown_sec, min_severity, alert_types_json, updated_at)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                enabled          = excluded.enabled,
                cooldown_sec     = excluded.cooldown_sec,
                min_severity     = excluded.min_severity,
                alert_types_json = excluded.alert_types_json,
                updated_at       = excluded.updated_at
            """,
            (
                1 if settings.get("enabled", True) else 0,
                settings.get("cooldown_sec", 600),
                settings.get("min_severity", "LOW"),
                alert_types,
                time.time(),
            ),
        )

    def get_notification_settings(self) -> Optional[Dict]:
        rows = self._query("SELECT * FROM notification_settings WHERE id = 1")
        if not rows:
            return None
        d = dict(rows[0])
        # Parse JSON alert types
        try:
            d["alert_types"] = json.loads(d.get("alert_types_json", "{}"))
        except Exception:
            d["alert_types"] = {}
        return d

