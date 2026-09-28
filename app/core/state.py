from enum import Enum, auto
from typing import Callable, List, Optional
import threading

class AssistantState(Enum):
    OFFLINE = auto()
    ONLINE = auto()
    ARMED = auto()
    ACTIVE_SESSION = auto()
    WAITING_FOR_CONFIRMATION = auto()
    SESSION_EXPIRY_CONFIRMATION = auto()  # Canonical session confirmation state
    SHUTTING_DOWN = auto()
    IDLE = auto()
    LISTENING = auto()
    LISTENING_FOR_WAKE_WORD = auto()
    LISTENING_FOR_COMMAND = auto()
    THINKING = auto()
    PROCESSING = auto()
    EXECUTING = auto()
    SCREEN_ANALYZING = auto()
    SPEAKING = auto()
    TIMEOUT = auto()
    COOLDOWN = auto()
    ERROR = auto()

class StateMachine:
    """Thread-safe central state machine with listener callbacks."""

    def __init__(self, initial_state: AssistantState = AssistantState.OFFLINE):
        self._state = initial_state
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[AssistantState], None]] = []

    @property
    def current_state(self) -> AssistantState:
        with self._lock:
            return self._state

    def add_callback(self, callback: Callable[[AssistantState], None]):
        with self._lock:
            self._callbacks.append(callback)

    def transition_to(self, new_state: AssistantState):
        with self._lock:
            if self._state == new_state:
                return
            self._state = new_state
            callbacks = list(self._callbacks)

        for cb in callbacks:
            try:
                cb(new_state)
            except Exception:
                pass
