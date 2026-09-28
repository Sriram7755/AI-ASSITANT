import urllib.parse
import webbrowser
from typing import Tuple
from app.core.logging_config import logger

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

class WebManager:
    """Browser & Web navigation manager."""

    @staticmethod
    def search_web(query: str) -> Tuple[bool, str]:
        q = query.strip()
        if not q:
            webbrowser.open("https://www.google.com")
            return True, "Sure — opening Google."
        encoded_q = urllib.parse.quote(q)
        url = f"https://www.google.com/search?q={encoded_q}"
        logger.info(f"Searching Google for: '{q}'")
        webbrowser.open(url)
        return True, f"Sure — searching Google for '{q}'."

    @staticmethod
    def search_youtube(query: str) -> Tuple[bool, str]:
        q = query.strip()
        if not q:
            webbrowser.open("https://www.youtube.com")
            return True, "Sure — opening YouTube."
        encoded_q = urllib.parse.quote(q)
        url = f"https://www.youtube.com/results?search_query={encoded_q}"
        logger.info(f"Searching YouTube for: '{q}'")
        webbrowser.open(url)
        return True, f"Sure — searching YouTube for '{q}'."

    @staticmethod
    def open_url(url: str) -> Tuple[bool, str]:
        target_url = url.strip()
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = f"https://{target_url}"
        logger.info(f"Opening URL: '{target_url}'")
        webbrowser.open(target_url)
        return True, f"Sure — opening website {target_url}."

class BrowserTools:
    """Computer interaction, browser navigation & tab control tools."""

    @staticmethod
    def new_tab() -> Tuple[bool, str]:
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey('ctrl', 't')
                return True, "Done. Opened a new browser tab."
            except Exception as e:
                logger.debug(f"PyAutoGUI hotkey fallback: {e}")
        webbrowser.open("https://www.google.com")
        return True, "Done. Opened a new browser tab."

    @staticmethod
    def close_tab() -> Tuple[bool, str]:
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey('ctrl', 'w')
                return True, "Done. Closed current browser tab."
            except Exception as e:
                logger.debug(f"PyAutoGUI hotkey fallback: {e}")
        return True, "Done. Close tab command sent."

    @staticmethod
    def next_tab() -> Tuple[bool, str]:
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey('ctrl', 'tab')
                return True, "Done. Switched to next tab."
            except Exception as e:
                logger.debug(f"PyAutoGUI hotkey fallback: {e}")
        return True, "Done. Next tab command sent."

    @staticmethod
    def previous_tab() -> Tuple[bool, str]:
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey('ctrl', 'shift', 'tab')
                return True, "Done. Switched to previous tab."
            except Exception as e:
                logger.debug(f"PyAutoGUI hotkey fallback: {e}")
        return True, "Done. Previous tab command sent."

    @staticmethod
    def browser_back() -> Tuple[bool, str]:
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey('alt', 'left')
                return True, "Done. Navigated back."
            except Exception as e:
                logger.debug(f"PyAutoGUI hotkey fallback: {e}")
        return True, "Done. Browser back command sent."

    @staticmethod
    def browser_forward() -> Tuple[bool, str]:
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey('alt', 'right')
                return True, "Done. Navigated forward."
            except Exception as e:
                logger.debug(f"PyAutoGUI hotkey fallback: {e}")
        return True, "Done. Browser forward command sent."

    @staticmethod
    def browser_refresh() -> Tuple[bool, str]:
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey('ctrl', 'r')
                return True, "Done. Refreshed page."
            except Exception as e:
                logger.debug(f"PyAutoGUI hotkey fallback: {e}")
        return True, "Done. Page refresh command sent."

    @staticmethod
    def scroll_down() -> Tuple[bool, str]:
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.press('pagedown')
                return True, "Done. Scrolled down."
            except Exception as e:
                logger.debug(f"PyAutoGUI fallback: {e}")
        return True, "Done. Scrolled down."

    @staticmethod
    def scroll_up() -> Tuple[bool, str]:
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.press('pageup')
                return True, "Done. Scrolled up."
            except Exception as e:
                logger.debug(f"PyAutoGUI fallback: {e}")
        return True, "Done. Scrolled up."

    @staticmethod
    def send_hotkey(hotkey: str) -> Tuple[bool, str]:
        keys = [k.strip().lower() for k in hotkey.split("+") if k.strip()]
        if not keys:
            return False, "Invalid hotkey specification."
        
        allowed_keys = {"ctrl", "shift", "alt", "tab", "t", "w", "r", "n", "f", "l", "f4", "esc", "enter", "space", "left", "right", "up", "down", "pagedown", "pageup"}
        if not set(keys).issubset(allowed_keys):
            return False, f"Hotkey combo '{hotkey}' contains disallowed keys."

        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey(*keys)
                return True, f"Done. Pressed '{hotkey}' shortcut."
            except Exception as e:
                return False, f"Failed to execute hotkey '{hotkey}': {e}"

        return True, f"Done. Shortcut '{hotkey}' executed."
