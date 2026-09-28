import time
import threading
from typing import Optional, Callable
from app.core.config import config
from app.core.logging_config import logger
from app.core.events import Command
from app.core.command_bus import CommandBus
from app.core.state import AssistantState
from app.core.session_manager import JarvisStateManager
from app.voice.wake_word import WakeWordDetector
from app.voice.stt import SpeechRecognizer

class VoicePipeline:
    """State-aware background voice pipeline for HP with resilient exception recovery and anti-self-feedback protection."""

    def __init__(
        self,
        command_bus: CommandBus,
        speech_recognizer: SpeechRecognizer,
        session_manager: Optional[JarvisStateManager] = None,
        is_speaking_callback: Optional[Callable[[], bool]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
        speak_prompt_callback: Optional[Callable[[str], None]] = None
    ):
        self.command_bus = command_bus
        self.speech_recognizer = speech_recognizer
        self.session_manager = session_manager or JarvisStateManager(timeout_seconds=config.session_timeout_seconds)
        self.is_speaking_callback = is_speaking_callback
        self.status_callback = status_callback
        self.speak_prompt_callback = speak_prompt_callback

        self.wake_detector = WakeWordDetector(
            speech_recognizer=self.speech_recognizer,
            is_speaking_callback=self.is_speaking_callback
        )
        self._voice_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self.is_running = False

    def start(self):
        self.is_running = True
        self._thread = threading.Thread(target=self._run_voice_loop, daemon=True)
        self._thread.start()
        logger.info("[OK] VoicePipeline background listener thread started.")

    def _update_state(self, new_state: AssistantState):
        self.session_manager.transition_to(new_state)
        if self.status_callback:
            self.status_callback(new_state.name)

    def _recover_voice_pipeline_state(self):
        """State recovery strategy ensuring the voice loop thread NEVER dies due to an exception."""
        try:
            if self.session_manager.is_session_active():
                logger.info("[VOICE RECOVERY] Recovering voice pipeline to ONLINE state.")
                self._update_state(AssistantState.ONLINE)
            else:
                logger.info("[VOICE RECOVERY] Recovering voice pipeline to OFFLINE state.")
                self._update_state(AssistantState.OFFLINE)
        except Exception as ex:
            logger.error(f"[VOICE RECOVERY] Defensive recovery fallback: {ex}")

    def _run_voice_loop(self):
        logger.info(f"[OK] Voice pipeline initialized. Hotkeys: '{config.global_hotkey}' (ON) / '{config.deactivate_hotkey}' (OFF)...")
        try:
            self.wake_detector.audio_manager.calibrate_ambient_noise()
        except Exception as e:
            logger.debug(f"Ambient noise calibration skipped: {e}")

        while self.is_running:
            try:
                curr_state = self.session_manager.current_state

                # OFFLINE check: Do NOT continuously listen or run speech recognition when OFFLINE!
                if curr_state == AssistantState.OFFLINE:
                    time.sleep(0.2)
                    continue

                # 1. Anti-Self-Feedback Protection: Pause mic while speaking
                if self.is_speaking_callback and self.is_speaking_callback():
                    self._update_state(AssistantState.SPEAKING)
                    time.sleep(0.3)
                    continue

                # Post-speech cooldown after TTS playback completes
                if curr_state == AssistantState.SPEAKING:
                    logger.info("[VOICE] Speech playback finished. Enforcing 0.8s cooldown...")
                    self._update_state(AssistantState.COOLDOWN)
                    time.sleep(config.post_speech_cooldown)
                    if self.session_manager.is_session_active():
                        self._update_state(AssistantState.ONLINE)
                    else:
                        self._update_state(AssistantState.OFFLINE)
                    continue

                # 2. State-Based Microphone Listening
                audio_data = self.wake_detector.audio_manager.capture_speech(max_duration=10)
                
                # Check state again post-capture to prevent race conditions
                curr_state = self.session_manager.current_state
                if curr_state == AssistantState.OFFLINE or audio_data is None or len(audio_data) == 0:
                    time.sleep(0.1)
                    continue

                raw_transcript = self.speech_recognizer.transcribe_audio_array(audio_data).strip()
                
                # Check state again post-transcription
                curr_state = self.session_manager.current_state
                if curr_state == AssistantState.OFFLINE or not raw_transcript:
                    logger.info(f"[VOICE] State is OFFLINE -> Discarding late transcription: '{raw_transcript}'")
                    continue

                logger.info(f"[VOICE] VOICE_TRANSCRIPTION: \"{raw_transcript}\"")
                is_wake, extracted_cmd = self.wake_detector.match_wake_word(raw_transcript)

                # 3. Confirmation State Decision Logic (WAITING_FOR_CONFIRMATION / SESSION_EXPIRY_CONFIRMATION)
                if self.session_manager.is_in_confirmation() or curr_state in (AssistantState.WAITING_FOR_CONFIRMATION, AssistantState.SESSION_EXPIRY_CONFIRMATION):
                    clean_tr = raw_transcript.lower().strip()
                    positive_phrases = ("yes", "yeah", "continue", "stay online", "keep me online", "keep it online", "sure", "yep", "ok", "okay", "keep going", "go ahead", "don't stop", "dont stop")
                    negative_phrases = ("no", "go offline", "stay offline", "not now", "sleep", "stop", "nope", "shutdown", "go idle", "that's enough", "you can stop")

                    if any(p in clean_tr for p in positive_phrases):
                        logger.info(f"[CONFIRMATION] Voice confirmation POSITIVE matched: '{clean_tr}'")
                        self.session_manager.handle_confirmation_response(True)
                    elif any(p in clean_tr for p in negative_phrases):
                        logger.info(f"[CONFIRMATION] Voice confirmation NEGATIVE matched: '{clean_tr}'")
                        self.session_manager.handle_confirmation_response(False)
                    else:
                        logger.info(f"[CONFIRMATION] Unrecognized confirmation response '{clean_tr}'. Rejecting.")
                        self.session_manager.handle_confirmation_response(False)
                    continue

                # 4. ONLINE Active Session Mode
                if self.session_manager.is_session_active() or curr_state in (AssistantState.ONLINE, AssistantState.ACTIVE_SESSION):
                    cmd_to_execute = extracted_cmd if (is_wake and extracted_cmd) else raw_transcript
                    logger.info(f"[VOICE] ONLINE mode -> Executing command directly: \"{cmd_to_execute}\"")
                    self._dispatch_command(cmd_to_execute)

                elif is_wake or curr_state == AssistantState.ARMED:
                    logger.info(f"[VOICE] WAKE_WORD matched (is_wake={is_wake}) -> Transitioning to ONLINE")
                    self.session_manager.start_session(reason="wake_word")

                    if extracted_cmd:
                        self._dispatch_command(extracted_cmd)
                    else:
                        if self.speak_prompt_callback:
                            self.speak_prompt_callback("Yes?")
                        else:
                            time.sleep(0.4)

                else:
                    logger.info(f"[VOICE] Speech rejected in state '{curr_state.name}': \"{raw_transcript}\"")

            except Exception as e:
                logger.exception(f"[VOICE] Exception caught in main voice loop: {e}")
                self._recover_voice_pipeline_state()
                time.sleep(0.5)

            time.sleep(0.1)

    def _dispatch_command(self, command_text: str):
        clean_cmd = command_text.strip()
        if not clean_cmd:
            return

        logger.info(f"[VOICE] COMMAND_SENT_TO_ORCHESTRATOR: \"{clean_cmd}\"")
        self.session_manager.reset_activity_timer()
        self._update_state(AssistantState.PROCESSING)
        self.command_bus.submit(Command(source="voice", text=clean_cmd))

    def stop(self):
        self.is_running = False
        self.wake_detector.stop()
        self.session_manager.stop()
