import time
import threading
from typing import Optional, Callable, List
from app.core.config import config
from app.core.logging_config import logger
from app.core.state import AssistantState, StateMachine
from app.audio.startup_sound import StartupSoundManager

class JarvisStateManager:
    """Authoritative state & session manager for HP supporting time-aware greetings, futuristic startup chime, hotkey toggles, and 10-minute sessions."""

    def __init__(
        self,
        timeout_seconds: float = 600.0,
        state_machine: Optional[StateMachine] = None,
        speak_callback: Optional[Callable[[str], None]] = None
    ):
        self.timeout_seconds = timeout_seconds or getattr(config, "session_timeout_seconds", 600.0)
        self.state_machine = state_machine or StateMachine(initial_state=AssistantState.OFFLINE)
        self.speak_callback = speak_callback

        self._primary_state: AssistantState = AssistantState.OFFLINE
        self._session_started_at: float = 0.0
        self._last_user_activity: float = 0.0
        self._is_active_session: bool = False
        self._warning_issued: bool = False
        
        # Confirmation state variables
        self._in_confirmation: bool = False
        self._confirmation_action: Optional[str] = None
        self._confirmation_start_time: float = 0.0
        self._confirmation_timeout: float = 10.0
        self._confirmation_callback: Optional[Callable[[bool], None]] = None

        self._lock = threading.Lock()
        self._timer_thread: Optional[threading.Thread] = None
        self._running: bool = True

        self._timer_thread = threading.Thread(target=self._monitor_inactivity, daemon=True)
        self._timer_thread.start()

    @property
    def current_state(self) -> AssistantState:
        return self.state_machine.current_state

    @property
    def primary_state(self) -> AssistantState:
        with self._lock:
            return self._primary_state

    def add_callback(self, callback: Callable[[AssistantState], None]):
        self.state_machine.add_callback(callback)

    def transition_to(self, new_state: AssistantState, reason: str = "general"):
        """Centralized thread-safe state transition with mandatory reason logging."""
        with self._lock:
            old_state = self.state_machine.current_state
            if old_state == new_state:
                return

            if new_state in (AssistantState.OFFLINE, AssistantState.ONLINE, AssistantState.ARMED, AssistantState.ACTIVE_SESSION, AssistantState.WAITING_FOR_CONFIRMATION, AssistantState.SESSION_EXPIRY_CONFIRMATION, AssistantState.SHUTTING_DOWN):
                self._primary_state = new_state

            logger.info(f"[STATE] {old_state.name} -> {new_state.name} reason={reason}")
            self.state_machine.transition_to(new_state)

    def toggle_online_offline(self, reason: str = "hotkey_toggle") -> AssistantState:
        """Ctrl+Shift+F3 global hotkey toggle: OFFLINE -> ONLINE or ONLINE -> OFFLINE."""
        with self._lock:
            is_currently_online = self._primary_state in (AssistantState.ONLINE, AssistantState.ACTIVE_SESSION, AssistantState.ARMED, AssistantState.WAITING_FOR_CONFIRMATION, AssistantState.SESSION_EXPIRY_CONFIRMATION)
            
            if not is_currently_online:
                # Transition OFFLINE -> ONLINE
                now = time.time()
                self._session_started_at = now
                self._last_user_activity = now
                self._is_active_session = True
                self._warning_issued = False
                self._in_confirmation = False
                self._primary_state = AssistantState.ONLINE
                logger.info(f"[STATE] OFFLINE -> ONLINE reason={reason}")
                self.state_machine.transition_to(AssistantState.ONLINE)
                target = AssistantState.ONLINE
                msg = config.get_random_hotkey_activation()
            else:
                # Already online check to prevent duplicate listeners
                logger.info(f"[HOTKEY] Already online when hotkey pressed. Reason={reason}")
                msg = "I'm already online."
                target = self._primary_state

        if self.speak_callback:
            try:
                self.speak_callback(msg)
            except Exception as e:
                logger.debug(f"Toggle prompt speech error: {e}")

        return target

    def start_startup_flow(self, callback: Optional[Callable[[bool], None]] = None):
        """Triggered on startup: Dynamic time-aware greeting followed by 10s confirmation window."""
        greeting = config.get_time_aware_greeting()
        with self._lock:
            self._in_confirmation = True
            self._confirmation_action = "startup"
            self._confirmation_start_time = 0.0  # Timer starts AFTER TTS completes!
            self._confirmation_timeout = 10.0
            self._confirmation_callback = callback
            self._primary_state = AssistantState.WAITING_FOR_CONFIRMATION
            logger.info("[STATE] Startup initialization -> WAITING_FOR_CONFIRMATION (10s post-TTS window)")
            self.state_machine.transition_to(AssistantState.WAITING_FOR_CONFIRMATION)

        if self.speak_callback:
            try:
                self.speak_callback(greeting)
            except Exception as e:
                logger.debug(f"Startup greeting error: {e}")

    def activate(self, reason: str = "activation", play_startup_sound: bool = True) -> AssistantState:
        """Activate HP ONLINE mode directly with cinematic startup chime sequence."""
        with self._lock:
            now = time.time()
            self._session_started_at = now
            self._last_user_activity = now
            self._is_active_session = True
            self._warning_issued = False
            self._in_confirmation = False
            self._primary_state = AssistantState.ONLINE
            logger.info(f"[STATE] {self.state_machine.current_state.name} -> ONLINE reason={reason}")
            self.state_machine.transition_to(AssistantState.ONLINE)

        if play_startup_sound and self.speak_callback:
            def _post_sound():
                if self.speak_callback:
                    try:
                        self.speak_callback("We're all set. I'm online.")
                    except Exception as ex:
                        logger.debug(f"Post-sound prompt error: {ex}")

            def _play_sound():
                StartupSoundManager.play_startup_sound_async(on_finish_callback=_post_sound)

            try:
                self.speak_callback("Alright. Give me a second to bring everything online.")
                threading.Thread(target=lambda: (time.sleep(2.8), _play_sound())[1], daemon=True).start()
            except Exception as e:
                logger.debug(f"Activation speech error: {e}")
        elif self.speak_callback:
            try:
                self.speak_callback(f"I'm online, {config.owner_name}. What can I do for you?")
            except Exception as e:
                logger.debug(f"Activation speech error: {e}")

        return AssistantState.ONLINE

    def start_session(self, reason: str = "wake_word") -> AssistantState:
        """Triggered by wake-word ('Hey HP') -> Transitions OFFLINE to ONLINE."""
        with self._lock:
            now = time.time()
            self._session_started_at = now
            self._last_user_activity = now
            self._is_active_session = True
            self._warning_issued = False
            self._in_confirmation = False
            self._primary_state = AssistantState.ONLINE
            logger.info(f"[STATE] {self.state_machine.current_state.name} -> ONLINE reason={reason}")
            self.state_machine.transition_to(AssistantState.ONLINE)

        if self.speak_callback:
            try:
                self.speak_callback("Yes?")
            except Exception as e:
                logger.debug(f"Wake word speech error: {e}")

        return AssistantState.ONLINE

    def reset_activity_timer(self, reason: str = "user_interaction"):
        """Reset the 600s countdown on valid user activity."""
        with self._lock:
            self._last_user_activity = time.time()
            self._warning_issued = False
            if self._is_active_session:
                logger.info(f"[SESSION] Activity timer reset: {int(self.timeout_seconds)}s (reason={reason})")
            elif self._primary_state not in (AssistantState.OFFLINE, AssistantState.WAITING_FOR_CONFIRMATION, AssistantState.SESSION_EXPIRY_CONFIRMATION, AssistantState.SHUTTING_DOWN):
                self._is_active_session = True
                self._primary_state = AssistantState.ONLINE
                self.state_machine.transition_to(AssistantState.ONLINE)

    def extend_session(self, seconds: Optional[float] = None, announce: bool = True) -> float:
        """Explicitly extend active session by another 10 minutes."""
        with self._lock:
            self._last_user_activity = time.time()
            self._warning_issued = False
            self._is_active_session = True
            self._primary_state = AssistantState.ONLINE
            logger.info(f"[SESSION] Session extended by {int(self.timeout_seconds)}s.")

        if announce and self.speak_callback:
            try:
                self.speak_callback("Got it. I'm staying with you.")
            except Exception as e:
                logger.debug(f"Extension speech error: {e}")

        return self.remaining_seconds()

    def is_session_active(self) -> bool:
        with self._lock:
            return self._is_active_session and self._primary_state in (AssistantState.ONLINE, AssistantState.ACTIVE_SESSION)

    def is_in_confirmation(self) -> bool:
        with self._lock:
            return self._in_confirmation or self._primary_state in (AssistantState.WAITING_FOR_CONFIRMATION, AssistantState.SESSION_EXPIRY_CONFIRMATION)

    def handle_confirmation_response(self, confirmed: bool) -> bool:
        """Process natural user response during confirmation window."""
        with self._lock:
            if not self._in_confirmation and self._primary_state not in (AssistantState.WAITING_FOR_CONFIRMATION, AssistantState.SESSION_EXPIRY_CONFIRMATION):
                return False

            self._in_confirmation = False
            self._confirmation_start_time = 0.0
            cb = self._confirmation_callback
            self._confirmation_callback = None
            action = self._confirmation_action
            self._confirmation_action = None

        if confirmed:
            logger.info(f"[CONFIRMATION] User confirmed action '{action}'. Transitioning to ONLINE.")
            if action == "startup":
                self.activate(reason="startup_confirmed", play_startup_sound=True)
            else:
                self.extend_session(announce=True)
            if cb:
                cb(True)
            return True
        else:
            logger.info(f"[CONFIRMATION] User rejected action '{action}'. Going OFFLINE.")
            msg = "Alright, I'll go offline for now." if action == "session_extension" else None
            self.deactivate(reason="confirmation_rejected", announce=True, custom_msg=msg)
            if cb:
                cb(False)
            return True

    def remaining_seconds(self) -> float:
        with self._lock:
            if not self._is_active_session:
                return 0.0
            elapsed = time.time() - self._last_user_activity
            return max(0.0, self.timeout_seconds - elapsed)

    def deactivate(self, reason: str = "user_command", announce: bool = True, custom_msg: Optional[str] = None):
        """Deactivate session and transition back to OFFLINE."""
        with self._lock:
            self._is_active_session = False
            self._warning_issued = False
            self._in_confirmation = False
            self._confirmation_start_time = 0.0
            old_state = self._primary_state
            self._primary_state = AssistantState.OFFLINE
            logger.info(f"[STATE] {old_state.name} -> OFFLINE reason={reason}")
            self.state_machine.transition_to(AssistantState.TIMEOUT)
            self.state_machine.transition_to(AssistantState.OFFLINE)

        if announce and self.speak_callback:
            msg = custom_msg or "Alright. I'm going offline."
            try:
                self.speak_callback(msg)
            except Exception as e:
                logger.debug(f"Deactivation speech error: {e}")

    def on_tts_finished(self):
        """Called when TTS completes -> Starts confirmation timer post-speech & reverts activity substate back to current primary_state."""
        with self._lock:
            if self._in_confirmation and self._confirmation_start_time == 0.0:
                self._confirmation_start_time = time.time()
                logger.info(f"[CONFIRMATION] Prompt TTS finished speaking. Starting {self._confirmation_timeout}s listening window now.")

            target_state = self._primary_state
            logger.info(f"[STATE] SPEAKING -> {target_state.name} reason=tts_finished")
            self.state_machine.transition_to(target_state)

    def _monitor_inactivity(self):
        """Background thread monitoring 10-minute inactivity timeouts & 30s proactive expiry warnings."""
        while self._running:
            time.sleep(0.5)
            with self._lock:
                if self._in_confirmation or self._primary_state in (AssistantState.WAITING_FOR_CONFIRMATION, AssistantState.SESSION_EXPIRY_CONFIRMATION):
                    if self._confirmation_start_time > 0.0:
                        conf_elapsed = time.time() - self._confirmation_start_time
                        if conf_elapsed >= self._confirmation_timeout:
                            logger.info("[CONFIRMATION] 10-second post-speech confirmation window timed out. Going OFFLINE.")
                            action = self._confirmation_action
                            self._in_confirmation = False
                            self._confirmation_start_time = 0.0
                            self._primary_state = AssistantState.OFFLINE
                            self.state_machine.transition_to(AssistantState.OFFLINE)
                            
                            if action == "session_extension" and self.speak_callback:
                                try:
                                    threading.Thread(
                                        target=self.speak_callback,
                                        args=("Alright, I'll go offline for now.",),
                                        daemon=True
                                    ).start()
                                except Exception:
                                    pass
                    continue

                if not self._is_active_session:
                    continue

                if self.current_state in (AssistantState.THINKING, AssistantState.PROCESSING, AssistantState.EXECUTING, AssistantState.SCREEN_ANALYZING, AssistantState.SPEAKING, AssistantState.SHUTTING_DOWN):
                    continue

                elapsed = time.time() - self._last_user_activity
                rem = max(0.0, self.timeout_seconds - elapsed)

                # Proactive 30-second warning threshold
                if rem <= 30.0 and rem > 0 and not self._warning_issued:
                    self._warning_issued = True
                    self._in_confirmation = True
                    self._confirmation_action = "session_extension"
                    self._confirmation_start_time = 0.0
                    self._confirmation_timeout = 10.0
                    self._primary_state = AssistantState.SESSION_EXPIRY_CONFIRMATION
                    logger.info("[SESSION] Session about to expire in 30s. Triggering proactive prompt...")
                    self.state_machine.transition_to(AssistantState.SESSION_EXPIRY_CONFIRMATION)

                    warning_msg = config.get_random_expiry_question()
                    if self.speak_callback:
                        try:
                            threading.Thread(
                                target=self.speak_callback,
                                args=(warning_msg,),
                                daemon=True
                            ).start()
                        except Exception as e:
                            logger.debug(f"Warning prompt error: {e}")

            if elapsed >= self.timeout_seconds:
                logger.info(f"[SESSION] No valid user interaction for {int(self.timeout_seconds)}s. Going offline.")
                self.deactivate(reason="inactivity_timeout", announce=True, custom_msg="Alright, I'll go offline for now.")

    def stop(self):
        self._running = False
