"""
main.py
-------
Entry point for the Software Aging Analyzer.

Starts:
  1. Database initialisation and baseline capture
  2. DataCollector daemon thread (psutil collection loop)
  3. Analysis loop (every ANALYSIS_EVERY_N samples):
       TrendAnalyzer → RootCauseEngine → FailurePredictor → PreventionEngine
  4. Flask dashboard (blocking, runs in main thread)
"""

import logging
import signal
import sys
import threading
import time

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("analyzer.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

# ── Module imports ────────────────────────────────────────────────────────────
from config.settings import SAMPLING_INTERVAL, ANALYSIS_EVERY_N
from database.db_manager import DatabaseManager
from core.collector import DataCollector
from core.analyzer  import TrendAnalyzer
from core.root_cause import RootCauseEngine
from core.predictor  import FailurePredictor
from core.prevention import PreventionEngine
from core.action_policy import ActionPolicyEngine
from core.notifier import SmartNotifier
from models.reliability_model import ReliabilityModel
from dashboard.app import run_dashboard


# ── Analysis orchestration loop ───────────────────────────────────────────────

def analysis_loop(
    db: DatabaseManager,
    collector: DataCollector,
    stop_event: threading.Event,
    interval_s: float,
) -> None:
    """
    Runs the complete analysis pipeline every `interval_s` seconds.
    Designed to run as a daemon thread.
    """
    # Build analysis objects once (they are stateless per call)
    analyzer  = TrendAnalyzer(db)
    rc_engine = RootCauseEngine(db, analyzer)
    model     = ReliabilityModel()
    predictor = FailurePredictor(db, analyzer, model)
    prevention = PreventionEngine(db)
    policy = ActionPolicyEngine(db)
    notifier = SmartNotifier(db)

    logger.info(
        "Analysis loop started — running every %.0f seconds.", interval_s
    )

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
            notifier.run()
            logger.info("── Analysis cycle complete ───────────────────────")
        except Exception as exc:
            logger.exception("Analysis loop error: %s", exc)

    logger.info("Analysis loop stopped.")


# ── Graceful shutdown ─────────────────────────────────────────────────────────

stop_event = threading.Event()


def _signal_handler(sig, frame):
    logger.info("Shutdown signal received (%s). Stopping…", sig)
    stop_event.set()
    sys.exit(0)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    signal.signal(signal.SIGINT,  _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("=" * 60)
    logger.info("  Software Aging Analyzer & Rejuvenation Prediction Tool")
    logger.info("=" * 60)

    # 1. Initialise the database
    db = DatabaseManager()
    db.initialize()
    logger.info("Database ready.")

    # 2. Capture initial baseline
    collector = DataCollector(db, interval=SAMPLING_INTERVAL)
    collector.capture_baseline()

    # 3. Start data collection daemon
    collector.start()
    logger.info(
        "Data collection started (interval=%ss). "
        "Waiting for initial samples…", SAMPLING_INTERVAL
    )

    # Brief warm-up wait so analyzer has data on first run
    warm_up = SAMPLING_INTERVAL * 2
    logger.info("Warm-up: waiting %ds before first analysis…", warm_up)
    time.sleep(warm_up)

    # 4. Start analysis loop daemon
    analysis_interval = SAMPLING_INTERVAL * ANALYSIS_EVERY_N
    analysis_thread = threading.Thread(
        target=analysis_loop,
        args=(db, collector, stop_event, analysis_interval),
        name="AnalysisLoop",
        daemon=True,
    )
    analysis_thread.start()

    # 5. Launch Flask dashboard (blocks main thread)
    logger.info("Launching dashboard…")
    try:
        run_dashboard(db)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        collector.stop()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()
