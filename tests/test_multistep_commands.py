import pytest
from app.ai.llm_client import LLMClient

def test_single_command_parsing():
    client = LLMClient()
    intent = client.process_user_input("open chrome")
    assert len(intent["actions"]) == 1
    assert intent["actions"][0]["tool"] == "open_application"
    assert intent["actions"][0]["arguments"]["application"] == "chrome"

def test_multistep_chrome_and_youtube_parsing():
    client = LLMClient()
    intent = client.process_user_input("open chrome and search youtube for java dsa")
    actions = intent["actions"]
    assert len(actions) == 2
    assert actions[0]["tool"] == "open_application"
    assert actions[0]["arguments"]["application"] == "chrome"
    assert actions[1]["tool"] == "search_youtube"
    assert actions[1]["arguments"]["query"] == "java dsa"

def test_multistep_taskmanager_and_cpu_usage_parsing():
    client = LLMClient()
    intent = client.process_user_input("open task manager and tell me my cpu usage")
    actions = intent["actions"]
    assert len(actions) == 2
    assert actions[0]["tool"] == "open_application"
    assert actions[0]["arguments"]["application"] == "task manager"
    assert actions[1]["tool"] == "get_cpu_usage"

def test_multistep_settings_and_file_explorer_parsing():
    client = LLMClient()
    intent = client.process_user_input("open settings and open file explorer")
    actions = intent["actions"]
    assert len(actions) == 2
    assert actions[0]["tool"] == "open_application"
    assert actions[0]["arguments"]["application"] == "settings"
    assert actions[1]["tool"] == "open_application"
    assert actions[1]["arguments"]["application"] == "file explorer"

def test_multistep_folder_and_chrome_parsing():
    client = LLMClient()
    intent = client.process_user_input("open RESUME1 folder and open chrome")
    actions = intent["actions"]
    assert len(actions) == 2
    assert actions[0]["tool"] == "find_and_open_folder"
    assert actions[0]["arguments"]["name"] == "resume1 folder"
    assert actions[1]["tool"] == "open_application"
    assert actions[1]["arguments"]["application"] == "chrome"
