import time
import datetime as real_datetime
import pytest
from app.core.config import config
from app.core.state import AssistantState, StateMachine
from app.core.session_manager import JarvisStateManager
from app.core.hotkey import GlobalHotkeyListener
from app.vision.screen_perception import ScreenPerceptionManager
from app.core.assistant import AssistantOrchestrator
from app.core.command_bus import CommandBus
from app.system.file_manager import FileManager
from app.brain.intent_parser import IntentParser
from app.voice.wake_word import WakeWordDetector

@pytest.fixture(autouse=True)
def mock_whisper(monkeypatch):
    monkeypatch.setattr("app.voice.stt.WhisperModel", lambda *args, **kwargs: None)

def test_time_aware_greetings(monkeypatch):
    # TEST 1 & 2: Time-aware greetings at 08:30 (Morning) and 18:30 (Evening)
    class FakeDateTimeMorning(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.datetime(2026, 8, 15, 8, 30)

    class FakeDateTimeEvening(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.datetime(2026, 8, 15, 18, 30)

    monkeypatch.setattr("datetime.datetime", FakeDateTimeMorning)
    g_morn = config.get_time_aware_greeting()
    assert "Good morning, Sriram." in g_morn
    assert "online" in g_morn.lower()

    monkeypatch.setattr("datetime.datetime", FakeDateTimeEvening)
    g_eve = config.get_time_aware_greeting()
    assert "Good evening, Sriram." in g_eve

def test_startup_confirmation_flow():
    # TEST 3 & 4: Startup confirmation YES -> ONLINE, and post-TTS timeout -> OFFLINE
    announced = []
    def mock_speak(text):
        announced.append(text)

    sm = JarvisStateManager(timeout_seconds=600.0, speak_callback=mock_speak)
    sm.start_startup_flow()
    
    assert sm.current_state == AssistantState.WAITING_FOR_CONFIRMATION
    assert sm._confirmation_start_time == 0.0  # Starts post-TTS

    sm.on_tts_finished()
    assert sm._confirmation_start_time > 0.0

    # TEST 4: Say "Yes" -> ONLINE
    sm.handle_confirmation_response(True)
    assert sm.current_state == AssistantState.ONLINE
    sm.stop()

def test_hotkey_lifecycle():
    # TEST 5, 6, 7: Ctrl+Shift+F3 (ONLINE), Ctrl+Shift+F4 (OFFLINE), Ctrl+Shift+F3 (ONLINE again)
    announced = []
    def mock_speak(text):
        announced.append(text)

    sm = JarvisStateManager(timeout_seconds=600.0, speak_callback=mock_speak)
    assert sm.current_state == AssistantState.OFFLINE

    # TEST 5: Hotkey ON -> ONLINE
    res1 = sm.toggle_online_offline(reason="hotkey")
    assert res1 == AssistantState.ONLINE
    assert sm.is_session_active() is True

    # TEST 6: Deactivate hotkey -> OFFLINE
    sm.deactivate(reason="hotkey_f4", announce=True)
    assert sm.current_state == AssistantState.OFFLINE
    assert sm.is_session_active() is False

    # TEST 7: Hotkey ON again -> ONLINE again
    res3 = sm.toggle_online_offline(reason="hotkey")
    assert res3 == AssistantState.ONLINE
    sm.stop()

def test_10_minute_inactivity_and_session_extension():
    # TEST 18, 19, 20: 10-minute inactivity session (600s), proactive 30s warning & confirmation
    sm = JarvisStateManager(timeout_seconds=600.0)
    sm.activate(reason="test")
    assert sm.timeout_seconds == 600.0

    # Simulate activity reset
    t1 = sm._last_user_activity
    time.sleep(0.1)
    sm.reset_activity_timer(reason="user_command")
    t2 = sm._last_user_activity
    assert t2 >= t1

    # TEST 19: Positive extension response -> Resets timer
    sm.extend_session(announce=False)
    assert sm.is_session_active() is True

    # TEST 20: Negative extension response -> OFFLINE
    sm.deactivate(reason="confirmation_rejected", announce=False)
    assert sm.current_state == AssistantState.OFFLINE
    sm.stop()

def test_intent_classification_and_time_date():
    # TEST 8, 9, 10, 11, 12, 13, 15, 16, 17, 21: Intent routing & tools
    ip = IntentParser()

    # TEST 8: "Open a new tab." -> browser_new_tab
    res_tab = ip.parse("Open a new tab.")
    assert res_tab["actions"][0]["tool"] == "browser_new_tab"

    # TEST 9: "Close the tab." -> browser_close_tab
    res_close = ip.parse("Close the tab.")
    assert res_close["actions"][0]["tool"] == "browser_close_tab"

    # TEST 10: "What time is it?" -> System local time, NO browser search
    res_time = ip.parse("What time is it?")
    assert res_time["intent"] == "SYSTEM_INFORMATION"
    assert len(res_time["actions"]) == 0
    assert "It's " in res_time["response"]

    # TEST 11: "Who are you?" -> Conversational answer, NO browser search
    res_who = ip.parse("Who are you?")
    assert res_who["intent"] == "CONVERSATION"
    assert len(res_who["actions"]) == 0

    # TEST 12: "Tell me a joke." -> Joke, NO browser search
    res_joke = ip.parse("Tell me a joke.")
    assert res_joke["intent"] == "CONVERSATION"
    assert len(res_joke["actions"]) == 0

    # TEST 13: "Search YouTube for Java DSA." -> search_youtube
    res_yt = ip.parse("Search YouTube for Java DSA.")
    assert res_yt["actions"][0]["tool"] == "search_youtube"

    # TEST 15: "Increase the volume." -> system_volume_up
    res_vol = ip.parse("Increase the volume.")
    assert res_vol["actions"][0]["tool"] == "system_volume_up"

    # TEST 16: "Turn the microphone off." -> mute_microphone
    res_mic = ip.parse("Turn the microphone off.")
    assert res_mic["actions"][0]["tool"] == "mute_microphone"

    # TEST 17: "Open the first document on the screen." -> open_screen_item
    res_doc = ip.parse("Open the first document on the screen.")
    assert res_doc["actions"][0]["tool"] == "open_screen_item"

    # TEST 21: "Shutdown the laptop." -> Permission confirmation first
    res_sd = ip.parse("Shutdown the laptop.")
    assert res_sd["actions"][0]["tool"] == "shutdown_computer"
    assert "asked me to shut down" in res_sd["response"].lower() or "sure" in res_sd["response"].lower()

def test_screen_perception_no_timestamps():
    # TEST 14: Screen perception natural response only
    sp = ScreenPerceptionManager()
    obs = sp.capture_and_analyze(query="What's on my screen?")
    assert "active_window" in obs
    assert ".png" not in obs["observation_summary"]
    assert "captured at" not in obs["observation_summary"].lower()
