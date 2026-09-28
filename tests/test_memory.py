import pytest
from app.memory.memory_manager import MemoryManager
from app.memory.conversation import ConversationManager

def test_memory_manager_crud(tmp_path):
    db_file = tmp_path / "test_memory.db"
    mem = MemoryManager(db_path=db_file)

    # 1. Remember
    assert mem.remember("preferred_editor", "VS Code", category="preferences") is True

    # 2. Retrieve
    res = mem.retrieve_memory("editor")
    assert len(res) == 1
    assert res[0]["value"] == "VS Code"

    # 3. Forget
    assert mem.forget_memory("preferred_editor") is True
    assert len(mem.retrieve_memory("editor")) == 0

def test_conversation_manager():
    conv = ConversationManager(max_history=2)
    conv.add_user_message("Hello")
    conv.add_assistant_message("Hi")
    conv.add_user_message("Open Chrome")
    conv.add_assistant_message("Chrome open")

    ctx = conv.get_context_formatted()
    assert "Open Chrome" in ctx
    assert len(conv.get_history()) == 4
