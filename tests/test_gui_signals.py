import sys
import pytest
from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow
from app.gui.chat_widgets import ChatBubbleWidget, JarvisAvatarWidget, WaveformVisualizer

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

def test_chat_bubble_widget_creation(qapp):
    user_bubble = ChatBubbleWidget("USER", "Hello Jarvis")
    assert user_bubble.sender == "USER"
    assert user_bubble.text_label.text() == "Hello Jarvis"

    jarvis_bubble = ChatBubbleWidget("JARVIS", "Hello! How can I help?")
    assert jarvis_bubble.sender == "JARVIS"
    assert jarvis_bubble.text_label.text() == "Hello! How can I help?"

    jarvis_bubble.update_text("Hello! How can I help you today?")
    assert jarvis_bubble.text_label.text() == "Hello! How can I help you today?"

def test_jarvis_avatar_widget(qapp):
    avatar = JarvisAvatarWidget()
    assert avatar.state == "IDLE"
    avatar.set_state("LISTENING")
    assert avatar.state == "LISTENING"
    avatar.set_state("EXECUTING")
    assert avatar.state == "EXECUTING"

def test_waveform_visualizer(qapp):
    wave = WaveformVisualizer()
    assert wave.is_animating is False
    wave.start_animation()
    assert wave.is_animating is True
    wave.stop_animation()
    assert wave.is_animating is False

def test_main_window_signals(qapp):
    win = MainWindow()
    assert win.status_badge.text() in ("IDLE", "OFFLINE")

    # Emit user message signal
    win.add_user_message_signal.emit("Open Chrome")
    qapp.processEvents()

    # Emit tool status signal
    win.add_tool_status_signal.emit("Opening Chrome...")
    qapp.processEvents()

    # Emit assistant response signal
    win.stream_assistant_response_signal.emit("Sure! Opening Chrome for you.")
    qapp.processEvents()
    assert win.active_assistant_bubble.text_label.text() == "Sure! Opening Chrome for you."

    # Update status signal
    win.update_status_signal.emit("SPEAKING")
    qapp.processEvents()
    assert win.status_badge.text() == "SPEAKING"
    assert win.avatar_widget.state == "SPEAKING"

    win.update_status_signal.emit("IDLE")
    qapp.processEvents()
    assert win.status_badge.text() == "IDLE"
    assert win.avatar_widget.state == "IDLE"
