from typing import Dict, Any, Tuple
from app.tools.registry import tool_registry, ToolSpec
from app.tools.permissions import PermissionManager
from app.core.logging_config import logger

class ToolExecutor:
    def __init__(self, permission_manager: PermissionManager):
        self.permission_manager = permission_manager

    def execute(self, tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates and executes a tool from the ToolRegistry.
        Returns (success: bool, result_message: str).
        """
        if not tool_registry.is_registered(tool_name):
            msg = f"Unknown tool request: '{tool_name}' is not registered."
            logger.warning(msg)
            return False, msg

        tool_spec: ToolSpec = tool_registry.get_tool(tool_name)

        # 1. Validate arguments against parameter schema
        validation_ok, val_err = self._validate_args(tool_spec, args)
        if not validation_ok:
            logger.warning(f"Tool argument validation failed for '{tool_name}': {val_err}")
            return False, f"Invalid arguments for tool '{tool_name}': {val_err}"

        # 2. Permission / Confirmation check
        if tool_spec.is_dangerous or self.permission_manager.is_tool_dangerous(tool_name):
            if not self.permission_manager.request_permission(tool_name, args):
                return False, f"Execution of dangerous tool '{tool_name}' was cancelled by the user."

        # 3. Safe execution
        try:
            logger.info(f"Executing tool '{tool_name}' with args {args}")
            result = tool_spec.handler(**args)
            if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], bool):
                return result
            return True, str(result)
        except TypeError as te:
            err_msg = f"Parameter mismatch for tool '{tool_name}': {te}"
            logger.error(err_msg)
            return False, err_msg
        except Exception as e:
            err_msg = f"Error while running tool '{tool_name}': {e}"
            logger.error(err_msg, exc_info=True)
            return False, err_msg

    def _validate_args(self, tool_spec: ToolSpec, args: Dict[str, Any]) -> Tuple[bool, str]:
        expected_params = tool_spec.parameters.get("properties", {})
        required_params = tool_spec.parameters.get("required", [])

        for req in required_params:
            if req not in args:
                return False, f"Missing required parameter '{req}'"

        return True, ""
