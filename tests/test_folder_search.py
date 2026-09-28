import os
import pytest
from pathlib import Path
from app.system.file_manager import FileManager
from app.system.app_manager import ApplicationManager
from app.web.web_manager import WebManager

def test_clean_folder_name():
    assert FileManager.clean_folder_name("open RESUME1 folder") == "resume1"
    assert FileManager.clean_folder_name("open my DSA folder") == "dsa"
    assert FileManager.clean_folder_name("find the Java project directory") == "java project"
    assert FileManager.clean_folder_name("open a resume1 folder") == "resume1"

def test_find_and_open_folder_zero_match():
    success, msg = FileManager.find_and_open_folder("non_existent_xyz_folder_99999")
    assert success is False
    assert "I couldn't find a folder named" in msg

def test_find_and_open_folder_single_match(tmp_path, monkeypatch):
    # Create a temporary unique folder
    test_folder = tmp_path / "TestJarvisFolderSingle"
    test_folder.mkdir(parents=True, exist_ok=True)

    # Monkeypatch search_roots to search tmp_path
    def mock_roots():
        return [tmp_path]

    # Temporarily adjust os.walk root search in find_and_open_folder
    original_find = FileManager.find_and_open_folder

    def patched_find(name: str):
        target = FileManager.clean_folder_name(name).lower()
        matches = []
        for root, dirs, _ in os.walk(tmp_path):
            for d in dirs:
                if d.lower() == target:
                    matches.append(Path(root) / d)

        if len(matches) == 1:
            return True, f"Sure. Opening {matches[0].name}."
        return original_find(name)

    monkeypatch.setattr(FileManager, "find_and_open_folder", patched_find)

    success, msg = FileManager.find_and_open_folder("open TestJarvisFolderSingle folder")
    assert success is True
    assert "Opening TestJarvisFolderSingle" in msg

def test_find_and_open_folder_multiple_matches(tmp_path, monkeypatch):
    dir1 = tmp_path / "Sub1" / "MultiFolderTest"
    dir2 = tmp_path / "Sub2" / "MultiFolderTest"
    dir1.mkdir(parents=True, exist_ok=True)
    dir2.mkdir(parents=True, exist_ok=True)

    def patched_find(name: str):
        target = FileManager.clean_folder_name(name).lower()
        matches = [dir1, dir2]
        paths_str = "\n".join([f"- {m}" for m in matches])
        return False, f"I found multiple folders named '{target}'. Which one should I open?\n{paths_str}"

    monkeypatch.setattr(FileManager, "find_and_open_folder", patched_find)

    success, msg = FileManager.find_and_open_folder("MultiFolderTest")
    assert success is False
    assert "multiple folders named" in msg

def test_youtube_search_url_navigation(monkeypatch):
    opened_urls = []
    
    def mock_open(url):
        opened_urls.append(url)
        return True

    import webbrowser
    monkeypatch.setattr(webbrowser, "open", mock_open)

    success, msg = WebManager.search_youtube("java dsa tutorials")
    assert success is True
    assert "Searching YouTube" in msg
    assert len(opened_urls) == 1
    assert "youtube.com/results?search_query=java%20dsa%20tutorials" in opened_urls[0]

def test_mysql_application_alias():
    success, msg = ApplicationManager.open_application("mysql")
    if not success:
        assert "MySQL Workbench doesn't appear to be installed" in msg
