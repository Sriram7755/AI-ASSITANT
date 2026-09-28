import os
import subprocess
import winreg
import psutil
from typing import Dict, Optional, Tuple
from app.core.logging_config import logger

# Trusted predefined Windows system utilities
SYSTEM_UTILITIES: Dict[str, Dict[str, str]] = {
    "task manager": {"exe": "taskmgr.exe", "cmd": "start taskmgr", "display_name": "Task Manager"},
    "taskmgr": {"exe": "taskmgr.exe", "cmd": "start taskmgr", "display_name": "Task Manager"},
    "device manager": {"exe": "devmgmt.msc", "cmd": "start devmgmt.msc", "display_name": "Device Manager"},
    "devmgmt": {"exe": "devmgmt.msc", "cmd": "start devmgmt.msc", "display_name": "Device Manager"},
    "control panel": {"exe": "control.exe", "cmd": "start control", "display_name": "Control Panel"},
    "control": {"exe": "control.exe", "cmd": "start control", "display_name": "Control Panel"},
    "settings": {"exe": "ms-settings:", "cmd": "start ms-settings:", "display_name": "Settings"},
    "windows settings": {"exe": "ms-settings:", "cmd": "start ms-settings:", "display_name": "Settings"},
    "file explorer": {"exe": "explorer.exe", "cmd": "start explorer", "display_name": "File Explorer"},
    "explorer": {"exe": "explorer.exe", "cmd": "start explorer", "display_name": "File Explorer"},
    "command prompt": {"exe": "cmd.exe", "cmd": "start cmd", "display_name": "Command Prompt"},
    "cmd": {"exe": "cmd.exe", "cmd": "start cmd", "display_name": "Command Prompt"},
    "powershell": {"exe": "powershell.exe", "cmd": "start powershell", "display_name": "PowerShell"},
    "windows powershell": {"exe": "powershell.exe", "cmd": "start powershell", "display_name": "PowerShell"},
    "calculator": {"exe": "calc.exe", "cmd": "start calc", "display_name": "Calculator"},
}

# Mapping of common user application aliases including phonetic Whisper STT mishearings
KNOWN_APPS: Dict[str, Dict[str, str]] = {
    "chrome": {"exe": "chrome.exe", "cmd": "start chrome", "display_name": "Chrome"},
    "google chrome": {"exe": "chrome.exe", "cmd": "start chrome", "display_name": "Chrome"},
    "grow": {"exe": "chrome.exe", "cmd": "start chrome", "display_name": "Chrome"},
    "gro": {"exe": "chrome.exe", "cmd": "start chrome", "display_name": "Chrome"},
    "grom": {"exe": "chrome.exe", "cmd": "start chrome", "display_name": "Chrome"},
    "chrom": {"exe": "chrome.exe", "cmd": "start chrome", "display_name": "Chrome"},
    "vscode": {"exe": "Code.exe", "cmd": "code", "display_name": "VS Code"},
    "vs code": {"exe": "Code.exe", "cmd": "code", "display_name": "VS Code"},
    "visual studio code": {"exe": "Code.exe", "cmd": "code", "display_name": "VS Code"},
    "notepad": {"exe": "notepad.exe", "cmd": "start notepad", "display_name": "Notepad"},
    "terminal": {"exe": "wt.exe", "cmd": "start wt", "display_name": "Windows Terminal"},
    "spotify": {"exe": "spotify.exe", "cmd": "start spotify", "display_name": "Spotify"},
    "edge": {"exe": "msedge.exe", "cmd": "start msedge", "display_name": "Microsoft Edge"},
    "microsoft edge": {"exe": "msedge.exe", "cmd": "start msedge", "display_name": "Microsoft Edge"},
}

class ApplicationManager:
    """Manages system utility aliases and user desktop application detection/launching."""

    @classmethod
    def is_app_installed(cls, app_name: str) -> bool:
        app_key = app_name.strip().lower()
        if app_key in SYSTEM_UTILITIES:
            return True

        if app_key in KNOWN_APPS:
            exe_name = KNOWN_APPS[app_key]["exe"]
            if cls._find_app_path_in_registry(exe_name) or cls._find_in_path(exe_name):
                return True
            if exe_name in ("notepad.exe", "cmd.exe", "explorer.exe", "powershell.exe", "calc.exe", "chrome.exe"):
                return True

        return cls._find_in_path(f"{app_name}.exe") is not None

    @staticmethod
    def _find_in_path(exe_name: str) -> Optional[str]:
        path_env = os.environ.get("PATH", "").split(os.pathsep)
        for dir_path in path_env:
            full_p = os.path.join(dir_path, exe_name)
            if os.path.isfile(full_p):
                return full_p
        return None

    @staticmethod
    def _find_app_path_in_registry(exe_name: str) -> Optional[str]:
        registry_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"
        ]
        for root_key in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for reg_path in registry_paths:
                try:
                    with winreg.OpenKey(root_key, f"{reg_path}\\{exe_name}") as key:
                        val, _ = winreg.QueryValueEx(key, "")
                        if val and os.path.exists(val):
                            return val
                except OSError:
                    pass
        return None

    @classmethod
    def open_application(cls, application: str) -> Tuple[bool, str]:
        app_key = application.strip().lower()

        # 1. Windows System Utilities Allowlist
        if app_key in SYSTEM_UTILITIES:
            util_info = SYSTEM_UTILITIES[app_key]
            cmd = util_info["cmd"]
            display_name = util_info["display_name"]
            try:
                logger.info(f"Launching Windows system utility '{display_name}' via command: {cmd}")
                subprocess.Popen(cmd, shell=True)
                return True, f"Done. {display_name} is open."
            except Exception as e:
                err = f"Failed to launch system utility '{display_name}': {e}"
                logger.error(err)
                return False, err

        # 2. Ambiguous MongoDB Check
        if app_key in ("mongodb", "mongo", "mongodb compass"):
            compass_exe = (
                cls._find_app_path_in_registry("MongoDBCompass.exe")
                or cls._find_in_path("MongoDBCompass.exe")
                or cls._find_in_path("mongodb-compass.exe")
            )
            if compass_exe:
                try:
                    subprocess.Popen(f'"{compass_exe}"', shell=True)
                    return True, "Done. MongoDB Compass is open."
                except Exception as e:
                    return False, f"Failed to launch MongoDB Compass: {e}"
            else:
                msg = "MongoDB Compass doesn't appear to be installed on your laptop. Did you want to use MongoDB Atlas in your browser instead?"
                logger.info(msg)
                return False, msg

        # 3. Ambiguous MySQL Check
        if app_key in ("mysql", "mysql workbench", "mysql shell"):
            mysql_exe = (
                cls._find_app_path_in_registry("MySQLWorkbench.exe")
                or cls._find_in_path("MySQLWorkbench.exe")
                or cls._find_in_path("mysql.exe")
            )
            if mysql_exe:
                try:
                    subprocess.Popen(f'"{mysql_exe}"', shell=True)
                    return True, "Done. MySQL Workbench is open."
                except Exception as e:
                    return False, f"Failed to launch MySQL Workbench: {e}"
            else:
                msg = "MySQL Workbench doesn't appear to be installed on your laptop."
                logger.info(msg)
                return False, msg

        # 4. Standard User Applications
        cmd = None
        display_name = app_key.capitalize()

        if app_key in KNOWN_APPS:
            cmd = KNOWN_APPS[app_key]["cmd"]
            exe = KNOWN_APPS[app_key]["exe"]
            display_name = KNOWN_APPS[app_key].get("display_name", app_key.capitalize())
            reg_path = cls._find_app_path_in_registry(exe)
            if reg_path:
                cmd = f'"{reg_path}"'

        if not cmd:
            if cls.is_app_installed(app_key):
                cmd = f'start {app_key}'
            else:
                msg = f"I couldn't find '{application}' installed on your laptop."
                logger.warning(msg)
                return False, msg

        try:
            logger.info(f"Opening application '{application}' using command: {cmd}")
            subprocess.Popen(cmd, shell=True)
            return True, f"Done. {display_name} is open."
        except Exception as e:
            err = f"Failed to open '{application}': {e}"
            logger.error(err)
            return False, err

    @classmethod
    def close_application(cls, application: str) -> Tuple[bool, str]:
        app_key = application.strip().lower()

        target_exe = None
        if app_key in SYSTEM_UTILITIES:
            target_exe = SYSTEM_UTILITIES[app_key]["exe"].lower()
        elif app_key in KNOWN_APPS:
            target_exe = KNOWN_APPS[app_key]["exe"].lower()
        else:
            target_exe = f"{app_key}.exe".lower()

        closed = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == target_exe:
                    proc.terminate()
                    closed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        display_name = (
            SYSTEM_UTILITIES.get(app_key, {}).get("display_name")
            or KNOWN_APPS.get(app_key, {}).get("display_name")
            or application.capitalize()
        )

        if closed:
            return True, f"Closed {display_name}."
        return False, f"Could not find a running instance of {display_name}."
