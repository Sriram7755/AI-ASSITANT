from typing import Callable, Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema parameter mapping
    handler: Callable
    is_dangerous: bool = False

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any], handler: Callable, is_dangerous: bool = False):
        """Register a tool with JSON schema specs."""
        self._tools[name] = ToolSpec(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            is_dangerous=is_dangerous
        )

    def get_tool(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Format tools for LLM system prompt."""
        result = []
        for name, spec in self._tools.items():
            result.append({
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
                "is_dangerous": spec.is_dangerous
            })
        return result

    def is_registered(self, name: str) -> bool:
        return name in self._tools

# Global tool registry singleton
tool_registry = ToolRegistry()
