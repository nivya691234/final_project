"""
core/pid_registry.py
--------------------
Lightweight PID registry for internal processes.
Used to exclude this tool's own processes from monitoring.
"""

import json
import os
import time
from typing import Dict, List

import psutil

from config.settings import BASE_DIR

REGISTRY_DIR = os.path.join(BASE_DIR, ".runtime")
REGISTRY_PATH = os.path.join(REGISTRY_DIR, "pids.json")


def _load_registry() -> Dict[str, Dict]:
    if not os.path.exists(REGISTRY_PATH):
        return {}
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_registry(data: Dict[str, Dict]) -> None:
    os.makedirs(REGISTRY_DIR, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


def register_pid(name: str, pid: int) -> None:
    data = _load_registry()
    proc_name = None
    try:
        proc_name = psutil.Process(pid).name()
    except Exception:
        proc_name = None
    data[name] = {"pid": pid, "ts": time.time(), "proc_name": proc_name}
    _save_registry(data)


def unregister_pid(name: str) -> None:
    data = _load_registry()
    if name in data:
        data.pop(name)
        _save_registry(data)


def get_registered_pids() -> List[int]:
    data = _load_registry()
    pids = []
    for entry in data.values():
        pid = entry.get("pid")
        if isinstance(pid, int):
            pids.append(pid)
    return pids


def get_registered_process_names() -> List[str]:
    data = _load_registry()
    names = []
    for entry in data.values():
        proc_name = entry.get("proc_name")
        if isinstance(proc_name, str) and proc_name:
            names.append(proc_name)
    return names
