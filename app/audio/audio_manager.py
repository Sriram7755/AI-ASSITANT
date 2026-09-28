import time
import queue
import numpy as np
import sounddevice as sd
from typing import Optional, Callable
from app.core.logging_config import logger

class AudioManager:
    """Microphone audio streamer with dynamic VAD ambient noise calibration."""

    def __init__(self, sample_rate: int = 16000, silence_duration: float = 1.2, energy_threshold: float = 0.02):
        self.sample_rate = sample_rate
        self.silence_duration = silence_duration
        self.energy_threshold = energy_threshold
        self.audio_queue = queue.Queue()
        self.is_recording = False

    def calibrate_ambient_noise(self, duration: float = 1.0):
        """Measure background microphone RMS noise level and dynamically set energy threshold."""
        try:
            logger.info("Calibrating ambient microphone noise...")
            recording = sd.rec(int(self.sample_rate * duration), samplerate=self.sample_rate, channels=1, dtype="float32")
            sd.wait()
            rms_noise = float(np.sqrt(np.mean(recording ** 2)))
            calculated_threshold = max(0.015, min(0.08, rms_noise * 2.5))
            self.energy_threshold = round(calculated_threshold, 4)
            logger.info(f"Microphone calibrated. Ambient noise RMS: {rms_noise:.4f}, Energy Threshold set to: {self.energy_threshold}")
        except Exception as e:
            logger.debug(f"Ambient noise calibration fallback: {e}")

    def capture_speech(self, max_duration: int = 10, status_callback: Optional[Callable[[str], None]] = None) -> Optional[np.ndarray]:
        """
        Record audio from default microphone until user stops speaking (silence detected).
        Returns float32 numpy audio array or None if silent / error.
        """
        if status_callback:
            status_callback("LISTENING")

        logger.debug("Microphone audio capture started...")
        frames = []
        silence_start = None
        speech_started = False
        start_time = time.time()

        def audio_callback(indata, frame_count, time_info, status):
            if status:
                logger.warning(f"Audio Stream Status: {status}")
            self.audio_queue.put(indata.copy())

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=audio_callback,
                blocksize=int(self.sample_rate * 0.1)  # 100ms blocks
            ):
                while time.time() - start_time < max_duration:
                    try:
                        block = self.audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    rms_energy = np.sqrt(np.mean(block ** 2))
                    frames.append(block)

                    if rms_energy > self.energy_threshold:
                        speech_started = True
                        silence_start = None
                    elif speech_started:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start >= self.silence_duration:
                            logger.info("Silence detected. Stopping audio capture.")
                            break

                    # If no speech started after 4 seconds, timeout silently
                    if not speech_started and (time.time() - start_time > 4.0):
                        logger.debug("No speech detected within initial timeout.")
                        return None

            if not speech_started or not frames:
                return None

            audio_data = np.concatenate(frames, axis=0).flatten()
            return audio_data

        except Exception as e:
            logger.error(f"Microphone recording error: {e}")
            return None
