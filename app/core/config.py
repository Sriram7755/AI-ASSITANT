import os
import random
import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
AUDIO_DIR = DATA_DIR / "audio"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class Config:
    """HP Central Configuration & System Settings."""
    app_name: str = "HP"
    version: str = "2.0.0"
    owner_name: str = "Sriram"
    
    # LLM & Vision Settings
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:1.5b")
    vision_enabled: bool = os.getenv("VISION_ENABLED", "true").lower() == "true"
    vision_model: str = os.getenv("VISION_MODEL", "llava:latest")
    screen_capture_on_demand: bool = os.getenv("SCREEN_CAPTURE_ON_DEMAND", "true").lower() == "true"
    
    # Voice & Speech Settings
    wake_word: str = os.getenv("WAKE_WORD", "Hey HP")
    stt_model: str = os.getenv("STT_MODEL", "small.en")
    stt_device: str = os.getenv("STT_DEVICE", "cpu")
    stt_compute_type: str = os.getenv("STT_COMPUTE_TYPE", "int8")
    stt_language: str = os.getenv("STT_LANGUAGE", "en")
    tts_voice: str = os.getenv("TTS_VOICE", "en-US-ChristopherNeural")
    
    # Session, Timing & Hotkey Settings
    session_timeout_seconds: float = float(os.getenv("SESSION_TIMEOUT_SECONDS", "600.0"))  # 10 minutes (600s)
    global_hotkey: str = os.getenv("GLOBAL_HOTKEY", "ctrl+shift+f3")
    deactivate_hotkey: str = os.getenv("DEACTIVATE_HOTKEY", "ctrl+shift+f4")
    conversation_timeout: float = 600.0
    post_speech_cooldown: float = 0.8  # seconds cooldown after TTS
    
    # Audio Capture & Hardware Settings
    microphone_device: Optional[int] = int(os.getenv("MICROPHONE_DEVICE")) if os.getenv("MICROPHONE_DEVICE") is not None else None
    sample_rate: int = 16000
    voice_debug: bool = False
    
    # VAD & Capture Parameters
    pre_roll_ms: int = 300
    silence_timeout_ms: int = 1200
    min_speech_ms: int = 500
    max_command_duration_ms: int = 15000
    
    # Paths
    db_path: Path = DATA_DIR / "memory.db"
    logs_dir: Path = LOGS_DIR
    startup_sound_path: Path = AUDIO_DIR / "startup.wav"

    def get_time_aware_greeting(self) -> str:
        """Generates dynamic time-aware greetings with varied phrasing."""
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            pool = [
                f"Good morning, {self.owner_name}. New day, new moves. Should I stay online?",
                f"Good morning, {self.owner_name}. Ready to make some progress today? Want me online?",
                f"Good morning, {self.owner_name}. Let's get things moving. Should I stay online?"
            ]
        elif 12 <= hour < 17:
            pool = [
                f"Good afternoon, {self.owner_name}. I'm up and ready. Should I stay online?",
                f"Good afternoon, {self.owner_name}. Let's get something productive done. Want me online?",
                f"Good afternoon, {self.owner_name}. Hope your day is going great. Should I stay online?"
            ]
        elif 17 <= hour < 22:
            pool = [
                f"Good evening, {self.owner_name}. Back at it? Want me online?",
                f"Good evening, {self.owner_name}. Ready to get things done? Should I stay online?",
                f"Good evening, {self.owner_name}. Let me know if you need assistance tonight. Should I stay online?"
            ]
        else:
            pool = [
                f"Hey {self.owner_name}, still working? I'm ready if you are. Should I stay online?",
                f"Late night session, {self.owner_name}? Let's make it count. Want me online?",
                f"Good night, {self.owner_name}. Need an AI co-pilot tonight? Should I stay online?"
            ]
        return random.choice(pool)

    def get_random_expiry_question(self) -> str:
        """Generates natural phrasing variations for 10-minute session expiry warning."""
        pool = [
            "Are we done for now, or would you like me to stay with you?",
            "We're coming up on the end of our session. Want me to stay online?",
            "Ten minutes is almost up. Should I keep going?",
            "We're nearly at the session limit. Continue or go offline?"
        ]
        return random.choice(pool)

    def get_random_hotkey_activation(self) -> str:
        """Generates natural phrasing variations for hotkey activation (Ctrl+Shift+F3)."""
        pool = [
            f"Alright {self.owner_name}, I'm online. What are we working on?",
            f"I'm online, {self.owner_name}. What can I do for you?",
            f"Ready when you are, {self.owner_name}. What's next?"
        ]
        return random.choice(pool)

    def get_random_shutdown_farewell(self) -> str:
        """Generates natural phrasing variations for application shutdown/exit."""
        pool = [
            f"Alright {self.owner_name}, I'm signing off. Keep going — you've got this.",
            "Going offline for now. See you next time.",
            f"That's me done for now. Have a good one, {self.owner_name}."
        ]
        return random.choice(pool)

    def get_current_local_time(self) -> str:
        now = datetime.datetime.now()
        return now.strftime("%I:%M %p").lstrip("0")

    def get_current_local_date(self) -> str:
        now = datetime.datetime.now()
        return now.strftime("%A, %B %d, %Y")

config = Config()
