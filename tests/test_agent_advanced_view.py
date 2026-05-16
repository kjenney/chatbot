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


# --- web_app.py /api/chat tests ---

def test_chat_response_includes_agents_called_field(client):
    """agents_called field always present in /api/chat response"""
    mock_chatbot = MagicMock()
    mock_chatbot.current_session_id = 1
    mock_chatbot.respond.return_value = "Hello!"
    mock_chatbot._last_agent_calls = []

    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/chat', json={"message": "hello", "session_id": 1})

    data = resp.get_json()
    assert data['success'] is True
    assert 'agents_called' in data
    assert data['agents_called'] == []


def test_chat_response_agents_called_populated(client):
    """agents_called contains metadata when agents ran"""
    mock_chatbot = MagicMock()
    mock_chatbot.current_session_id = 1
    mock_chatbot.respond.return_value = "The time is 12:00"
    mock_chatbot._last_agent_calls = [
        {"agent": "time", "success": True, "latency_ms": 15}
    ]

    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/chat', json={"message": "what time is it?", "session_id": 1})

    data = resp.get_json()
    assert data['success'] is True
    assert len(data['agents_called']) == 1
    assert data['agents_called'][0]['agent'] == 'time'
    assert data['agents_called'][0]['success'] is True
    assert 'latency_ms' in data['agents_called'][0]
