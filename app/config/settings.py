import os
import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_dotenv_simple(env_path: Path):
    """Simple parser for .env files without external dependencies."""
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key, val)

load_dotenv_simple(BASE_DIR / ".env")

@dataclass
class Settings:
    # Ollama & Vision Settings
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:1.5b")
    vision_enabled: bool = os.getenv("VISION_ENABLED", "true").lower() == "true"
    vision_model: str = os.getenv("VISION_MODEL", "llava:latest")

    # Speech Recognition
    whisper_model: str = os.getenv("STT_MODEL", "small.en")
    whisper_device: str = os.getenv("STT_DEVICE", "cpu")
    whisper_compute_type: str = os.getenv("STT_COMPUTE_TYPE", "int8")

    stt_model: str = os.getenv("STT_MODEL", "small.en")
    stt_device: str = os.getenv("STT_DEVICE", "cpu")
    stt_compute_type: str = os.getenv("STT_COMPUTE_TYPE", "int8")
    stt_language: str = os.getenv("STT_LANGUAGE", "en")

    wake_word: str = os.getenv("WAKE_WORD", "hey jarvis").lower()
    microphone_device: Optional[int] = int(os.getenv("MICROPHONE_DEVICE")) if os.getenv("MICROPHONE_DEVICE") is not None else None

    # Session, Timing & Hotkey
    session_timeout_seconds: float = float(os.getenv("SESSION_TIMEOUT_SECONDS", "180.0"))
    global_hotkey: str = os.getenv("GLOBAL_HOTKEY", "ctrl+shift+f3")

    # Audio & TTS
    tts_voice: str = os.getenv("TTS_VOICE", "en-US-ChristopherNeural")
    tts_rate: str = os.getenv("TTS_RATE", "+0%")
    tts_volume: str = os.getenv("TTS_VOLUME", "+0%")

    # System & Security
    allowed_directories: List[str] = field(default_factory=lambda: [
        os.path.expanduser("~"),
        "C:\\Users",
        "D:\\"
    ])
    dangerous_tools: List[str] = field(default_factory=lambda: [
        "shutdown_computer",
        "restart_computer",
        "delete_file",
        "mass_file_move"
    ])
    startup_enabled: bool = False
    memory_enabled: bool = True

    # Directories
    data_dir: Path = BASE_DIR / os.getenv("DATA_DIR", "data")
    log_dir: Path = BASE_DIR / os.getenv("LOG_DIR", "logs")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def save_user_config(self):
        """Save runtime configuration to user_settings.json"""
        user_config_path = self.data_dir / "user_settings.json"
        data = {
            "llm_model": self.llm_model,
            "whisper_model": self.whisper_model,
            "stt_model": self.stt_model,
            "wake_word": self.wake_word,
            "session_timeout_seconds": self.session_timeout_seconds,
            "global_hotkey": self.global_hotkey,
            "tts_voice": self.tts_voice,
            "tts_rate": self.tts_rate,
            "tts_volume": self.tts_volume,
            "startup_enabled": self.startup_enabled,
            "memory_enabled": self.memory_enabled,
        }
        with open(user_config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_user_config(self):
        """Load runtime configuration overrides from user_settings.json"""
        user_config_path = self.data_dir / "user_settings.json"
        if user_config_path.exists():
            try:
                with open(user_config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if hasattr(self, k):
                            setattr(self, k, v)
            except Exception as e:
                print(f"Error loading user config: {e}")

settings = Settings()
settings.load_user_config()
