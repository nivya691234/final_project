"""
core/remediation.py
-------------------
Execution engine for automated remediation actions.
Uses psutil to interact with running processes (kill, suspend, resume, change priority, set affinity).
Also supports best-effort restart and Windows startup disabling.
"""

import logging
import os
import shutil
import subprocess
from typing import Iterable, Optional

import psutil

logger = logging.getLogger(__name__)


class RemediationEngine:
    def execute_action(
        self,
        action: str,
        target: Optional[str] = None,
        pid: Optional[int] = None,
        **kwargs,
    ) -> dict:
        """
        Execute a specific remediation action against a target process name.
        Actions supported:
          - kill
          - restart
          - suspend
          - resume
          - limit_cpu (affinity)
          - set_affinity
          - lower_priority
          - disable_startup (Windows Startup folder)
        """
        logger.info("Remediation executing: %s on target=%s pid=%s", action, target, pid)

        if action == "disable_startup":
            if not target:
                return {"success": False, "message": "disable_startup requires a target name."}
            return self._disable_startup(target)

        procs = self._get_processes(target=target, pid=pid)
        if not procs:
            return {"success": False, "message": "Process not found or already terminated."}

        success_count = 0
        errors = []

        for p in procs:
            try:
                if action == "kill":
                    p.kill()
                elif action == "restart":
                    self._restart_process(p)
                elif action == "suspend":
                    p.suspend()
                elif action == "resume":
                    p.resume()
                elif action == "limit_cpu":
                    # Restrict to a single core (core 0)
                    p.cpu_affinity([0])
                elif action == "set_affinity":
                    cores = self._parse_cores(kwargs.get("cores"))
                    if not cores:
                        return {"success": False, "message": "set_affinity requires a non-empty cores list."}
                    p.cpu_affinity(cores)
                elif action == "lower_priority":
                    # Reduce scheduling priority
                    # Use psutil.BELOW_NORMAL_PRIORITY_CLASS on Windows, or positive nice value on Unix
                    if hasattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS"):
                        p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    else:
                        p.nice(10) # Unix nice
                else:
                    return {"success": False, "message": f"Unknown action: {action}"}
                
                success_count += 1
            except psutil.NoSuchProcess:
                pass # Already dead
            except psutil.AccessDenied:
                errors.append(f"Access denied to PID {p.pid}")
            except Exception as e:
                errors.append(f"Error on PID {p.pid}: {str(e)}")

        if success_count > 0:
            msg = f"Successfully executed '{action}' on {success_count} instance(s)."
            if errors:
                msg += f" (Some errors: {', '.join(errors)})"
            return {"success": True, "message": msg}
        else:
            return {"success": False, "message": f"Failed to execute '{action}' on '{target}'. Errors: {', '.join(errors)}"}

    def _get_processes(self, target: Optional[str], pid: Optional[int]) -> list[psutil.Process]:
        if pid:
            try:
                return [psutil.Process(int(pid))]
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                return []

        if not target:
            return []

        procs = []
        for p in psutil.process_iter(["name"]):
            try:
                if p.info["name"] == target:
                    procs.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return procs

    def _parse_cores(self, cores_value: Optional[Iterable]) -> list[int]:
        if cores_value is None:
            return []
        if isinstance(cores_value, str):
            cores = [c.strip() for c in cores_value.split(",") if c.strip().isdigit()]
            return [int(c) for c in cores]
        try:
            return [int(c) for c in cores_value]
        except Exception:
            return []

    def _restart_process(self, proc: psutil.Process) -> None:
        try:
            cmdline = proc.cmdline()
            exe = proc.exe()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            raise psutil.AccessDenied(proc.pid)

        try:
            proc.kill()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            raise

        launch_cmd = cmdline if cmdline else ([exe] if exe else [])
        if not launch_cmd:
            raise RuntimeError("Unable to resolve executable for restart.")
        subprocess.Popen(launch_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _disable_startup(self, target: str) -> dict:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return {"success": False, "message": "APPDATA not set; cannot locate Startup folder."}

        startup_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        if not os.path.isdir(startup_dir):
            return {"success": False, "message": "Startup folder not found."}

        disabled_dir = os.path.join(startup_dir, "disabled")
        os.makedirs(disabled_dir, exist_ok=True)

        target_l = target.lower()
        moved = 0
        for name in os.listdir(startup_dir):
            if name.lower().find(target_l) == -1:
                continue
            src = os.path.join(startup_dir, name)
            if os.path.isdir(src):
                continue
            dst = os.path.join(disabled_dir, name)
            try:
                shutil.move(src, dst)
                moved += 1
            except Exception as exc:
                logger.warning("Failed to move %s: %s", name, exc)

        if moved == 0:
            return {"success": False, "message": f"No Startup entries matched '{target}'."}
        return {"success": True, "message": f"Disabled {moved} Startup item(s) matching '{target}'."}
