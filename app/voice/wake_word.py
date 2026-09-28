import re
import time
import difflib
import numpy as np
from typing import Callable, Optional, Tuple
from app.voice.microphone import MicrophoneStreamer
from app.voice.stt import SpeechRecognizer
from app.config.settings import settings
from app.core.logging_config import logger

class WakeWordDetector:
    """Wake word detector supporting robust HP wake phrase matching ('Hey HP', 'Hi HP', 'Hello HP', 'HP') and STT variations."""

    WAKE_VARIANTS = [
        "hey hp",
        "hi hp",
        "hello hp",
        "ok hp",
        "okay hp",
        "hp",
        "hb",
        "age p",
        "h.p.",
        "h p",
        "hey jarvis",
        "jarvis"
    ]

    def __init__(
        self,
        speech_recognizer: SpeechRecognizer,
        wake_phrase: Optional[str] = None,
        is_speaking_callback: Optional[Callable[[], bool]] = None
    ):
        self.speech_recognizer = speech_recognizer
        self.wake_phrase = (wake_phrase or "hey hp").lower()
        self.is_speaking_callback = is_speaking_callback
        self.audio_manager = MicrophoneStreamer(silence_duration=0.8, energy_threshold=0.02)
        self.is_running = False

    @staticmethod
    def normalize_text(text: str) -> str:
        cleaned = re.sub(r'[^\w\s]', '', text.lower())
        return " ".join(cleaned.split())

    def match_wake_word(self, raw_text: str) -> Tuple[bool, str]:
        """Check if raw_text contains any wake word variant or standalone greeting and return (is_match, extracted_cmd)."""
        norm = self.normalize_text(raw_text)
        if not norm:
            return False, ""

        # Standalone conversational greetings ("hello", "hi", "hey")
        if norm in ("hello", "hi", "hey"):
            return True, norm

        matched_variant = None
        for variant in self.WAKE_VARIANTS:
            if variant in norm:
                matched_variant = variant
                break

        if not matched_variant:
            # Fuzzy match check for 2-word windows
            words = norm.split()
            target = "hey hp"
            for i in range(len(words) - 1):
                window = f"{words[i]} {words[i+1]}"
                ratio = difflib.SequenceMatcher(None, window, target).ratio()
                if ratio >= 0.80:
                    matched_variant = window
                    break

        if not matched_variant:
            return False, ""

        # Extract command by stripping wake phrase prefix
        clean_cmd = raw_text.strip()
        lower_raw = clean_cmd.lower()
        for variant in self.WAKE_VARIANTS:
            if lower_raw.startswith(variant):
                clean_cmd = clean_cmd[len(variant):].strip().lstrip(",").lstrip(".").strip()
                break

        return True, clean_cmd

    def extract_wake_command(self, audio_data: np.ndarray) -> Tuple[bool, str, str]:
        if audio_data is None or len(audio_data) == 0:
            return False, "", ""

        raw_transcript = self.speech_recognizer.transcribe_audio_array(audio_data).strip()
        if not raw_transcript:
            return False, "", ""

        is_wake, extracted_cmd = self.match_wake_word(raw_transcript)
        return is_wake, extracted_cmd, raw_transcript

    def stop(self):
        self.is_running = False
