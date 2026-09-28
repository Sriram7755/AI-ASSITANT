import sys
import psutil
import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QProgressBar, QTabWidget,
    QCheckBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont

from app.config.settings import settings
from app.system.startup import StartupManager
from app.core.config import config
from app.core.logging_config import logger
from app.gui.chat_widgets import (
    CyberAvatarWidget, CyberTerminalWidget, CyberTelemetryGraphWidget, WaveformVisualizer
)

class MainWindow(QMainWindow):
    """Futuristic Cyber Security Command Center Workstation for HP 2.0."""

    # Thread-Safe Qt Signals for cross-thread GUI updates
    user_submitted_command = Signal(str)
    toggle_listening_requested = Signal()
    stop_tts_requested = Signal()

    add_user_message_signal = Signal(str)
    add_tool_status_signal = Signal(str)
    stream_assistant_response_signal = Signal(str)
    update_status_signal = Signal(str)
    tts_speaking_signal = Signal(bool)

    tray_icon_ref = None

    def __init__(self, orchestrator=None):
        super().__init__()
        self.orchestrator = orchestrator
        self.active_assistant_bubble = None

        self.setWindowTitle("HP 2.0 — CYBER COMMAND CENTER WORKSTATION")
        self.resize(1100, 760)
        self.setMinimumSize(900, 620)

        self._apply_cyber_security_theme()
        self._init_ui()
        self._connect_signals()

        # Display cyber boot sequence on terminal initialization
        QTimer.singleShot(300, self._show_cyber_boot_sequence)

        # Update CPU/RAM usage & session countdown timer (every 1 second)
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self._update_system_metrics)
        self.metrics_timer.start(1000)

    def _connect_signals(self):
        """Connect thread-safe signals to GUI slots."""
        self.add_user_message_signal.connect(self._slot_add_user_message)
        self.add_tool_status_signal.connect(self._slot_add_tool_status)
        self.stream_assistant_response_signal.connect(self._slot_stream_assistant_response)
        self.update_status_signal.connect(self._slot_update_status)
        self.tts_speaking_signal.connect(self._slot_tts_speaking)

    def _apply_cyber_security_theme(self):
        """Apply ultra-dark Cyber Security Workstation stylesheet."""
        stylesheet = """
        QMainWindow {
            background-color: #030712;
        }
        QWidget {
            color: #cbd5e1;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
        }
        QFrame#HeaderFrame {
            background-color: #090d16;
            border-bottom: 1px solid #1e293b;
            padding: 8px 16px;
        }
        QLabel#TitleLabel {
            font-size: 18px;
            font-weight: bold;
            color: #00f2fe;
            letter-spacing: 2px;
        }
        QLabel#StatusBadge {
            background-color: #0f172a;
            color: #00f2fe;
            font-weight: bold;
            font-size: 12px;
            padding: 5px 14px;
            border-radius: 12px;
            border: 1px solid #00f2fe;
        }
        QLabel#CountdownBadge {
            background-color: #121827;
            color: #00f260;
            font-weight: bold;
            font-size: 12px;
            padding: 5px 14px;
            border-radius: 12px;
            border: 1px solid #00f260;
        }
        QFrame#TelemetryPanel {
            background-color: #060a13;
            border-right: 1px solid #1e293b;
            padding: 12px;
        }
        QFrame#TelemetryCard {
            background-color: #0d1322;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 8px;
        }
        QLineEdit#InputBox {
            background-color: #090d16;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 10px 14px;
            color: #00f2fe;
            font-size: 13px;
            font-family: 'Consolas', monospace;
        }
        QLineEdit#InputBox:focus {
            border: 1px solid #00f2fe;
        }
        QPushButton#ExecuteBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052d4, stop:1 #4364f7);
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-weight: bold;
            font-size: 12px;
        }
        QPushButton#ExecuteBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4364f7, stop:1 #6fb1fc);
        }
        QPushButton#MicButton {
            background-color: #0f172a;
            color: #00f2fe;
            border: 1px solid #00f2fe;
            border-radius: 8px;
            padding: 10px 16px;
            font-weight: bold;
        }
        QPushButton#MicButton:hover {
            background-color: #1e293b;
        }
        QPushButton#StopBtn {
            background-color: #ff0844;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: bold;
        }
        QPushButton#StopBtn:hover {
            background-color: #ff4d6d;
        }
        QProgressBar {
            border: 1px solid #1e293b;
            border-radius: 5px;
            text-align: center;
            background-color: #0f172a;
            color: #cbd5e1;
            font-weight: bold;
            font-size: 10px;
            height: 16px;
        }
        QProgressBar::chunk {
            background-color: #00f2fe;
            border-radius: 4px;
        }
        QTabWidget::pane {
            border: 1px solid #1e293b;
            background-color: #030712;
        }
        QTabBar::tab {
            background: #090d16;
            padding: 8px 20px;
            border: 1px solid #1e293b;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }
        QTabBar::tab:selected {
            background: #0d1322;
            color: #00f2fe;
            font-weight: bold;
        }
        """
        self.setStyleSheet(stylesheet)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Header Bar ---
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(header_frame)

        title_layout = QVBoxLayout()
        title_label = QLabel("HP 2.0 CYBER COMMAND CENTER")
        title_label.setObjectName("TitleLabel")
        title_layout.addWidget(title_label)

        sub_label = QLabel("HOTKEYS: [Ctrl+Shift+F3] ONLINE/OFFLINE  •  [Ctrl+Shift+F4] EMERGENCY STOP")
        sub_label.setStyleSheet("color: #64748b; font-size: 11px; font-family: 'Consolas', monospace;")
        title_layout.addWidget(sub_label)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        self.countdown_badge = QLabel("OFFLINE")
        self.countdown_badge.setObjectName("CountdownBadge")
        header_layout.addWidget(self.countdown_badge)

        self.status_badge = QLabel("OFFLINE")
        self.status_badge.setObjectName("StatusBadge")
        header_layout.addWidget(self.status_badge)

        self.stop_btn = QPushButton("⏹️ STOP")
        self.stop_btn.setObjectName("StopBtn")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        header_layout.addWidget(self.stop_btn)

        main_layout.addWidget(header_frame)

        # --- Main Tabs ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Workstation Command Console
        dash_widget = QWidget()
        dash_layout = QHBoxLayout(dash_widget)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_layout.setSpacing(0)

        # LEFT COLUMN: Telemetry & Main AI Core (300px)
        telemetry_frame = QFrame()
        telemetry_frame.setObjectName("TelemetryPanel")
        telemetry_frame.setFixedWidth(300)
        telemetry_layout = QVBoxLayout(telemetry_frame)
        telemetry_layout.setSpacing(10)

        # Giant Cyber Avatar Core (180x180 px)
        avatar_container = QHBoxLayout()
        avatar_container.addStretch()
        self.avatar_widget = CyberAvatarWidget()
        avatar_container.addWidget(self.avatar_widget)
        avatar_container.addStretch()
        telemetry_layout.addLayout(avatar_container)

        # 12-Bar Equalizer Visualizer
        wf_container = QHBoxLayout()
        wf_container.addStretch()
        self.waveform_widget = WaveformVisualizer()
        wf_container.addWidget(self.waveform_widget)
        wf_container.addStretch()
        telemetry_layout.addLayout(wf_container)

        # Live Telemetry Graphs
        self.cpu_graph = CyberTelemetryGraphWidget("CPU LOAD")
        telemetry_layout.addWidget(self.cpu_graph)

        self.ram_graph = CyberTelemetryGraphWidget("MEMORY USAGE")
        telemetry_layout.addWidget(self.ram_graph)

        # Battery Level Card
        battery_card = QFrame()
        battery_card.setObjectName("TelemetryCard")
        battery_layout = QVBoxLayout(battery_card)
        battery_layout.addWidget(QLabel("🔋 BATTERY POWER"))
        self.battery_bar = QProgressBar()
        self.battery_bar.setRange(0, 100)
        self.battery_bar.setValue(85)
        self.battery_bar.setStyleSheet("QProgressBar::chunk { background-color: #f6d365; }")
        battery_layout.addWidget(self.battery_bar)
        telemetry_layout.addWidget(battery_card)

        # System Services Card
        status_card = QFrame()
        status_card.setObjectName("TelemetryCard")
        status_card_layout = QVBoxLayout(status_card)
        status_card_layout.addWidget(QLabel("⚡ SYSTEM SERVICES"))
        self.service_info_label = QLabel("OLLAMA: READY  •  STT: READY\nTTS: ONLINE    •  DB: MEMORY")
        self.service_info_label.setStyleSheet("color: #00f260; font-size: 10px; font-family: 'Consolas', monospace;")
        status_card_layout.addWidget(self.service_info_label)
        telemetry_layout.addWidget(status_card)

        telemetry_layout.addStretch()
        dash_layout.addWidget(telemetry_frame)

        # RIGHT COLUMN: Live Terminal Log & Console Dock
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        # Live Terminal Panel (Replaces chat bubbles!)
        self.terminal_widget = CyberTerminalWidget()
        right_layout.addWidget(self.terminal_widget, stretch=1)

        # Command Console Dock
        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setObjectName("InputBox")
        self.input_box.setPlaceholderText("> awaiting command... (Press Ctrl+Shift+F3 or say 'Hey HP')")
        self.input_box.returnPressed.connect(self._on_send_clicked)
        input_layout.addWidget(self.input_box, stretch=1)

        self.send_btn = QPushButton("[EXECUTE]")
        self.send_btn.setObjectName("ExecuteBtn")
        self.send_btn.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.send_btn)

        self.mic_btn = QPushButton("[MIC: LISTENING]")
        self.mic_btn.setObjectName("MicButton")
        self.mic_btn.setCheckable(True)
        self.mic_btn.setChecked(True)
        self.mic_btn.clicked.connect(self._on_mic_toggled)
        input_layout.addWidget(self.mic_btn)

        right_layout.addLayout(input_layout)
        dash_layout.addWidget(right_container, stretch=1)

        self.tabs.addTab(dash_widget, "Cyber Command Console")

        # Tab 2: Settings
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(20, 20, 20, 20)

        self.startup_check = QCheckBox("Start Assistant automatically with Windows startup")
        self.startup_check.setChecked(StartupManager.is_startup_enabled())
        self.startup_check.toggled.connect(self._on_startup_toggled)
        settings_layout.addWidget(self.startup_check)

        self.memory_check = QCheckBox("Enable SQLite Long-Term Memory")
        self.memory_check.setChecked(settings.memory_enabled)
        settings_layout.addWidget(self.memory_check)

        settings_layout.addStretch()
        self.tabs.addTab(settings_widget, "Settings")

    def _show_cyber_boot_sequence(self):
        """Displays short cyber boot sequence on terminal startup."""
        self.terminal_widget.append_system_event("BOOT", "BOOT SEQUENCE INITIATED...", "#00f2fe")
        self.terminal_widget.append_system_event("SYSTEM", "INITIALIZING HP CORE...", "#00f2fe")
        self.terminal_widget.append_system_event("AUDIO", "LOADING AUDIO ENGINE & PYGAME MIXER...", "#00f260")
        self.terminal_widget.append_system_event("LLM", "CONNECTING LOCAL OLLAMA / QWEN 2.5...", "#f6d365")
        self.terminal_widget.append_system_event("MEMORY", "INITIALIZING SQLITE MEMORY DB...", "#b15eff")
        self.terminal_widget.append_system_event("HOTKEY", "REGISTERED CTRL+SHIFT+F3 & CTRL+SHIFT+F4", "#00f2fe")
        self.terminal_widget.append_system_event("STATUS", "HP CYBER CORE READY", "#00f260")

    @Slot()
    def _on_send_clicked(self):
        text = self.input_box.text().strip()
        if text:
            self.input_box.clear()
            self.terminal_widget.append_user_voice(text)
            if self.orchestrator:
                self.orchestrator.process_command_async(text)

    @Slot()
    def _on_mic_toggled(self):
        is_active = self.mic_btn.isChecked()
        self.mic_btn.setText("[MIC: LISTENING]" if is_active else "[MIC: MUTED]")
        self.toggle_listening_requested.emit()

    @Slot()
    def _on_stop_clicked(self):
        if self.orchestrator and hasattr(self.orchestrator, "speech_manager"):
            self.orchestrator.speech_manager.stop()
        elif self.orchestrator and hasattr(self.orchestrator, "tts"):
            self.orchestrator.tts.stop()
        self._slot_tts_speaking(False)
        self._slot_update_status("OFFLINE")

    @Slot(bool)
    def _on_startup_toggled(self, checked: bool):
        StartupManager.set_startup(checked)
        settings.startup_enabled = checked
        settings.save_user_config()

    @Slot(str)
    def _slot_add_user_message(self, text: str):
        self.terminal_widget.append_user_voice(text)

    @Slot(str)
    def _slot_add_tool_status(self, friendly_text: str):
        self.terminal_widget.append_tool_execution(friendly_text, "SUCCESS")

    @Slot(str)
    def _slot_stream_assistant_response(self, text: str):
        self.terminal_widget.append_ai_response(text)

    @Slot(str)
    def _slot_update_status(self, status: str):
        status_upper = status.upper()
        self.status_badge.setText(status_upper)
        self.avatar_widget.set_state(status_upper)
        self.terminal_widget.append_system_event("STATE", f"TRANSITION -> {status_upper}", "#00f2fe")

        colors = {
            "OFFLINE": ("#0f172a", "#64748b"),
            "ONLINE": ("#0f172a", "#00f2fe"),
            "ARMED": ("#0f172a", "#00f2fe"),
            "ACTIVE_SESSION": ("#0052d4", "#ffffff"),
            "IDLE": ("#0f172a", "#00f2fe"),
            "LISTENING": ("#0072ff", "#ffffff"),
            "THINKING": ("#f6d365", "#0f172a"),
            "PROCESSING": ("#f6d365", "#0f172a"),
            "EXECUTING": ("#b15eff", "#ffffff"),
            "SCREEN_ANALYZING": ("#7000ff", "#ffffff"),
            "SPEAKING": ("#00f260", "#0f172a"),
            "WAITING_FOR_CONFIRMATION": ("#0072ff", "#ffffff"),
            "SESSION_EXPIRY_CONFIRMATION": ("#ff8c00", "#ffffff"),
            "TIMEOUT": ("#334155", "#cbd5e1"),
            "ERROR": ("#ff0844", "#ffffff")
        }
        bg, fg = colors.get(status_upper, ("#0f172a", "#00f2fe"))
        self.status_badge.setStyleSheet(f"background-color: {bg}; color: {fg}; font-weight: bold; padding: 5px 14px; border-radius: 12px; border: 1px solid {fg};")

    @Slot(bool)
    def _slot_tts_speaking(self, is_speaking: bool):
        if is_speaking:
            self.waveform_widget.start_animation()
        else:
            self.waveform_widget.stop_animation()

    def append_chat(self, sender: str, text: str):
        if sender.upper() == "USER":
            self.terminal_widget.append_user_voice(text)
        else:
            self.terminal_widget.append_ai_response(text)

    def update_status(self, status: str):
        self._slot_update_status(status)

    def request_confirmation_dialog(self, prompt: str) -> bool:
        reply = QMessageBox.question(
            self,
            "Security Confirmation",
            prompt,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def _update_system_metrics(self):
        try:
            cpu = int(psutil.cpu_percent())
            ram = int(psutil.virtual_memory().percent)
            battery = psutil.sensors_battery()
            bat_val = int(battery.percent) if battery else 100

            self.cpu_graph.push_value(cpu)
            self.ram_graph.push_value(ram)
            self.battery_bar.setValue(bat_val)

            # Update live session countdown
            if self.orchestrator and hasattr(self.orchestrator, "session_manager"):
                rem_sec = int(self.orchestrator.session_manager.remaining_seconds())
                curr_st = self.orchestrator.session_manager.current_state.name
                
                if curr_st == "SESSION_EXPIRY_CONFIRMATION":
                    self.countdown_badge.setText("SESSION ENDING")
                    self.countdown_badge.setStyleSheet("background-color: #ff8c00; color: #ffffff; font-weight: bold; padding: 5px 14px; border-radius: 12px; border: 1px solid #ff8c00;")
                elif self.orchestrator.session_manager.is_session_active() and rem_sec > 0:
                    mins, secs = divmod(rem_sec, 60)
                    self.countdown_badge.setText(f"Session Active {mins:02d}:{secs:02d}")
                    self.countdown_badge.setStyleSheet("background-color: #121827; color: #00f260; font-weight: bold; padding: 5px 14px; border-radius: 12px; border: 1px solid #00f260;")
                else:
                    self.countdown_badge.setText(curr_st)
                    self.countdown_badge.setStyleSheet("background-color: #0f172a; color: #64748b; font-weight: bold; padding: 5px 14px; border-radius: 12px; border: 1px solid #334155;")
        except Exception:
            pass

    def closeEvent(self, event):
        if self.tray_icon_ref and self.tray_icon_ref.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()
