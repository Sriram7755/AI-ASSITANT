import pytest
from app.tools.permissions import PermissionManager

def test_permission_manager_approved():
    confirmed_calls = []
    
    def callback(prompt: str) -> bool:
        confirmed_calls.append(prompt)
        return True

    pm = PermissionManager(confirmation_callback=callback)
    assert pm.is_tool_dangerous("shutdown_computer") is True

    allowed = pm.request_permission("shutdown_computer", {})
    assert allowed is True
    assert len(confirmed_calls) == 1

def test_permission_manager_rejected():
    def callback(prompt: str) -> bool:
        return False

    pm = PermissionManager(confirmation_callback=callback)
    allowed = pm.request_permission("restart_computer", {})
    assert allowed is False
