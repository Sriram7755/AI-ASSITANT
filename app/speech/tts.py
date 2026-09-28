import os
import asyncio
import tempfile
import threading
from typing import Optional, Callable
from app.config.settings import settings
from app.core.logging_config import logger

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts is not installed. TTS voice synthesis will be disabled.")

class TextToSpeech:
    """Edge-TTS speech synthesizer managing a persistent background asyncio event loop thread."""

    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or settings.tts_voice
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._start_persistent_event_loop()

    def _start_persistent_event_loop(self):
        def _run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=_run_loop, args=(self._loop,), daemon=True)
        self._loop_thread.start()
        logger.info("Persistent TTS asyncio event loop thread started.")

    def generate_speech_file(self, text: str) -> Optional[str]:
        if not EDGE_TTS_AVAILABLE or not self._loop or not self._loop.is_running():
            logger.warning("Edge-TTS unavailable or event loop not running.")
            return None

        clean_text = text.strip()
        if not clean_text:
            return None

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_path = temp_file.name
        temp_file.close()

        async def _synthesize():
            communicate = edge_tts.Communicate(clean_text, self.voice)
            await communicate.save(temp_path)

        try:
            future = asyncio.run_coroutine_threadsafe(_synthesize(), self._loop)
            future.result(timeout=15)
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                return temp_path
        except Exception as e:
            logger.error(f"Edge-TTS synthesis error: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
        return None

    def shutdown(self):
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            logger.info("Persistent TTS asyncio loop shutdown requested.")
