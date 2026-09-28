import os
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional
from app.core.logging_config import logger

class FolderAssistant:
    """Safe folder assistant searching safe user directories without scanning C:\\Windows or C:\\Program Files."""

    SAFE_SEARCH_DIRS: List[Path] = [
        Path.home() / "Documents",
        Path.home() / "Desktop",
        Path.home() / "Downloads",
        Path.home() / "Projects",
        Path("D:/AI_Assistant"),
        Path("D:/")
    ]

    NOISE_WORDS = {"a", "the", "my", "folder", "directory", "please", "open", "find", "show", "me", "launch"}

    @classmethod
    def clean_folder_query(cls, raw_query: str) -> str:
        words = raw_query.lower().strip().split()
        cleaned_words = [w for w in words if w not in cls.NOISE_WORDS]
        return " ".join(cleaned_words) if cleaned_words else raw_query.strip()

    @classmethod
    def find_and_open_folder(cls, name: str) -> Tuple[bool, str]:
        target_name = cls.clean_folder_query(name)
        if not target_name:
            target_name = name.strip().lower()

        logger.info(f"Searching for folder matching query: '{target_name}'...")
        matched_path: Optional[Path] = None

        for base_dir in cls.SAFE_SEARCH_DIRS:
            if not base_dir.exists():
                continue

            try:
                for root, dirs, _ in os.walk(base_dir):
                    root_path = Path(root)
                    if any(part.startswith(".") for part in root_path.parts):
                        continue
                    if "Windows" in root_path.parts or "Program Files" in root_path.parts:
                        continue

                    for d in dirs:
                        if d.startswith("."):
                            continue
                        if target_name in d.lower():
                            matched_path = root_path / d
                            break
                    if matched_path:
                        break
            except Exception as e:
                logger.debug(f"Error scanning {base_dir}: {e}")

            if matched_path:
                break

        if matched_path and matched_path.exists():
            try:
                logger.info(f"Opening folder: {matched_path}")
                subprocess.Popen(f'explorer "{matched_path}"', shell=True)
                return True, f"Sure — opening your '{matched_path.name}' folder."
            except Exception as e:
                return False, f"Failed to open folder '{matched_path.name}': {e}"

        msg = f"I couldn't find a folder named '{target_name}' in your configured search locations."
        logger.warning(msg)
        return False, msg
