import pytest
from app.core.config import config
from app.core.state import StateMachine, AssistantState
from app.core.events import Command, Action, Response
from app.core.command_bus import CommandBus
from app.core.assistant import AssistantOrchestrator
from app.brain.intent_parser import IntentParser

def test_command_bus_dispatch():
    bus = CommandBus()
    received_commands = []

    def mock_handler(cmd: Command):
        received_commands.append(cmd)

    bus.register_handler(mock_handler)
    cmd = Command(source="voice", text="open chrome")
    bus.submit(cmd)

    assert len(received_commands) == 1
    assert received_commands[0].source == "voice"
    assert received_commands[0].text == "open chrome"

def test_state_machine_transitions():
    sm = StateMachine(AssistantState.IDLE)
    states_logged = []

    def on_change(new_state):
        states_logged.append(new_state)

    sm.add_callback(on_change)
    sm.transition_to(AssistantState.LISTENING)
    sm.transition_to(AssistantState.THINKING)
    sm.transition_to(AssistantState.EXECUTING)
    sm.transition_to(AssistantState.SPEAKING)
    sm.transition_to(AssistantState.IDLE)

    assert states_logged == [
        AssistantState.LISTENING,
        AssistantState.THINKING,
        AssistantState.EXECUTING,
        AssistantState.SPEAKING,
        AssistantState.IDLE
    ]

def test_intent_parser_greetings():
    parser = IntentParser()
    intent = parser.parse("Hello.")
    assert intent["actions"] == []
    assert any(w in intent["response"].lower() for w in ("help", "assist", "hey", "hello"))

def test_orchestrator_unified_command_bus():
    bus = CommandBus()
    orch = AssistantOrchestrator(text_mode=True, command_bus=bus)
    
    executed = []
    def mock_exec(tool_name, args):
        executed.append((tool_name, args))
        return True, "Done. Chrome is open."

    orch.tool_executor.execute = mock_exec
    res = orch.handle_command("open chrome")

    assert "Chrome is open" in res
    assert len(executed) == 1
    assert executed[0][0] == "open_application"
    assert executed[0][1]["application"] == "chrome"
