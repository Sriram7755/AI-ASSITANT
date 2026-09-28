from typing import List, Dict, Any

class ConversationManager:
    """Manages short-term conversation context with bounded window size."""

    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.history: List[Dict[str, str]] = []

    def add_user_message(self, content: str):
        self.history.append({"role": "user", "content": content})
        self._trim_history()

    def add_assistant_message(self, content: str):
        self.history.append({"role": "assistant", "content": content})
        self._trim_history()

    def get_history(self) -> List[Dict[str, str]]:
        return self.history

    def get_context_formatted(self) -> str:
        """Format full history for LLM prompt context."""
        lines = []
        for msg in self.history[-self.max_history:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def get_prior_context_formatted(self, exclude_last_n: int = 1) -> str:
        """Format prior conversation history excluding the current user turn."""
        slice_history = self.history[:-exclude_last_n] if (exclude_last_n > 0 and len(self.history) >= exclude_last_n) else self.history
        lines = []
        for msg in slice_history[-self.max_history:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def _trim_history(self):
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]

    def clear(self):
        self.history.clear()
