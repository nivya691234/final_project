"""
dashboard/app.py
----------------
Flask web application for the Software Aging Analyzer dashboard.
Serves 5 HTML pages and JSON API endpoints consumed by Chart.js.
"""

import json
import time
import logging
import sys
import os

from flask import Flask, jsonify, render_template, request

# Ensure project root on path when launched from any CWD
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config.settings import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, IGNORE_PROCESS_NAMES
from database.db_manager import DatabaseManager
from core.remediation import RemediationEngine
from core.llm_agent import LlmAgent
from core.pid_registry import get_registered_pids, get_registered_process_names

logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── DB instance (injected at startup via init_app) ─────────────────────────
_db: DatabaseManager = None


def init_app(db: DatabaseManager) -> None:
    """Call this before app.run() to wire the shared DB instance."""
    global _db
    _db = db


def _get_db() -> DatabaseManager:
    if _db is None:
        raise RuntimeError("Dashboard DB not initialised – call init_app() first.")
    return _db


# ═══════════════════════════════════════════════════════════════════════════════
# HTML Pages
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/processes")
def processes():
    return render_template("processes.html")


@app.route("/root-cause")
def root_cause():
    return render_template("root_cause.html")


@app.route("/predictions")
def predictions():
    return render_template("predictions.html")


@app.route("/recommendations")
def recommendations():
    return render_template("recommendations.html")


@app.route("/settings")
def settings():
    return render_template("settings.html")


# ═══════════════════════════════════════════════════════════════════════════════
# JSON API Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/current-status")
def api_current_status():
    """Single-card KPI snapshot for the overview page."""
    db   = _get_db()
    sys_latest = db.get_latest_system_metric() or {}
    pred_latest = db.get_latest_prediction() or {}
    rc_latest   = _latest_unresolved_root_cause(db) or {}
    baseline    = db.get_baseline() or {}
    stats       = db.get_db_stats()

    return jsonify({
        "cpu":               sys_latest.get("cpu", 0),
        "ram":               sys_latest.get("ram", 0),
        "ram_used_gb":       round(sys_latest.get("ram_used", 0) / 1073741824, 2),
        "ram_avail_gb":      round(sys_latest.get("ram_available", 0) / 1073741824, 2),
        "disk":              sys_latest.get("disk", 0),
        "net_send_kbps":     round(sys_latest.get("net_send_rate", 0) / 1024, 2),
        "net_recv_kbps":     round(sys_latest.get("net_recv_rate", 0) / 1024, 2),
        "load_avg":          sys_latest.get("load_avg", 0),
        "failure_probability": pred_latest.get("failure_probability", 0),
        "priority":          pred_latest.get("priority", "NORMAL"),
        "latest_cause":      rc_latest.get("cause", "—"),
        "latest_severity":   rc_latest.get("severity", "LOW"),
        "baseline_cpu":      baseline.get("cpu_baseline", 0),
        "baseline_ram":      baseline.get("ram_baseline", 0),
        "baseline_disk":     baseline.get("disk_baseline", 0),
        "db_stats":          stats,
        "server_ts":         time.time(),
    })


@app.route("/api/system-metrics")
def api_system_metrics():
    """Last N system-metric rows for chart rendering."""
    db   = _get_db()
    rows = db.get_system_metrics(limit=120)

    labels        = [_fmt_ts(r["timestamp"]) for r in rows]
    cpu           = [r["cpu"]            for r in rows]
    ram           = [r["ram"]            for r in rows]
    disk          = [r["disk"]           for r in rows]
    net_recv_kb   = [round(r["net_recv_rate"] / 1024, 2) for r in rows]
    net_send_kb   = [round(r["net_send_rate"] / 1024, 2) for r in rows]
    context_sw    = [r["context_switches"] for r in rows]
    load_avg      = [r["load_avg"]       for r in rows]

    return jsonify({
        "labels":       labels,
        "cpu":          cpu,
        "ram":          ram,
        "disk":         disk,
        "net_recv_kb":  net_recv_kb,
        "net_send_kb":  net_send_kb,
        "context_sw":   context_sw,
        "load_avg":     load_avg,
    })


@app.route("/api/process-metrics")
def api_process_metrics():
    """Recent process metrics grouped by process name (top processes)."""
    db        = _get_db()
    top_procs = db.get_top_processes(limit=15)
    detailed  = db.get_process_metrics(limit=300)

    # Build per-name time series for top 5 by memory
    name_set = []
    seen     = set()
    for p in top_procs:
        n = p["name"]
        if n not in seen:
            seen.add(n)
            name_set.append(n)
        if len(name_set) >= 5:
            break

    series = {}
    for name in name_set:
        pts = [r for r in detailed if r["name"] == name][-60:]
        series[name] = {
            "labels": [_fmt_ts(r["timestamp"]) for r in pts],
            "memory": [round(r["memory"], 2)   for r in pts],
            "cpu":    [round(r["cpu"],    2)    for r in pts],
        }

    return jsonify({
        "top_processes": top_procs,
        "series":        series,
    })


@app.route("/api/root-causes")
def api_root_causes():
    db   = _get_db()
    rows = db.get_root_causes(limit=50)
    filtered = []
    last_exec_cache = {}
    ignore = {n.lower() for n in IGNORE_PROCESS_NAMES}
    for r in rows:
        target = r.get("name") or "system"
        if target.lower() in ignore:
            continue
        if target not in last_exec_cache:
            last_exec_cache[target] = db.get_last_executed_action_time(target)
        last_exec = last_exec_cache[target]
        if last_exec and r.get("timestamp", 0) <= last_exec:
            continue
        r["ts_human"] = _fmt_ts(r["timestamp"])
        filtered.append(r)
    return jsonify({"causes": filtered})


@app.route("/api/predictions")
def api_predictions():
    db   = _get_db()
    rows = db.get_predictions(limit=100)

    labels  = [_fmt_ts(r["timestamp"])             for r in rows]
    probs   = [round(r["failure_probability"]*100, 2) for r in rows]
    lambdas = [r["lambda_val"]                     for r in rows]

    # Failure curve from the latest lambda
    curve      = []
    curve_ts   = []
    curve_prob = []
    if rows:
        from models.reliability_model import ReliabilityModel
        model = ReliabilityModel()
        lam   = rows[-1]["lambda_val"]
        for pt in model.failure_curve(lam, horizon_minutes=120, points=60):
            curve_ts.append(f"{pt['t']:.0f} min")
            curve_prob.append(round(pt["p"] * 100, 2))

    latest = db.get_latest_prediction() or {}
    restart_ts  = latest.get("predicted_restart_time")
    crash_ts    = latest.get("predicted_crash_time")
    rc_latest   = _latest_unresolved_root_cause(db) or {}

    if not rc_latest:
        restart_ts = None
        crash_ts = None

    return jsonify({
        "labels":            labels,
        "probabilities":     probs,
        "lambdas":           lambdas,
        "curve_labels":      curve_ts,
        "curve_probs":       curve_prob,
        "latest_probability": latest.get("failure_probability", 0),
        "priority":           latest.get("priority", "NORMAL") if rc_latest else "NORMAL",
        "predicted_restart":  _fmt_abs_ts(restart_ts),
        "predicted_crash":    _fmt_abs_ts(crash_ts),
        "lambda_val":         latest.get("lambda_val", 0),
        "cause_name":         rc_latest.get("name", "—") if rc_latest else "—",
        "cause_type":         rc_latest.get("cause", "—") if rc_latest else "—",
    })


@app.route("/api/recommendations")
def api_recommendations():
    db   = _get_db()
    rows = db.get_recommendations(limit=30)
    filtered = []
    last_exec_cache = {}
    ignore = {n.lower() for n in IGNORE_PROCESS_NAMES}
    for r in rows:
        target = _extract_quoted_name(r.get("recommendation") or "")
        if target:
            if target.lower() in ignore:
                continue
            if target not in last_exec_cache:
                last_exec_cache[target] = db.get_last_executed_action_time(target)
            last_exec = last_exec_cache[target]
            if last_exec and r.get("timestamp", 0) <= last_exec:
                continue
        r["ts_human"] = _fmt_ts(r["timestamp"])
        filtered.append(r)
    return jsonify({"recommendations": filtered})


@app.route("/api/pending-actions")
def api_pending_actions():
    db = _get_db()
    rows = db.get_pending_actions(limit=20)
    filtered = []
    last_exec_cache = {}
    internal_pids = set(get_registered_pids())
    internal_names = {n.lower() for n in get_registered_process_names()}
    ignore = {n.lower() for n in IGNORE_PROCESS_NAMES}
    for r in rows:
        target = r.get("target")
        pid = r.get("pid")
        if (pid and pid in internal_pids) or (target and target.lower() in internal_names):
            continue
        if target and target.lower() in ignore:
            continue
        if target:
            if target not in last_exec_cache:
                last_exec_cache[target] = db.get_last_executed_action_time(target)
            last_exec = last_exec_cache[target]
            if last_exec and r.get("timestamp", 0) <= last_exec:
                continue
        r["ts_human"] = _fmt_ts(r["timestamp"])
        try:
            r["params"] = json.loads(r.get("params_json") or "{}")
        except Exception:
            r["params"] = {}
        filtered.append(r)
    return jsonify({"actions": filtered})


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _fmt_ts(epoch: float) -> str:
    if not epoch:
        return "—"
    import datetime
    return datetime.datetime.fromtimestamp(epoch).strftime("%H:%M:%S")


def _fmt_abs_ts(epoch) -> str:
    if epoch is None:
        return "—"
    import datetime
    return datetime.datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


def _latest_unresolved_root_cause(db: DatabaseManager) -> dict | None:
    rows = db.get_root_causes(limit=50)
    last_exec_cache = {}
    ignore = {n.lower() for n in IGNORE_PROCESS_NAMES}
    for r in rows:
        target = r.get("name") or "system"
        if target.lower() in ignore:
            continue
        if target not in last_exec_cache:
            last_exec_cache[target] = db.get_last_executed_action_time(target)
        last_exec = last_exec_cache[target]
        if last_exec and r.get("timestamp", 0) <= last_exec:
            continue
        return r
    return None


def _extract_quoted_name(text: str) -> str | None:
    if "'" not in text:
        return None
    parts = text.split("'")
    return parts[1] if len(parts) >= 3 else None


# ═══════════════════════════════════════════════════════════════════════════════
# AI Chatbot Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json or {}
    message = data.get("message", "")
    
    agent = LlmAgent(_get_db())
    response_data = agent.process_message(message)
    
    return jsonify(response_data)

@app.route("/api/action", methods=["POST"])
def api_action():
    data = request.json or {}
    action = data.get("action")
    target = data.get("target")
    pid = data.get("pid")
    params = data.get("params") or {}

    if not action:
        return jsonify({"success": False, "message": "Missing action."}), 400
    if not target and not pid and action != "disable_startup":
        return jsonify({"success": False, "message": "Missing target or pid."}), 400

    remediator = RemediationEngine()
    result = remediator.execute_action(action, target=target, pid=pid, **params)
    return jsonify(result)


@app.route("/api/action/decision", methods=["POST"])
def api_action_decision():
    data = request.json or {}
    action_id = data.get("id")
    decision = data.get("decision")
    if not action_id or decision not in {"approve", "deny"}:
        return jsonify({"success": False, "message": "Missing id or decision."}), 400

    db = _get_db()
    # Fetch action payload
    action_row = db.get_action_by_id(action_id)
    if not action_row:
        return jsonify({"success": False, "message": "Action not found."}), 404

    if decision == "deny":
        db.update_action_status(action_id, "CANCELLED", "User denied.")
        return jsonify({"success": True, "message": "Action cancelled."})

    remediator = RemediationEngine()
    params = {}
    try:
        params = json.loads(action_row.get("params_json") or "{}")
    except Exception:
        params = {}

    result = remediator.execute_action(
        action_row.get("action"),
        target=action_row.get("target"),
        pid=action_row.get("pid"),
        **params,
    )

    status = "EXECUTED" if result.get("success") else "FAILED"
    db.update_action_status(action_id, status, result.get("message", ""))
    if result.get("success"):
        return jsonify({
            "success": True,
            "message": f"Problem fixed. {result.get('message', '')}".strip(),
        })
    return jsonify(result)

# ═══════════════════════════════════════════════════════════════════════════════
# Notification Preferences & History
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/notifications/settings", methods=["GET"])
def api_notification_settings_get():
    """Return current notification preferences."""
    db = _get_db()
    prefs = db.get_notification_settings()
    if not prefs:
        # Return defaults from config
        from config.settings import (
            NOTIFY_ENABLED, NOTIFY_COOLDOWN_SEC,
            NOTIFY_MIN_SEVERITY, NOTIFY_ALERT_TYPES,
        )
        prefs = {
            "enabled":      NOTIFY_ENABLED,
            "cooldown_sec": NOTIFY_COOLDOWN_SEC,
            "min_severity": NOTIFY_MIN_SEVERITY,
            "alert_types":  dict(NOTIFY_ALERT_TYPES),
        }
    return jsonify(prefs)


@app.route("/api/notifications/settings", methods=["POST"])
def api_notification_settings_post():
    """Update notification preferences."""
    db   = _get_db()
    data = request.json or {}

    settings = {
        "enabled":          data.get("enabled", True),
        "cooldown_sec":     data.get("cooldown_sec", 600),
        "min_severity":     data.get("min_severity", "LOW"),
        "alert_types_json": data.get("alert_types", {}),
    }
    db.upsert_notification_settings(settings)
    return jsonify({"success": True, "message": "Notification settings saved."})


@app.route("/api/notifications/settings", methods=["DELETE"])
def api_notification_settings_reset():
    """Reset notification preferences to defaults."""
    db = _get_db()
    # Delete the settings row to fall back to config defaults
    db._execute("DELETE FROM notification_settings WHERE id = 1")
    return jsonify({"success": True, "message": "Settings reset to defaults."})


@app.route("/api/notifications/history")
def api_notification_history():
    """Return recent notification log entries."""
    db    = _get_db()
    limit = request.args.get("limit", 50, type=int)
    rows  = db.get_notification_history(limit=limit)
    for r in rows:
        r["ts_human"] = _fmt_ts(r.get("timestamp", 0))
    return jsonify({"notifications": rows})


# ═══════════════════════════════════════════════════════════════════════════════
# Stand-alone launch
# ═══════════════════════════════════════════════════════════════════════════════

def run_dashboard(db: DatabaseManager) -> None:
    init_app(db)
    logger.info("Dashboard starting at http://%s:%s", FLASK_HOST, FLASK_PORT)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, use_reloader=False)
