import sys
import os
import argparse
import threading
import time

# Ensure project directory is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.config import config
from app.core.logging_config import logger
from app.core.system_check import run_system_check
from app.core.command_bus import CommandBus
from app.core.assistant import AssistantOrchestrator
from app.core.hotkey import GlobalHotkeyListener
from app.core.shutdown_manager import ShutdownManager
from app.voice.microphone import MicrophoneStreamer

def run_text_mode(orchestrator: AssistantOrchestrator):
    """Interactive command-line interface for non-GUI / non-voice testing."""
    print("\n" + "=" * 60)
    print("  HP PERSONAL AI ASSISTANT FOR WINDOWS (TEXT MODE)")
    print("  Type your command below. Type 'exit' or 'quit' to stop.")
    print("=" * 60 + "\n")

    while True:
        try:
            cmd = input("User > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit"):
                print("Exiting HP. Goodbye!")
                break
            
            response = orchestrator.handle_command(cmd)
            print(f"HP > {response}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting HP.")
            break

def main():
    parser = argparse.ArgumentParser(description="HP Personal AI Assistant for Windows")
    parser.add_argument("--text-mode", action="store_true", help="Run interactive CLI text mode without GUI/voice")
    parser.add_argument("--no-gui", action="store_true", help="Run headless background assistant in system tray")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--voice-debug", action="store_true", help="Enable verbose voice pipeline telemetry logging")
    args = parser.parse_args()

    if args.debug:
        config.log_level = "DEBUG"
    if args.voice_debug:
        config.voice_debug = True
        logger.info("[VOICE DEBUG] Verbose voice pipeline telemetry logging enabled.")

    logger.info("Starting HP Personal AI Assistant...")

    # Log available microphones
    mics = MicrophoneStreamer.list_available_microphones()
    logger.info("=" * 50)
    logger.info("AVAILABLE AUDIO INPUT DEVICES (MICROPHONES):")
    for mic in mics:
        logger.info(f"  [{mic['index']}] {mic['name']} (Channels: {mic['channels']}, SampleRate: {mic['sample_rate']}Hz)")
    logger.info("=" * 50)

    check_res = run_system_check()
    if not check_res.is_all_ok:
        logger.warning("System check reported warnings/errors. Review startup log messages above.")

    command_bus = CommandBus()

    if args.text_mode:
        orchestrator = AssistantOrchestrator(text_mode=True, command_bus=command_bus)
        run_text_mode(orchestrator)
        sys.exit(0)

    try:
        from PySide6.QtWidgets import QApplication
        from app.gui.main_window import MainWindow
        from app.gui.tray import SystemTrayManager
        from app.gui.notifications import NotificationManager
        from app.voice.voice_pipeline import VoicePipeline

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        main_window = MainWindow()
        orchestrator = AssistantOrchestrator(gui_window=main_window, command_bus=command_bus)
        main_window.orchestrator = orchestrator

        tray_manager = SystemTrayManager()
        main_window.tray_icon_ref = tray_manager.tray_icon
        notification_mgr = NotificationManager(tray_manager.tray_icon)

        main_window.user_submitted_command.connect(orchestrator.process_command_async)
        tray_manager.toggle_window_signal.connect(
            lambda: main_window.showNormal() if main_window.isHidden() else main_window.hide()
        )
        tray_manager.go_online_signal.connect(lambda: orchestrator.session_manager.activate(reason="tray"))
        tray_manager.go_offline_signal.connect(lambda: orchestrator.session_manager.deactivate(reason="tray", announce=True))

        def on_global_hotkey_toggle():
            logger.info(f"[HOTKEY] Global hotkey toggle '{config.global_hotkey}' pressed!")
            orchestrator.session_manager.toggle_online_offline(reason="hotkey")

        voice_pipeline = VoicePipeline(
            command_bus=command_bus,
            speech_recognizer=orchestrator.speech_recognizer,
            session_manager=orchestrator.session_manager,
            is_speaking_callback=orchestrator.speech_manager.is_speaking,
            status_callback=orchestrator.update_status,
            speak_prompt_callback=orchestrator.speak_prompt
        )

        shutdown_mgr = ShutdownManager.get_instance(
            orchestrator=orchestrator,
            voice_pipeline=voice_pipeline,
            hotkey_listener=None,
            gui_app=app
        )

        hotkey_listener = GlobalHotkeyListener(
            hotkey_str=config.global_hotkey,
            deactivate_hotkey_str=config.deactivate_hotkey,
            callback=on_global_hotkey_toggle,
            deactivate_callback=lambda: shutdown_mgr.shutdown(reason="hotkey_f4", speak_farewell=True)
        )
        shutdown_mgr.hotkey_listener = hotkey_listener
        hotkey_listener.start()

        tray_manager.exit_app_signal.connect(lambda: shutdown_mgr.shutdown(reason="tray_exit", speak_farewell=False))
        app.aboutToQuit.connect(lambda: shutdown_mgr.shutdown(reason="app_quit", speak_farewell=False))

        if not args.no_gui:
            main_window.show()

        voice_pipeline.start()

        # Trigger automatic friendly startup greeting flow
        threading.Thread(target=lambda: (time.sleep(1.0), orchestrator.session_manager.start_startup_flow())[1], daemon=True).start()

        logger.info(f"HP Personal AI Assistant GUI Dashboard, Global Hotkey Toggle ({config.global_hotkey}) & Emergency Stop ({config.deactivate_hotkey}) running.")
        sys.exit(app.exec())

    except ImportError as ie:
        logger.error(f"PySide6 GUI unavailable ({ie}). Falling back to text mode...")
        orchestrator = AssistantOrchestrator(text_mode=True, command_bus=command_bus)
        run_text_mode(orchestrator)

if __name__ == "__main__":
    main()
