"""
notifier_service.py
-------------------
Background notifier service.

Can run as a standalone process OR is automatically integrated into
the main analysis loop via core/notifier.py.

When run standalone (python notifier_service.py), it polls the database
every POLL_SEC seconds and fires toasts for new events — useful when
you want notifications without running the full dashboard.
"""

import logging
import signal
import sys
import threading
import time
import os

from database.db_manager import DatabaseManager
from core.pid_registry import register_pid, unregister_pid
from core.notifier import SmartNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("notifier.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("notifier_service")

stop_event = threading.Event()

POLL_SEC = 10


def _signal_handler(sig, frame):
    logger.info("Shutdown signal received (%s). Stopping…", sig)
    stop_event.set()
    sys.exit(0)


def main() -> None:
    register_pid("notifier_service", os.getpid())
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    db = DatabaseManager()
    db.initialize()

    notifier = SmartNotifier(db)

    logger.info("Notifier service running. Polling every %ss.", POLL_SEC)

    while not stop_event.is_set():
        try:
            sent = notifier.run()
            if sent:
                logger.info("Sent %d notification(s) this cycle.", len(sent))
        except Exception as exc:
            logger.debug("Notifier error: %s", exc)

        stop_event.wait(POLL_SEC)

    unregister_pid("notifier_service")


if __name__ == "__main__":
    main()
