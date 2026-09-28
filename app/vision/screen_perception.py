import os
import time
import ctypes
from pathlib import Path
from typing import Optional, Dict, Any
from app.core.config import config, DATA_DIR
from app.core.logging_config import logger

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class ScreenPerceptionManager:
    """On-demand screen perception manager for Windows screen capture and active window inspection."""

    def __init__(self, capture_dir: Optional[Path] = None):
        self.capture_dir = capture_dir or (DATA_DIR / "screenshots")
        self.capture_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_active_window_title() -> str:
        """Get the title of the currently focused foreground window on Windows."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return "Unknown Window"
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return "Untitled Window"
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except Exception as e:
            logger.debug(f"Error reading foreground window title: {e}")
            return "Windows Desktop"

    def capture_screen(self, filename_prefix: str = "screen_cap") -> Optional[Path]:
        """Capture the current primary screen on demand."""
        if not PIL_AVAILABLE:
            logger.warning("PIL ImageGrab is unavailable. Screenshot capture skipped.")
            return None

        try:
            timestamp = int(time.time())
            save_path = self.capture_dir / f"{filename_prefix}_{timestamp}.png"
            img = ImageGrab.grab()
            img.save(save_path, "PNG")
            logger.info(f"[VISION] Screen captured successfully: '{save_path.name}'")
            return save_path
        except Exception as e:
            logger.error(f"Failed to capture screen: {e}")
            return None

    def capture_and_analyze(self, query: str = "Analyze screen") -> Dict[str, Any]:
        """On-demand screen capture & structured visual observation package."""
        active_window = self.get_active_window_title()
        img_path = self.capture_screen()

        observation = {
            "query": query,
            "active_window": active_window,
            "screenshot_path": str(img_path) if img_path else None,
            "screenshot_available": img_path is not None,
            "screen_understood": False,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "observation_summary": f"Active window: '{active_window}'. Screenshot captured on demand at {time.strftime('%H:%M:%S')}."
        }

        logger.info(f"[VISION] Visual Observation Generated: Window='{active_window}', Screenshot={img_path is not None}")
        return observation
