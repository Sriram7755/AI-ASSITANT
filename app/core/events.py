import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class Action:
    tool: str
    arguments: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Command:
    source: str  # "voice" or "text"
    text: str
    timestamp: float = field(default_factory=time.time)
    conversation_id: Optional[str] = None

@dataclass
class Response:
    command: Command
    actions: List[Action]
    response_text: str
    success: bool = True
    error_message: Optional[str] = None
