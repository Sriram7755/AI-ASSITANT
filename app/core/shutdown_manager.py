import sys
import time
import threading
from typing import Optional
from app.core.logging_config import logger
from app.core.state import AssistantState

class ShutdownManager:
    """Centralized thread-safe shutdown manager for HP ensuring 100% clean resource cleanup."""

    _instance: Optional['ShutdownManager'] = None
    _lock = threading.Lock()

    def __init__(self, orchestrator=None, voice_pipeline=None, hotkey_listener=None, gui_app=None):
        self.orchestrator = orchestrator
        self.voice_pipeline = voice_pipeline
        self.hotkey_listener = hotkey_listener
        self.gui_app = gui_app
        self._shutting_down = False

    @classmethod
    def get_instance(cls, **kwargs) -> 'ShutdownManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(**kwargs)
            return cls._instance

    def shutdown(self, reason: str = "user_exit", speak_farewell: bool = True):
        """Perform a complete, graceful shutdown of all threads, mic, TTS, PyGame, scheduler, and GUI."""
        with self._lock:
            if self._shutting_down:
                return
            self._shutting_down = True

        logger.info(f"[SHUTDOWN] Initiate clean HP shutdown (reason='{reason}')...")

        # 1. Update State Machine
        if self.orchestrator and hasattr(self.orchestrator, "session_manager"):
            try:
                self.orchestrator.session_manager.transition_to(AssistantState.SHUTTING_DOWN, reason=reason)
            except Exception:
                pass

        # 2. Farewell Voice Speech
        farewell_msg = "Alright, Sriram. I'm shutting down. Keep going — you've got this."
        if speak_farewell and self.orchestrator and hasattr(self.orchestrator, "speech_manager"):
            try:
                logger.info(f"[SHUTDOWN] Speaking farewell: \"{farewell_msg}\"")
                done_evt = threading.Event()
                self.orchestrator.speech_manager.speak(farewell_msg, on_finish=lambda: done_evt.set())
                done_evt.wait(timeout=4.0)
            except Exception as e:
                logger.debug(f"Farewell speech error: {e}")

        # 3. Stop Voice Pipeline & Audio Capture
        if self.voice_pipeline:
            try:
                logger.info("[SHUTDOWN] Stopping VoicePipeline & audio capture...")
                self.voice_pipeline.stop()
            except Exception as e:
                logger.debug(f"VoicePipeline stop error: {e}")

        # 4. Stop Orchestrator Queue & Scheduler
        if self.orchestrator:
            try:
                if hasattr(self.orchestrator, "scheduler") and self.orchestrator.scheduler:
                    logger.info("[SHUTDOWN] Stopping APScheduler...")
                    self.orchestrator.scheduler.shutdown()
                self.orchestrator._worker_running = False
            except Exception as e:
                logger.debug(f"Orchestrator cleanup error: {e}")

        # 5. Stop Global Hotkey Listener
        if self.hotkey_listener:
            try:
                logger.info("[SHUTDOWN] Stopping GlobalHotkeyListener...")
                self.hotkey_listener.stop()
            except Exception as e:
                logger.debug(f"Hotkey stop error: {e}")

        # 6. Close PyGame Mixer
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.stop()
                pygame.mixer.quit()
                logger.info("[SHUTDOWN] Pygame mixer released.")
        except Exception as e:
            logger.debug(f"Pygame cleanup error: {e}")

        # 7. Quit GUI Application if active
        if self.gui_app:
            try:
                logger.info("[SHUTDOWN] Quitting PySide6 Application...")
                self.gui_app.quit()
            except Exception as e:
                logger.debug(f"GUI quit error: {e}")

        logger.info("[SHUTDOWN] HP application shutdown complete. Exiting process.")
        time.sleep(0.3)
        sys.exit(0)
