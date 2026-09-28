import pytest
from app.system.system_manager import SystemManager
from app.system.app_manager import ApplicationManager

def test_system_manager_metrics():
    cpu_msg = SystemManager.get_cpu_usage()
    assert "CPU usage" in cpu_msg

    ram_msg = SystemManager.get_memory_usage()
    assert "RAM usage" in ram_msg

    sys_info = SystemManager.get_system_information()
    assert "Windows Laptop" in sys_info

def test_application_manager_detection():
    # Notepad is standard on Windows
    installed = ApplicationManager.is_app_installed("notepad")
    assert installed is True

def test_system_utility_aliases():
    utilities = [
        "task manager",
        "device manager",
        "control panel",
        "settings",
        "file explorer",
        "cmd",
        "powershell",
        "calculator"
    ]
    for util in utilities:
        assert ApplicationManager.is_app_installed(util) is True

def test_mongodb_ambiguous_app_check():
    success, msg = ApplicationManager.open_application("mongodb")
    # If MongoDB Compass is not installed on test runner, it provides clear prompt asking if user meant Atlas
    if not success:
        assert "MongoDB Compass doesn't appear to be installed" in msg
        assert "MongoDB Atlas" in msg
