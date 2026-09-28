import json
import re
import requests
from typing import Dict, Any, Optional
from app.core.config import config
from app.core.logging_config import logger

class OllamaClient:
    """Ollama REST API client abstraction layer."""

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = host or config.ollama_host
        self.model = model or config.llm_model

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 256
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                return res.json().get("response", "").strip()
            else:
                logger.error(f"Ollama HTTP error {res.status_code}: {res.text}")
                return f"Local AI engine error (HTTP {res.status_code})."
        except requests.exceptions.ConnectionError:
            msg = "Your local AI engine (Ollama) is currently unavailable. Please make sure Ollama is running."
            logger.error(msg)
            return msg
        except Exception as e:
            msg = f"LLM generation failed: {e}"
            logger.error(msg)
            return msg
