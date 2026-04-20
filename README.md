# Software Aging Analyzer & Early Warning System

A **lightweight, rule-based software aging detection system** that operates as a hybrid desktop + web monitoring application.

Continuously monitors OS-level metrics (CPU, RAM, disk, network, thread count) to detect degrading performance in long-running applications before failures occur.

## Key Features

✅ **Real-Time Detection** — Identifies memory leaks, CPU runaways, and thread leaks in <15 seconds  
✅ **Hybrid Architecture** — Monitoring continues in background even if browser is closed  
✅ **Explainable AI** — Rule-based detection with clear root cause attribution (no black-box ML)  
✅ **Low Overhead** — <1% CPU, ~20 MB memory, minimal disk I/O  
✅ **Windows Integration** — Optional system tray + auto-start support  
✅ **Production-Ready** — Desktop executable, PyInstaller packaging, extensive configuration options  

## Quick Start

### Windows Users
```bash
# Download and extract SoftAgingAnalyzer.zip
# Double-click SoftAgingAnalyzer.exe
# Dashboard opens automatically at http://127.0.0.1:5000
# Monitoring continues even after closing browser
```

### Python Users (Development)
```bash
# Navigate to project directory
cd softwareaginganalyser

# Install dependencies
pip install -r requirements.txt

# Launch with dashboard (opens browser)
python softaging_launcher.py

# Or background mode (no browser)
python softaging_launcher.py --daemon

# Demo mode (with stress generators for testing)
python softaging_launcher.py --demo

# Stop running instance
python softaging_launcher.py --stop
```

## System Architecture

The application runs as an integrated system of background processes:

```
┌─────────────────────────────────────────────────────────┐
│         Software Aging Analyzer (Hybrid Desktop)        │
├───────────────────┬──────────────────┬────────────────┤
│ Monitor Agent     │ Flask Dashboard  │ Notifier       │
│ (continuous)      │ (API + Web UI)   │ (alerts)       │
├───────────────────┴──────────────────┴────────────────┤
│  Local SQLite Database (metrics storage)               │
├────────────────────────────────────────────────────────┤
│  Optional: System Tray Controller, Auto-Start, etc.    │
└────────────────────────────────────────────────────────┘
```

### Core Components

| Component | Purpose | File |
|-----------|---------|------|
| **Monitor Agent** | Collects system/process metrics via psutil | `monitor_agent.py` |
| **Dashboard Server** | Exposes metrics via Flask REST API | `dashboard_server.py` |
| **Analyzer Engine** | Detects aging via trend analysis + thresholds | `core/analyzer.py` |
| **Predictor** | Estimates failure probability over time | `core/predictor.py` |
| **Root Cause** | Maps metrics to failure causes | `core/root_cause.py` |
| **Launcher** | Manages all services + auto-start | `softaging_launcher.py` |
| **Web Dashboard** | Browser-based visualization | `dashboard/` |
| **Notifier** | Optional desktop alerts | `notifier_service.py` |

## Detection Algorithm: Three-Gate Trend Analysis

For each monitored metric (RAM, CPU, threads, etc.):

1. **Slope Condition** — Recent trend must show sustained growth  
2. **Monotonicity** — ≥80% of recent samples are increasing  
3. **Baseline Deviation** — Current average significantly exceeds baseline  

**All three must be true simultaneously** to trigger an alert.  
This design suppresses transient workload spikes while catching genuine aging.

### Example: Memory Leak

```
Baseline (healthy):        RAM ≈ 30%
After 5 minutes:           RAM = 35% (small deviation, not alarming)
After 10 minutes:          RAM = 45% (slope increasing, but recent)
After 15 minutes:          RAM = 65% (strong slope + monotonic + dev >15%)
                           ▶ ALERT: Memory Leak Detected
                           ▶ Process: python.exe (allocated array)
                           ▶ Recommendation: Restart process
```

## Configuration

All settings are in `config/settings.py`:

```python
# Data Collection
SAMPLING_INTERVAL   = 1           # seconds between metrics snapshots
TREND_WINDOW        = 10          # samples used for trend analysis

# Demo‐Friendly Thresholds (detect aging in 15-30 seconds)
MEMORY_SLOPE_THRESHOLD = 0.01     # % per sample
CPU_SLOPE_THRESHOLD    = 0.10     # % per sample
THREAD_SLOPE_THRESHOLD = 0.01     # threads per sample

# Production Thresholds (only extreme aging)
# MEMORY_SLOPE_THRESHOLD = 0.15
# CPU_SLOPE_THRESHOLD    = 0.35
# THREAD_SLOPE_THRESHOLD = 0.06

# Dashboard
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000

# Auto-Remediation (optional)
AUTO_POLICY_ENABLED = True
AUTO_POLICY_MODE    = "auto"  # or "prompt"
```

## Dashboard Views

Access the dashboard at **http://127.0.0.1:5000**:

### System Overview
- CPU, RAM, disk, network gauges
- System health status (Healthy / Warning / Critical)
- Real-time metric trends

### Processes
- Per-application resource usage
- Memory growth slopes
- Thread count trends
- Sortable by risk

### Root Cause Analysis
- Detected aging causes with timestamps
- Dominant failure type (memory leak, CPU runaway, etc.)
- Per-process attribution
- Severity levels (CRITICAL / HIGH / MEDIUM / LOW)

### Predictions
- Failure probability over next 60 minutes
- Estimated time until system intervention needed
- Recommended restart time window

### Recommendations
- Actionable maintenance suggestions
- Auto-generated or manual approval based on policy
- Process-specific actions (targeted restart, CPU limiting)

## Demo Scenarios

See [DESKTOP_DEPLOYMENT.md](DESKTOP_DEPLOYMENT.md#demo-scenarios) for full demo instructions.

### Quick Demo (1 minute)
```bash
# Terminal 1
python softaging_launcher.py

# Terminal 2 (wait 5 seconds for dashboard to start)
python stress_scenarios.py --all

# →→→ Within 15 seconds, see memory/CPU/thread growth detected
```

## Performance & Resource Usage

| Metric | Value |
|--------|-------|
| **CPU Overhead** | 0.3–0.8% (typically <1%) |
| **Memory (Agent)** | 18–25 MB |
| **Memory (Dashboard)** | 40–60 MB |
| **Startup Time** | 5–10 seconds |
| **Database Growth** | 4–5 MB/hour |

---

## Advanced Usage

### Windows Auto-Start
```bash
# Register to autostart on boot (runs in background)
python softaging_launcher.py --install-startup

# Unregister from auto-start
python softaging_launcher.py --uninstall-startup
```

### System Tray (Optional)
```bash
# Install tray dependencies
pip install pystray pillow

# Run tray controller
python softaging_tray.py
```

### Building Standalone Executable
```bash
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller softaging_launcher.spec

# Output: dist/SoftAgingAnalyzer/SoftAgingAnalyzer.exe
```

### Headless/Server Mode
```bash
# Run in background without opening browser
python softaging_launcher.py --daemon

# Dashboard still accessible at http://127.0.0.1:5000
# Stop with: python softaging_launcher.py --stop
```

---

## Documentation

- **[DESKTOP_DEPLOYMENT.md](DESKTOP_DEPLOYMENT.md)** — Detailed deployment, packaging, and configuration guide
- **[DESIGN_SYSTEM.md](DESIGN_SYSTEM.md)** — System architecture and component deep-dives
- **[QUICK_REFERENCE.js](QUICK_REFERENCE.js)** — API endpoints and JavaScript utilities
- **[config/settings.py](config/settings.py)** — All configuration parameters with comments

---

## Project Structure

```
softwareaginganalyser/
├── softaging_launcher.py          ← Main entry point (desktop app)
├── softaging_tray.py              ← Optional system tray integration
├── softaging_launcher.spec        ← PyInstaller build spec
│
├── monitor_agent.py               ← Background metrics collector
├── dashboard_server.py            ← Flask API + dashboard
├── notifier_service.py            ← Alert notifications
│
├── core/
│   ├── collector.py               ← psutil metrics collection
│   ├── analyzer.py                ← Trend analysis engine
│   ├── root_cause.py              ← Cause classification
│   ├── predictor.py               ← Failure probability estimator
│   ├── prevention.py              ← Recommendation generation
│   └── action_policy.py           ← Auto-remediation policies
│
├── dashboard/
│   ├── app.py                     ← Flask routes & API
│   ├── templates/
│   │   ├── index.html             ← System overview
│   │   ├── processes.html         ← Per-process view
│   │   ├── root_cause.html        ← Root cause analysis
│   │   ├── predictions.html       ← Failure predictions
│   │   └── ...
│   └── static/
│       ├── css/style.css          ← Dashboard styling
│       └── js/                    ← Charts, animations
│
├── database/
│   ├── db_manager.py              ← SQLite abstraction
│   └── schema.sql                 ← Database schema
│
├── config/
│   └── settings.py                ← All configuration
│
├── models/
│   └── reliability_model.py       ← Failure probability math
│
├── requirements.txt               ← Python dependencies
├── DESKTOP_DEPLOYMENT.md          ← THIS FILE
├── DESIGN_SYSTEM.md               ← Architecture deep-dive
└── README.md                       ← You are here
```

---

## Installing Dependencies

```bash
# Core requirements
pip install -r requirements.txt

# Optional: System tray support  
pip install pystray pillow

# Optional: PyInstaller packaging
pip install pyinstaller
```

---

## Key Research References

The system is grounded in academic research on software rejuvenation:

- **Huang et al. (1995)** — Foundational work on software rejuvenation
- **Carnevali et al. (2025)** — Mixed inspection-based rejuvenation policies  
- **Grottke et al. (2008)** — Taxonomy of aging-related faults
- **Bao et al. (2005)** — Workload-adaptive rejuvenation
- **Matias Jr. & Maciel (2006)** — Experimental validation on J2EE servers

See paper references in [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) for full citations.

---

## Troubleshooting

### Port 5000 Already in Use
```bash
# Kill process (Windows)
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Or change port in config/settings.py
FLASK_PORT = 5001
```

### Dashboard Not Loading
```bash
# Check if services are running
curl http://127.0.0.1:5000/api/system-metrics

# Check logs
tail agent.log
tail server.log
```

### High CPU Usage
Reduce collection frequency in `config/settings.py`:
```python
SAMPLING_INTERVAL = 5   # instead of 1
ANALYSIS_EVERY_N = 10   # instead of 5
```

---

## Contributing & Development

To extend the system:

1. **Add a new metric**: Edit `core/collector.py` → `dashboard/templates/`
2. **Change detection thresholds**: `config/settings.py`
3. **Add a new root cause**: `core/root_cause.py` → decision rules
4. **Custom recommendations**: `core/prevention.py` → generation logic

All modules are designed for easy integration and extension.

---

## License

Educational & Research Use  
(See LICENSE file for details)

---

## Contact & Support

**Authors**: B. Lakshmi Nivasan, K. Ajay  
**Guided by**: R. Subaja  
**Institution**: Prince Shri Venkateshwara Padmavathy Engineering College, Chennai

For questions or issues, refer to:
- [DESKTOP_DEPLOYMENT.md](DESKTOP_DEPLOYMENT.md) — Deployment guide
- [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) — Architecture reference
- [config/settings.py](config/settings.py) — Configuration documentation

---

**Version**: 1.0  
**Released**: March 5, 2026  
**Status**: Stable (Demo & Production Ready)
