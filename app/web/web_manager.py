import webbrowser
import urllib.parse
from typing import Tuple
from app.core.logging_config import logger

class WebManager:
    """Safe browser and web search navigation manager."""

    @staticmethod
    def open_website(url: str) -> Tuple[bool, str]:
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            logger.info(f"Opening website: {url}")
            webbrowser.open(url)
            return True, f"Opened website: {url}"
        except Exception as e:
            err = f"Failed to open URL '{url}': {e}"
            logger.error(err)
            return False, err

    @staticmethod
    def search_web(query: str) -> Tuple[bool, str]:
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.google.com/search?q={encoded_query}"
            logger.info(f"Searching Google for: '{query}'")
            webbrowser.open(url)
            return True, f"Searching the web for '{query}'."
        except Exception as e:
            err = f"Failed to search web: {e}"
            logger.error(err)
            return False, err

    @staticmethod
    def search_youtube(query: str) -> Tuple[bool, str]:
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            logger.info(f"Searching YouTube for: '{query}'")
            webbrowser.open(url)
            return True, f"Searching YouTube for '{query}'."
        except Exception as e:
            err = f"Failed to search YouTube: {e}"
            logger.error(err)
            return False, err
