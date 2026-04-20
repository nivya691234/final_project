"""
dashboard_server.py
--------------------
Dashboard server and analysis engine.
Runs analysis loop and serves the Flask web dashboard.
"""

import logging
import signal
import sys
import threading
import time
import os

from config.settings import ANALYSIS_EVERY_N, SAMPLING_INTERVAL
from core.action_policy import ActionPolicyEngine
from core.analyzer import TrendAnalyzer
from core.predictor import FailurePredictor
from core.prevention import PreventionEngine
from core.root_cause import RootCauseEngine
from dashboard.app import run_dashboard
from database.db_manager import DatabaseManager
from models.reliability_model import ReliabilityModel
from core.pid_registry import register_pid, unregister_pid
from core.collector import DataCollector
from core.notifier import SmartNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("server.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("dashboard_server")

stop_event = threading.Event()


def _signal_handler(sig, frame):
    logger.info("Shutdown signal received (%s). Stopping…", sig)
    stop_event.set()
    sys.exit(0)


def analysis_loop(db: DatabaseManager, stop_event: threading.Event, interval_s: float) -> None:
    analyzer = TrendAnalyzer(db)
    rc_engine = RootCauseEngine(db, analyzer)
    model = ReliabilityModel()
    predictor = FailurePredictor(db, analyzer, model)
    prevention = PreventionEngine(db)
    policy = ActionPolicyEngine(db)

    logger.info("Analysis loop started — running every %.0f seconds.", interval_s)

    while not stop_event.is_set():
        stop_event.wait(interval_s)
        if stop_event.is_set():
            break
        try:
            logger.info("── Analysis cycle start ──────────────────────────")
            rc_engine.run()
            predictor.run()
            prevention.run()
            policy.run()
            logger.info("── Analysis cycle complete ───────────────────────")
        except Exception as exc:
            logger.exception("Analysis loop error: %s", exc)

    logger.info("Analysis loop stopped.")


def agent_loop(db: DatabaseManager, stop_event: threading.Event, interval_s: float) -> None:
    collector = DataCollector(db, interval=interval_s)
    collector.capture_baseline()
    collector.start()

    logger.info("Monitor agent running (interval=%ss).", interval_s)

    try:
        while not stop_event.is_set():
            stop_event.wait(1)
    except KeyboardInterrupt:
        pass
    finally:
        collector.stop()
        logger.info("Agent shutdown complete.")


def notifier_loop(db: DatabaseManager, stop_event: threading.Event, poll_sec: float) -> None:
    notifier = SmartNotifier(db)

    logger.info("Notifier service running. Polling every %ss.", poll_sec)

    while not stop_event.is_set():
        try:
            sent = notifier.run()
            if sent:
                logger.info("Sent %d notification(s) this cycle.", len(sent))
        except Exception as exc:
            logger.debug("Notifier error: %s", exc)

        stop_event.wait(poll_sec)

    logger.info("Notifier shutdown complete.")


def main() -> None:
    register_pid("dashboard_server", os.getpid())
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("=" * 60)
    logger.info("  Software Aging Dashboard Server")
    logger.info("=" * 60)

    db = DatabaseManager()
    db.initialize()

    warm_up = SAMPLING_INTERVAL * 2
    logger.info("Warm-up: waiting %ds before first analysis…", warm_up)
    time.sleep(warm_up)

    analysis_interval = SAMPLING_INTERVAL * ANALYSIS_EVERY_N
    analysis_thread = threading.Thread(
        target=analysis_loop,
        args=(db, stop_event, analysis_interval),
        name="AnalysisLoop",
        daemon=True,
    )
    analysis_thread.start()

    # Start monitor agent thread
    agent_thread = threading.Thread(
        target=agent_loop,
        args=(db, stop_event, SAMPLING_INTERVAL),
        name="MonitorAgent",
        daemon=True,
    )
    agent_thread.start()

    # Start notifier thread
    notifier_thread = threading.Thread(
        target=notifier_loop,
        args=(db, stop_event, 10),  # POLL_SEC = 10
        name="NotifierService",
        daemon=True,
    )
    notifier_thread.start()

    logger.info("Launching dashboard…")
    try:
        run_dashboard(db)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        unregister_pid("dashboard_server")
        logger.info("Dashboard server shutdown complete.")


if __name__ == "__main__":
    main()
