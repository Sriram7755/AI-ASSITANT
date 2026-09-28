import os
import tempfile
import numpy as np
import scipy.io.wavfile as wav
from typing import Optional
from app.config.settings import settings
from app.core.logging_config import logger

class SpeechRecognizer:
    """Faster-Whisper STT engine optimized for CPU execution."""

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        self.model_name = model_name or settings.whisper_model
        self.device = device or settings.whisper_device
        self.compute_type = settings.whisper_compute_type
        self._model = None

    def _ensure_model_loaded(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Loading Faster-Whisper model '{self.model_name}' on {self.device} ({self.compute_type})...")
                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type
                )
                logger.info("Faster-Whisper STT model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Faster-Whisper model: {e}")
                raise e

    def transcribe_audio_array(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe raw floating point or int16 numpy audio array with noise filtering."""
        if audio_data is None or len(audio_data) < sample_rate * 0.4:
            # Ignore recordings under 0.4s
            return ""

        self._ensure_model_loaded()
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            # Convert float32 to int16 if needed
            if audio_data.dtype != np.int16:
                audio_int16 = (audio_data * 32767).astype(np.int16)
            else:
                audio_int16 = audio_data

            wav.write(tmp_path, sample_rate, audio_int16)

            # Transcribe with tuned decoding options for English CPU accuracy
            segments, info = self._model.transcribe(
                tmp_path,
                beam_size=5,
                language="en",
                vad_filter=True,
                condition_on_previous_text=False
            )

            text_parts = [segment.text.strip() for segment in segments if segment.text]
            result_text = " ".join(text_parts).strip()

            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            # Filter out common Whisper hallucination artifacts on short noise
            hallucinations = {"thank you", "thanks for watching", "subtitles by", "amara.org", "so", "you"}
            if result_text.lower() in hallucinations:
                logger.debug(f"Filtered out Whisper noise artifact: '{result_text}'")
                return ""

            if result_text:
                logger.info(f"Speech Transcribed: '{result_text}' (Prob: {info.language_probability:.2f})")
            return result_text
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""
