"""Unit tests for web_app.py Flask routes."""
import pytest
from unittest.mock import patch, MagicMock, call
from web_app import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def mock_chatbot():
    cb = MagicMock()
    cb.current_session_id = 1
    cb._last_agent_calls = []
    cb.list_sessions.return_value = []
    cb.start_new_session.return_value = 1
    cb.load_session.return_value = True
    cb.get_conversation_history.return_value = []
    cb.respond.return_value = "mocked response"
    cb.search_messages.return_value = []
    return cb


# --- index ---

def test_index_renders(client):
    resp = client.get('/')
    assert resp.status_code == 200


# --- get_chatbot factory ---

def test_get_chatbot_creates_instance_once():
    from web_app import get_chatbot
    with flask_app.test_request_context('/'):
        flask_app.preprocess_request()
        with patch('web_app.PersistentChatbot') as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            cb1 = get_chatbot()
            cb2 = get_chatbot()
            assert cb1 is cb2
            mock_class.assert_called_once()


# --- teardown ---

def test_close_chatbot_teardown_with_objects():
    from web_app import close_chatbot
    from flask import g
    with flask_app.app_context():
        mock_cb = MagicMock()
        mock_db = MagicMock()
        g.chatbot = mock_cb
        g.db = mock_db
        close_chatbot(None)
        mock_cb.close.assert_called_once()
        mock_db.close.assert_called_once()


def test_close_chatbot_teardown_no_objects():
    from web_app import close_chatbot
    with flask_app.app_context():
        close_chatbot(None)  # Should not raise


# --- get_db ---

def test_get_db_creates_connection():
    from web_app import get_db
    with flask_app.test_request_context('/'):
        flask_app.preprocess_request()
        with patch('web_app.sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            db = get_db()
            assert db is mock_conn
            mock_connect.assert_called_once()


def test_get_db_returns_same_connection_in_same_request():
    from web_app import get_db
    with flask_app.test_request_context('/'):
        flask_app.preprocess_request()
        with patch('web_app.sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            db1 = get_db()
            db2 = get_db()
            assert db1 is db2
            mock_connect.assert_called_once()


# --- get_models ---

def test_get_models_success(client):
    mock_model = MagicMock()
    mock_model.model = "llama2"
    mock_result = MagicMock()
    mock_result.models = [mock_model]
    with patch('ollama.list', return_value=mock_result):
        resp = client.get('/api/models')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert 'llama2' in data['models']


def test_get_models_error(client):
    with patch('ollama.list', side_effect=Exception("Ollama not running")):
        resp = client.get('/api/models')
    assert resp.status_code == 500
    data = resp.get_json()
    assert data['success'] is False
    assert 'Ollama not running' in data['error']


# --- get_sessions ---

def test_get_sessions_empty(client, mock_chatbot):
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.get('/api/sessions')
    data = resp.get_json()
    assert data['success'] is True
    assert data['sessions'] == []


def test_get_sessions_with_data(client, mock_chatbot):
    mock_chatbot.list_sessions.return_value = [
        {'session_id': 1, 'session_name': 'Test', 'created_at': '2024-01-01', 'last_active': '2024-01-01', 'message_count': 0}
    ]
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.get('/api/sessions')
    data = resp.get_json()
    assert data['success'] is True
    assert len(data['sessions']) == 1


def test_get_sessions_error(client):
    with patch('web_app.get_chatbot', side_effect=Exception("DB error")):
        resp = client.get('/api/sessions')
    assert resp.status_code == 500
    data = resp.get_json()
    assert data['success'] is False


# --- create_session ---

def test_create_session_with_name(client, mock_chatbot):
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/sessions', json={'name': 'My Chat'})
    data = resp.get_json()
    assert data['success'] is True
    assert data['session_name'] == 'My Chat'
    assert data['session_id'] == 1


def test_create_session_no_name_uses_default(client, mock_chatbot):
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/sessions', json={})
    data = resp.get_json()
    assert data['success'] is True
    assert 'Chat' in data['session_name']


def test_create_session_error(client):
    with patch('web_app.get_chatbot', side_effect=Exception("fail")):
        resp = client.post('/api/sessions', json={'name': 'x'})
    assert resp.status_code == 500


# --- load_session ---

def test_load_session_found(client, mock_chatbot):
    mock_chatbot.get_conversation_history.return_value = [
        {'role': 'user', 'content': 'hi', 'timestamp': '2024-01-01'}
    ]
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.get('/api/sessions/1')
    data = resp.get_json()
    assert data['success'] is True
    assert data['session_id'] == 1
    assert len(data['history']) == 1


def test_load_session_not_found(client, mock_chatbot):
    mock_chatbot.load_session.return_value = False
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.get('/api/sessions/999')
    assert resp.status_code == 404
    data = resp.get_json()
    assert data['success'] is False
    assert 'not found' in data['error']


def test_load_session_error(client):
    with patch('web_app.get_chatbot', side_effect=Exception("fail")):
        resp = client.get('/api/sessions/1')
    assert resp.status_code == 500


# --- chat ---

def test_chat_success(client, mock_chatbot):
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/chat', json={'message': 'hello', 'session_id': 1})
    data = resp.get_json()
    assert data['success'] is True
    assert data['bot_response'] == 'mocked response'
    assert data['user_message'] == 'hello'
    assert 'agents_called' in data


def test_chat_empty_message(client, mock_chatbot):
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/chat', json={'message': '', 'session_id': 1})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['success'] is False
    assert 'empty' in data['error'].lower()


def test_chat_whitespace_only_message(client, mock_chatbot):
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/chat', json={'message': '   ', 'session_id': 1})
    assert resp.status_code == 400


def test_chat_no_session_auto_creates(client, mock_chatbot):
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/chat', json={'message': 'hello'})
    data = resp.get_json()
    assert data['success'] is True
    mock_chatbot.start_new_session.assert_called()


def test_chat_with_model(client, mock_chatbot):
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/chat', json={'message': 'hi', 'session_id': 1, 'model': 'llama2'})
    data = resp.get_json()
    assert data['success'] is True
    mock_chatbot.respond.assert_called_with('hi', model='llama2')


def test_chat_error(client):
    with patch('web_app.get_chatbot', side_effect=Exception("crash")):
        resp = client.post('/api/chat', json={'message': 'hi'})
    assert resp.status_code == 500
    data = resp.get_json()
    assert data['success'] is False


# --- get_history ---

def test_get_history_no_session(client, mock_chatbot):
    mock_chatbot.current_session_id = None
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.get('/api/history')
    data = resp.get_json()
    assert data['success'] is True
    assert data['history'] == []


def test_get_history_with_session(client, mock_chatbot):
    mock_chatbot.current_session_id = 1
    mock_chatbot.get_conversation_history.return_value = [
        {'role': 'user', 'content': 'hey', 'timestamp': '2024-01-01'}
    ]
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        with client.session_transaction() as sess:
            sess['current_session_id'] = 1
        resp = client.get('/api/history')
    data = resp.get_json()
    assert data['success'] is True
    assert 'history' in data


def test_get_history_error(client):
    with patch('web_app.get_chatbot', side_effect=Exception("fail")):
        resp = client.get('/api/history')
    assert resp.status_code == 500


# --- search ---

def test_search_empty_query(client, mock_chatbot):
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/search', json={'query': ''})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['success'] is False


def test_search_with_results(client, mock_chatbot):
    mock_chatbot.search_messages.return_value = [
        {'session_id': 1, 'role': 'user', 'content': 'Python rocks', 'timestamp': '2024-01-01', 'session_name': 'Test'}
    ]
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/search', json={'query': 'Python'})
    data = resp.get_json()
    assert data['success'] is True
    assert data['count'] == 1
    assert len(data['results']) == 1


def test_search_no_results(client, mock_chatbot):
    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/search', json={'query': 'zzznomatch'})
    data = resp.get_json()
    assert data['success'] is True
    assert data['count'] == 0


def test_search_error(client):
    with patch('web_app.get_chatbot', side_effect=Exception("fail")):
        resp = client.post('/api/search', json={'query': 'test'})
    assert resp.status_code == 500


# --- delete_session ---

def test_delete_session_not_implemented(client):
    resp = client.delete('/api/sessions/1')
    assert resp.status_code == 501
    data = resp.get_json()
    assert data['success'] is False
    assert 'not yet implemented' in data['error']


# --- benchmarks ---

def test_benchmarks_page(client):
    resp = client.get('/benchmarks')
    assert resp.status_code == 200


# --- get_benchmark_runs ---

def test_get_benchmark_runs_empty(client):
    mock_db = MagicMock()
    mock_row = []
    mock_db.execute.return_value.fetchall.return_value = mock_row
    with patch('web_app.get_db', return_value=mock_db):
        resp = client.get('/api/benchmarks/runs')
    data = resp.get_json()
    assert data['success'] is True
    assert data['runs'] == []


def test_get_benchmark_runs_with_data(client):
    mock_db = MagicMock()
    mock_row = MagicMock()
    mock_row.keys.return_value = ['run_id', 'timestamp', 'model', 'total_cases', 'passed_cases', 'avg_latency_ms', 'agent_count']
    mock_row.__iter__ = MagicMock(return_value=iter(['run1', '2024-01-01', 'llama2', 10, 8, 500, 3]))

    import sqlite3
    # Create real row-like dict
    with patch('web_app.get_db') as mock_get_db:
        mock_conn = MagicMock()
        # Return a list of sqlite3.Row-compatible dicts
        mock_conn.execute.return_value.fetchall.return_value = [{'run_id': 'r1', 'timestamp': 't', 'model': 'm', 'total_cases': 5, 'passed_cases': 4, 'avg_latency_ms': 100, 'agent_count': 2}]
        mock_get_db.return_value = mock_conn
        resp = client.get('/api/benchmarks/runs')
    assert resp.status_code == 200


def test_get_benchmark_runs_error(client):
    with patch('web_app.get_db', side_effect=Exception("no table")):
        resp = client.get('/api/benchmarks/runs')
    assert resp.status_code == 500
    data = resp.get_json()
    assert data['success'] is False


# --- get_benchmark_run ---

def test_get_benchmark_run_empty(client):
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = []
    with patch('web_app.get_db', return_value=mock_db):
        resp = client.get('/api/benchmarks/runs/abc123')
    data = resp.get_json()
    assert data['success'] is True
    assert data['results'] == []


def test_get_benchmark_run_error(client):
    with patch('web_app.get_db', side_effect=Exception("fail")):
        resp = client.get('/api/benchmarks/runs/bad')
    assert resp.status_code == 500
    data = resp.get_json()
    assert data['success'] is False
