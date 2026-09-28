import pytest
import numpy as np
from app.voice.wake_word import WakeWordDetector
from app.voice.stt import SpeechRecognizer
from app.voice.voice_pipeline import VoicePipeline
from app.voice.microphone import MicrophoneStreamer
from app.core.command_bus import CommandBus
from app.core.assistant import AssistantOrchestrator
from app.core.state import AssistantState

@pytest.fixture(autouse=True)
def mock_whisper_model(monkeypatch):
    """Prevent loading or downloading real WhisperModel during unit tests."""
    monkeypatch.setattr("app.voice.stt.WhisperModel", lambda *args, **kwargs: None)

def test_extract_wake_command(monkeypatch):
    rec = SpeechRecognizer()

    def mock_transcribe(audio_data, sample_rate=16000):
        return audio_data.get("text", "")

    monkeypatch.setattr(rec, "transcribe_audio_array", mock_transcribe)
    detector = WakeWordDetector(speech_recognizer=rec)

    # 1. Single-shot command
    is_wake, cmd, raw = detector.extract_wake_command({"text": "hey jarvis open chrome"})
    assert is_wake is True
    assert cmd == "open chrome"

    # 2. Two-step wake word only
    is_wake, cmd, raw = detector.extract_wake_command({"text": "Hey Jarvis"})
    assert is_wake is True
    assert cmd == ""

    # 3. Conversational greeting
    is_wake, cmd, raw = detector.extract_wake_command({"text": "hello"})
    assert is_wake is True
    assert cmd == "hello"

    # 4. Non-wake speech
    is_wake, cmd, raw = detector.extract_wake_command({"text": "hello world"})
    assert is_wake is False
    assert cmd == ""

def test_empty_transcript_ignored():
    orch = AssistantOrchestrator(text_mode=True)
    res = orch.handle_command("   ")
    assert res == ""

def test_voice_command_reaches_orchestrator(monkeypatch):
    orch = AssistantOrchestrator(text_mode=True)
    executed_tools = []

    def mock_execute(tool_name, args):
        executed_tools.append((tool_name, args))
        return True, "Done. Chrome is open."

    monkeypatch.setattr(orch.tool_executor, "execute", mock_execute)

    res = orch.handle_command("Hey Jarvis, open chrome")
    assert "Chrome is open" in res
    assert len(executed_tools) == 1
    assert executed_tools[0][0] == "open_application"
    assert executed_tools[0][1]["application"] == "chrome"

def test_canonical_pipeline_convergence(monkeypatch):
    bus = CommandBus()
    orch = AssistantOrchestrator(text_mode=True, command_bus=bus)
    received = []

    def mock_exec(tool_name, args):
        received.append((tool_name, args))
        return True, "Done. Task Manager is open."

    monkeypatch.setattr(orch.tool_executor, "execute", mock_exec)

    orch.handle_command("Open Task Manager")
    assert len(received) == 1
    assert received[0][0] == "open_application"
    assert received[0][1]["application"] == "task manager"

def test_voice_pipeline_active_command_mode():
    bus = CommandBus()
    rec = SpeechRecognizer()
    pipeline = VoicePipeline(command_bus=bus, speech_recognizer=rec)

    pipeline._update_state(AssistantState.LISTENING_FOR_COMMAND)

    received = []
    bus.register_handler(lambda cmd: received.append(cmd))

    pipeline._dispatch_command("Open Chrome")
    assert len(received) == 1
    assert received[0].source == "voice"
    assert received[0].text == "Open Chrome"

def test_audio_preprocessing():
    mic = MicrophoneStreamer(target_sample_rate=16000)
    raw = np.ones((44100,), dtype=np.float32) * 0.5
    cleaned = mic.preprocess_audio(raw, native_sr=44100)
    assert len(cleaned) == 16000
    assert abs(float(np.mean(cleaned))) < 1e-4

def test_tts_failure_does_not_crash_assistant(monkeypatch):
    orch = AssistantOrchestrator(text_mode=True)
    def mock_speak_fail(text, on_finish=None):
        if on_finish:
            on_finish()
    monkeypatch.setattr(orch.speech_manager, "speak", mock_speak_fail)

    res = orch.handle_command("hello")
    assert res != ""
