# HP 2.0: Real-Time Personal AI Laptop Agent for Windows

A production-quality, local-first, privacy-focused stateful personal AI agent built for Windows, designed for **Sriram**. Runs completely on CPU with lightweight local models, local SQLite long-term memory, dual activation mechanisms (`Ctrl+Shift+F3` global toggle & voice wake-words), a friendly time-aware startup greeting with 10s confirmation window, a futuristic computer startup sound chime, an active 10-minute (600-second) conversational session manager with proactive 30s expiry warnings, emergency shutdown hotkey (`Ctrl+Shift+F4`), on-demand screen perception, laptop volume & brightness controls, browser tab management, system time/date queries, an ultra-modern Cyberpunk Holographic HUD Dashboard GUI, background system tray execution, and structured tool allowlist security.

---

## 🌟 Key Features

1. **Persistent Stateful AI Agent**:
   - **Dual Activation & Hotkey Toggle**:
     - **Global Hotkey Toggle (`Ctrl + Shift + F3`)**: Press `Ctrl + Shift + F3` anytime to toggle between `ONLINE` and `OFFLINE` system-wide.
       - When `OFFLINE`: Pressing `Ctrl + Shift + F3` transitions to `ONLINE` and speaks *"I'm online, Sriram. What can I do for you?"*.
       - When `ONLINE`: Pressing `Ctrl + Shift + F3` transitions to `OFFLINE` and speaks *"Going offline."*.
     - **Voice Wake-Word Activation**: Saying *"Hey HP"*, *"Hello HP"*, *"Hi HP"*, *"HP"* wakes HP (`OFFLINE` → `ONLINE`) and speaks *"Yes?"*.
   - **Time-Aware Startup Greeting**: On launch, HP evaluates local time to speak a natural greeting:
     - Morning: *"Good morning, Sriram. Welcome back. Ready to make some progress today?"*
     - Afternoon: *"Good afternoon, Sriram. Welcome back. Let's get something productive done."*
     - Evening: *"Good evening, Sriram. Welcome back. Ready to get things done?"*
     - Night: *"Good night, Sriram. You're still working? Let's make it count."*
     - Followed by: *"Would you like me to stay online?"* (`WAITING_FOR_CONFIRMATION` for 10s post-TTS).
   - **Futuristic Computer Startup Chime**: Confirming YES plays a 3.5-second futuristic hardware/cyberpunk power-up sound before speaking *"I'm online, Sriram. What can I do for you?"*.
   - **Active 10-Minute Session Window (600s)**: Consecutively process natural commands (*"Open Chrome"*, *"Open a new tab"*, *"Search YouTube for Java"*, *"What's on my screen?"*, *"Who are you?"*) without repeating wake words before every command.
   - **Proactive 30-Second Expiry Warning & Natural Extension**:
     - At 30s before session expiry, HP asks: *"We've been idle for a while. Would you like me to stay online?"*.
     - Responding *"Yes"*, *"Continue"*, *"Stay online"*, *"Keep going"* extends the session by another 10 minutes (**10:00**).
     - Responding *"No"*, *"Stop"*, *"Go offline"* deactivates the session (`ONLINE` → `OFFLINE`).
   - **Emergency Application Shutdown Hotkey (`Ctrl + Shift + F4`)**:
     - Instantly stops active microphone listening, STT, TTS playback, scheduler, hotkey threads, and GUI, speaks *"Alright, Sriram. I'm shutting down. Keep going — you've got this."*, and cleanly exits the application with **zero background process leakage**.
2. **Natural Conversational AI & System Clock Routing**:
   - Time & Date queries (*"What time is it?"*, *"What date is it?"*) use Windows local system clock directly (*"It's 6:56 PM."* / *"Today is Saturday, August 15, 2026."*).
   - Conversational & knowledge questions (*"Who are you?"*, *"Who is Sriram?"*, *"Tell me a joke"*, *"How are you?"*, *"What is Python?"*) produce natural responses aloud directly via Ollama LLM. **NEVER** opens Chrome or launches web search unnecessarily.
   - Web search tools (`search_web`, `search_youtube`) are **ONLY** used when explicitly requested (*"Search Google for..."*, *"Search YouTube for..."*).
3. **Computer & Browser Control Tools**:
   - Browser navigation tools: `browser_new_tab` (`Ctrl+T`), `browser_close_tab` (`Ctrl+W`), `browser_next_tab` (`Ctrl+Tab`), `browser_previous_tab` (`Ctrl+Shift+Tab`), `browser_back` (`Alt+Left`), `browser_forward` (`Alt+Right`), `browser_refresh` (`Ctrl+R`), `scroll_down`, `scroll_up`.
   - Laptop controls: `system_volume_up`, `system_volume_down`, `system_mute`, `system_brightness_up`, `system_brightness_down`, `lock_pc`, `mute_microphone` (confirmation required), `turn_camera_off` (confirmation required), `toggle_backlight`.
4. **Screen Perception & Visual Item Interaction**:
   - Captures active desktop screen on demand (*"What is on my screen?"*, *"Read this error"*).
   - Spoken response focuses purely on visual content (*"You have File Explorer open, showing your ML folder."*).
   - **NEVER** speaks technical metadata (screenshot path, timestamp, "Screen captured on demand at...") aloud.
   - Relative UI requests (*"Open the first document on the screen"*) route to dedicated `open_screen_item` tool.
5. **Serialized Command Execution Queue**:
   - Thread-safe command queue in `AssistantOrchestrator` ensuring commands execute sequentially without race conditions or overlapping responses.
6. **Local AI Brain**: Powered locally by Ollama with `qwen2.5:1.5b`. No API key required for core operations.
7. **CPU-First Speech Recognition**: Faster-Whisper (`small.en` int8 on CPU) with optimal decoding parameters and low-confidence artifact filtering.
8. **Python-Native PyGame Audio Playback**: High-quality Microsoft Edge TTS voice synthesis (`en-US-ChristopherNeural`) played natively via `pygame.mixer`. No PowerShell dependencies, zero event loop locks.
9. **Ultra-Modern Cyberpunk Holographic HUD Dashboard**:
    - **160px Holographic ARC Reactor Core Avatar (`JarvisAvatarWidget`)**: Concentric rotating/pulsing neon arcs with dynamic state reactions (`OFFLINE`, `ONLINE`, `WAITING_FOR_CONFIRMATION`, `SESSION_EXPIRY_CONFIRMATION`, `THINKING`, `EXECUTING`, `SPEAKING`).
    - **Live Session Countdown Timer**: Real-time session countdown badge (`Session Active 09:59`, `09:58`...).
    - **12-Bar Cyberpunk Audio Equalizer (`WaveformVisualizer`)**: Animated gradient audio bars (`#00f260` → `#00f2fe`).
    - **Live Hardware Telemetry Cards**: Real-time CPU, RAM memory, and battery level monitoring cards.
10. **Anti-Self-Feedback Protection**: Microphone recording automatically pauses while HP is speaking and enforces a **0.8-second post-speech cooldown** before resuming wake-word listening.
11. **Structured Tool Security**: LLM produces structured JSON tool requests. **NEVER** executes arbitrary shell commands. Allowlist security with confirmation prompts for dangerous operations (e.g. shutdown, restart, file deletion).
12. **SQLite Long-Term Memory**: Store facts, preferences, paths, and recall them anytime (`data/memory.db`).
13. **APScheduler Reminders**: Timers, reminders, and scheduled alerts with system notifications and voice prompts.

---

## 🏗️ State Machine Flowchart

```text
[Windows CMD Launch: python run.py]
            │
            ▼
 ( WAITING_FOR_CONFIRMATION ) ── 10s Timeout / "No" ──► ( OFFLINE ) ◄── (Ctrl+Shift+F4 / Exit)
            │                                               ▲
            │ "Yes" / "Stay online"                         │
            ▼                                               │
       ( ONLINE ) ◄── Timeout (600s) / "No" / Timeout ──────┤
   (Resets 600s timer on user command)                      │
   (Triggers warning at <= 30s)                             │
            │                                               │
            ▼                                               │
 ( SESSION_EXPIRY_CONFIRMATION ) ───────────────────────────┘
```

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+
- **LLM**: Ollama (`qwen2.5:1.5b`)
- **STT**: `faster-whisper` (`small.en` on CPU `int8`)
- **TTS & Audio**: `edge-tts` (`en-US-ChristopherNeural`), `pygame.mixer`
- **GUI**: PySide6 (Qt) with Custom Holographic QPainter Widgets
- **Database**: SQLite3 (`data/memory.db`)
- **Scheduler**: APScheduler
- **Metrics & Perception**: `psutil`, `sounddevice`, `PIL` (ImageGrab), `numpy`, `scipy`

---

## 🚀 Quick Setup & Installation

### 1. Prerequisites
- **Windows 10/11**
- **Python 3.10 or later**
- **Ollama**: Download and install [Ollama for Windows](https://ollama.com).
- Pull the model:
  ```powershell
  ollama pull qwen2.5:1.5b
  ```

### 2. Install Dependencies
```powershell
cd d:\AI_Assistant
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🎮 How to Run

### GUI Cyberpunk HUD Mode (Default)
Launches the PySide6 Holographic HUD Dashboard, Global Hotkeys (`Ctrl+Shift+F3` & `Ctrl+Shift+F4`), and Windows system tray icon:
```powershell
python run.py
```

### Verbose Voice Diagnostic Mode
Enable verbose voice pipeline telemetry logging:
```powershell
python run.py --voice-debug
```

### Interactive Text Mode (CLI Testing)
Test AI intent classification, laptop tools, folder search, memory, and scheduling without microphone input:
```powershell
python run.py --text-mode
```

---

## 🛠️ Interactive Session Commands & Examples

1. **Activate via Hotkey**: Press `Ctrl + Shift + F3` → HP speaks *"I'm online, Sriram. What can I do for you?"* and starts a 10-minute active session (**10:00**). Press again to go offline.
2. **Emergency Application Shutdown**: Press `Ctrl + Shift + F4` → HP speaks *"Alright, Sriram. I'm shutting down. Keep going — you've got this."* and terminates cleanly.
3. **Conversational Queries (No Browser Opening)**:
   - *"What time is it?"* → *"It's 6:56 PM."*
   - *"What date is it?"* → *"Today is Saturday, August 15, 2026."*
   - *"Who are you?"* → Conversational response aloud.
   - *"Who is Sriram?"* → HP identifies Sriram as an ambitious engineering student in AI, machine learning, deep learning, computer vision, Java, Python, Spring Boot, FastAPI, React, and AI agents.
   - *"Tell me a joke."* → Tells a joke aloud.
   - *"What is Python?"* → Explains Python.
4. **Laptop Controls & Browser Multi-Command Stream**:
   - *"Open Chrome."*
   - *"Open a new tab."*
   - *"Search YouTube for Java DSA."*
   - *"Switch to next tab."*
   - *"Turn up the volume."*
   - *"Increase brightness."*
   - *"Lock my PC."*
   - *"What is on my screen?"* → Speaks natural screen description.
5. **Proactive Expiry Warning & Extension**:
   - At 30s remaining: *"We've been idle for a while. Would you like me to stay online?"*.
   - User says *"Yes"* → Timer resets to **10:00** and speaks *"Sure. I'm staying with you."*.
6. **Deactivate Session**:
   - Say *"Go offline"*, *"Stop"*, *"Shutdown"* → HP speaks *"Going offline."* and returns to `OFFLINE`.

---

## 🧪 Running Automated Tests

Run the full test suite with `pytest`:
```powershell
pytest -o pythonpath=.
```

---

## 🛡️ Security & Privacy

- **Allowlist Only**: The LLM cannot execute shell scripts or Python code directly. It can only emit pre-defined JSON tool signatures.
- **Dangerous Action Gatekeeping**: Destructive tools (shutdown computer, restart computer, delete file, mute microphone, turn camera off) trigger a mandatory UI/CLI confirmation dialog.
- **Offline First**: Speech transcription, intent parsing, memory storage, folder search, screen perception, and system monitoring run 100% locally on your machine.
