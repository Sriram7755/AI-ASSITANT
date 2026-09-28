import sys
import pytest
from PySide6.QtWidgets import QApplication
from app.voice.wake_word import WakeWordDetector
from app.voice.stt import SpeechRecognizer
from app.voice.microphone import MicrophoneStreamer
from app.gui.chat_widgets import JarvisAvatarWidget, WaveformVisualizer

@pytest.fixture(autouse=True)
def mock_whisper_model(monkeypatch):
    """Prevent loading real WhisperModel during unit tests."""
    monkeypatch.setattr("app.voice.stt.WhisperModel", lambda *args, **kwargs: None)

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

def test_strict_wake_word_acceptance(monkeypatch):
    rec = SpeechRecognizer()

    def mock_transcribe(audio_data, sample_rate=16000):
        return audio_data.get("text", "")

    monkeypatch.setattr(rec, "transcribe_audio_array", mock_transcribe)
    detector = WakeWordDetector(speech_recognizer=rec)

    is_wake, cmd, _ = detector.extract_wake_command({"text": "hey jarvis"})
    assert is_wake is True
    assert cmd == ""

    is_wake, cmd, _ = detector.extract_wake_command({"text": "Hey, Jarvis!"})
    assert is_wake is True

    is_wake, cmd, _ = detector.extract_wake_command({"text": "hey jarvis open chrome"})
    assert is_wake is True
    assert cmd == "open chrome"

def test_strict_wake_word_rejection(monkeypatch):
    rec = SpeechRecognizer()

    def mock_transcribe(audio_data, sample_rate=16000):
        return audio_data.get("text", "")

    monkeypatch.setattr(rec, "transcribe_audio_array", mock_transcribe)
    detector = WakeWordDetector(speech_recognizer=rec)

    rejected_phrases = [
        "hey that was",
        "hey it's out of us",
        "pray darwis",
        "hey there",
        "hey guys",
        "something else"
    ]

    for phrase in rejected_phrases:
        is_wake, cmd, _ = detector.extract_wake_command({"text": phrase})
        assert is_wake is False, f"Phrase '{phrase}' should have been rejected."

def test_ambient_noise_calibration(monkeypatch):
    mgr = MicrophoneStreamer()
    
    import numpy as np
    dummy_rec = np.array([0.002, -0.002, 0.003, -0.001], dtype="float32")
    
    import sounddevice as sd
    monkeypatch.setattr(sd, "rec", lambda frames, samplerate, channels, dtype, device=None: dummy_rec)
    monkeypatch.setattr(sd, "wait", lambda: None)

    mgr.calibrate_ambient_noise(duration=0.1)
    assert mgr.energy_threshold >= 0.012

def test_gui_widget_timer_teardown(qapp):
    avatar = JarvisAvatarWidget()
    avatar.set_state("LISTENING")
    avatar.close()
    avatar.deleteLater()

    waveform = WaveformVisualizer()
    waveform.start_animation()
    waveform.stop_animation()
    waveform.close()
    waveform.deleteLater()
    qapp.processEvents()
