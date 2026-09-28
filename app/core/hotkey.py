import threading
import time
import ctypes
from ctypes import wintypes
from typing import Callable, Optional
from app.core.logging_config import logger

try:
    import keyboard
    KEYBOARD_LIB_AVAILABLE = True
except ImportError:
    KEYBOARD_LIB_AVAILABLE = False

class GlobalHotkeyListener:
    """Reliable Windows global keyboard shortcut listener for activation (Ctrl+Shift+F3) and deactivation (Ctrl+Shift+F4)."""

    def __init__(
        self,
        hotkey_str: str = "ctrl+shift+f3",
        deactivate_hotkey_str: str = "ctrl+shift+f4",
        callback: Optional[Callable[[], None]] = None,
        deactivate_callback: Optional[Callable[[], None]] = None
    ):
        self.hotkey_str = hotkey_str.lower()
        self.deactivate_hotkey_str = deactivate_hotkey_str.lower()
        self.callback = callback
        self.deactivate_callback = deactivate_callback

        self.is_running = False
        self._last_act_time = 0.0
        self._last_deact_time = 0.0
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True

        if KEYBOARD_LIB_AVAILABLE:
            try:
                keyboard.add_hotkey(self.hotkey_str, self._on_activation_hotkey)
                keyboard.add_hotkey(self.deactivate_hotkey_str, self._on_deactivation_hotkey)
                logger.info(f"[HOTKEY] Registered global activation '{self.hotkey_str}' and deactivation '{self.deactivate_hotkey_str}'.")
                return
            except Exception as e:
                logger.debug(f"Keyboard module hotkey registration fallback: {e}")

        # Fallback to Win32 RegisterHotKey API thread
        self._thread = threading.Thread(target=self._run_win32_hotkey_loop, daemon=True)
        self._thread.start()
        logger.info(f"[HOTKEY] Registered global hotkeys via Win32 RegisterHotKey API thread.")

    def _on_activation_hotkey(self):
        now = time.time()
        if now - self._last_act_time < 0.8:
            logger.debug(f"[HOTKEY] Debouncing rapid press of '{self.hotkey_str}'.")
            return
        self._last_act_time = now

        logger.info(f"[HOTKEY] Global activation shortcut '{self.hotkey_str}' pressed!")
        if self.callback:
            try:
                self.callback()
            except Exception as e:
                logger.error(f"Error executing activation hotkey callback: {e}")

    def _on_deactivation_hotkey(self):
        now = time.time()
        if now - self._last_deact_time < 0.8:
            logger.debug(f"[HOTKEY] Debouncing rapid press of '{self.deactivate_hotkey_str}'.")
            return
        self._last_deact_time = now

        logger.info(f"[HOTKEY] Global deactivation shortcut '{self.deactivate_hotkey_str}' pressed!")
        if self.deactivate_callback:
            try:
                self.deactivate_callback()
            except Exception as e:
                logger.error(f"Error executing deactivation hotkey callback: {e}")

    def _run_win32_hotkey_loop(self):
        """Win32 RegisterHotKey API event loop for Windows."""
        try:
            user32 = ctypes.windll.user32
            MOD_CONTROL = 0x0002
            MOD_SHIFT = 0x0004
            VK_F3 = 0x72
            VK_F4 = 0x73
            HOTKEY_ACT_ID = 9999
            HOTKEY_DEACT_ID = 9998

            modifiers = MOD_CONTROL | MOD_SHIFT
            user32.RegisterHotKey(None, HOTKEY_ACT_ID, modifiers, VK_F3)
            user32.RegisterHotKey(None, HOTKEY_DEACT_ID, modifiers, VK_F4)

            msg = wintypes.MSG()
            while self.is_running:
                if user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == 0x0312:  # WM_HOTKEY
                        if msg.wParam == HOTKEY_ACT_ID:
                            self._on_activation_hotkey()
                        elif msg.wParam == HOTKEY_DEACT_ID:
                            self._on_deactivation_hotkey()
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.01)

            user32.UnregisterHotKey(None, HOTKEY_ACT_ID)
            user32.UnregisterHotKey(None, HOTKEY_DEACT_ID)
        except Exception as e:
            logger.debug(f"Win32 hotkey loop exited: {e}")

    def stop(self):
        self.is_running = False
        if KEYBOARD_LIB_AVAILABLE:
            try:
                keyboard.remove_hotkey(self.hotkey_str)
                keyboard.remove_hotkey(self.deactivate_hotkey_str)
            except Exception:
                pass
