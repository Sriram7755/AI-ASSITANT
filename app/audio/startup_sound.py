import os
import math
import wave
import struct
import threading
from pathlib import Path
from app.core.config import config
from app.core.logging_config import logger

class StartupSoundManager:
    """Generates and plays a non-blocking 3.5s futuristic cyberpunk computer startup sound using PyGame."""

    @staticmethod
    def generate_futuristic_startup_wav(file_path: Path):
        """Generates a subtle 3.5-second futuristic ascending harmonic chime (16-bit PCM WAV)."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            sample_rate = 44100
            duration = 3.5
            n_samples = int(sample_rate * duration)

            with wave.open(str(file_path), "w") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)

                # Base frequencies for futuristic power-up chord: E4, G#4, B4, E5 (329Hz -> 659Hz)
                samples = []
                for i in range(n_samples):
                    t = i / sample_rate
                    # Pitch bend / sweep envelope
                    freq = 220 + (440 * (t / duration) ** 1.5)
                    # Harmonics: Fundamental + Octave + Synth chord shimmer
                    val1 = math.sin(2 * math.pi * freq * t)
                    val2 = 0.5 * math.sin(2 * math.pi * (freq * 1.5) * t)
                    val3 = 0.25 * math.sin(2 * math.pi * (freq * 2.0) * t)
                    combined = (val1 + val2 + val3) / 1.75

                    # Smooth Fade-in (0.2s) and Fade-out (0.5s) envelope
                    if t < 0.2:
                        env = t / 0.2
                    elif t > (duration - 0.5):
                        env = (duration - t) / 0.5
                    else:
                        env = 1.0

                    sample_val = int(combined * env * 12000)  # Gentle non-clipping volume
                    samples.append(struct.pack("<h", max(-32768, min(32767, sample_val))))

                wav_file.writeframes(b"".join(samples))
            logger.info(f"[AUDIO] Generated futuristic startup chime at: {file_path}")
        except Exception as e:
            logger.debug(f"Could not generate fallback startup sound: {e}")

    @classmethod
    def play_startup_sound_async(cls, on_finish_callback=None):
        """Non-blocking playback of futuristic startup sound effect using PyGame mixer."""
        def _play_worker():
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

                sound_file = config.startup_sound_path
                if not sound_file.exists():
                    cls.generate_futuristic_startup_wav(sound_file)

                if sound_file.exists():
                    sound = pygame.mixer.Sound(str(sound_file))
                    sound.set_volume(0.6)  # Subtle, professional volume
                    sound.play()
                    logger.info("[AUDIO] Playing futuristic startup sound effect...")
                    # Duration is ~3.5 seconds
                    import time
                    time.sleep(3.2)

            except Exception as e:
                logger.debug(f"Startup sound playback skipped/handled: {e}")
            finally:
                if on_finish_callback:
                    try:
                        on_finish_callback()
                    except Exception as ex:
                        logger.debug(f"Startup sound callback error: {ex}")

        threading.Thread(target=_play_worker, daemon=True).start()
