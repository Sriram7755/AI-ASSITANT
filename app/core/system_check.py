import sys
import os
import requests
import sounddevice as sd
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple
from app.config.settings import settings
from app.core.logging_config import logger

@dataclass
class SystemCheckResult:
    python_ok: bool
    ollama_ok: bool
    qwen_model_ok: bool
    audio_input_ok: bool
    audio_output_ok: bool
    whisper_ok: bool
    tts_ok: bool
    storage_ok: bool
    messages: List[str]

    @property
    def is_all_ok(self) -> bool:
        return (
            self.python_ok
            and self.ollama_ok
            and self.qwen_model_ok
            and self.storage_ok
        )

def run_system_check() -> SystemCheckResult:
    messages = []
    
    # 1. Python version check
    python_ver = sys.version_info
    python_ok = python_ver >= (3, 10)
    if python_ok:
        messages.append(f"[OK] Python version: {sys.version.split()[0]}")
    else:
        messages.append(f"[ERROR] Python 3.10+ required. Current: {sys.version.split()[0]}")

    # 2. Ollama & Qwen check
    ollama_ok = False
    qwen_model_ok = False
    try:
        res = requests.get(f"{settings.ollama_host}/api/tags", timeout=3)
        if res.status_code == 200:
            ollama_ok = True
            messages.append(f"[OK] Ollama server active at {settings.ollama_host}")
            models = [m.get("name") for m in res.json().get("models", [])]
            if any(settings.llm_model in m for m in models):
                qwen_model_ok = True
                messages.append(f"[OK] LLM Model '{settings.llm_model}' available in Ollama")
            else:
                messages.append(
                    f"[WARNING] Model '{settings.llm_model}' not found in Ollama. Available: {models}. Run: 'ollama pull {settings.llm_model}'"
                )
        else:
            messages.append(f"[ERROR] Ollama returned status {res.status_code}")
    except Exception as e:
        messages.append(f"[ERROR] Cannot connect to Ollama at {settings.ollama_host}: {e}")

    # 3. Audio Input (Microphone) Check
    audio_input_ok = False
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]
        if input_devices:
            audio_input_ok = True
            messages.append(f"[OK] Audio input device found: {input_devices[0]['name']}")
        else:
            messages.append("[WARNING] No audio input (microphone) devices found.")
    except Exception as e:
        messages.append(f"[WARNING] Audio device check failed: {e}")

    # 4. Audio Output (Speakers) Check
    audio_output_ok = False
    try:
        devices = sd.query_devices()
        output_devices = [d for d in devices if d.get("max_output_channels", 0) > 0]
        if output_devices:
            audio_output_ok = True
            messages.append(f"[OK] Audio output device found: {output_devices[0]['name']}")
        else:
            messages.append("[WARNING] No audio output devices found.")
    except Exception as e:
        messages.append(f"[WARNING] Speaker check failed: {e}")

    # 5. Whisper STT package check
    whisper_ok = False
    try:
        import faster_whisper
        whisper_ok = True
        messages.append(f"[OK] Speech-to-Text engine (faster-whisper) ready for '{settings.whisper_model}'")
    except ImportError:
        messages.append("[WARNING] faster-whisper package not installed. Text-mode available.")

    # 6. Edge TTS check
    tts_ok = False
    try:
        import edge_tts
        tts_ok = True
        messages.append(f"[OK] Edge-TTS engine ready with voice '{settings.tts_voice}'")
    except ImportError:
        messages.append("[WARNING] edge-tts package not installed. Text responses only.")

    # 7. Storage / Directory check
    storage_ok = True
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        messages.append(f"[OK] Data & Log directories created: {settings.data_dir}")
    except Exception as e:
        storage_ok = False
        messages.append(f"[ERROR] Directory creation failed: {e}")

    for msg in messages:
        logger.info(msg)

    return SystemCheckResult(
        python_ok=python_ok,
        ollama_ok=ollama_ok,
        qwen_model_ok=qwen_model_ok,
        audio_input_ok=audio_input_ok,
        audio_output_ok=audio_output_ok,
        whisper_ok=whisper_ok,
        tts_ok=tts_ok,
        storage_ok=storage_ok,
        messages=messages
    )
