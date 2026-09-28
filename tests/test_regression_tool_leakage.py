import os
import pytest
from app.ai.llm_client import LLMClient
from app.audio.tts_manager import TTSManager
from app.core.orchestrator import AssistantOrchestrator

def test_greeting_does_not_reuse_previous_tool():
    client = LLMClient()
    
    # 1. Process CPU request
    intent1 = client.process_user_input("What is my CPU usage?", conversation_context="")
    assert intent1["tool"] == "get_cpu_usage"

    # 2. Process greeting request with prior CPU conversation context
    prior_ctx = "User: What is my CPU usage?\nAssistant: Current CPU usage is 20%."
    intent2 = client.process_user_input("hello", conversation_context=prior_ctx)
    
    # Assert greeting does NOT reuse get_cpu_usage
    assert intent2["tool"] is None
    assert intent2["response"] != ""

def test_tool_call_is_not_reused_after_conversational_message():
    client = LLMClient()

    # Turn 1: open chrome
    i1 = client.process_user_input("open chrome", conversation_context="")
    assert i1["tool"] == "open_application"

    # Turn 2: hello
    ctx1 = "User: open chrome\nAssistant: Opened chrome."
    i2 = client.process_user_input("hello", conversation_context=ctx1)
    assert i2["tool"] is None

    # Turn 3: what is Java? (Must NOT reuse open_application from turn 1)
    ctx2 = ctx1 + "\nUser: hello\nAssistant: Hello! How can I help you today?"
    i3 = client.process_user_input("what is Java?", conversation_context=ctx2)
    assert i3["tool"] != "open_application"

    # Turn 4: open notepad
    i4 = client.process_user_input("open notepad", conversation_context=ctx2)
    assert i4["tool"] == "open_application"

    # Turn 5: hello
    ctx4 = ctx2 + "\nUser: open notepad\nAssistant: Opened notepad."
    i5 = client.process_user_input("hello", conversation_context=ctx4)
    assert i5["tool"] is None

def test_invalid_llm_response_does_not_reuse_previous_tool():
    client = LLMClient()

    # Simulate invalid raw text output from LLM
    parsed = client._extract_json("Invalid non-json output string")
    assert parsed is None

    # Test processing when extraction fails
    intent = client.process_user_input("Random question", conversation_context="User: get cpu usage\nAssistant: 20%")
    assert intent["tool"] is None

def test_multiple_independent_commands():
    client = LLMClient()

    cmd1 = client.process_user_input("What is my CPU usage?")
    assert cmd1["tool"] == "get_cpu_usage"

    cmd2 = client.process_user_input("How much RAM am I using?")
    assert cmd2["tool"] == "get_memory_usage"

    cmd3 = client.process_user_input("Take a screenshot")
    assert cmd3["tool"] == "take_screenshot"

def test_tts_lifecycle(monkeypatch, tmp_path):
    dummy_file = tmp_path / "test.mp3"
    dummy_file.write_text("audio")
    tts = TTSManager()
    monkeypatch.setattr(tts, "_synthesize", lambda text: str(dummy_file))
    
    mp3_path = tts._synthesize("Testing TTS lifecycle.")
    assert os.path.exists(mp3_path)
    assert tts._loop.is_running()
    tts.shutdown()
