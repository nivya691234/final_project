"""
monitor_agent.py
----------------
Background monitoring agent.
Collects system and process metrics and stores them in SQLite.
"""

import logging
import signal
import sys
import threading
import time
import os

from config.settings import SAMPLING_INTERVAL
from core.collector import DataCollector
from database.db_manager import DatabaseManager
from core.pid_registry import register_pid, unregister_pid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("monitor_agent")

stop_event = threading.Event()


def _signal_handler(sig, frame):
    logger.info("Shutdown signal received (%s). Stopping…", sig)
    stop_event.set()
    sys.exit(0)


def main() -> None:
    register_pid("monitor_agent", os.getpid())
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("=" * 60)
    logger.info("  Software Aging Monitoring Agent")
    logger.info("=" * 60)

    db = DatabaseManager()
    db.initialize()
    logger.info("Database ready.")

    collector = DataCollector(db, interval=SAMPLING_INTERVAL)
    collector.capture_baseline()
    collector.start()

    logger.info("Agent running (interval=%ss).", SAMPLING_INTERVAL)

    try:
        while not stop_event.is_set():
            stop_event.wait(1)
    except KeyboardInterrupt:
        pass
    finally:
        collector.stop()
        unregister_pid("monitor_agent")
        logger.info("Agent shutdown complete.")


if __name__ == "__main__":
    main()
