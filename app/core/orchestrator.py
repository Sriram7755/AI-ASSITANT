import threading
from typing import Optional, Tuple, Dict, Any, List
from app.config.settings import settings
from app.core.logging_config import logger
from app.ai.llm_client import LLMClient
from app.memory.memory_manager import MemoryManager
from app.memory.conversation import ConversationManager
from app.tools.registry import tool_registry
from app.tools.permissions import PermissionManager
from app.tools.executor import ToolExecutor
from app.system.system_manager import SystemManager
from app.system.app_manager import ApplicationManager
from app.system.file_manager import FileManager
from app.web.web_manager import WebManager
from app.automation.scheduler import SchedulerManager
from app.automation.workflows import WorkflowManager
from app.audio.speech_recognizer import SpeechRecognizer
from app.audio.tts_manager import TTSManager

class AssistantOrchestrator:
    """Central orchestrator managing intent routing, multi-step actions, memory, and TTS."""

    def __init__(self, gui_window=None, text_mode: bool = False):
        self.gui_window = gui_window
        self.text_mode = text_mode

        # Core Components
        self.llm_client = LLMClient()
        self.memory_manager = MemoryManager()
        self.conversation = ConversationManager()
        self.permission_manager = PermissionManager(
            confirmation_callback=self._get_confirmation
        )
        self.tool_executor = ToolExecutor(self.permission_manager)

        self.scheduler = SchedulerManager(
            memory_manager=self.memory_manager,
            notify_callback=self._on_scheduler_alert
        )
        self.workflow_manager = WorkflowManager(
            timer_callback=self.scheduler.set_timer
        )

        self.tts = TTSManager()
        self.speech_recognizer = SpeechRecognizer() if not text_mode else None

        self._register_all_tools()
        logger.info("AssistantOrchestrator initialized with all tools registered.")

    def _get_confirmation(self, prompt: str) -> bool:
        if self.gui_window and hasattr(self.gui_window, "request_confirmation_dialog"):
            return self.gui_window.request_confirmation_dialog(prompt)
        # CLI fallback for text-mode
        print(f"\n[SECURITY CONFIRMATION REQUIRED]\n{prompt}")
        ans = input("Allow execution? (y/N): ").strip().lower()
        return ans in ("y", "yes")

    def _on_scheduler_alert(self, message: str):
        logger.info(f"Scheduler Alert: {message}")
        if self.gui_window and hasattr(self.gui_window, "append_chat_signal"):
            self.gui_window.append_chat_signal.emit("JARVIS Alert", message, "ASSISTANT")
        self.tts.speak(message)

    def update_status(self, status: str):
        if self.gui_window and hasattr(self.gui_window, "update_status_signal"):
            self.gui_window.update_status_signal.emit(status)

    def process_command_async(self, user_command: str):
        """Run command processing in background thread to keep GUI responsive."""
        threading.Thread(target=self.handle_command, args=(user_command,), daemon=True).start()

    def handle_command(self, user_command: str) -> str:
        """Main pipeline: user input -> LLM -> Sequential Actions / Response -> TTS."""
        if not user_command or not user_command.strip():
            return ""

        clean_cmd = user_command.strip()
        lower_cmd = clean_cmd.lower()
        for wake_phrase in ("hey jarvis", "jarvis"):
            if lower_cmd.startswith(wake_phrase):
                clean_cmd = clean_cmd[len(wake_phrase):].strip().lstrip(",").strip()
                break

        if not clean_cmd:
            clean_cmd = user_command.strip()

        logger.info(f"Processing user command: '{clean_cmd}'")
        self.update_status("PROCESSING")

        if self.gui_window and hasattr(self.gui_window, "add_user_message_signal"):
            self.gui_window.add_user_message_signal.emit(clean_cmd)

        self.conversation.add_user_message(clean_cmd)

        # 1. Fetch memory context
        memory_items = self.memory_manager.retrieve_memory(clean_cmd)
        memory_ctx = "\n".join([f"- {m['key']}: {m['value']}" for m in memory_items[:3]]) if memory_items else ""

        # 2. LLM Intent & Action Sequence Selection
        intent = self.llm_client.process_user_input(
            user_input=clean_cmd,
            conversation_context=self.conversation.get_prior_context_formatted(exclude_last_n=1),
            memory_context=memory_ctx
        )

        actions = intent.get("actions", [])
        if not actions and intent.get("tool"):
            actions = [{"tool": intent["tool"], "arguments": intent.get("arguments", {})}]

        response_text = ""

        # 3. Sequential Execution of Actions
        if actions:
            self.update_status("EXECUTING")
            results = []
            failed_step = None

            for idx, action in enumerate(actions, 1):
                tool_name = action.get("tool")
                args = action.get("arguments", {})
                if not tool_name or not tool_registry.is_registered(tool_name):
                    continue

                friendly_tool_msg = self._get_friendly_tool_status(tool_name, args)
                if len(actions) > 1:
                    step_msg = f"Step {idx}/{len(actions)}: {friendly_tool_msg}"
                else:
                    step_msg = friendly_tool_msg

                if self.gui_window and hasattr(self.gui_window, "add_tool_status_signal"):
                    self.gui_window.add_tool_status_signal.emit(step_msg)

                success, result_msg = self.tool_executor.execute(tool_name, args)
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
            response_text = intent.get("response", "I am listening. How can I help you?")

        # 4. Save assistant response
        self.conversation.add_assistant_message(response_text)
        logger.info(f"JARVIS Response: '{response_text}'")

        if self.gui_window and hasattr(self.gui_window, "stream_assistant_response_signal"):
            self.gui_window.stream_assistant_response_signal.emit(response_text)

        # 5. Speak response with GUI sync
        self.update_status("SPEAKING")
        if self.gui_window and hasattr(self.gui_window, "tts_speaking_signal"):
            self.gui_window.tts_speaking_signal.emit(True)

        def _on_tts_finished():
            if self.gui_window and hasattr(self.gui_window, "tts_speaking_signal"):
                self.gui_window.tts_speaking_signal.emit(False)
            self.update_status("IDLE")

        self.tts.speak(response_text, on_finish=_on_tts_finished)

        return response_text

    def _get_friendly_tool_status(self, tool_name: str, args: dict) -> str:
        """Format human-friendly tool execution status message."""
        if tool_name == "open_application":
            app = args.get("application", "app").title()
            return f"Opening {app}..."
        elif tool_name == "close_application":
            app = args.get("application", "app").title()
            return f"Closing {app}..."
        elif tool_name == "find_and_open_folder":
            folder = args.get("name", "folder").title()
            return f"Looking for your {folder} folder..."
        elif tool_name == "get_cpu_usage":
            return "Checking CPU usage..."
        elif tool_name == "get_memory_usage":
            return "Checking RAM memory usage..."
        elif tool_name == "get_battery_status":
            return "Checking battery level..."
        elif tool_name == "get_disk_usage":
            return "Checking disk storage..."
        elif tool_name == "get_system_information":
            return "Checking system specifications..."
        elif tool_name == "take_screenshot":
            return "Capturing desktop screenshot..."
        elif tool_name == "read_clipboard":
            return "Reading clipboard..."
        elif tool_name == "search_web":
            q = args.get("query", "")
            return f"Searching Google for '{q}'..." if q else "Opening Google Search..."
        elif tool_name == "search_youtube":
            q = args.get("query", "")
            return f"Searching YouTube for '{q}'..." if q else "Opening YouTube..."
        elif tool_name == "search_files":
            q = args.get("query", "")
            return f"Searching files matching '{q}'..."
        elif tool_name == "remember":
            return "Saving memory..."
        elif tool_name == "retrieve_memory":
            return "Searching stored memories..."
        elif tool_name == "set_timer":
            m = args.get("minutes", 0)
            return f"Setting a {m}-minute timer..."
        elif tool_name == "set_reminder":
            return "Scheduling reminder..."
        elif tool_name == "run_preset_workflow":
            wf = args.get("workflow_name", "").title()
            return f"Preparing workflow '{wf}'..."
        return f"Executing {tool_name}..."

    def _register_all_tools(self):
        """Register all laptop control, web, file, memory, scheduling, and workflow tools."""

        # Application tools
        tool_registry.register(
            name="open_application",
            description="Open an installed desktop application (e.g. chrome, vscode, notepad, spotify, terminal).",
            parameters={
                "type": "object",
                "properties": {"application": {"type": "string"}},
                "required": ["application"]
            },
            handler=ApplicationManager.open_application
        )
        tool_registry.register(
            name="close_application",
            description="Close a running application.",
            parameters={
                "type": "object",
                "properties": {"application": {"type": "string"}},
                "required": ["application"]
            },
            handler=ApplicationManager.close_application
        )

        # System Metrics & Power
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
            name="read_clipboard",
            description="Read text stored in the clipboard.",
            parameters={"type": "object", "properties": {}},
            handler=SystemManager.read_clipboard
        )

        # Dangerous Power Tools
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

        # Web Tools
        tool_registry.register(
            name="search_web",
            description="Search Google for a query.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            },
            handler=WebManager.search_web
        )
        tool_registry.register(
            name="search_youtube",
            description="Search YouTube for videos.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            },
            handler=WebManager.search_youtube
        )

        # File Tools
        tool_registry.register(
            name="search_files",
            description="Search for files by name query and optional extension.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "extension": {"type": "string"}
                },
                "required": ["query"]
            },
            handler=FileManager.search_files
        )
        tool_registry.register(
            name="find_recent_files",
            description="Find recently modified files in Downloads or Documents.",
            parameters={
                "type": "object",
                "properties": {"days": {"type": "integer"}}
            },
            handler=FileManager.find_recent_files
        )
        tool_registry.register(
            name="open_file",
            description="Open a file with default application.",
            parameters={
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"]
            },
            handler=FileManager.open_file
        )
        tool_registry.register(
            name="open_folder",
            description="Open a folder in Windows File Explorer.",
            parameters={
                "type": "object",
                "properties": {"folder_path": {"type": "string"}},
                "required": ["folder_path"]
            },
            handler=FileManager.open_folder
        )
        tool_registry.register(
            name="find_and_open_folder",
            description="Find and open a folder or directory by name in safe user locations.",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            },
            handler=FileManager.find_and_open_folder
        )

        # Memory Tools
        tool_registry.register(
            name="remember",
            description="Remember a fact, preference, or path for long-term storage.",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"}
                },
                "required": ["key", "value"]
            },
            handler=self.memory_manager.remember
        )
        tool_registry.register(
            name="retrieve_memory",
            description="Recall stored facts or memories.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            },
            handler=lambda query: f"Memories found: {self.memory_manager.retrieve_memory(query)}"
        )

        # Automation & Scheduling Tools
        tool_registry.register(
            name="set_timer",
            description="Set a countdown timer in minutes.",
            parameters={
                "type": "object",
                "properties": {
                    "minutes": {"type": "integer"},
                    "label": {"type": "string"}
                },
                "required": ["minutes"]
            },
            handler=self.scheduler.set_timer
        )
        tool_registry.register(
            name="set_reminder",
            description="Set a reminder for a specific time.",
            parameters={
                "type": "object",
                "properties": {
                    "time_str": {"type": "string"},
                    "message": {"type": "string"}
                },
                "required": ["time_str", "message"]
            },
            handler=self.scheduler.set_reminder
        )
        tool_registry.register(
            name="run_preset_workflow",
            description="Run preset automation workflow e.g. 'coding' or 'dsa_study'.",
            parameters={
                "type": "object",
                "properties": {"workflow_name": {"type": "string"}},
                "required": ["workflow_name"]
            },
            handler=self.workflow_manager.run_workflow
        )
