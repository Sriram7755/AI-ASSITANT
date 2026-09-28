import numpy as np
from typing import Optional
from app.core.config import config
from app.config.settings import settings
from app.core.logging_config import logger

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("faster-whisper is not installed. Speech recognition will be disabled.")

class SpeechRecognizer:
    """Faster-Whisper STT engine loaded ONCE on application startup with optimal CPU decoding parameters."""

    HALLUCINATIONS = {
        "thank you", "thanks for watching", "subtitles", "amara.org", "you", "so",
        "thank you for watching", "boom!", "boom", "film", "heads ends.", "heads ends",
        "3-0 dimension, all in.", "3-0 dimension", "all", "pray darwis", "hey that was",
        "hey it's out of us", "the end", "bye"
    }

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or getattr(config, "stt_model", settings.stt_model)
        self.model: Optional[WhisperModel] = None

        if WHISPER_AVAILABLE:
            try:
                device = getattr(config, "stt_device", settings.stt_device)
                compute_type = getattr(config, "stt_compute_type", settings.stt_compute_type)
                logger.info(f"Loading Faster-Whisper STT engine '{self.model_name}' on {device} ({compute_type})...")
                self.model = WhisperModel(
                    self.model_name,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=4
                )
                logger.info("Faster-Whisper STT engine loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Faster-Whisper model '{self.model_name}': {e}")

    def transcribe_audio_array(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        if not WHISPER_AVAILABLE or self.model is None:
            logger.warning("Whisper STT model is not initialized.")
            return ""

        if audio_data is None or len(audio_data) == 0:
            return ""

        try:
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=5,
                best_of=5,
                language=getattr(config, "stt_language", "en"),
                vad_filter=True,
                condition_on_previous_text=False,
                temperature=0.0
            )

            text_segments = [segment.text.strip() for segment in segments if segment.text.strip()]
            full_text = " ".join(text_segments).strip()

            # Hallucination filter for low-confidence Whisper artifacts
            if full_text.lower() in self.HALLUCINATIONS:
                logger.debug(f"Filtered Whisper hallucination: '{full_text}'")
                return ""

            return full_text
        except Exception as e:
            logger.error(f"STT transcription error: {e}")
            return ""
