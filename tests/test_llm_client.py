import pytest
from app.ai.llm_client import LLMClient

def test_rule_based_intent_check():
    client = LLMClient()

    res1 = client._rule_based_intent_check("open chrome")
    assert res1 is not None
    assert res1["tool"] == "open_application"
    assert res1["arguments"]["application"] == "chrome"

    res2 = client._rule_based_intent_check("what is my cpu usage?")
    assert res2 is not None
    assert res2["tool"] == "get_cpu_usage"

    res3 = client._rule_based_intent_check("search youtube for python tutorials")
    assert res3 is not None
    assert res3["tool"] == "search_youtube"
    assert res3["arguments"]["query"] == "python tutorials"

    greeting = client._rule_based_intent_check("hello")
    assert greeting is not None
    assert greeting["tool"] is None
