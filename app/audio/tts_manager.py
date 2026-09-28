import os
import time
import asyncio
import tempfile
import threading
from typing import Optional, Callable
from app.config.settings import settings
from app.core.logging_config import logger

class TTSManager:
    """Edge-TTS speech synthesis manager with PyGame native audio playback."""

    def __init__(
        self,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        volume: Optional[str] = None
    ):
        self.voice = voice or settings.tts_voice
        self.rate = rate or settings.tts_rate
        self.volume = volume or settings.tts_volume
        self._is_speaking = False
        self._mixer_initialized = False

        self._init_pygame_mixer()

        # Persistent asyncio event loop running in a dedicated background daemon thread
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._loop_thread.start()

    def _init_pygame_mixer(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=1024)
            self._mixer_initialized = True
            logger.info("PyGame audio mixer initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PyGame audio mixer: {e}")
            self._mixer_initialized = False

    def _run_async_loop(self):
        """Background thread target to keep event loop alive for async TTS operations."""
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        except Exception:
            pass

    def is_speaking(self) -> bool:
        return self._is_speaking

    def stop(self):
        """Interrupt and stop active TTS audio playback."""
        self._is_speaking = False
        if self._mixer_initialized:
            try:
                import pygame
                if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
            except Exception:
                pass

    def speak(self, text: str, on_start: Optional[Callable[[], None]] = None, on_finish: Optional[Callable[[], None]] = None):
        """Synthesize and play speech in a background worker thread."""
        if not text or not text.strip():
            if on_finish:
                on_finish()
            return

        def _worker():
            self._is_speaking = True
            if on_start:
                on_start()
            audio_file = None
            try:
                clean_text = text[:250] if len(text) > 250 else text
                audio_file = self._synthesize(clean_text)
                if audio_file and os.path.exists(audio_file) and self._is_speaking:
                    self._play_audio_pygame(audio_file)
            except Exception as e:
                logger.error(f"TTS playback error: {e}")
            finally:
                if audio_file and os.path.exists(audio_file):
                    try:
                        os.remove(audio_file)
                    except Exception:
                        pass
                self._is_speaking = False
                if on_finish:
                    on_finish()

        threading.Thread(target=_worker, daemon=True).start()

    def _synthesize(self, text: str) -> Optional[str]:
        """Synthesize speech using Edge-TTS on the persistent background event loop."""
        try:
            import edge_tts

            if not self._loop.is_running():
                return None

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                out_path = tmp.name

            async def _run_edge():
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=self.voice,
                    rate=self.rate,
                    volume=self.volume
                )
                await communicate.save(out_path)

            future = asyncio.run_coroutine_threadsafe(_run_edge(), self._loop)
            future.result(timeout=15)

            return out_path
        except RuntimeError:
            return None
        except Exception as e:
            logger.error(f"Edge-TTS synthesis failed: {e}")
            return None

    def _play_audio_pygame(self, mp3_path: str):
        """Play synthesized MP3 file natively using PyGame mixer."""
        if not self._mixer_initialized:
            self._init_pygame_mixer()

        try:
            import pygame
            pygame.mixer.music.load(mp3_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy() and self._is_speaking:
                time.sleep(0.05)

            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception as e:
            logger.error(f"PyGame audio playback error: {e}")

    def shutdown(self):
        """Cleanly stop and close the background event loop and mixer."""
        self.stop()
        if self._mixer_initialized:
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
            except Exception:
                pass
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
