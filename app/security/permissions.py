from typing import Callable, Optional
from app.core.logging_config import logger

class PermissionManager:
    """Security gatekeeper requiring user confirmation before executing dangerous tools."""

    DANGEROUS_TOOLS = {
        "shutdown_computer",
        "restart_computer",
        "shutdown",
        "restart",
        "delete_file",
        "delete_folder"
    }

    def __init__(self, confirmation_callback: Optional[Callable[[str], bool]] = None):
        self.confirmation_callback = confirmation_callback

    def is_tool_dangerous(self, tool_name: str) -> bool:
        return tool_name in self.DANGEROUS_TOOLS

    def is_action_allowed(self, tool_name: str, arguments: dict) -> bool:
        if not self.is_tool_dangerous(tool_name):
            return True

        prompt_msg = f"Confirmation Required: Are you sure you want to execute '{tool_name}' with parameters {arguments}?"
        logger.warning(f"[SECURITY CHECK] Dangerous tool requested: '{tool_name}'")

        if self.confirmation_callback:
            allowed = self.confirmation_callback(prompt_msg)
            if allowed:
                logger.info(f"[SECURITY APPROVED] Action '{tool_name}' permitted by user.")
                return True
            else:
                logger.warning(f"[SECURITY BLOCKED] Action '{tool_name}' rejected by user.")
                return False

        logger.warning(f"[SECURITY BLOCKED] No confirmation callback set. Denying '{tool_name}'.")
        return False
