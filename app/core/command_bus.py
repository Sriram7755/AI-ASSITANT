import queue
import threading
from typing import Callable, List, Optional
from app.core.events import Command
from app.core.logging_config import logger

class CommandBus:
    """Central thread-safe command bus connecting voice, text, and GUI inputs to the orchestrator."""

    def __init__(self):
        self._handlers: List[Callable[[Command], None]] = []
        self._lock = threading.Lock()

    def register_handler(self, handler: Callable[[Command], None]):
        with self._lock:
            self._handlers.append(handler)

    def submit(self, command: Command):
        if not command or not command.text or not command.text.strip():
            logger.debug("Empty command submitted to CommandBus. Ignoring.")
            return

        logger.info(f"[COMMAND BUS] ({command.source.upper()}) Dispatching: '{command.text}'")

        with self._lock:
            handlers = list(self._handlers)

        for handler in handlers:
            try:
                handler(command)
            except Exception as e:
                logger.error(f"Error in CommandBus handler: {e}")
