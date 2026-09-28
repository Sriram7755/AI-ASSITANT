from typing import Optional
from app.core.logging_config import logger

class NotificationManager:
    """Desktop notification manager."""

    def __init__(self, tray_icon=None):
        self.tray_icon = tray_icon

    def show_notification(self, title: str, message: str, icon_type=None):
        logger.info(f"Notification: [{title}] {message}")
        if self.tray_icon and hasattr(self.tray_icon, "showMessage"):
            try:
                from PySide6.QtWidgets import QSystemTrayIcon
                q_icon = icon_type or QSystemTrayIcon.Information
                self.tray_icon.showMessage(title, message, q_icon, 4000)
            except Exception as e:
                logger.error(f"Failed to show tray notification: {e}")
        else:
            # Fallback Windows PowerShell balloon notification
            try:
                import subprocess
                ps_cmd = f"""
                [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
                $objNotify = New-Object System.Windows.Forms.NotifyIcon
                $objNotify.Icon = [System.Drawing.SystemIcons]::Information
                $objNotify.BalloonTipTitle = "{title}"
                $objNotify.BalloonTipText = "{message}"
                $objNotify.Visible = $True
                $objNotify.ShowBalloonTip(5000)
                """
                subprocess.Popen(["powershell", "-Command", ps_cmd])
            except Exception:
                pass
