import pytest
from app.config.settings import Settings

def test_settings_initialization(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", log_dir=tmp_path / "logs")
    assert settings.ollama_host == "http://localhost:11434"
    assert settings.llm_model == "qwen2.5:1.5b"
    assert settings.whisper_model in ("tiny.en", "small.en")
    assert settings.wake_word == "hey jarvis"
    assert (tmp_path / "data").exists()

def test_user_config_save_load(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", log_dir=tmp_path / "logs")
    settings.wake_word = "hello assistant"
    settings.save_user_config()

    settings_new = Settings(data_dir=tmp_path / "data", log_dir=tmp_path / "logs")
    settings_new.load_user_config()
    assert settings_new.wake_word == "hello assistant"
