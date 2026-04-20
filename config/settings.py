"""
config/settings.py
------------------
Central configuration for the Software Aging Analyzer.
Adjust all thresholds and parameters here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "aging.db")

# ── Data collection ───────────────────────────────────────────────────────────
SAMPLING_INTERVAL   = 1           # seconds between each psutil snapshot
ANALYSIS_EVERY_N    = 5           # run analysis after every N samples (~5 sec)
TREND_WINDOW        = 10          # number of recent samples used for regression

# ── Slope / trend thresholds ─────────────────────────────────────────────────
# Demo‑friendly thresholds (low values make aging visible quickly).
# In production, these can be raised for ``extreme only`` detection.
MEMORY_SLOPE_THRESHOLD = 0.01     # % per sample → memory leak
CPU_SLOPE_THRESHOLD    = 0.10     # % per sample → CPU runaway
THREAD_SLOPE_THRESHOLD = 0.01     # threads per sample → thread leak
DISK_SLOPE_THRESHOLD   = 0.12     # % per sample → disk bottleneck (extreme only)
NET_SLOPE_THRESHOLD    = 200_000  # bytes per sample → network bottleneck (extreme only)
RSQUARED_THRESHOLD     = 0.50     # minimum R² accuracy (0-1) for a trend to be considered valid

# ── Reliability / prediction ──────────────────────────────────────────────────
FAILURE_THRESHOLD      = 0.75     # P(failure) level that triggers alert
RESTART_SAFETY_MARGIN  = 0.15     # restart this fraction before predicted crash
MIN_LAMBDA             = 1e-6     # minimum failure rate to avoid div-by-zero

# ── Flask dashboard ───────────────────────────────────────────────────────────
FLASK_HOST  = os.environ.get("HOST", "0.0.0.0")
FLASK_PORT  = int(os.environ.get("PORT", 5000))
FLASK_DEBUG = False

# ── Severity mapping ──────────────────────────────────────────────────────────
SEVERITY_LEVELS = {
    "CRITICAL": 4,
    "HIGH":     3,
    "MEDIUM":   2,
    "LOW":      1,
}

# ── AI API Configuration ──────────────────────────────────────────────────────
# Provide an API key here to unlock true natural language understanding
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ── Auto-remediation policy (rule-based, no AI required) ─────────────────────
AUTO_POLICY_ENABLED = True
# prompt | auto
AUTO_POLICY_MODE = "auto"  # Automatically apply fixes for low issues
# Minimum severity that can trigger actions
AUTO_SEVERITY_MIN = "LOW"
# Failure probability threshold (0-1) for emergency action
AUTO_PROB_THRESHOLD = 0.75
# Allowed actions for automatic policy (exclude manual ones like restart)
AUTO_ALLOWED_ACTIONS = [
    "limit_cpu",
    "set_affinity",
    "lower_priority",
    "suspend",
    "resume",
    "kill",
    # "restart",  # Manual only - will notify instead
]
# Avoid spamming identical actions
AUTO_DEDUP_WINDOW_SEC = 600
# Max proposals per analysis cycle
AUTO_MAX_PROPOSALS = 3

# ── Ignore list for root-cause and recommendations ─────────────────────────-
# Process names (case-insensitive) that should never be flagged.
IGNORE_PROCESS_NAMES = [
    "system",
    "system idle process",
    "svchost.exe",
    "antigravity.exe",
    "cmd.exe",
    "conhost.exe",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "searchhost.exe",
    "searchprotocolhost.exe",
    "msmpeng.exe",
    "whatsapp.root.exe",
    "widgetservice.exe",
    "language_server_windows_x64.exe",
    "explorer.exe",
    "winword.exe",
    "excel.exe",
    "powerpnt.exe",
    "notepad.exe",
    "code.exe",
]

# ── Notification settings (antivirus-style background alerts) ─────────────────
NOTIFY_ENABLED          = False       # Master switch — turn OFF to silence all alerts
NOTIFY_COOLDOWN_SEC     = 600         # Minimum seconds between same alert (10 min)
NOTIFY_MIN_SEVERITY     = "HIGH"      # Only notify for HIGH+ issues (auto-handles LOW/MEDIUM)
NOTIFY_ALERT_TYPES      = {           # Toggle individual alert categories
    "root_cause":       True,         # ⚠️  Only HIGH+ root causes
    "prediction":       True,         # 🔴  Only HIGH+ failure risks
    "recommendation":   True,         # 💡  Manual actions needed
    "degradation":      True,         # 📈  Only HIGH degradation
    "health_summary":   False,        # ✅  Disabled to reduce noise
}
NOTIFY_HEALTH_INTERVAL  = 1800        # Seconds between health-summary toasts (30 min)
NOTIFY_DEGRADATION_THRESHOLD = 0.35   # Degradation score (0-1) that triggers a toast
