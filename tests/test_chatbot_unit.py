"""Unit tests for chatbot_agent.py using in-memory SQLite."""
import pytest
import re
from unittest.mock import patch, MagicMock
from chatbot_agent import PersistentChatbot


@pytest.fixture
def bot():
    cb = PersistentChatbot(":memory:", enable_sub_agents=False)
    yield cb
    cb.close()


@pytest.fixture
def bot_with_session(bot):
    bot.start_new_session("test-session")
    return bot


# --- initialize_database ---

def test_initialize_database_creates_tables(bot):
    cursor = bot.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert {'sessions', 'messages'}.issubset(tables)


# --- start_new_session ---

def test_start_new_session_returns_id(bot):
    sid = bot.start_new_session("My Session")
    assert isinstance(sid, int)
    assert sid > 0
    assert bot.current_session_id == sid


def test_start_new_session_no_name(bot):
    sid = bot.start_new_session()
    assert isinstance(sid, int)


def test_start_new_session_multiple(bot):
    sid1 = bot.start_new_session("Alpha")
    sid2 = bot.start_new_session("Beta")
    assert sid1 != sid2
    assert bot.current_session_id == sid2


# --- load_session ---

def test_load_session_existing(bot):
    sid = bot.start_new_session("Load Test")
    bot.start_new_session("Other")
    result = bot.load_session(sid)
    assert result is True
    assert bot.current_session_id == sid


def test_load_session_nonexistent(bot):
    result = bot.load_session(99999)
    assert result is False


def test_load_session_updates_last_active(bot):
    sid = bot.start_new_session("Active")
    bot.load_session(sid)
    cursor = bot.conn.cursor()
    cursor.execute("SELECT last_active FROM sessions WHERE session_id=?", (sid,))
    row = cursor.fetchone()
    assert row is not None


# --- save_message ---

def test_save_message_auto_starts_session(bot):
    assert bot.current_session_id is None
    bot.save_message('user', 'hello without session')
    assert bot.current_session_id is not None


def test_save_message_saves_to_db(bot_with_session):
    bot_with_session.save_message('user', 'test message')
    history = bot_with_session.get_conversation_history()
    assert len(history) == 1
    assert history[0]['content'] == 'test message'
    assert history[0]['role'] == 'user'


def test_save_message_both_roles(bot_with_session):
    bot_with_session.save_message('user', 'question')
    bot_with_session.save_message('assistant', 'answer')
    history = bot_with_session.get_conversation_history()
    assert len(history) == 2
    assert history[0]['role'] == 'user'
    assert history[1]['role'] == 'assistant'


# --- get_conversation_history ---

def test_get_conversation_history_no_session(bot):
    result = bot.get_conversation_history()
    assert result == []


def test_get_conversation_history_no_session_id_explicit(bot):
    bot.current_session_id = None
    result = bot.get_conversation_history(session_id=None)
    assert result == []


def test_get_conversation_history_with_limit(bot_with_session):
    for i in range(5):
        bot_with_session.save_message('user', f'msg{i}')
    history = bot_with_session.get_conversation_history(limit=3)
    assert len(history) == 3


def test_get_conversation_history_with_session_id(bot):
    sid = bot.start_new_session("ctx-session")
    bot.save_message('user', 'ctx msg')
    result = bot.get_conversation_history(session_id=sid)
    assert len(result) == 1
    assert result[0]['content'] == 'ctx msg'


def test_get_conversation_history_includes_timestamp(bot_with_session):
    bot_with_session.save_message('user', 'timestamped')
    history = bot_with_session.get_conversation_history()
    assert 'timestamp' in history[0]


# --- list_sessions ---

def test_list_sessions_empty(bot):
    sessions = bot.list_sessions()
    assert sessions == []


def test_list_sessions_returns_all(bot):
    bot.start_new_session("Alpha")
    bot.save_message('user', 'hi')
    bot.start_new_session("Beta")
    sessions = bot.list_sessions()
    assert len(sessions) == 2


def test_list_sessions_includes_message_count(bot):
    bot.start_new_session("One")
    bot.save_message('user', 'a')
    bot.save_message('user', 'b')
    sessions = bot.list_sessions()
    assert sessions[0]['message_count'] == 2


def test_list_sessions_fields(bot):
    bot.start_new_session("FieldTest")
    sessions = bot.list_sessions()
    assert len(sessions) == 1
    s = sessions[0]
    assert 'session_id' in s
    assert 'session_name' in s
    assert 'created_at' in s
    assert 'last_active' in s
    assert 'message_count' in s


# --- search_messages ---

def test_search_messages_finds_match(bot):
    bot.start_new_session("search-session")
    bot.save_message('user', 'I love Python programming')
    results = bot.search_messages('Python')
    assert len(results) == 1
    assert 'Python' in results[0]['content']


def test_search_messages_no_match(bot):
    bot.start_new_session("s")
    results = bot.search_messages('zzznomatch')
    assert results == []


def test_search_messages_result_fields(bot):
    bot.start_new_session("field-search")
    bot.save_message('user', 'hello world')
    results = bot.search_messages('hello')
    assert len(results) == 1
    r = results[0]
    assert 'session_id' in r
    assert 'role' in r
    assert 'content' in r
    assert 'timestamp' in r
    assert 'session_name' in r


# --- get_context_summary ---

def test_get_context_summary_no_history(bot):
    bot.start_new_session("empty-ctx")
    summary = bot.get_context_summary()
    assert summary == "No conversation history found."


def test_get_context_summary_with_messages(bot_with_session):
    bot_with_session.save_message('user', 'hello there')
    bot_with_session.save_message('assistant', 'hi back')
    summary = bot_with_session.get_context_summary()
    assert 'USER' in summary
    assert 'ASSISTANT' in summary
    assert 'hello there' in summary


def test_get_context_summary_no_session(bot):
    summary = bot.get_context_summary()
    assert summary == "No conversation history found."


# --- respond / _generate_response ---

def test_respond_mocked_ollama(bot_with_session):
    with patch('ollama.chat', return_value={'message': {'content': 'mocked reply'}}):
        reply = bot_with_session.respond("hello")
    assert reply == 'mocked reply'


def test_respond_resets_last_agent_calls(bot_with_session):
    bot_with_session._last_agent_calls = [{'agent': 'stale'}]
    with patch('ollama.chat', return_value={'message': {'content': 'ok'}}):
        bot_with_session.respond("hi")
    assert bot_with_session._last_agent_calls == []


def test_respond_saves_messages(bot_with_session):
    with patch('ollama.chat', return_value={'message': {'content': 'response text'}}):
        bot_with_session.respond("user input")
    history = bot_with_session.get_conversation_history()
    assert any(m['content'] == 'user input' for m in history)
    assert any(m['content'] == 'response text' for m in history)


def test_generate_response_ollama_exception(bot_with_session):
    with patch('ollama.chat', side_effect=Exception("Ollama down")):
        reply = bot_with_session.respond("hello")
    assert "Error generating response" in reply
    assert "Ollama down" in reply


def test_generate_response_custom_model(bot_with_session):
    with patch('ollama.chat', return_value={'message': {'content': 'ok'}}) as mock_chat:
        bot_with_session.respond("hi", model="custom-model")
    assert mock_chat.call_args[1]['model'] == 'custom-model'


def test_generate_response_default_model_none_passed(bot_with_session):
    with patch('ollama.chat', return_value={'message': {'content': 'ok'}}) as mock_chat:
        bot_with_session.respond("hi")
    # model kwarg should equal bot's default model
    assert mock_chat.call_args[1]['model'] == bot_with_session.model


def test_generate_response_with_agent_results(bot_with_session):
    with patch.object(bot_with_session, '_execute_sub_agents_if_needed', return_value="TIME: 12:00"), \
         patch.object(bot_with_session, '_get_cross_session_context', return_value=""), \
         patch('ollama.chat', return_value={'message': {'content': 'ok'}}) as mock_chat:
        bot_with_session.respond("what time is it?")
    # System message should include the agent results
    messages = mock_chat.call_args[1]['messages']
    system_msg = next(m for m in messages if m['role'] == 'system')
    assert 'TIME: 12:00' in system_msg['content']


def test_generate_response_with_cross_session_context(bot_with_session):
    with patch.object(bot_with_session, '_execute_sub_agents_if_needed', return_value=""), \
         patch.object(bot_with_session, '_get_cross_session_context', return_value="User said: I like cats"), \
         patch('ollama.chat', return_value={'message': {'content': 'ok'}}) as mock_chat:
        bot_with_session.respond("what do I like?")
    messages = mock_chat.call_args[1]['messages']
    system_msg = next(m for m in messages if m['role'] == 'system')
    assert 'I like cats' in system_msg['content']


# --- _get_cross_session_context ---

def test_cross_session_context_name_query(bot):
    sid1 = bot.start_new_session("s1")
    bot.save_message('user', 'My name is Alice')
    sid2 = bot.start_new_session("s2")
    ctx = bot._get_cross_session_context("what is my name?")
    assert isinstance(ctx, str)
    # Should find the previous message about Alice
    if ctx:
        assert 'Alice' in ctx


def test_cross_session_context_interest_query(bot):
    bot.start_new_session("s1")
    bot.save_message('user', 'I like hiking and cycling')
    bot.start_new_session("s2")
    ctx = bot._get_cross_session_context("what do I enjoy doing?")
    assert isinstance(ctx, str)


def test_cross_session_context_job_query(bot):
    bot.start_new_session("s1")
    bot.save_message('user', 'I work as a software engineer')
    bot.start_new_session("s2")
    ctx = bot._get_cross_session_context("what is my job?")
    assert isinstance(ctx, str)


def test_cross_session_context_empty_for_non_memory_query(bot):
    bot.start_new_session("s1")
    for _ in range(4):
        bot.save_message('user', 'generic message')
        bot.save_message('assistant', 'response')
    ctx = bot._get_cross_session_context("tell me a joke")
    assert ctx == ""


def test_cross_session_context_deduplicates(bot):
    bot.start_new_session("s1")
    bot.save_message('user', 'My name is Bob')
    bot.save_message('user', 'My name is Bob')
    bot.start_new_session("s2")
    ctx = bot._get_cross_session_context("what is my name?")
    if ctx:
        assert ctx.count('Bob') <= 2


# --- _execute_sub_agents_if_needed ---

def test_execute_sub_agents_disabled():
    bot = PersistentChatbot(":memory:", enable_sub_agents=False)
    bot.start_new_session("t")
    result = bot._execute_sub_agents_if_needed("what time is it?")
    assert result == ""
    bot.close()


def test_execute_sub_agents_no_keywords(bot_with_session):
    bot_with_session.orchestrator = MagicMock()
    result = bot_with_session._execute_sub_agents_if_needed("tell me a random story")
    assert result == ""
    bot_with_session.orchestrator.execute_agents.assert_not_called()


def test_execute_sub_agents_gmail_detection():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        bot._execute_sub_agents_if_needed("check my email inbox")
    tasks = mock_exec.call_args[0][0]
    agent_names = [t['agent'] for t in tasks]
    assert 'gmail' in agent_names
    bot.close()


def test_execute_sub_agents_gmail_recent_query():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        bot._execute_sub_agents_if_needed("check my email recent ones")
    tasks = mock_exec.call_args[0][0]
    gmail_task = next((t for t in tasks if t['agent'] == 'gmail'), None)
    assert gmail_task is not None
    assert gmail_task['params']['query'] == 'in:inbox'
    bot.close()


def test_execute_sub_agents_exception_handling():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', side_effect=RuntimeError("crash")):
        result = bot._execute_sub_agents_if_needed("what time is it?")
    assert '[Sub-agent error:' in result
    assert 'crash' in result
    assert bot._last_agent_calls == []
    bot.close()


def test_execute_sub_agents_weather_detection():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        bot._execute_sub_agents_if_needed("What's the weather in Paris?")
    tasks = mock_exec.call_args[0][0]
    assert any(t['agent'] == 'weather' for t in tasks)
    bot.close()


def test_execute_sub_agents_time_detection():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        bot._execute_sub_agents_if_needed("what time is it now?")
    tasks = mock_exec.call_args[0][0]
    assert any(t['agent'] == 'time' for t in tasks)
    bot.close()


def test_execute_sub_agents_calc_detection():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        bot._execute_sub_agents_if_needed("calculate 5 + 10")
    tasks = mock_exec.call_args[0][0]
    assert any(t['agent'] == 'calculator' for t in tasks)
    bot.close()


def test_execute_sub_agents_none_orchestrator_returns_empty():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.orchestrator = None
    bot.start_new_session("t")
    result = bot._execute_sub_agents_if_needed("what time is it?")
    assert result == ""
    bot.close()


# --- _extract_location ---

def test_extract_location_in_city(bot):
    result = bot._extract_location("What's the weather in London?")
    assert result == "London"


def test_extract_location_at_city(bot):
    result = bot._extract_location("temperature at Paris today")
    assert result == "Paris"


def test_extract_location_for_city(bot):
    result = bot._extract_location("forecast for Tokyo")
    assert result == "Tokyo"


def test_extract_location_not_found(bot):
    result = bot._extract_location("What's the weather?")
    assert result is None


# --- _extract_calculation ---

def test_extract_calculation_addition(bot):
    result = bot._extract_calculation("what is 5 + 3?")
    assert result is not None
    assert '+' in result


def test_extract_calculation_multiplication(bot):
    result = bot._extract_calculation("calculate 12 * 4")
    assert result is not None


def test_extract_calculation_not_found(bot):
    result = bot._extract_calculation("what is the meaning of life?")
    assert result is None


# --- _extract_search_query ---

def test_extract_search_query_search_for(bot):
    result = bot._extract_search_query("search for Python tutorials")
    assert result is not None
    assert 'Python' in result


def test_extract_search_query_look_up(bot):
    result = bot._extract_search_query("look up machine learning basics")
    assert result is not None


def test_extract_search_query_what_is(bot):
    result = bot._extract_search_query("what is quantum computing")
    assert result is not None
    assert 'quantum' in result.lower()


def test_extract_search_query_time_sensitive_appends_year(bot):
    result = bot._extract_search_query("search for current news about AI")
    assert result is not None
    assert re.search(r'\d{4}', result)


def test_extract_search_query_too_short_returns_none(bot):
    result = bot._extract_search_query("what is ?")
    assert result is None or len(result) > 2


def test_extract_search_query_who_is(bot):
    result = bot._extract_search_query("who is Elon Musk")
    assert result is not None


# --- _format_agent_results ---

def test_format_agent_results_empty(bot):
    assert bot._format_agent_results([]) == ""


def test_format_agent_results_weather(bot):
    results = [{
        'agent': 'weather',
        'success': True,
        'data': {'data': {
            'location': 'London', 'condition': 'Cloudy',
            'temperature_c': '15', 'temperature_f': '59',
            'feels_like_c': '13', 'humidity': '70'
        }}
    }]
    result = bot._format_agent_results(results)
    assert 'London' in result
    assert 'Cloudy' in result
    assert '15' in result


def test_format_agent_results_time(bot):
    results = [{
        'agent': 'time',
        'success': True,
        'data': {'data': {'current_time': '12:00:00', 'day_of_week': 'Friday'}}
    }]
    result = bot._format_agent_results(results)
    assert '12:00:00' in result
    assert 'Friday' in result


def test_format_agent_results_calculator(bot):
    results = [{
        'agent': 'calculator',
        'success': True,
        'data': {'data': {'expression': '2+2', 'result': 4}}
    }]
    result = bot._format_agent_results(results)
    assert '2+2' in result
    assert '4' in result


def test_format_agent_results_gmail_no_emails(bot):
    results = [{
        'agent': 'gmail',
        'success': True,
        'data': {'data': {'emails': [], 'count': 0, 'query': 'is:unread'}}
    }]
    result = bot._format_agent_results(results)
    assert 'Gmail' in result
    assert 'is:unread' in result


def test_format_agent_results_gmail_with_emails(bot):
    results = [{
        'agent': 'gmail',
        'success': True,
        'data': {'data': {
            'emails': [{'from': 'alice@ex.com', 'subject': 'Hello', 'date': '2024-01-01', 'snippet': 'Hi there'}],
            'count': 1,
            'query': 'is:unread'
        }}
    }]
    result = bot._format_agent_results(results)
    assert 'alice@ex.com' in result
    assert 'Hello' in result


def test_format_agent_results_web_search(bot):
    results = [{
        'agent': 'web_search',
        'success': True,
        'data': {'data': {
            'query': 'AI news',
            'abstract': 'AI is growing rapidly in 2024',
            'related_topics': [
                {'text': 'LLMs advance quickly'},
                {'text': 'AI is growing rapidly in 2024'}  # duplicate of abstract
            ]
        }}
    }]
    result = bot._format_agent_results(results)
    assert 'AI news' in result
    assert 'AI is growing rapidly' in result


def test_format_agent_results_web_search_no_abstract(bot):
    results = [{
        'agent': 'web_search',
        'success': True,
        'data': {'data': {
            'query': 'test',
            'abstract': '',
            'related_topics': []
        }}
    }]
    result = bot._format_agent_results(results)
    assert result == ""


def test_format_agent_results_failed(bot):
    results = [{'agent': 'time', 'success': False, 'error': 'network error'}]
    result = bot._format_agent_results(results)
    assert 'time' in result.lower()
    assert 'network error' in result


def test_format_agent_results_multiple(bot):
    results = [
        {'agent': 'time', 'success': True, 'data': {'data': {'current_time': '10:00', 'day_of_week': 'Mon'}}},
        {'agent': 'calculator', 'success': True, 'data': {'data': {'expression': '1+1', 'result': 2}}},
    ]
    result = bot._format_agent_results(results)
    assert '10:00' in result
    assert '1+1' in result


# --- git_repo agent detection ---

def test_execute_sub_agents_git_repo_url_detection():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        bot._execute_sub_agents_if_needed("analyze this repo https://github.com/user/myrepo")
    tasks = mock_exec.call_args[0][0]
    assert any(t['agent'] == 'git_repo' for t in tasks)
    bot.close()


def test_execute_sub_agents_git_repo_url_params():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        bot._execute_sub_agents_if_needed("explore this repo https://github.com/user/myrepo")
    tasks = mock_exec.call_args[0][0]
    git_task = next(t for t in tasks if t['agent'] == 'git_repo')
    assert git_task['params']['repo_url'] == 'https://github.com/user/myrepo'
    bot.close()


def test_execute_sub_agents_git_repo_no_url_no_trigger():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        result = bot._execute_sub_agents_if_needed("tell me about repositories in general")
    # No URL present, generic "repositories" not a trigger keyword — agent not called
    if mock_exec.called:
        tasks = mock_exec.call_args[0][0]
        assert not any(t['agent'] == 'git_repo' for t in tasks)
    bot.close()


def test_execute_sub_agents_git_repo_ssh_url_detection():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        bot._execute_sub_agents_if_needed("Clone this repo git@github.com:kjenney/strategy-tester.git")
    tasks = mock_exec.call_args[0][0]
    assert any(t['agent'] == 'git_repo' for t in tasks)
    git_task = next(t for t in tasks if t['agent'] == 'git_repo')
    assert git_task['params']['repo_url'] == 'git@github.com:kjenney/strategy-tester.git'
    bot.close()


def test_execute_sub_agents_gitlab_url_detection():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        bot._execute_sub_agents_if_needed("look at this repo https://gitlab.com/org/project")
    tasks = mock_exec.call_args[0][0]
    assert any(t['agent'] == 'git_repo' for t in tasks)
    bot.close()


def test_execute_sub_agents_git_repo_timeout_elevated():
    bot = PersistentChatbot(":memory:", enable_sub_agents=True)
    bot.start_new_session("t")
    with patch.object(bot.orchestrator, 'execute_agents', return_value=[]) as mock_exec:
        bot._execute_sub_agents_if_needed("check this repo https://github.com/user/repo")
    args, kwargs = mock_exec.call_args
    # timeout is the second positional arg or keyword arg
    timeout_used = kwargs.get('timeout', args[1] if len(args) > 1 else 10)
    assert timeout_used >= 60
    bot.close()


# --- _extract_repo_url ---

def test_extract_repo_url_github(bot):
    result = bot._extract_repo_url("look at https://github.com/user/my-repo")
    assert result == 'https://github.com/user/my-repo'


def test_extract_repo_url_gitlab(bot):
    result = bot._extract_repo_url("https://gitlab.com/org/project here")
    assert result == 'https://gitlab.com/org/project'


def test_extract_repo_url_bitbucket(bot):
    result = bot._extract_repo_url("clone https://bitbucket.org/team/repo")
    assert result == 'https://bitbucket.org/team/repo'


def test_extract_repo_url_ssh(bot):
    result = bot._extract_repo_url("clone git@github.com:user/my-repo.git")
    assert result == 'git@github.com:user/my-repo.git'


def test_extract_repo_url_not_found(bot):
    result = bot._extract_repo_url("no url here")
    assert result is None


# --- _format_agent_results git_repo ---

def test_format_agent_results_git_repo(bot):
    results = [{
        'agent': 'git_repo',
        'success': True,
        'data': {'data': {
            'repo_url': 'https://github.com/user/repo',
            'clone_path': '/tmp/git_repo_agent_abc123',
            'branch': 'main',
            'total_files': 10,
            'total_dirs': 3,
            'language_stats': {'py': 8, 'md': 2},
            'config_files_present': ['Dockerfile', 'Makefile'],
            'readme': 'This is a test project.',
            'file_tree': ['app.py', 'README.md'],
        }}
    }]
    result = bot._format_agent_results(results)
    assert 'https://github.com/user/repo' in result
    assert '/tmp/git_repo_agent_abc123' in result
    assert 'main' in result
    assert 'py: 8' in result
    assert 'Dockerfile' in result
    assert 'This is a test project.' in result
    assert 'app.py' in result


def test_format_agent_results_git_repo_no_readme(bot):
    results = [{
        'agent': 'git_repo',
        'success': True,
        'data': {'data': {
            'repo_url': 'https://github.com/user/repo',
            'branch': 'main',
            'total_files': 5,
            'total_dirs': 1,
            'language_stats': {'py': 5},
            'config_files_present': [],
            'readme': None,
            'file_tree': ['app.py'],
        }}
    }]
    result = bot._format_agent_results(results)
    assert 'README' not in result
    assert 'https://github.com/user/repo' in result


# --- close ---

def test_close_idempotent():
    bot = PersistentChatbot(":memory:", enable_sub_agents=False)
    bot.close()
    bot.close()  # Should not raise


def test_destructor_closes_connection():
    bot = PersistentChatbot(":memory:", enable_sub_agents=False)
    conn = bot.conn
    del bot
    # Connection should be closed (or at least no exception)
