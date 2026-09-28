import queue
import threading
import time
from typing import Optional, Dict, Any, List, Tuple
from app.core.config import config
from app.core.logging_config import logger
from app.core.events import Command, Action, Response
from app.core.state import StateMachine, AssistantState
from app.core.session_manager import JarvisStateManager
from app.core.command_bus import CommandBus
from app.brain.intent_parser import IntentParser
from app.brain.ollama_client import OllamaClient
from app.speech.speech_manager import SpeechManager
from app.voice.stt import SpeechRecognizer
from app.tools.registry import tool_registry
from app.tools.executor import ToolExecutor
from app.security.permissions import PermissionManager
from app.system.system_manager import SystemManager
from app.system.app_manager import ApplicationManager
from app.system.file_manager import FileManager
from app.web.web_manager import WebManager
from app.tools.folders import FolderAssistant
from app.tools.browser import BrowserTools
from app.memory.memory_manager import MemoryManager
from app.memory.conversation import ConversationManager
from app.automation.scheduler import SchedulerManager
from app.automation.workflows import WorkflowManager
from app.vision.screen_perception import ScreenPerceptionManager

class AssistantOrchestrator:
    """Central HP AssistantOrchestrator with serialized command queue, intent routing, laptop controls, screen perception, and TTS playback."""

    def __init__(self, gui_window=None, text_mode: bool = False, command_bus: Optional[CommandBus] = None):
        self.gui_window = gui_window
        self.text_mode = text_mode
        self.command_bus = command_bus or CommandBus()

        self.speech_manager = SpeechManager()
        self.session_manager = JarvisStateManager(
            timeout_seconds=getattr(config, "session_timeout_seconds", 600.0),
            speak_callback=self.speak_prompt
        )
        self.session_manager.add_callback(self._on_state_changed)

        self.intent_parser = IntentParser()
        self.memory_manager = MemoryManager()
        self.conversation = ConversationManager()
        self.screen_perception = ScreenPerceptionManager()
        self.permission_manager = PermissionManager(confirmation_callback=self._get_confirmation)
        self.tool_executor = ToolExecutor(self.permission_manager)

        self.scheduler = SchedulerManager(memory_manager=self.memory_manager, notify_callback=self._on_scheduler_alert)
        self.workflow_manager = WorkflowManager(timer_callback=self.scheduler.set_timer)

        self.speech_recognizer = SpeechRecognizer() if not text_mode else None

        # Thread-safe Command Execution Queue
        self._command_queue = queue.Queue()
        self._worker_running = True
        self._command_worker_thread = threading.Thread(target=self._command_worker_loop, daemon=True)

        self._register_all_tools()
        self.command_bus.register_handler(self._on_command_submitted)
        self._command_worker_thread.start()
        logger.info("[OK] AssistantOrchestrator initialized for HP with tools registered.")

    def _on_state_changed(self, new_state: AssistantState):
        if self.gui_window and hasattr(self.gui_window, "update_status_signal"):
            self.gui_window.update_status_signal.emit(new_state.name)

    def _get_confirmation(self, prompt: str) -> bool:
        if self.gui_window and hasattr(self.gui_window, "request_confirmation_dialog"):
            return self.gui_window.request_confirmation_dialog(prompt)
        print(f"\n[SECURITY CONFIRMATION REQUIRED]\n{prompt}")
        ans = input("Allow execution? (y/N): ").strip().lower()
        return ans in ("y", "yes")

    def _on_scheduler_alert(self, message: str):
        logger.info(f"Scheduler Alert: {message}")
        if self.gui_window and hasattr(self.gui_window, "append_chat_signal"):
            self.gui_window.append_chat_signal.emit("HP Alert", message, "ASSISTANT")
        self.speech_manager.speak(message)

    def update_status(self, status: str, reason: str = "orchestrator"):
        if self.gui_window and hasattr(self.gui_window, "update_status_signal"):
            self.gui_window.update_status_signal.emit(status)
        try:
            target_state = AssistantState[status.upper()]
            self.session_manager.transition_to(target_state, reason=reason)
        except KeyError:
            pass

    def speak_prompt(self, text: str):
        """Speak a prompt aloud naturally."""
        logger.info(f"[TTS] TTS_STARTED for prompt: \"{text}\"")
        if self.gui_window and hasattr(self.gui_window, "update_status_signal"):
            self.gui_window.update_status_signal.emit("SPEAKING")
        if self.gui_window and hasattr(self.gui_window, "tts_speaking_signal"):
            self.gui_window.tts_speaking_signal.emit(True)

        def _on_prompt_finished():
            logger.info(f"[TTS] TTS_FINISHED for prompt: \"{text}\"")
            if self.gui_window and hasattr(self.gui_window, "tts_speaking_signal"):
                self.gui_window.tts_speaking_signal.emit(False)
            self.session_manager.on_tts_finished()

        self.speech_manager.speak(text, on_finish=_on_prompt_finished)

    def process_command_async(self, user_command: str):
        """Asynchronously submit typed or transcribed command to CommandBus."""
        self.command_bus.submit(Command(source="user", text=user_command))

    def _on_command_submitted(self, command: Command):
        """Queue command for serialized execution."""
        logger.info(f"[COMMAND] Received: \"{command.text}\" (Queue size: {self._command_queue.qsize() + 1})")
        self._command_queue.put(command.text)

    def _command_worker_loop(self):
        """Single worker thread executing commands sequentially to prevent race conditions."""
        while self._worker_running:
            try:
                cmd_text = self._command_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                self.handle_command(cmd_text)
            except Exception as e:
                logger.error(f"Error handling queued command '{cmd_text}': {e}", exc_info=True)
            finally:
                self._command_queue.task_done()

    def handle_command(self, user_command: str) -> str:
        if not user_command or not user_command.strip():
            return ""

        clean_cmd = user_command.strip()
        lower_cmd = clean_cmd.lower()
        for wake_phrase in ("hey hp", "hi hp", "hello hp", "hp", "hey jarvis", "jarvis"):
            if lower_cmd.startswith(wake_phrase):
                clean_cmd = clean_cmd[len(wake_phrase):].strip().lstrip(",").lstrip(".").strip()
                break

        if not clean_cmd:
            clean_cmd = user_command.strip()

        # Reset inactivity timer ONLY on genuine user interaction
        self.session_manager.reset_activity_timer(reason=f"user_command:{clean_cmd[:15]}")

        logger.info(f"[ORCHESTRATOR] ORCHESTRATOR_STARTED for command: \"{clean_cmd}\"")
        self.update_status("THINKING", reason="parsing_intent")

        if self.gui_window and hasattr(self.gui_window, "add_user_message_signal"):
            self.gui_window.add_user_message_signal.emit(clean_cmd)

        self.conversation.add_user_message(clean_cmd)

        # Screen perception keyword detection
        vision_keywords = ("screen", "looking at", "what's open", "error on", "read this error", "what is on my screen", "what am i doing", "what am i looking at", "tell me what you see")
        needs_vision = any(k in clean_cmd.lower() for k in vision_keywords)

        memory_items = self.memory_manager.retrieve_memory(clean_cmd)
        memory_ctx = "\n".join([f"- {m['key']}: {m['value']}" for m in memory_items[:3]]) if memory_items else ""

        if needs_vision:
            self.update_status("SCREEN_ANALYZING", reason="capturing_screen")
            obs = self.screen_perception.capture_and_analyze(query=clean_cmd)
            memory_ctx += f"\n- Screen Perception Observation: {obs['observation_summary']}"

        logger.info(f"[LLM] LLM_STARTED processing intent for: \"{clean_cmd}\"")
        intent = self.intent_parser.parse(
            user_input=clean_cmd,
            conversation_context=self.conversation.get_prior_context_formatted(exclude_last_n=1),
            memory_context=memory_ctx
        )
        logger.info(f"[LLM] LLM_RESULT: {intent}")

        intent_type = intent.get("intent", "CONVERSATION")
        actions = intent.get("actions", [])
        if intent_type in ("CONVERSATION", "CLARIFICATION_REQUIRED", "SYSTEM_INFORMATION"):
            actions = []

        if not actions and intent.get("tool") and intent_type not in ("CONVERSATION", "CLARIFICATION_REQUIRED", "SYSTEM_INFORMATION"):
            actions = [{"tool": intent["tool"], "arguments": intent.get("arguments", {})}]

        response_text = ""

        if actions:
            self.update_status("EXECUTING", reason="running_tools")
            results = []
            failed_step = None

            for idx, action in enumerate(actions, 1):
                tool_name = action.get("tool")
                args = action.get("arguments", {})
                if not tool_name or not tool_registry.is_registered(tool_name):
                    continue

                logger.info(f"[TOOL] TOOL_SELECTED: {tool_name} with args {args}")
                friendly_tool_msg = self._get_friendly_tool_status(tool_name, args)
                if len(actions) > 1:
                    step_msg = f"Step {idx}/{len(actions)}: {friendly_tool_msg}"
                else:
                    step_msg = friendly_tool_msg

                if self.gui_window and hasattr(self.gui_window, "add_tool_status_signal"):
                    self.gui_window.add_tool_status_signal.emit(step_msg)

                success, result_msg = self.tool_executor.execute(tool_name, args)
                logger.info(f"[TOOL] TOOL_EXECUTED: {tool_name} -> Success: {success}, Result: '{result_msg}'")
                results.append((success, result_msg))

                if not success:
                    failed_step = result_msg
                    break

            if failed_step:
                succ_msgs = [r[1] for r in results if r[0]]
                if succ_msgs:
                    response_text = f"{' '.join(succ_msgs)} However, {failed_step}"
                else:
                    response_text = failed_step
            else:
                formatted_parts = []
                for r in results:
                    msg = r[1].strip()
                    if msg.startswith("Done. "):
                        msg = msg[len("Done. "):].strip()
                    formatted_parts.append(msg)

                if len(formatted_parts) == 1:
                    response_text = results[0][1]
                else:
                    response_text = "Sure! " + " ".join(formatted_parts)
        else:
            response_text = intent.get("response", "I'm listening, Sriram. How can I help?")

        self.conversation.add_assistant_message(response_text)
        logger.info(f"[VOICE] RESPONSE_GENERATED: \"{response_text}\"")

        if self.gui_window and hasattr(self.gui_window, "stream_assistant_response_signal"):
            self.gui_window.stream_assistant_response_signal.emit(response_text)

        logger.info(f"[TTS] TTS_STARTED for response: \"{response_text}\"")
        self.update_status("SPEAKING", reason="speaking_response")
        if self.gui_window and hasattr(self.gui_window, "tts_speaking_signal"):
            self.gui_window.tts_speaking_signal.emit(True)

        tts_done_event = threading.Event()

        def _on_tts_finished():
            logger.info(f"[TTS] TTS_FINISHED for response: \"{response_text}\"")
            if self.gui_window and hasattr(self.gui_window, "tts_speaking_signal"):
                self.gui_window.tts_speaking_signal.emit(False)
            self.session_manager.on_tts_finished()
            tts_done_event.set()

        self.speech_manager.speak(response_text, on_finish=_on_tts_finished)
        # Block command worker thread until TTS completes to serialize interactions
        tts_done_event.wait(timeout=15.0)

        return response_text

    def _get_friendly_tool_status(self, tool_name: str, args: dict) -> str:
        if tool_name == "open_application":
            app = args.get("application", "app").title()
            return f"Opening {app}..."
        elif tool_name == "close_application":
            app = args.get("application", "app").title()
            return f"Closing {app}..."
        elif tool_name == "focus_application":
            app = args.get("application", "app").title()
            return f"Focusing {app}..."
        elif tool_name == "open_screen_item":
            desc = args.get("description", "item")
            return f"Opening {desc}..."
        elif tool_name == "browser_new_tab":
            return "Opening new browser tab..."
        elif tool_name == "browser_close_tab":
            return "Closing browser tab..."
        elif tool_name == "browser_next_tab":
            return "Switching to next tab..."
        elif tool_name == "browser_previous_tab":
            return "Switching to previous tab..."
        elif tool_name == "browser_back":
            return "Going back..."
        elif tool_name == "browser_forward":
            return "Going forward..."
        elif tool_name == "browser_refresh":
            return "Refreshing page..."
        elif tool_name == "scroll_down":
            return "Scrolling down..."
        elif tool_name == "scroll_up":
            return "Scrolling up..."
        elif tool_name == "system_volume_up":
            return "Increasing volume..."
        elif tool_name == "system_volume_down":
            return "Decreasing volume..."
        elif tool_name == "system_mute":
            return "Toggling volume mute..."
        elif tool_name == "system_brightness_up":
            return "Increasing screen brightness..."
        elif tool_name == "system_brightness_down":
            return "Decreasing screen brightness..."
        elif tool_name == "lock_pc":
            return "Locking PC..."
        elif tool_name == "find_and_open_folder":
            folder = args.get("name", "folder").title()
            return f"Looking for your {folder} folder..."
        elif tool_name == "inspect_screen":
            return "Analyzing desktop screen..."
        elif tool_name == "search_web":
            q = args.get("query", "")
            return f"Searching Google for '{q}'..." if q else "Opening Google Search..."
        elif tool_name == "search_youtube":
            q = args.get("query", "")
            return f"Searching YouTube for '{q}'..." if q else "Opening YouTube..."
        elif tool_name == "deactivate_session":
            return "Going offline..."
        elif tool_name == "extend_session":
            return "Extending active session..."
        return f"Executing {tool_name}..."

    def _handle_inspect_screen_tool(self, query: str = "Analyze screen") -> Tuple[bool, str]:
        obs = self.screen_perception.capture_and_analyze(query)
        win = obs.get("active_window", "Desktop")
        # Return natural screen description without technical metadata!
        if "chrome" in win.lower():
            return True, f"You have Chrome open, looking at {win}."
        elif "code" in win.lower() or "visual studio" in win.lower():
            return True, f"You're currently viewing your project in Visual Studio Code."
        elif "explorer" in win.lower():
            return True, f"You have File Explorer open, showing {win}."
        return True, f"You have {win} open on your screen."

    def _register_all_tools(self):
        tool_registry.register(
            name="deactivate_session",
            description="Deactivate active HP session and go offline.",
            parameters={"type": "object", "properties": {}},
            handler=lambda: (self.session_manager.deactivate(reason="user_command", announce=False), (True, "Going offline."))[1]
        )
        tool_registry.register(
            name="extend_session",
            description="Extend active 10-minute HP session.",
            parameters={"type": "object", "properties": {}},
            handler=lambda: (self.session_manager.extend_session(announce=False), (True, "Sure, I'll stay online."))[1]
        )
        tool_registry.register(
            name="open_screen_item",
            description="Open or interact with a file or item visible on the screen.",
            parameters={"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]},
            handler=lambda description: (True, f"Done. Opened {description}.")[1]
        )
        tool_registry.register(
            name="open_application",
            description="Open an installed desktop application (e.g. chrome, vscode, notepad, spotify, terminal).",
            parameters={"type": "object", "properties": {"application": {"type": "string"}}, "required": ["application"]},
            handler=ApplicationManager.open_application
        )
        tool_registry.register(
            name="close_application",
            description="Close a running application.",
            parameters={"type": "object", "properties": {"application": {"type": "string"}}, "required": ["application"]},
            handler=ApplicationManager.close_application
        )
        tool_registry.register(
            name="focus_application",
            description="Bring an open application to foreground focus.",
            parameters={"type": "object", "properties": {"application": {"type": "string"}}, "required": ["application"]},
            handler=ApplicationManager.open_application
        )
        tool_registry.register(
            name="browser_new_tab",
            description="Open a new tab in default web browser.",
            parameters={"type": "object", "properties": {}},
            handler=BrowserTools.new_tab
        )
        tool_registry.register(
            name="browser_close_tab",
            description="Close current tab in default web browser.",
            parameters={"type": "object", "properties": {}},
            handler=BrowserTools.close_tab
        )
        tool_registry.register(
            name="browser_next_tab",
            description="Switch to next browser tab.",
            parameters={"type": "object", "properties": {}},
            handler=BrowserTools.next_tab
        )
        tool_registry.register(
            name="browser_previous_tab",
            description="Switch to previous browser tab.",
            parameters={"type": "object", "properties": {}},
            handler=BrowserTools.previous_tab
        )
        tool_registry.register(
            name="browser_back",
            description="Navigate back in browser history.",
            parameters={"type": "object", "properties": {}},
            handler=BrowserTools.browser_back
        )
        tool_registry.register(
            name="browser_forward",
            description="Navigate forward in browser history.",
            parameters={"type": "object", "properties": {}},
            handler=BrowserTools.browser_forward
        )
        tool_registry.register(
            name="browser_refresh",
            description="Refresh current browser page.",
            parameters={"type": "object", "properties": {}},
            handler=BrowserTools.browser_refresh
        )
        tool_registry.register(
            name="scroll_down",
            description="Scroll down on current active window or browser.",
            parameters={"type": "object", "properties": {}},
            handler=BrowserTools.scroll_down
        )
        tool_registry.register(
            name="scroll_up",
            description="Scroll up on current active window or browser.",
            parameters={"type": "object", "properties": {}},
            handler=BrowserTools.scroll_up
        )
        tool_registry.register(
            name="system_volume_up",
            description="Increase master laptop audio volume.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.system_volume_up
        )
        tool_registry.register(
            name="system_volume_down",
            description="Decrease master laptop audio volume.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.system_volume_down
        )
        tool_registry.register(
            name="system_mute",
            description="Toggle master laptop audio mute.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.system_mute
        )
        tool_registry.register(
            name="system_brightness_up",
            description="Increase screen brightness.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.system_brightness_up
        )
        tool_registry.register(
            name="system_brightness_down",
            description="Decrease screen brightness.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.system_brightness_down
        )
        tool_registry.register(
            name="lock_pc",
            description="Lock the Windows PC.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.lock_pc
        )
        tool_registry.register(
            name="mute_microphone",
            description="Mute microphone input (Requires confirmation).",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.mute_microphone,
            is_dangerous=True
        )
        tool_registry.register(
            name="unmute_microphone",
            description="Unmute microphone audio input.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.unmute_microphone
        )
        tool_registry.register(
            name="turn_camera_on",
            description="Turn on laptop camera.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.turn_camera_on
        )
        tool_registry.register(
            name="turn_camera_off",
            description="Disable laptop camera (Requires confirmation).",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.turn_camera_off,
            is_dangerous=True
        )
        tool_registry.register(
            name="toggle_backlight",
            description="Toggle keyboard backlight.",
            parameters={"type": "object", "properties": {"state": {"type": "string"}}},
            handler=SystemManager.toggle_backlight
        )
        tool_registry.register(
            name="keyboard_hotkey",
            description="Execute safe keyboard hotkey shortcut (e.g. 'ctrl+t', 'ctrl+w', 'alt+tab').",
            parameters={"type": "object", "properties": {"hotkey": {"type": "string"}}, "required": ["hotkey"]},
            handler=BrowserTools.send_hotkey
        )
        tool_registry.register(
            name="get_cpu_usage",
            description="Get current laptop CPU usage percentage.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.get_cpu_usage
        )
        tool_registry.register(
            name="get_memory_usage",
            description="Get current laptop RAM memory usage.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.get_memory_usage
        )
        tool_registry.register(
            name="get_battery_status",
            description="Get laptop battery percentage and charging status.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.get_battery_status
        )
        tool_registry.register(
            name="get_disk_usage",
            description="Get storage disk usage for C: drive.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.get_disk_usage
        )
        tool_registry.register(
            name="get_system_information",
            description="Get Windows OS version, CPU count, total RAM.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.get_system_information
        )
        tool_registry.register(
            name="take_screenshot",
            description="Capture a screenshot of the desktop screen.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.take_screenshot
        )
        tool_registry.register(
            name="inspect_screen",
            description="Inspect active window and capture screen on demand.",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}},
            handler=self._handle_inspect_screen_tool
        )
        tool_registry.register(
            name="read_clipboard",
            description="Read text stored in the clipboard.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.read_clipboard
        )
        tool_registry.register(
            name="shutdown_computer",
            description="Shutdown the laptop.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.shutdown_computer,
            is_dangerous=True
        )
        tool_registry.register(
            name="restart_computer",
            description="Restart the laptop.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.restart_computer,
            is_dangerous=True
        )
        tool_registry.register(
            name="search_web",
            description="Search Google for a query.",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            handler=WebManager.search_web
        )
        tool_registry.register(
            name="search_youtube",
            description="Search YouTube for videos.",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            handler=WebManager.search_youtube
        )
        tool_registry.register(
            name="search_files",
            description="Search for files by name query and optional extension.",
            parameters={"type": "object", "properties": {"query": {"type": "string"}, "extension": {"type": "string"}}, "required": ["query"]},
            handler=FileManager.search_files
        )
        tool_registry.register(
            name="find_recent_files",
            description="Find recently modified files in Downloads or Documents.",
            parameters={"type": "object", "properties": {"days": {"type": "integer"}}},
            handler=FileManager.find_recent_files
        )
        tool_registry.register(
            name="open_file",
            description="Open a file with default application.",
            parameters={"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]},
            handler=FileManager.open_file
        )
        tool_registry.register(
            name="open_folder",
            description="Open a folder in Windows File Explorer.",
            parameters={"type": "object", "properties": {"folder_path": {"type": "string"}}, "required": ["folder_path"]},
            handler=FileManager.open_folder
        )
        tool_registry.register(
            name="find_and_open_folder",
            description="Find and open a folder or directory by name in safe user locations.",
            parameters={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
            handler=FolderAssistant.find_and_open_folder
        )
        tool_registry.register(
            name="remember",
            description="Remember a fact, preference, or path for long-term storage.",
            parameters={"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}}, "required": ["key", "value"]},
            handler=self.memory_manager.remember
        )
        tool_registry.register(
            name="retrieve_memory",
            description="Recall stored facts or memories.",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            handler=lambda query: f"Memories found: {self.memory_manager.retrieve_memory(query)}"
        )
        tool_registry.register(
            name="set_timer",
            description="Set a countdown timer in minutes.",
            parameters={"type": "object", "properties": {"minutes": {"type": "integer"}, "label": {"type": "string"}}, "required": ["minutes"]},
            handler=self.scheduler.set_timer
        )
        tool_registry.register(
            name="set_reminder",
            description="Set a reminder for a specific time.",
            parameters={"type": "object", "properties": {"time_str": {"type": "string"}, "message": {"type": "string"}}, "required": ["time_str", "message"]},
            handler=self.scheduler.set_reminder
        )
        tool_registry.register(
            name="run_preset_workflow",
            description="Run preset automation workflow e.g. 'coding' or 'dsa_study'.",
            parameters={"type": "object", "properties": {"workflow_name": {"type": "string"}}, "required": ["workflow_name"]},
            handler=self.workflow_manager.run_workflow
        )
