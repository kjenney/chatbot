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
