"""
core/notifier.py
----------------
Antivirus-style smart notification engine.

Integrates directly into the analysis loop and fires non-blocking
Windows toast notifications when aging events are detected.

Features:
  • Per-alert cooldown (same alert won't fire twice within N seconds)
  • Severity-based toast styling (CRITICAL/HIGH/MEDIUM/LOW)
  • User-controllable preferences (enable/disable, severity filter, alert types)
  • All notifications are logged to the notification_log table
"""

import ctypes
import logging
import subprocess
import sys
import threading
import time
from typing import Dict, List, Optional

from config.settings import (
    NOTIFY_ENABLED,
    NOTIFY_COOLDOWN_SEC,
    NOTIFY_MIN_SEVERITY,
    NOTIFY_ALERT_TYPES,
    NOTIFY_HEALTH_INTERVAL,
    NOTIFY_DEGRADATION_THRESHOLD,
    SEVERITY_LEVELS,
    IGNORE_PROCESS_NAMES,
)
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

# ── Toast backend ────────────────────────────────────────────────────────────

_TOAST_AVAILABLE = False
_WIN10TOAST_AVAILABLE = False

try:
    from winsdk.windows.data.xml.dom import XmlDocument
    from winsdk.windows.ui.notifications import (
        ToastNotification,
        ToastNotificationManager,
    )
    _TOAST_AVAILABLE = True
except Exception:
    pass

try:
    from plyer import notification as _plyer_notify
    _TOAST_AVAILABLE = True
except ImportError:
    _plyer_notify = None

try:
    from win10toast import ToastNotifier
    _WIN10TOAST_AVAILABLE = True
    _TOAST_AVAILABLE = True
except ImportError:
    ToastNotifier = None

APP_ID = "SoftwareAgingAnalyzer"


def _set_windows_app_id(app_id: str) -> None:
    """Set the Windows AppUserModelID for toast notifications."""
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        # If it fails, the system may still show a toast via fallback backends.
        pass


# ── Severity → emoji / label ─────────────────────────────────────────────────

SEVERITY_ICON = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
    "LOW":      "🔵",
}

SEVERITY_AUDIO = {
    "CRITICAL": "ms-winsoundevent:Notification.Looping.Alarm",
    "HIGH":     "ms-winsoundevent:Notification.Default",
    "MEDIUM":   "",  # silent by default, so medium alerts do not disturb
    "LOW":      "",  # ignored unless user explicitly lowers threshold
}


# ── Toast display functions ──────────────────────────────────────────────────

def _build_toast_xml(title: str, body: str, severity: str = "LOW") -> str:
    """Build styled Windows toast XML with severity-based audio."""
    icon = SEVERITY_ICON.get(severity, "🔵")
    audio_src = SEVERITY_AUDIO.get(severity, "")

    # For CRITICAL: persistent toast (scenario=reminder keeps it on screen)
    scenario = ' scenario="reminder"' if severity == "CRITICAL" else ""

    audio_tag = ""
    if audio_src:
        audio_tag = f"  <audio src='{audio_src}' loop='false'/>"
    elif severity in {"LOW", "MEDIUM"}:
        audio_tag = "  <audio silent='true'/>"

    xml = (
        f"<toast{scenario}>"
        "  <visual>"
        "    <binding template='ToastGeneric'>"
        f"      <text>{icon} {title}</text>"
        f"      <text>{body}</text>"
        "      <text placement='attribution'>Software Aging Analyzer</text>"
        "    </binding>"
        "  </visual>"
        f"{audio_tag}"
        "</toast>"
    )
    return xml


def _show_toast(title: str, body: str, severity: str = "LOW") -> bool:
    """
    Show a Windows toast notification.  Returns True on success.
    Falls back to plyer and win10toast if winsdk is unavailable.
    """
    _set_windows_app_id(APP_ID)

    # Preferred backend: win10toast when installed, since your manual test worked with it.
    if _WIN10TOAST_AVAILABLE and ToastNotifier is not None:
        try:
            toaster = ToastNotifier()
            icon_map = {"CRITICAL": "⚠", "HIGH": "⚠", "MEDIUM": "ℹ", "LOW": "ℹ"}
            toaster.show_toast(
                f"{icon_map.get(severity, 'ℹ')} {title}",
                body,
                threaded=False,
                duration=10 if severity in {"LOW", "MEDIUM"} else 20 if severity == "HIGH" else 30,
                icon_path=None,
            )
            return True
        except Exception as exc0:
            logger.debug("win10toast first-pass failed: %s — falling back", exc0)

    try:
        from winsdk.windows.data.xml.dom import XmlDocument
        from winsdk.windows.ui.notifications import (
            ToastNotification,
            ToastNotificationManager,
        )
        notifier = ToastNotificationManager.create_toast_notifier(APP_ID)
        xml_str = _build_toast_xml(title, body, severity)
        doc = XmlDocument()
        doc.load_xml(xml_str)
        toast = ToastNotification(doc)
        notifier.show(toast)
        return True
    except Exception as exc:
        logger.debug("winsdk toast failed: %s — trying plyer fallback", exc)

    # Fallback: plyer
    if _plyer_notify is not None:
        try:
            icon_map = {"CRITICAL": "⚠", "HIGH": "⚠", "MEDIUM": "ℹ", "LOW": "ℹ"}
            _plyer_notify.notify(
                title=f"{icon_map.get(severity, 'ℹ')} {title}",
                message=body,
                app_name="Software Aging Analyzer",
                timeout=10 if severity in {"LOW", "MEDIUM"} else 20 if severity == "HIGH" else 30,
            )
            return True
        except Exception as exc2:
            logger.debug("plyer toast failed: %s", exc2)

    # Fallback: win10toast
    if _WIN10TOAST_AVAILABLE and ToastNotifier is not None:
        try:
            toaster = ToastNotifier(app_id=APP_ID)
            icon_map = {"CRITICAL": "⚠", "HIGH": "⚠", "MEDIUM": "ℹ", "LOW": "ℹ"}
            toaster.show_toast(
                f"{icon_map.get(severity, 'ℹ')} {title}",
                body,
                threaded=True,
                duration=10 if severity in {"LOW", "MEDIUM"} else 20 if severity == "HIGH" else 30,
                icon_path=None,
            )
            return True
        except Exception as exc3:
            logger.debug("win10toast failed: %s", exc3)

    # Fallback: Windows PowerShell native toast if available
    if sys.platform.startswith("win"):
        try:
            powershell_script = (
                '$title = "' + title.replace('"', '`"') + '"; '
                '$body  = "' + body.replace('"', '`"') + '"; '
                '$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02; '
                '$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template); '
                '$textNodes = $xml.GetElementsByTagName("text"); '
                '$textNodes.Item(0).AppendChild($xml.CreateTextNode($title)) > $null; '
                '$textNodes.Item(1).AppendChild($xml.CreateTextNode($body)) > $null; '
                '$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); '
                '[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Software Aging Analyzer").Show($toast)'
            )
            subprocess.run([
                "powershell", "-NoProfile", "-Command", powershell_script
            ], check=True, capture_output=True)
            return True
        except Exception as exc4:
            logger.debug("PowerShell toast failed: %s", exc4)

    logger.warning("No toast backend available — notification not shown.")

    if _show_fallback_window(title, body, severity):
        logger.info("Displayed fallback window notification.")
        return True

    return False


def _show_fallback_window(title: str, body: str, severity: str = "LOW") -> bool:
    """Fallback visible desktop popup using Tkinter when notification toasts fail."""
    try:
        import tkinter as tk
    except ImportError:
        return False

    color_map = {
        "CRITICAL": "#ff4d4d",
        "HIGH": "#ff9900",
        "MEDIUM": "#ffd24d",
        "LOW": "#5bc0de",
    }
    bg_color = color_map.get(severity, "#5bc0de")
    fg_color = "#202020"

    def popup() -> None:
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.95)

        width, height = 320, 100
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = screen_width - width - 16
        y = screen_height - height - 80
        root.geometry(f"{width}x{height}+{x}+{y}")

        frame = tk.Frame(root, bg=bg_color, bd=2, relief="raised")
        frame.pack(expand=True, fill="both")

        title_label = tk.Label(
            frame,
            text=title,
            font=("Segoe UI", 11, "bold"),
            bg=bg_color,
            fg=fg_color,
            anchor="w",
            pady=6,
        )
        title_label.pack(fill="x", padx=12)

        body_label = tk.Label(
            frame,
            text=body,
            font=("Segoe UI", 10),
            bg=bg_color,
            fg=fg_color,
            justify="left",
            wraplength=296,
        )
        body_label.pack(fill="x", padx=12, pady=(0, 10))

        root.after(4500, root.destroy)
        root.mainloop()

    thread = threading.Thread(target=popup, daemon=True)
    thread.start()
    return True


# ── Smart Notifier ───────────────────────────────────────────────────────────

class SmartNotifier:
    """
    Antivirus-style notification engine.

    Call ``run()`` after each analysis cycle. It reads the latest
    root causes, predictions, recommendations, and system trends from
    the database, then fires desktop toasts as needed — with cooldown
    and user-preference filtering.
    """

    def __init__(self, db: DatabaseManager):
        self.db = db
        self._last_health_toast = 0.0  # epoch of last health-summary toast
        self._ignore = {n.lower() for n in IGNORE_PROCESS_NAMES}

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(self) -> List[Dict]:
        """
        Run one notification pass.  Returns list of notifications that
        were actually shown (for logging / testing).
        """
        prefs = self._load_prefs()

        if not prefs["enabled"]:
            return []

        shown: List[Dict] = []

        # 1. Root cause alerts
        if prefs["alert_types"].get("root_cause", True):
            shown.extend(self._check_root_causes(prefs))

        # 2. Prediction alerts
        if prefs["alert_types"].get("prediction", True):
            shown.extend(self._check_predictions(prefs))

        # 3. Recommendation alerts
        if prefs["alert_types"].get("recommendation", True):
            shown.extend(self._check_recommendations(prefs))

        # 4. Degradation score alerts
        if prefs["alert_types"].get("degradation", True):
            shown.extend(self._check_degradation(prefs))

        # 5. Periodic health summary
        if prefs["alert_types"].get("health_summary", False):
            shown.extend(self._check_health_summary(prefs))

        if shown:
            logger.info("Notifier: %d notification(s) sent.", len(shown))

        return shown

    # ── Category checkers ─────────────────────────────────────────────────────

    def _check_root_causes(self, prefs: Dict) -> List[Dict]:
        """Fire toast for each *new* root cause that passes filters."""
        results = []
        causes = self.db.get_root_causes(limit=10)

        for rc in causes:
            name = rc.get("name", "system")
            cause = rc.get("cause", "")
            severity = rc.get("severity", "LOW")

            # Skip Normal Operation, ignored processes
            if cause == "Normal Operation":
                continue
            if name.lower() in self._ignore:
                continue
            if not self._passes_severity(severity, prefs):
                continue

            key = f"root_cause:{name}:{cause}"
            if self._on_cooldown(key, prefs["cooldown_sec"]):
                continue

            title = f"Aging Detected — {cause}"
            pid = rc.get("pid")
            detail = rc.get("detail", cause)
            action = self._suggest_action_for_root_cause(cause, name, severity)
            body = (
                f"Process: {name}"
                f"{f' (PID {pid})' if pid else ''}: {detail}. "
                f"Action: {action}"
            )

            if self._fire(title, body, severity, "root_cause", name, key):
                results.append({"category": "root_cause", "target": name, "severity": severity})

        return results

    def _check_predictions(self, prefs: Dict) -> List[Dict]:
        """Fire toast when failure probability crosses warning thresholds."""
        results = []
        pred = self.db.get_latest_prediction()
        if not pred:
            return results

        prob = pred.get("failure_probability", 0)
        priority = pred.get("priority", "NORMAL")

        # Map probability ranges to notification tiers
        tiers = [
            (0.85, "CRITICAL", "CRITICAL failure risk"),
            (0.65, "HIGH",     "High failure risk"),
            (0.40, "MEDIUM",   "Moderate failure risk"),
            (0.15, "LOW",      "Low degradation detected"),
        ]

        for threshold, severity, label in tiers:
            if prob < threshold:
                continue
            if not self._passes_severity(severity, prefs):
                break

            key = f"prediction:{severity}"
            if self._on_cooldown(key, prefs["cooldown_sec"]):
                break

            title = f"System Failure Risk: {prob*100:.0f}%"
            body = f"{label}. Priority: {priority}. "
            crash_ts = pred.get("predicted_crash_time")
            if crash_ts:
                import datetime
                crash_str = datetime.datetime.fromtimestamp(crash_ts).strftime("%H:%M:%S")
                body += f"Estimated crash: {crash_str}."

            if self._fire(title, body, severity, "prediction", "system", key):
                results.append({"category": "prediction", "target": "system", "severity": severity})
            break  # Only show the highest matching tier

        return results

    def _check_recommendations(self, prefs: Dict) -> List[Dict]:
        """Fire toast for new high-priority recommendations."""
        results = []
        recs = self.db.get_recommendations(limit=5)

        for rec in recs:
            priority = rec.get("priority", "LOW")
            text = rec.get("recommendation", "")

            # Only notify for HIGH+ recommendations to avoid spam
            if SEVERITY_LEVELS.get(priority, 0) < SEVERITY_LEVELS.get("HIGH", 3):
                continue
            if not self._passes_severity(priority, prefs):
                continue

            key = f"recommendation:{text[:80]}"
            if self._on_cooldown(key, prefs["cooldown_sec"]):
                continue

            title = "Action Recommended"
            related = rec.get("related_cause")
            action_note = "Please review this action and apply it promptly."
            if related:
                action_note = f"Related cause: {related}. {action_note}"
            body = f"{text[:180]} {action_note}".strip()

            if self._fire(title, body, priority, "recommendation", "system", key):
                results.append({"category": "recommendation", "target": "system", "severity": priority})

        return results

    def _check_degradation(self, prefs: Dict) -> List[Dict]:
        """Fire toast when system degradation score exceeds threshold."""
        results = []

        # We need the latest prediction's data to compute degradation
        # Re-use the analyzer if available, or read from recent system trend
        latest = self.db.get_latest_system_metric()
        pred = self.db.get_latest_prediction()
        if not latest or not pred:
            return results

        # Approximate degradation from the prediction's lambda
        lam = pred.get("lambda_val", 0)
        # A high lambda means high degradation
        # Map lambda to a 0-1 score using threshold
        deg_score = min(lam / 0.01, 1.0) if lam > 0 else 0.0

        if deg_score < NOTIFY_DEGRADATION_THRESHOLD:
            return results

        severity = "HIGH" if deg_score > 0.6 else "MEDIUM"
        if not self._passes_severity(severity, prefs):
            return results

        key = f"degradation:{severity}"
        if self._on_cooldown(key, prefs["cooldown_sec"]):
            return results

        title = f"System Degradation: {deg_score*100:.0f}%"
        body = (
            f"CPU: {latest.get('cpu', 0):.1f}%  "
            f"RAM: {latest.get('ram', 0):.1f}%  "
            f"Disk: {latest.get('disk', 0):.1f}%  — "
            "Performance is declining."
        )

        if self._fire(title, body, severity, "degradation", "system", key):
            results.append({"category": "degradation", "target": "system", "severity": severity})

        return results

    def _check_health_summary(self, prefs: Dict) -> List[Dict]:
        """Periodic 'system is healthy' toast (like antivirus scan complete)."""
        results = []
        now = time.time()

        if now - self._last_health_toast < NOTIFY_HEALTH_INTERVAL:
            return results

        # Only show if no active root causes
        causes = self.db.get_root_causes(limit=5)
        has_issues = any(
            c.get("cause") != "Normal Operation" and c.get("name", "").lower() not in self._ignore
            for c in causes
        )

        if has_issues:
            return results

        key = "health_summary:periodic"
        if self._on_cooldown(key, NOTIFY_HEALTH_INTERVAL):
            return results

        latest = self.db.get_latest_system_metric() or {}
        title = "System Health: Normal"
        body = (
            f"CPU: {latest.get('cpu', 0):.1f}%  "
            f"RAM: {latest.get('ram', 0):.1f}%  "
            f"Disk: {latest.get('disk', 0):.1f}%  — "
            "No aging detected."
        )

        if self._fire(title, body, "LOW", "health_summary", "system", key):
            self._last_health_toast = now
            results.append({"category": "health_summary", "target": "system", "severity": "LOW"})

        return results

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _load_prefs(self) -> Dict:
        """
        Load user preferences from DB, falling back to config defaults.
        """
        db_prefs = self.db.get_notification_settings()
        if db_prefs:
            prefs = {
                "enabled":      bool(db_prefs.get("enabled", 1)),
                "cooldown_sec": db_prefs.get("cooldown_sec", NOTIFY_COOLDOWN_SEC),
                "min_severity": db_prefs.get("min_severity", NOTIFY_MIN_SEVERITY),
                "alert_types":  db_prefs.get("alert_types", NOTIFY_ALERT_TYPES),
            }
            logger.info("Loaded prefs from DB: %s", prefs)
            return prefs
        # Defaults from settings.py
        prefs = {
            "enabled":      NOTIFY_ENABLED,
            "cooldown_sec": NOTIFY_COOLDOWN_SEC,
            "min_severity": NOTIFY_MIN_SEVERITY,
            "alert_types":  dict(NOTIFY_ALERT_TYPES),
        }
        logger.info("Loaded prefs from config: %s", prefs)
        return prefs

    def _passes_severity(self, severity: str, prefs: Dict) -> bool:
        """Does this severity meet the user's minimum threshold?"""
        sev_val = SEVERITY_LEVELS.get(severity, 0)
        min_val = SEVERITY_LEVELS.get(prefs["min_severity"], 0)
        return sev_val >= min_val

    def _suggest_action_for_root_cause(self, cause: str, name: str, severity: str) -> str:
        """Build a short action recommendation for a root cause alert."""
        lower = cause.lower()
        if "memory" in lower:
            return f"Investigate {name} and restart it if memory use keeps rising."
        if "cpu" in lower or "processor" in lower or "load" in lower:
            return f"Check {name} for CPU runaway and consider restarting the process."
        if "disk" in lower or "i/o" in lower or "io" in lower:
            return f"Inspect disk activity for {name} and free or relocate files if needed."
        if "thread" in lower or "handle" in lower:
            return f"Review thread growth in {name} and terminate it if it is stuck."
        if severity == "CRITICAL":
            return f"Take immediate action on {name}: investigate and remediate now."
        if severity == "HIGH":
            return f"Review {name} soon and apply the suggested fix."
        return f"Investigate {name} and take corrective action."

    def _on_cooldown(self, key: str, cooldown_sec: int) -> bool:
        """Was a notification with this key sent recently?"""
        return self.db.notification_sent_recently(key, cooldown_sec)

    def _fire(
        self,
        title: str,
        body: str,
        severity: str,
        category: str,
        target: str,
        cooldown_key: str,
    ) -> bool:
        """
        Show the toast and log it.  Returns True if successfully shown.
        """
        shown = _show_toast(title, body, severity)

        # Always log, even if display failed (for audit trail)
        self.db.insert_notification({
            "timestamp":    time.time(),
            "category":     category,
            "severity":     severity,
            "target":       target,
            "title":        title,
            "body":         body,
            "cooldown_key": cooldown_key,
        })

        if shown:
            logger.info(
                "🔔 [%s] %s → %s: %s",
                severity, category, target, title,
            )
        return shown
