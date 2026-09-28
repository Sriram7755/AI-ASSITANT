import re
import time
import difflib
import numpy as np
from typing import Callable, Optional, Tuple
from app.audio.audio_manager import AudioManager
from app.audio.speech_recognizer import SpeechRecognizer
from app.config.settings import settings
from app.core.logging_config import logger

class WakeWordDetector:
    """Lightweight wake word detector abstraction for 'Hey Jarvis' with strict candidate validation."""

    def __init__(
        self,
        speech_recognizer: SpeechRecognizer,
        wake_phrase: Optional[str] = None,
        is_speaking_callback: Optional[Callable[[], bool]] = None
    ):
        self.speech_recognizer = speech_recognizer
        self.wake_phrase = (wake_phrase or settings.wake_word).lower()
        self.is_speaking_callback = is_speaking_callback
        self.audio_manager = AudioManager(silence_duration=0.8, energy_threshold=0.02)
        self.is_running = False

    @staticmethod
    def normalize_text(text: str) -> str:
        """Strip punctuation and extra whitespace from text."""
        cleaned = re.sub(r'[^\w\s]', '', text.lower())
        return " ".join(cleaned.split())

    def is_strict_wake_word_match(self, raw_text: str) -> bool:
        """
        Validates if raw_text contains a strict match for 'hey jarvis'.
        Rejects false candidates like 'hey that was', 'pray darwis', 'hey there', etc.
        """
        norm = self.normalize_text(raw_text)
        if not norm:
            return False

        # 1. Direct exact phrase match
        if "hey jarvis" in norm:
            return True

        # 2. Check word windows for close similarity (threshold >= 0.85)
        words = norm.split()
        if len(words) < 2:
            return False

        target = "hey jarvis"
        for i in range(len(words) - 1):
            window = f"{words[i]} {words[i+1]}"
            ratio = difflib.SequenceMatcher(None, window, target).ratio()
            if ratio >= 0.85:
                return True

        return False

    def extract_wake_command(self, audio_data: np.ndarray) -> Tuple[bool, str]:
        """
        Transcribe audio snippet and strictly check for wake word.
        If valid wake word is found, returns (True, extracted_command_text).
        If false candidate is found, logs candidate rejection and returns (False, "").
        """
        if audio_data is None or len(audio_data) == 0:
            return False, ""
        text = self.speech_recognizer.transcribe_audio_array(audio_data).strip()
        if not text:
            return False, ""

        if not self.is_strict_wake_word_match(text):
            logger.info(f"Wake-word candidate rejected: '{text}'")
            return False, ""

        # Extract remaining command text after stripping wake phrase
        clean_cmd = text
        for prefix in ("hey jarvis", "jarvis"):
            if clean_cmd.lower().startswith(prefix):
                clean_cmd = clean_cmd[len(prefix):].strip().lstrip(",").strip()
                break

        return True, clean_cmd

    def listen_loop(
        self,
        on_wake_word_detected: Callable[[str], None],
        stop_check: Optional[Callable[[], bool]] = None
    ):
        """Continuous background listening loop for wake word with post-speech cooldown."""
        self.is_running = True
        logger.info(f"Wake-word listener started. Waiting for '{self.wake_phrase}'...")

        # Calibrate background noise once on start
        try:
            self.audio_manager.calibrate_ambient_noise()
        except Exception as e:
            logger.debug(f"Ambient noise calibration skipped: {e}")

        while self.is_running:
            if stop_check and stop_check():
                break

            # Skip microphone capture if JARVIS is currently speaking to prevent self-listening
            if self.is_speaking_callback and self.is_speaking_callback():
                time.sleep(0.3)
                continue

            try:
                audio_snippet = self.audio_manager.capture_speech(max_duration=3)
                if audio_snippet is not None:
                    is_wake, extracted_cmd = self.extract_wake_command(audio_snippet)
                    if is_wake:
                        logger.info(f"Wake word detected: '{self.wake_phrase}', Extracted Command: '{extracted_cmd}'")
                        on_wake_word_detected(extracted_cmd)
                        time.sleep(0.8)
            except Exception as e:
                logger.error(f"Error in wake word listener loop: {e}")
                time.sleep(1)

            time.sleep(0.1)

    def stop(self):
        self.is_running = False
