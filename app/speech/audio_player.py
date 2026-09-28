import os
import time
import threading
from typing import Optional, Callable
from app.core.logging_config import logger

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logger.warning("PyGame is not installed. Audio playback will be disabled.")

class AudioPlayer:
    """Python-native PyGame audio player for speech synthesis."""

    def __init__(self):
        self._is_playing = False
        self._playback_lock = threading.Lock()

        if PYGAME_AVAILABLE:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=1024)
                logger.info("PyGame audio mixer initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize PyGame audio mixer: {e}")

    def is_playing(self) -> bool:
        if not PYGAME_AVAILABLE or not pygame.mixer.get_init():
            return False
        try:
            return pygame.mixer.music.get_busy() or self._is_playing
        except Exception:
            return False

    def stop(self):
        if not PYGAME_AVAILABLE or not pygame.mixer.get_init():
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception as e:
            logger.debug(f"Error stopping PyGame audio playback: {e}")
        finally:
            self._is_playing = False

    def play_file(self, mp3_path: str, on_finish: Optional[Callable[[], None]] = None) -> bool:
        if not PYGAME_AVAILABLE or not pygame.mixer.get_init():
            logger.warning("Cannot play audio: PyGame mixer not initialized.")
            if on_finish:
                on_finish()
            return False

        if not os.path.exists(mp3_path):
            logger.error(f"Audio file does not exist: {mp3_path}")
            if on_finish:
                on_finish()
            return False

        def _play_thread():
            with self._playback_lock:
                try:
                    self._is_playing = True
                    pygame.mixer.music.load(mp3_path)
                    pygame.mixer.music.play()

                    while PYGAME_AVAILABLE and pygame.mixer.get_init() and pygame.mixer.music.get_busy() and self._is_playing:
                        time.sleep(0.05)

                    if PYGAME_AVAILABLE and pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()
                except Exception as e:
                    logger.debug(f"PyGame playback exception: {e}")
                finally:
                    self._is_playing = False
                    try:
                        if os.path.exists(mp3_path):
                            os.remove(mp3_path)
                    except Exception:
                        pass
                    if on_finish:
                        try:
                            on_finish()
                        except Exception:
                            pass

        threading.Thread(target=_play_thread, daemon=True).start()
        return True
