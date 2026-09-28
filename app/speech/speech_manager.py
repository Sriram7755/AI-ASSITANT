from typing import Optional, Callable
from app.speech.tts import TextToSpeech
from app.speech.audio_player import AudioPlayer
from app.core.logging_config import logger

class SpeechManager:
    """Manages Edge-TTS voice generation and PyGame native audio playback lifecycle."""

    def __init__(self):
        self.tts = TextToSpeech()
        self.player = AudioPlayer()

    def is_speaking(self) -> bool:
        return self.player.is_playing()

    def stop(self):
        self.player.stop()

    def speak(self, text: str, on_finish: Optional[Callable[[], None]] = None):
        if not text or not text.strip():
            if on_finish:
                on_finish()
            return

        mp3_file = self.tts.generate_speech_file(text)
        if mp3_file:
            self.player.play_file(mp3_file, on_finish=on_finish)
        else:
            logger.warning(f"Could not synthesize speech for: '{text}'")
            if on_finish:
                on_finish()

    def shutdown(self):
        self.player.stop()
        self.tts.shutdown()
