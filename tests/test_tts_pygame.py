import os
import time
import pytest
from app.audio.tts_manager import TTSManager

def test_tts_manager_initialization():
    tts = TTSManager()
    assert tts._loop is not None
    assert tts._loop.is_running() is True
    assert tts.is_speaking() is False
    tts.shutdown()

def test_tts_manager_pygame_playback(monkeypatch):
    tts = TTSManager()
    
    # Mock synthesis to return a dummy file path
    dummy_path = "test_dummy_audio.mp3"
    with open(dummy_path, "wb") as f:
        f.write(b"ID3\x03\x00\x00\x00\x00\x00\x00")

    def mock_synthesize(text: str):
        return dummy_path

    played_files = []
    def mock_play(mp3_path: str):
        played_files.append(mp3_path)

    monkeypatch.setattr(tts, "_synthesize", mock_synthesize)
    monkeypatch.setattr(tts, "_play_audio_pygame", mock_play)

    finished = []
    tts.speak("Hello test", on_finish=lambda: finished.append(True))

    # Wait for background thread worker
    for _ in range(20):
        if finished:
            break
        time.sleep(0.1)

    assert len(finished) == 1
    assert len(played_files) == 1
    assert played_files[0] == dummy_path

    tts.shutdown()
