import time
from typing import Tuple, Dict, Any, Callable
from app.system.app_manager import ApplicationManager
from app.web.web_manager import WebManager
from app.core.logging_config import logger

class WorkflowManager:
    """Executes preset multi-step automation workflows."""

    def __init__(self, timer_callback: Callable[[int, str], None]):
        self.timer_callback = timer_callback

    def run_workflow(self, workflow_name: str) -> Tuple[bool, str]:
        name_clean = workflow_name.strip().lower()
        logger.info(f"Running multi-step workflow: '{name_clean}'")

        if "coding" in name_clean or "code" in name_clean:
            return self._coding_workflow()
        elif "dsa" in name_clean or "study" in name_clean:
            return self._dsa_study_workflow()
        else:
            return False, f"Unknown workflow preset '{workflow_name}'. Available: 'coding', 'dsa_study'."

    def _coding_workflow(self) -> Tuple[bool, str]:
        results = []
        # 1. Open VS Code
        ok1, msg1 = ApplicationManager.open_application("vscode")
        results.append(msg1)

        # 2. Launch Terminal
        ok2, msg2 = ApplicationManager.open_application("terminal")
        results.append(msg2)

        # 3. Launch Browser
        ok3, msg3 = ApplicationManager.open_application("chrome")
        results.append(msg3)

        return True, "Coding workspace prepared: VS Code, Terminal, and Browser launched."

    def _dsa_study_workflow(self) -> Tuple[bool, str]:
        results = []
        # 1. Open VS Code
        ApplicationManager.open_application("vscode")

        # 2. Open browser with DSA search
        WebManager.search_youtube("Java DSA Data Structures Algorithms tutorial")

        # 3. Start 90 minute timer
        if self.timer_callback:
            self.timer_callback(90, "DSA Study Session Complete!")

        return True, "90-minute DSA study session started. VS Code and YouTube tutorials are open."
