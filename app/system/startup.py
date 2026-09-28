import sys
import os
import winreg
from app.core.logging_config import logger

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "PersonalAIAssistant"

class StartupManager:
    """Manages Windows auto-start via CurrentUser registry key."""

    @staticmethod
    def is_startup_enabled() -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except OSError:
            return False

    @staticmethod
    def set_startup(enable: bool) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    # Executable path (python run.py or compiled executable)
                    python_exe = sys.executable
                    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "run.py"))
                    cmd = f'"{python_exe}" "{script_path}" --no-gui'
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                    logger.info("Windows autostart enabled in registry.")
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                        logger.info("Windows autostart disabled in registry.")
                    except OSError:
                        pass
            return True
        except Exception as e:
            logger.error(f"Failed to update Windows autostart registry: {e}")
            return False
