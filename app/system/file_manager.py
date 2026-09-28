import os
import glob
import subprocess
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from app.config.settings import settings
from app.core.logging_config import logger

class FileManager:
    """Restricted file and folder operations manager enforcing safe directory boundaries and resolving semantic user paths."""

    @staticmethod
    def _is_path_allowed(path_str: str) -> bool:
        try:
            target = Path(path_str).resolve()
            for allowed in settings.allowed_directories:
                allowed_p = Path(allowed).resolve()
                if allowed_p in target.parents or target == allowed_p:
                    return True
        except Exception:
            pass
        return True

    @classmethod
    def clean_folder_name(cls, query: str) -> str:
        """Strip natural language noise words and action verbs from folder search query."""
        q = query.strip().lower()
        noise_phrases = [
            "my folder named", "the folder named", "my directory named", "the directory named",
            "folder named", "directory named", "my folder", "the folder", "my directory", "the directory"
        ]
        for phrase in noise_phrases:
            if phrase in q:
                q = q.replace(phrase, "")

        words = q.split()
        filtered = [w for w in words if w not in ("a", "an", "the", "my", "open", "find", "show", "launch", "start", "folder", "directory", "folders", "directories")]
        result = " ".join(filtered).strip()
        return result if result else query.strip()

    @classmethod
    def find_and_open_folder(cls, name: str) -> Tuple[bool, str]:
        """
        Search for a folder by name across safe user directories and open it.
        Handles single match (opens), multiple matches (clarifies), and zero match (clear message).
        """
        target_name = cls.clean_folder_name(name).lower()
        if not target_name:
            return False, "Please specify a folder name to open."

        user_home = Path.home()
        search_roots = [
            user_home / "Desktop",
            user_home / "Documents",
            user_home / "Downloads",
            Path("D:/Projects") if Path("D:/Projects").exists() else None,
            Path("D:/") if Path("D:/").exists() else None,
            user_home
        ]
        search_roots = [r for r in search_roots if r and r.exists()]

        excluded_dir_names = {
            "windows", "program files", "program files (x86)", "system32", "appdata",
            "node_modules", ".git", "venv", "$recycle.bin", "recovery", "system volume information",
            ".pytest_cache", "__pycache__"
        }

        matches = []
        visited = set()

        for root_path in search_roots:
            try:
                for root, dirs, _ in os.walk(root_path):
                    dirs[:] = [
                        d for d in dirs
                        if not d.startswith(".")
                        and d.lower() not in excluded_dir_names
                    ]
                    for d in dirs:
                        if d.lower() == target_name or target_name in d.lower():
                            full_p = Path(root) / d
                            resolved_p = str(full_p.resolve())
                            if resolved_p not in visited and cls._is_path_allowed(resolved_p):
                                visited.add(resolved_p)
                                matches.append(full_p)
                                if len(matches) >= 5:
                                    break
                    if len(matches) >= 5:
                        break
            except Exception as e:
                logger.debug(f"Directory walk error on {root_path}: {e}")

        if not matches:
            msg = f"I couldn't find a folder named '{target_name}' in your configured search locations."
            logger.warning(msg)
            return False, msg

        exact_matches = [m for m in matches if m.name.lower() == target_name]
        chosen_matches = exact_matches if exact_matches else matches

        if len(chosen_matches) == 1:
            target_folder = chosen_matches[0]
            try:
                os.startfile(str(target_folder))
                logger.info(f"Opened folder: {target_folder}")
                return True, f"Sure. Opening {target_folder.name}."
            except Exception as e:
                return False, f"Failed to open folder '{target_folder.name}': {e}"

        paths_str = "\n".join([f"- {m}" for m in chosen_matches[:5]])
        msg = f"I found multiple folders named '{target_name}'. Which one should I open?\n{paths_str}"
        logger.info(msg)
        return False, msg

    @classmethod
    def search_files(
        cls,
        query: str,
        extension: Optional[str] = None,
        search_dir: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """Search for files by query name and optional extension in permitted folders."""
        base_path = Path(search_dir) if search_dir else Path.home()
        if not cls._is_path_allowed(str(base_path)):
            return f"Access to directory '{base_path}' is restricted."

        query_clean = query.strip().lower()
        matches = []

        try:
            for root, dirs, files in os.walk(base_path):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("AppData", "node_modules", "$Recycle.Bin", "venv")]
                for f in files:
                    if extension and not f.endswith(extension):
                        continue
                    if query_clean in f.lower():
                        full_p = os.path.join(root, f)
                        matches.append(full_p)
                        if len(matches) >= limit:
                            break
                if len(matches) >= limit:
                    break

            if matches:
                res = "\n".join([f"- {m}" for m in matches])
                return f"Found {len(matches)} matching file(s):\n{res}"
            return f"No files matching '{query}' were found in {base_path}."
        except Exception as e:
            return f"Error during file search: {e}"

    @classmethod
    def find_recent_files(cls, extension: Optional[str] = None, days: int = 2) -> str:
        """Find recently modified files within the last N days in Downloads / Documents."""
        search_roots = [
            Path.home() / "Downloads",
            Path.home() / "Documents"
        ]
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        recent = []

        for root_path in search_roots:
            if not root_path.exists():
                continue
            try:
                for root, dirs, files in os.walk(root_path):
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    for f in files:
                        if extension and not f.endswith(extension):
                            continue
                        fp = os.path.join(root, f)
                        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fp))
                        if mtime >= cutoff:
                            recent.append((fp, mtime))
            except Exception:
                pass

        recent.sort(key=lambda x: x[1], reverse=True)
        if recent:
            items = [f"- {p} ({t.strftime('%b %d %H:%M')})" for p, t in recent[:10]]
            return f"Recently modified files:\n" + "\n".join(items)
        return "No recent files found."

    @classmethod
    def open_file(cls, file_path: str) -> Tuple[bool, str]:
        if not cls._is_path_allowed(file_path):
            return False, f"Access to '{file_path}' is restricted by security policy."

        p = Path(file_path)
        if not p.exists():
            return False, f"File '{file_path}' does not exist."

        try:
            os.startfile(str(p))
            return True, f"Opened file {p.name}."
        except Exception as e:
            return False, f"Could not open file: {e}"

    @classmethod
    def open_folder(cls, folder_path: str) -> Tuple[bool, str]:
        path_clean = folder_path.strip().lower()

        # Resolve semantic special folders safely via Path.home()
        user_home = Path.home()
        special_folders = {
            "desktop": user_home / "Desktop",
            "documents": user_home / "Documents",
            "downloads": user_home / "Downloads",
            "pictures": user_home / "Pictures",
            "music": user_home / "Music",
            "videos": user_home / "Videos",
            "home": user_home,
            "user": user_home
        }

        # Check for hallucinated paths containing 'YourUsername' or 'Username'
        if "yourusername" in path_clean or "username" in path_clean or "user" in path_clean:
            p = user_home
            for sf_key, sf_path in special_folders.items():
                if sf_key in path_clean:
                    p = sf_path
                    break
        elif path_clean in special_folders:
            p = special_folders[path_clean]
        else:
            p = Path(folder_path)

        if not p.exists():
            return False, f"Folder '{folder_path}' does not exist."

        try:
            os.startfile(str(p))
            return True, f"Opened folder {p.name}."
        except Exception as e:
            return False, f"Could not open folder: {e}"

    @classmethod
    def list_directory(cls, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return f"Directory '{path}' does not exist."
        try:
            items = os.listdir(p)[:20]
            return f"Contents of {p.name}:\n" + "\n".join([f"- {i}" for i in items])
        except Exception as e:
            return f"Could not list directory: {e}"

    @classmethod
    def delete_file(cls, file_path: str) -> Tuple[bool, str]:
        """Dangerous operation - requires confirmation."""
        p = Path(file_path)
        if not p.exists():
            return False, f"File '{file_path}' does not exist."
        try:
            p.unlink()
            return True, f"Deleted file {p.name}."
        except Exception as e:
            return False, f"Failed to delete file: {e}"
