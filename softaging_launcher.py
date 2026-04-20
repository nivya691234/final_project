"""
softaging_launcher.py
---------------------
Desktop launcher for the Software Aging Analyzer.
Manages background monitoring agent and Flask dashboard as a hybrid application.
Supports daemon mode, auto-start registration, and optional system tray integration.

Usage:
    # launch normally (foreground, opens browser)
    py softaging_launcher.py

    # launch in background daemon mode
    py softaging_launcher.py --daemon

    # register for Windows auto-start
    py softaging_launcher.py --install-startup

    # unregister from auto-start
    py softaging_launcher.py --uninstall-startup

    # stop running background instance
    py softaging_launcher.py --stop

    # demo mode (launches stress generators)
    py softaging_launcher.py --demo
"""

import argparse
import json
import logging
import os
import platform
import signal
import socket
import subprocess
import sys
import time
import threading
import webbrowser
from pathlib import Path

from config.settings import FLASK_HOST, FLASK_PORT

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("softaging_launcher")

# ── Application metadata ──────────────────────────────────────────────────────
APP_NAME = "SoftAgingAnalyzer"
STATE_DIR = Path.home() / ".softaging"
PID_FILE = STATE_DIR / "launcher.pid"
STATE_FILE = STATE_DIR / "launcher.state.json"


def ensure_state_dir() -> None:
    """Ensure the hidden .softaging directory exists."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def save_pids(agent_pid: int, server_pid: int, notifier_pid: int) -> None:
    """Save process PIDs for later cleanup."""
    ensure_state_dir()
    state = {
        "agent_pid": agent_pid,
        "server_pid": server_pid,
        "notifier_pid": notifier_pid,
        "timestamp": time.time(),
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    logger.debug("PID state saved to %s", STATE_FILE)


def load_pids() -> dict:
    """Load saved process PIDs."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def cleanup_pids() -> None:
    """Try to terminate saved processes."""
    state = load_pids()
    for key in ["agent_pid", "server_pid", "notifier_pid"]:
        pid = state.get(key)
        if pid:
            try:
                if platform.system() == "Windows":
                    subprocess.run(
                        ["taskkill", "/pid", str(pid), "/f"], 
                        capture_output=True
                    )
                else:
                    os.kill(pid, signal.SIGTERM)
                logger.info("Terminated process pid=%s", pid)
            except Exception:
                pass
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def is_port_open(host: str = FLASK_HOST, port: int = FLASK_PORT, 
                 timeout_sec: float = 1.0) -> bool:
    """Check if a port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except OSError:
        return False


def wait_for_port(host: str, port: int, timeout_sec: int = 30) -> bool:
    """Wait for a port to become available, up to timeout_sec seconds."""
    import time
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if is_port_open(host, port, timeout_sec=0.5):
            return True
        time.sleep(0.5)
    return False


# ── Windows Auto-Start Registration ───────────────────────────────────────────

def register_windows_startup() -> bool:
    """Register the application for Windows auto-start."""
    if platform.system() != "Windows":
        logger.warning("Auto-start registration is Windows-only")
        return False
    
    try:
        import winreg
        
        exe_path = os.path.abspath(sys.argv[0])
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, 
                           winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, 
                            f"python {exe_path} --daemon")
        
        logger.info("Registered application for Windows auto-start")
        print(f"✓ {APP_NAME} will start automatically on Windows boot")
        return True
    except ImportError:
        logger.error("winreg module not available (Windows-only)")
        return False
    except Exception as e:
        logger.error("Failed to register startup: %s", e)
        print(f"✗ Failed to register auto-start: {e}")
        return False


def unregister_windows_startup() -> bool:
    """Unregister the application from Windows auto-start."""
    if platform.system() != "Windows":
        logger.warning("Auto-start removal is Windows-only")
        return False
    
    try:
        import winreg
        
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                           winreg.KEY_WRITE) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        
        logger.info("Unregistered application from Windows auto-start")
        print(f"✓ {APP_NAME} will no longer start automatically")
        return True
    except ImportError:
        logger.error("winreg module not available (Windows-only)")
        return False
    except Exception as e:
        logger.error("Failed to unregister startup: %s", e)
        print(f"✗ Failed to unregister auto-start: {e}")
        return False


# ── Main launcher logic ───────────────────────────────────────────────────────

def start_services(demo: bool = False) -> tuple:
    """Start the monitoring agent, dashboard, and notifier.
    
    Returns: (agent_proc, server_proc, notifier_proc)
    """
    root = os.path.dirname(os.path.abspath(__file__))
    python = sys.executable

    logger.info("=" * 60)
    logger.info("  Software Aging Analyzer — Launcher")
    logger.info("=" * 60)
    logger.info("Starting background services...")

    agent = subprocess.Popen(
        [python, os.path.join(root, "monitor_agent.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    logger.info("✓ Monitor agent started (pid=%s)", agent.pid)

    server = subprocess.Popen(
        [python, os.path.join(root, "dashboard_server.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    logger.info("✓ Dashboard server started (pid=%s)", server.pid)

    notifier = subprocess.Popen(
        [python, os.path.join(root, "notifier_service.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    logger.info("✓ Notifier service started (pid=%s)", notifier.pid)

    # Save PIDs for later cleanup
    save_pids(agent.pid, server.pid, notifier.pid)

    # Optionally start the stress-scenario generators
    if demo:
        def _launch_stress():
            stress_script = os.path.join(root, "stress_scenarios.py")
            try:
                subprocess.Popen(
                    [python, stress_script, "--all"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                logger.info("✓ Demo mode: stress_scenarios launched")
            except Exception as e:
                logger.error("Failed to launch stress scenarios: %s", e)

        # Schedule after 3 seconds to allow baseline capture
        threading.Timer(3.0, _launch_stress).start()

    return agent, server, notifier


def main() -> int:
    """Main entry point for the launcher."""
    parser = argparse.ArgumentParser(
        description="Software Aging Analyzer Desktop Launcher"
    )
    parser.add_argument(
        "--daemon", action="store_true",
        help="run as background daemon (no browser popup)"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="start with built-in stress scenarios for demo"
    )
    parser.add_argument(
        "--install-startup", action="store_true",
        help="register for Windows auto-start on boot"
    )
    parser.add_argument(
        "--uninstall-startup", action="store_true",
        help="unregister from Windows auto-start"
    )
    parser.add_argument(
        "--stop", action="store_true",
        help="stop the running background instance"
    )
    args = parser.parse_args()

    # Handle startup registration commands
    if args.install_startup:
        return 0 if register_windows_startup() else 1

    if args.uninstall_startup:
        return 0 if unregister_windows_startup() else 1

    # Handle stop command
    if args.stop:
        logger.info("Stopping running instance...")
        cleanup_pids()
        print("✓ Background instance stopped")
        return 0

    # Normal launch
    try:
        agent, server, notifier = start_services(demo=args.demo)

        # Wait for Flask server to be ready
        logger.info("Waiting for dashboard server to be ready...")
        if not wait_for_port(FLASK_HOST, FLASK_PORT, timeout_sec=30):
            logger.error("Dashboard server failed to start within 30 seconds")
            for proc in (agent, server, notifier):
                if proc.poll() is None:
                    proc.terminate()
            return 1

        logger.info("Dashboard ready at http://%s:%d", FLASK_HOST, FLASK_PORT)

        # Open browser unless in daemon mode
        if not args.daemon:
            logger.info("Opening dashboard in browser...")
            webbrowser.open(f"http://{FLASK_HOST}:{FLASK_PORT}")
            print()
            print("=" * 60)
            print("  Software Aging Analyzer is running!")
            print("=" * 60)
            print(f"  Dashboard: http://{FLASK_HOST}:{FLASK_PORT}")
            print()
            print("  Press Ctrl+C to stop")
            print("=" * 60)
        else:
            logger.info("Running in daemon mode (no browser)")
            print(f"✓ {APP_NAME} is running in background")
            print(f"  Dashboard: http://{FLASK_HOST}:{FLASK_PORT}")
            print(f"  To stop: py softaging_launcher.py --stop")

        # Keep the launcher alive
        try:
            while True:
                time.sleep(1)
                # Check if any process has died unexpectedly
                for i, proc in enumerate((agent, server, notifier)):
                    if proc.poll() is not None:
                        logger.error("Service died: proc=%s", 
                                   ["agent", "server", "notifier"][i])
                        raise RuntimeError(f"Service {i} died unexpectedly")
        except KeyboardInterrupt:
            logger.info("Shutdown signal received (Ctrl+C)")
            print("\nShutting down...")

    except Exception as e:
        logger.exception("Fatal error: %s", e)
        return 1

    finally:
        logger.info("Cleaning up...")
        cleanup_pids()
        logger.info("Launcher shutdown complete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
