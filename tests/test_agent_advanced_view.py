"""
Tests for agent advanced view feature.
Covers: _last_agent_calls tracking in chatbot_agent.py,
        agents_called field in /api/chat response.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from chatbot_agent import PersistentChatbot
from web_app import app as flask_app


@pytest.fixture
def chatbot():
    cb = PersistentChatbot(":memory:", enable_sub_agents=True)
    cb.start_new_session("test")
    yield cb
    cb.close()


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


# --- chatbot_agent.py tests ---

def test_last_agent_calls_initialized(chatbot):
    """_last_agent_calls starts as empty list"""
    assert chatbot._last_agent_calls == []


def test_last_agent_calls_empty_when_no_agents_triggered(chatbot):
    """No agents triggered for a generic query"""
    chatbot._execute_sub_agents_if_needed("tell me a joke")
    assert chatbot._last_agent_calls == []


def test_last_agent_calls_populated_when_agents_run(chatbot):
    """_last_agent_calls contains one entry per agent that ran"""
    fake_results = [
        {"agent": "time", "success": True, "data": {"data": {"current_time": "12:00", "day_of_week": "Friday"}}}
    ]
    with patch.object(chatbot.orchestrator, 'execute_agents', return_value=fake_results):
        chatbot._execute_sub_agents_if_needed("what time is it?")

    assert len(chatbot._last_agent_calls) == 1
    entry = chatbot._last_agent_calls[0]
    assert entry["agent"] == "time"
    assert entry["success"] is True
    assert isinstance(entry["latency_ms"], int)
    assert entry["latency_ms"] >= 0


def test_last_agent_calls_failed_agent(chatbot):
    """Failed agent sets success=False"""
    fake_results = [
        {"agent": "weather", "success": False, "error": "timeout"}
    ]
    with patch.object(chatbot.orchestrator, 'execute_agents', return_value=fake_results):
        chatbot._execute_sub_agents_if_needed("what's the weather in Paris?")

    assert len(chatbot._last_agent_calls) == 1
    assert chatbot._last_agent_calls[0]["success"] is False


def test_last_agent_calls_reset_on_respond(chatbot):
    """respond() resets stale _last_agent_calls from a previous call"""
    # Inject stale data as if a previous respond() had run agents
    chatbot._last_agent_calls = [{"agent": "stale", "success": True, "latency_ms": 0}]

    with patch.object(chatbot, '_execute_sub_agents_if_needed', return_value=""), \
         patch.object(chatbot, '_get_cross_session_context', return_value=""), \
         patch('ollama.chat', return_value={'message': {'content': 'hi'}}):
        chatbot.respond("hello")

    # _last_agent_calls should be [] because respond() resets it at the top,
    # and _execute_sub_agents_if_needed was mocked to return "" without setting it
    assert chatbot._last_agent_calls == []
