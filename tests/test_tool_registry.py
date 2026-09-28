import pytest
from app.tools.registry import ToolRegistry, ToolSpec
from app.tools.permissions import PermissionManager
from app.tools.executor import ToolExecutor

def test_tool_registry_and_executor():
    registry = ToolRegistry()
    
    def dummy_app(application: str):
        return True, f"Opened {application}"

    registry.register(
        name="open_app",
        description="Open application",
        parameters={
            "type": "object",
            "properties": {"application": {"type": "string"}},
            "required": ["application"]
        },
        handler=dummy_app
    )

    assert registry.is_registered("open_app")
    
    # Test valid execution
    perm = PermissionManager()
    executor = ToolExecutor(perm)
    
    # We patch tool_registry inside executor test by using tool_registry instance
    from app.tools.registry import tool_registry
    tool_registry.register(
        name="open_app",
        description="Open application",
        parameters={
            "type": "object",
            "properties": {"application": {"type": "string"}},
            "required": ["application"]
        },
        handler=dummy_app
    )

    ok, msg = executor.execute("open_app", {"application": "notepad"})
    assert ok is True
    assert "Opened notepad" in msg

def test_invalid_tool_call():
    perm = PermissionManager()
    executor = ToolExecutor(perm)
    ok, msg = executor.execute("non_existent_tool", {})
    assert ok is False
    assert "Unknown tool" in msg
