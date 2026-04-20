"""
register_startup.py
-------------------
Create or remove a Startup entry for start_tool.
Usage:
  python register_startup.py install
  python register_startup.py uninstall
"""

import os
import sys

STARTUP_NAME = "SoftwareAgingAnalyzer"


def startup_dir() -> str:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA not set.")
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def install() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    startup = startup_dir()
    os.makedirs(startup, exist_ok=True)

    exe_path = os.path.join(root, "start_tool.exe")
    if os.path.isfile(exe_path):
        cmd = f"\"{exe_path}\""
    else:
        cmd = f"\"{sys.executable}\" \"{os.path.join(root, 'start_tool.py')}\""

    bat_path = os.path.join(startup, f"{STARTUP_NAME}.cmd")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(f"@echo off\n{cmd}\n")

    print(f"Startup entry created at: {bat_path}")


def uninstall() -> None:
    startup = startup_dir()
    bat_path = os.path.join(startup, f"{STARTUP_NAME}.cmd")
    if os.path.exists(bat_path):
        os.remove(bat_path)
        print("Startup entry removed.")
    else:
        print("Startup entry not found.")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python register_startup.py install|uninstall")
        return

    cmd = sys.argv[1].lower()
    if cmd == "install":
        install()
    elif cmd == "uninstall":
        uninstall()
    else:
        print("Unknown command. Use install or uninstall.")


if __name__ == "__main__":
    main()
