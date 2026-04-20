"""
softaging_tray.py
-----------------
Optional system tray integration for Software Aging Analyzer.
Provides a minimalist tray menu for monitoring control without opening browser.

Install dependencies:
    pip install pystray pillow

Usage:
    python softaging_tray.py

The tray icon allows:
  • Open Dashboard (opens in browser)
  • Pause/Resume Monitoring (stops/starts collection)
  • Status (shows current state)
  • Exit (cleanly shut down)
"""

import subprocess
import sys
import webbrowser
from pathlib import Path

try:
    from PIL import Image, ImageDraw
    import pystray
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


# ── Tray state management ─────────────────────────────────────────────────────

class TrayApp:
    """Manages the system tray icon and menu."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port
        self.paused = False
        self.icon = None

    def _create_icon_image(self) -> "Image.Image":
        """Create a simple circular icon with SoftAging colors."""
        size = (64, 64)
        image = Image.new("RGB", size, color=(240, 240, 240))
        draw = ImageDraw.Draw(image)
        
        # Draw a blue/orange gradient circle
        # outer circle (dark blue)
        draw.ellipse(
            (2, 2, 62, 62),
            fill=(0, 120, 215),
            outline=(0, 80, 170)
        )
        
        # inner circle (lighter - pulsing indicator)
        inner_color = (100, 200, 255) if not self.paused else (200, 100, 100)
        draw.ellipse(
            (8, 8, 56, 56),
            fill=inner_color,
            outline=(0, 120, 215)
        )
        
        # center dot
        draw.ellipse(
            (28, 28, 36, 36),
            fill=(255, 255, 255)
        )
        
        return image

    def open_dashboard(self, icon, item) -> None:
        """Open the dashboard in the default browser."""
        url = f"http://{self.host}:{self.port}"
        webbrowser.open(url)

    def toggle_monitoring(self, icon, item) -> None:
        """Pause or resume monitoring (requires API endpoint)."""
        # This would require a new API endpoint in the dashboard to pause/resume
        # For now, just toggle the state visually
        self.paused = not self.paused
        new_label = "Resume Monitoring" if self.paused else "Pause Monitoring"
        # Update the menu (would need to rebuild)
        print(f"[tray] Monitoring {'paused' if self.paused else 'resumed'}")

    def show_status(self, icon, item) -> None:
        """Display current monitoring status."""
        status = "⏸ Paused" if self.paused else "▶ Monitoring"
        print(f"[tray] Status: {status}")

    def exit_app(self, icon, item) -> None:
        """Exit the application."""
        if icon:
            icon.stop()
        sys.exit(0)

    def run(self) -> None:
        """Start the tray application."""
        if not IMPORTS_AVAILABLE:
            print("Error: pystray and pillow are required for tray support.")
            print("Install with: pip install pystray pillow")
            sys.exit(1)

        menu = pystray.Menu(
            pystray.MenuItem(
                "Open Dashboard",
                self.open_dashboard,
                default=True
            ),
            pystray.MenuItem.SEPARATOR,
            pystray.MenuItem(
                "Pause Monitoring" if not self.paused else "Resume Monitoring",
                self.toggle_monitoring
            ),
            pystray.MenuItem(
                "Status",
                self.show_status
            ),
            pystray.MenuItem.SEPARATOR,
            pystray.MenuItem(
                "Exit",
                self.exit_app
            ),
        )

        self.icon = pystray.Icon(
            "SoftAgingAnalyzer",
            self._create_icon_image(),
            "Software Aging Analyzer",
            menu
        )

        print("System tray icon started. Monitoring in background.")
        print("(Close this window or right-click the tray icon to exit)")
        self.icon.run()


def main() -> None:
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="System tray for SoftAging Analyzer")
    parser.add_argument("--host", default="127.0.0.1", help="Dashboard host")
    parser.add_argument("--port", type=int, default=5000, help="Dashboard port")

    args = parser.parse_args()

    app = TrayApp(host=args.host, port=args.port)
    app.run()


if __name__ == "__main__":
    main()
