# Installation & Setup Guide

Quick start for getting Software Aging Analyzer running on your system.

## Prerequisites

- **Python 3.8+** (tested on Python 3.11)
- **pip** (Python package manager)
- **Windows 10+, macOS 10.15+, or Linux (any modern distro)**

## Step 1: Extract & Install

```bash
# Extract the project folder
cd softwareaginganalyser

# Install core dependencies
pip install -r requirements.txt

# (Optional) Install system tray support
pip install pystray pillow

# (Optional) Install packaging tools
pip install pyinstaller
```

## Step 2: Launch the Application

### Quick Launch (Recommended)
```bash
python softaging_launcher.py
```
✓ Starts all background services  
✓ Opens dashboard in your default browser  
✓ Dashboard available at **http://127.0.0.1:5000**  
✓ Press Ctrl+C to stop

### Background Mode (No Browser)
```bash
python softaging_launcher.py --daemon
```
✓ Monitoring runs silently in background  
✓ Dashboard accessible at **http://127.0.0.1:5000** (open manually)  
✓ Stop with: `python softaging_launcher.py --stop`

### Demo Mode (With Stress Generators)
```bash
python softaging_launcher.py --demo
```
✓ All services start + stress generators run  
✓ Simulate memory leaks, CPU runaways, thread leaks  
✓ See aging detection in real-time on dashboard  
✓ Perfect for demos and testing

## Step 3: Access the Dashboard

Open your browser to: **http://127.0.0.1:5000**

You should see:
- **System Overview** — CPU, RAM, disk, network gauges
- **Processes** — Per-application metrics
- **Root Cause** — Detected aging causes
- **Predictions** — Failure probability estimates
- **Recommendations** — Maintenance suggestions

## Step 4: Optional Configuration

Edit `config/settings.py` to customize:

```python
# Faster detection (demo mode)
MEMORY_SLOPE_THRESHOLD = 0.01
CPU_SLOPE_THRESHOLD = 0.10

# Slower detection (production mode)
MEMORY_SLOPE_THRESHOLD = 0.15
CPU_SLOPE_THRESHOLD = 0.35

# Collection frequency
SAMPLING_INTERVAL = 1  # seconds
```

## Windows Auto-Start (Optional)

Register the application to start automatically on boot:

```bash
python softaging_launcher.py --install-startup
```

Unregister:
```bash
python softaging_launcher.py --uninstall-startup
```

## Building a Standalone Executable (Optional)

Convert to a Windows .exe file:

```bash
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller softaging_launcher.spec

# Result: dist/SoftAgingAnalyzer/SoftAgingAnalyzer.exe
```

Users can then run the .exe directly without Python installed.

## Troubleshooting

### Port Already in Use
```bash
# Windows: Find and kill process on port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Or change port in config/settings.py:
FLASK_PORT = 5001
```

### Dashboard Not Loading
```bash
# Check Flask is running
curl http://127.0.0.1:5000

# If error, check logs
cat agent.log
cat server.log
```

### High CPU Usage
Increase sampling interval in `config/settings.py`:
```python
SAMPLING_INTERVAL = 5  # instead of 1
```

## What to Look For

Once running, the dashboard should show:

1. **System metrics updating** in real-time (green/yellow/red gauges)
2. **Process list** with memory/CPU trends
3. **Health status** (Healthy / Warning / Critical)

If everything shows "—" (no data), wait 30 seconds for initial collection.

## Next Steps

- **Read**: [README.md](README.md) — Full feature documentation
- **Configure**: [config/settings.py](config/settings.py) — Customize detection thresholds
- **Deploy**: [DESKTOP_DEPLOYMENT.md](DESKTOP_DEPLOYMENT.md) — Packaging & distribution
- **Understand**: [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) — System architecture deep-dive

## Need Help?

Check the documentation:
- Q: "Aging not detected" → See DESIGN_SYSTEM.md (thresholds section)
- Q: "Want to add custom metric" → See DESIGN_SYSTEM.md (collector extension)
- Q: "Need to deploy to servers" → See DESKTOP_DEPLOYMENT.md (headless mode)
- Q: "Want to build .exe" → See this file (Building section)

---

**Version**: 1.0  
**Last Updated**: March 5, 2026
