from typing import Callable, Optional
from app.config.settings import settings
from app.core.logging_config import logger

class PermissionManager:
    def __init__(self, confirmation_callback: Optional[Callable[[str], bool]] = None):
        """
        confirmation_callback: A callable taking a prompt string (e.g. "Delete file X?")
        and returning True if confirmed by the user, False otherwise.
        """
        self.confirmation_callback = confirmation_callback

    def is_tool_dangerous(self, tool_name: str) -> bool:
        return tool_name in settings.dangerous_tools

    def request_permission(self, tool_name: str, args: dict) -> bool:
        """Check permission for dangerous tool execution."""
        if not self.is_tool_dangerous(tool_name):
            return True

        msg = f"Security Warning: The action '{tool_name}' with arguments {args} is marked as dangerous."
        logger.warning(msg)

        if self.confirmation_callback:
            prompt = f"Confirmation Required: Do you want to execute '{tool_name}' ({args})?"
            confirmed = self.confirmation_callback(prompt)
            if confirmed:
                logger.info(f"User APPROVED dangerous tool '{tool_name}'")
                return True
            else:
                logger.info(f"User REJECTED dangerous tool '{tool_name}'")
                return False

        # If no callback registered, reject dangerous operation by default
        logger.error(f"Dangerous operation '{tool_name}' blocked because no confirmation callback is set.")
        return False
