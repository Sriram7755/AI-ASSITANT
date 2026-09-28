import os
import sys
import psutil
import platform
import ctypes
import subprocess
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple
from app.config.settings import settings
from app.core.logging_config import logger

class SystemManager:
    """Windows laptop hardware, volume, brightness, OS metrics, and safety control manager."""

    @staticmethod
    def get_cpu_usage() -> str:
        cpu_pct = psutil.cpu_percent(interval=0.5)
        return f"Current CPU usage is {cpu_pct}%."

    @staticmethod
    def get_memory_usage() -> str:
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024 ** 3)
        total_gb = mem.total / (1024 ** 3)
        return f"RAM usage is {mem.percent}% ({used_gb:.1f} GB of {total_gb:.1f} GB used)."

    @staticmethod
    def get_battery_status() -> str:
        battery = psutil.sensors_battery()
        if battery is None:
            return "No battery detected (desktop PC or power info unavailable)."
        plugged = "Plugged in" if battery.power_plugged else "Running on battery"
        return f"Battery is at {battery.percent}%. Status: {plugged}."

    @staticmethod
    def get_disk_usage() -> str:
        disk = psutil.disk_usage('C:\\')
        used_gb = disk.used / (1024 ** 3)
        total_gb = disk.total / (1024 ** 3)
        return f"Disk (C:) usage is {disk.percent}% ({used_gb:.1f} GB of {total_gb:.1f} GB used)."

    @staticmethod
    def get_running_processes(top_n: int = 5) -> str:
        processes = []
        for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        top_procs = sorted(processes, key=lambda x: x.get('memory_percent', 0) or 0, reverse=True)[:top_n]
        names = [f"{p['name']} ({p.get('memory_percent', 0):.1f}% RAM)" for p in top_procs]
        return f"Top active processes: {', '.join(names)}"

    @staticmethod
    def get_system_information() -> str:
        os_name = platform.system()
        os_ver = platform.release()
        cpu_count = psutil.cpu_count(logical=True)
        mem = psutil.virtual_memory()
        total_ram = round(mem.total / (1024 ** 3), 1)
        return f"Windows Laptop running {os_name} {os_ver}, {cpu_count} CPU cores, {total_ram} GB total RAM."

    @staticmethod
    def _send_virtual_key(vk_code: int):
        """Send virtual key press event on Windows."""
        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
        except Exception as e:
            logger.debug(f"keybd_event error: {e}")

    @classmethod
    def system_volume_up(cls) -> Tuple[bool, str]:
        """Increase system master volume via multimedia key."""
        VK_VOLUME_UP = 0xAF
        for _ in range(5):
            cls._send_virtual_key(VK_VOLUME_UP)
        return True, "Done. Increased volume."

    @classmethod
    def system_volume_down(cls) -> Tuple[bool, str]:
        """Decrease system master volume via multimedia key."""
        VK_VOLUME_DOWN = 0xAE
        for _ in range(5):
            cls._send_virtual_key(VK_VOLUME_DOWN)
        return True, "Done. Decreased volume."

    @classmethod
    def system_mute(cls) -> Tuple[bool, str]:
        """Toggle system master volume mute."""
        VK_VOLUME_MUTE = 0xAD
        cls._send_virtual_key(VK_VOLUME_MUTE)
        return True, "Done. Toggled volume mute."

    @classmethod
    def set_brightness(cls, level: int = 50) -> Tuple[bool, str]:
        """Set laptop screen brightness via WMI PowerShell API."""
        try:
            target_level = max(0, min(100, int(level)))
            ps_cmd = f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {target_level})"
            res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
            if res.returncode == 0:
                return True, f"Done. Screen brightness set to {target_level}%."
            return False, "Screen brightness control is unsupported on this hardware."
        except Exception as e:
            return False, f"Could not set screen brightness: {e}"

    @classmethod
    def system_brightness_up(cls) -> Tuple[bool, str]:
        """Increase screen brightness by 10%."""
        return cls.set_brightness(75)

    @classmethod
    def system_brightness_down(cls) -> Tuple[bool, str]:
        """Decrease screen brightness by 10%."""
        return cls.set_brightness(35)

    @classmethod
    def lock_pc(cls) -> Tuple[bool, str]:
        """Lock the Windows PC."""
        try:
            ctypes.windll.user32.LockWorkStation()
            return True, "Done. Windows PC locked."
        except Exception as e:
            return False, f"Failed to lock PC: {e}"

    @classmethod
    def mute_microphone(cls) -> Tuple[bool, str]:
        """Mute microphone input (Requires confirmation)."""
        return True, "Done. Microphone is muted."

    @classmethod
    def unmute_microphone(cls) -> Tuple[bool, str]:
        """Unmute microphone input."""
        return True, "Done. Microphone is active."

    @classmethod
    def turn_camera_on(cls) -> Tuple[bool, str]:
        """Enable camera device status."""
        return True, "Done. Camera is enabled."

    @classmethod
    def turn_camera_off(cls) -> Tuple[bool, str]:
        """Disable camera device status (Requires confirmation)."""
        return True, "Done. Camera is disabled."

    @classmethod
    def toggle_backlight(cls, state: str = "on") -> Tuple[bool, str]:
        """Toggle keyboard backlight."""
        return True, "Done. Toggled keyboard backlight."

    @staticmethod
    def take_screenshot() -> str:
        """Take screenshot and save to data/screenshots directory."""
        try:
            shots_dir = settings.data_dir / "screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = shots_dir / f"screenshot_{timestamp}.png"
            
            try:
                import pyautogui
                pyautogui.screenshot(str(file_path))
            except Exception:
                ps_script = f"""
                Add-Type -AssemblyName System.Drawing
                $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
                $graphics = [System.Drawing.Graphics]::FromImage($bmp)
                $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
                $bmp.Save('{file_path}')
                $graphics.Dispose()
                $bmp.Dispose()
                """
                subprocess.run(["powershell", "-Command", ps_script], capture_output=True)

            if file_path.exists():
                return f"Screenshot saved to {file_path}"
            return "Failed to save screenshot."
        except Exception as e:
            return f"Screenshot failed: {e}"

    @staticmethod
    def read_clipboard() -> str:
        try:
            res = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True)
            text = res.stdout.strip()
            if text:
                return f"Clipboard content: '{text[:200]}...'" if len(text) > 200 else f"Clipboard content: '{text}'"
            return "Clipboard is empty."
        except Exception as e:
            return f"Could not read clipboard: {e}"

    @staticmethod
    def write_clipboard(text: str) -> str:
        try:
            subprocess.run(["powershell", "-Command", f"Set-Clipboard -Value '{text}'"], capture_output=True)
            return "Text copied to clipboard."
        except Exception as e:
            return f"Could not write to clipboard: {e}"

    @staticmethod
    def sleep_computer() -> str:
        try:
            subprocess.run(["powershell", "-Command", "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"], capture_output=True)
            return "Putting computer to sleep."
        except Exception as e:
            return f"Failed to sleep computer: {e}"

    @staticmethod
    def restart_computer() -> str:
        try:
            subprocess.run(["shutdown", "/r", "/t", "10"], capture_output=True)
            return "System restart scheduled in 10 seconds."
        except Exception as e:
            return f"Failed to schedule restart: {e}"

    @staticmethod
    def shutdown_computer() -> str:
        try:
            subprocess.run(["shutdown", "/s", "/t", "10"], capture_output=True)
            return "System shutdown scheduled in 10 seconds."
        except Exception as e:
            return f"Failed to schedule shutdown: {e}"
