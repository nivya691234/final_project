"""
start_tool.py
-------------
All-in-one launcher for the monitoring agent and dashboard server.
Starts both processes and opens the dashboard in a browser.
"""

import os
import signal
import socket
import subprocess
import sys
import time
import threading
import webbrowser

from config.settings import FLASK_HOST, FLASK_PORT


def _show_startup_toast() -> None:
    """Show a simple startup toast when the launcher starts all services."""
    try:
        # Check if notifications are enabled
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        db.initialize()
        prefs = db.get_notification_settings()
        if prefs and not bool(prefs.get("enabled", 1)):
            return  # Notifications disabled
        from core.notifier import _show_toast
        _show_toast(
            title="Software Aging Analyzer",
            body="Monitoring agent, dashboard, and notifier launched successfully.",
            severity="LOW",
        )
    except Exception:
        pass


def wait_for_port(host: str, port: int, timeout_sec: int = 20) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> None:
    import argparse

    root = os.path.dirname(os.path.abspath(__file__))
    python = sys.executable

    parser = argparse.ArgumentParser(description="Launch analyzer + dashboard")
    parser.add_argument("--demo", action="store_true",
                        help="start built-in stress scenarios for demonstration")
    args = parser.parse_args()

    agent = subprocess.Popen([python, os.path.join(root, "monitor_agent.py")])
    server = subprocess.Popen([python, os.path.join(root, "dashboard_server.py")])
    notifier = subprocess.Popen([python, os.path.join(root, "notifier_service.py")])

    # optionally spawn the stress generators with a short delay so
    # baseline capture (which usually happens on agent start) isn't
    # polluted by the injected load.
    if args.demo:
        def _launch_stress():
            stress_script = os.path.join(root, "stress_scenarios.py")
            try:
                subprocess.Popen([python, stress_script, "--all"])
                print("[start_tool] demo mode: stress_scenarios launched")
            except Exception as e:
                print("[start_tool] failed to launch stress scenarios:", e)

        # schedule after 3 seconds
        threading.Timer(3.0, _launch_stress).start()

    if wait_for_port(FLASK_HOST, FLASK_PORT, timeout_sec=30):
        webbrowser.open(f"http://{FLASK_HOST}:{FLASK_PORT}")
        # _show_startup_toast()  # Disabled to respect user notification settings

    try:
        while True:
            time.sleep(1)
            if agent.poll() is not None or server.poll() is not None:
                break
    except KeyboardInterrupt:
        pass
    finally:
        for proc in (agent, server, notifier):
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    main()
