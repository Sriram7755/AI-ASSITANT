import time
import queue
import collections
import numpy as np
import sounddevice as sd
from typing import Optional, Callable, List, Dict, Any
from app.core.config import config
from app.core.logging_config import logger

try:
    from scipy.signal import resample as scipy_resample
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

class MicrophoneStreamer:
    """Robust audio capture streamer with device selection, native resampling, DC offset removal, amplitude normalization, ring buffer, and VAD."""

    def __init__(
        self,
        target_sample_rate: int = 16000,
        device_index: Optional[int] = None,
        silence_timeout_ms: int = 1200,
        pre_roll_ms: int = 300,
        min_speech_ms: int = 500,
        max_duration_ms: int = 15000,
        silence_duration: Optional[float] = None,
        energy_threshold: Optional[float] = None
    ):
        self.target_sample_rate = target_sample_rate
        self.device_index = device_index if device_index is not None else config.microphone_device
        self.silence_timeout_ms = int(silence_duration * 1000) if silence_duration is not None else silence_timeout_ms
        self.pre_roll_ms = pre_roll_ms
        self.min_speech_ms = min_speech_ms
        self.max_duration_ms = max_duration_ms

        self.energy_threshold = energy_threshold if energy_threshold is not None else 0.015
        self.audio_queue = queue.Queue()
        self.native_sample_rate = self._get_native_sample_rate()

    @staticmethod
    def list_available_microphones() -> List[Dict[str, Any]]:
        """List all available audio input devices (microphones)."""
        devices = []
        try:
            all_devs = sd.query_devices()
            for idx, dev in enumerate(all_devs):
                if dev.get("max_input_channels", 0) > 0:
                    devices.append({
                        "index": idx,
                        "name": dev.get("name", f"Microphone {idx}"),
                        "channels": dev.get("max_input_channels"),
                        "sample_rate": dev.get("default_samplerate", 16000)
                    })
        except Exception as e:
            logger.debug(f"Error querying microphone devices: {e}")
        return devices

    def _get_native_sample_rate(self) -> int:
        try:
            if self.device_index is not None:
                info = sd.query_devices(self.device_index, 'input')
                return int(info.get("default_samplerate", 16000))
            default_dev = sd.query_devices(kind='input')
            return int(default_dev.get("default_samplerate", 16000))
        except Exception as e:
            logger.debug(f"Fallback to default sample rate 16000 Hz: {e}")
            return 16000

    def calibrate_ambient_noise(self, duration: float = 1.0):
        """Sample ambient noise and calculate adaptive VAD threshold."""
        try:
            logger.info("Calibrating ambient microphone noise...")
            dev_sr = self.native_sample_rate
            recording = sd.rec(
                int(dev_sr * duration),
                samplerate=dev_sr,
                channels=1,
                dtype="float32",
                device=self.device_index
            )
            sd.wait()
            recording = recording.flatten()
            recording = recording - np.mean(recording)  # DC offset removal
            rms_noise = float(np.sqrt(np.mean(recording ** 2)))
            calculated = max(0.012, min(0.06, rms_noise * 2.8))
            self.energy_threshold = round(calculated, 4)
            logger.info(f"Microphone calibrated. Native SR: {dev_sr}Hz, RMS Noise: {rms_noise:.5f}, Energy Threshold: {self.energy_threshold}")
        except Exception as e:
            logger.debug(f"Ambient noise calibration fallback: {e}")

    def _resample_audio(self, audio_data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        if orig_sr == target_sr:
            return audio_data
        num_target_samples = int(len(audio_data) * target_sr / orig_sr)
        if SCIPY_AVAILABLE:
            resampled = scipy_resample(audio_data, num_target_samples)
            return resampled.astype(np.float32)
        else:
            orig_indices = np.linspace(0, len(audio_data) - 1, num=len(audio_data))
            target_indices = np.linspace(0, len(audio_data) - 1, num=num_target_samples)
            return np.interp(target_indices, orig_indices, audio_data).astype(np.float32)

    def preprocess_audio(self, raw_audio: np.ndarray, native_sr: int) -> np.ndarray:
        """Preprocessing pipeline: Mono conversion -> Resample to 16kHz -> Remove DC offset -> Peak normalization."""
        if raw_audio is None or len(raw_audio) == 0:
            return np.array([], dtype=np.float32)

        # 1. Mono conversion
        if raw_audio.ndim > 1:
            raw_audio = np.mean(raw_audio, axis=1)
        audio = raw_audio.flatten()

        # 2. Resample to 16000 Hz if needed
        audio_16k = self._resample_audio(audio, native_sr, self.target_sample_rate)

        # 3. Remove DC Offset
        audio_16k = audio_16k - np.mean(audio_16k)

        # 4. Amplitude Peak Normalization
        peak = np.max(np.abs(audio_16k))
        if peak > 1e-4:
            audio_16k = (audio_16k / peak) * 0.95

        return audio_16k.astype(np.float32)

    def capture_speech(self, max_duration: Optional[float] = None, status_callback: Optional[Callable[[str], None]] = None) -> Optional[np.ndarray]:
        """Capture speech using a 300ms pre-roll ring buffer and 1200ms silence detection."""
        if status_callback:
            status_callback("LISTENING")

        dev_sr = self.native_sample_rate
        block_len = int(dev_sr * 0.1)  # 100ms blocks
        pre_roll_blocks_count = max(1, int(self.pre_roll_ms / 100))
        ring_buffer = collections.deque(maxlen=pre_roll_blocks_count)

        frames = []
        speech_started = False
        silence_start = None
        start_time = time.time()
        max_sec = (max_duration or (self.max_duration_ms / 1000.0))

        def audio_callback(indata, frame_count, time_info, status):
            if status and config.voice_debug:
                logger.warning(f"Audio Stream Status: {status}")
            self.audio_queue.put(indata.copy())

        try:
            with sd.InputStream(
                samplerate=dev_sr,
                channels=1,
                dtype="float32",
                device=self.device_index,
                callback=audio_callback,
                blocksize=block_len
            ):
                while time.time() - start_time < max_sec:
                    try:
                        block = self.audio_queue.get(timeout=0.2).flatten()
                    except queue.Empty:
                        continue

                    block_dc = block - np.mean(block)
                    rms_energy = np.sqrt(np.mean(block_dc ** 2))

                    if not speech_started:
                        ring_buffer.append(block)
                        if rms_energy > self.energy_threshold:
                            speech_started = True
                            frames.extend(list(ring_buffer))
                            ring_buffer.clear()
                            silence_start = None
                        elif time.time() - start_time > 4.0:
                            return None
                    else:
                        frames.append(block)
                        if rms_energy > self.energy_threshold:
                            silence_start = None
                        else:
                            if silence_start is None:
                                silence_start = time.time()
                            elif (time.time() - silence_start) * 1000 >= self.silence_timeout_ms:
                                logger.debug(f"Silence timeout ({self.silence_timeout_ms}ms) reached. Stopping capture.")
                                break

            if not speech_started or not frames:
                return None

            raw_audio = np.concatenate(frames, axis=0)
            cleaned_16k = self.preprocess_audio(raw_audio, dev_sr)

            duration = len(cleaned_16k) / self.target_sample_rate
            if duration * 1000 < self.min_speech_ms:
                logger.debug(f"Captured audio too short ({duration:.2f}s < min {self.min_speech_ms}ms). Discarding.")
                return None

            rms = float(np.sqrt(np.mean(cleaned_16k ** 2)))
            peak = float(np.max(np.abs(cleaned_16k)))
            logger.info(f"Audio captured: duration={duration:.2f}s, sample_rate={self.target_sample_rate}, channels=1, rms={rms:.4f}, peak={peak:.4f}")

            return cleaned_16k

        except Exception as e:
            logger.error(f"Microphone recording error: {e}")
            return None
