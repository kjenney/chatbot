"""Unit tests for all agent classes and the agents plugin system."""
import re
import pytest
from unittest.mock import patch, MagicMock
from multiprocessing import Queue

from agents.base_agent import BaseAgent
from agents.calculator_agent import CalculatorAgent
from agents.time_agent import TimeAgent
from agents.weather_agent import WeatherAgent
from agents.web_search_agent import WebSearchAgent
from agents.gmail_agent import GmailAgent
from agents import get_agent, list_agents, discover_agents


# --- Helpers ---

class ConcreteAgent(BaseAgent):
    """Minimal concrete implementation for testing BaseAgent."""
    def __init__(self, fail=False):
        super().__init__(name="test_concrete", description="Test agent")
        self.fail = fail

    def execute(self, **kwargs):
        if self.fail:
            raise ValueError("deliberate failure")
        return {'success': True, 'data': 'ok'}


# --- BaseAgent ---

def test_base_agent_init():
    agent = ConcreteAgent()
    assert agent.name == "test_concrete"
    assert agent.description == "Test agent"


def test_base_agent_run_in_process_success():
    agent = ConcreteAgent()
    q = Queue()
    agent.run_in_process(q)
    result = q.get(timeout=2)
    assert result['agent'] == 'test_concrete'
    assert result['success'] is True
    assert result['data'] == {'success': True, 'data': 'ok'}


def test_base_agent_run_in_process_exception():
    agent = ConcreteAgent(fail=True)
    q = Queue()
    agent.run_in_process(q)
    result = q.get(timeout=2)
    assert result['agent'] == 'test_concrete'
    assert result['success'] is False
    assert 'deliberate failure' in result['error']


def test_base_agent_run_in_process_with_kwargs():
    class KwagAgent(BaseAgent):
        def __init__(self):
            super().__init__(name="kwarg_agent", description="Kwarg tester")
        def execute(self, value=None, **kwargs):
            return {'received': value}

    agent = KwagAgent()
    q = Queue()
    agent.run_in_process(q, value="hello")
    result = q.get(timeout=2)
    assert result['success'] is True
    assert result['data'] == {'received': 'hello'}


# --- CalculatorAgent ---

def test_calculator_addition():
    result = CalculatorAgent().execute(expression="2 + 3")
    assert result['success'] is True
    assert result['data']['result'] == 5


def test_calculator_subtraction():
    result = CalculatorAgent().execute(expression="10 - 4")
    assert result['success'] is True
    assert result['data']['result'] == 6


def test_calculator_multiplication():
    result = CalculatorAgent().execute(expression="7 * 6")
    assert result['success'] is True
    assert result['data']['result'] == 42


def test_calculator_division():
    result = CalculatorAgent().execute(expression="15 / 3")
    assert result['success'] is True
    assert result['data']['result'] == 5.0


def test_calculator_modulo():
    result = CalculatorAgent().execute(expression="10 % 3")
    assert result['success'] is True
    assert result['data']['result'] == 1


def test_calculator_power():
    result = CalculatorAgent().execute(expression="2 ** 8")
    assert result['success'] is True
    assert result['data']['result'] == 256


def test_calculator_stores_expression_in_result():
    expr = "3 + 4"
    result = CalculatorAgent().execute(expression=expr)
    assert result['data']['expression'] == expr


def test_calculator_invalid_chars():
    result = CalculatorAgent().execute(expression="import os")
    assert result['success'] is False
    assert 'invalid characters' in result['error']


def test_calculator_division_by_zero():
    result = CalculatorAgent().execute(expression="1 / 0")
    assert result['success'] is False
    assert 'Calculation failed' in result['error']


def test_calculator_complex_expression():
    result = CalculatorAgent().execute(expression="(3 + 4) * 2")
    assert result['success'] is True
    assert result['data']['result'] == 14


def test_calculator_name_and_description():
    agent = CalculatorAgent()
    assert agent.name == "calculator"
    assert "calculation" in agent.description.lower()


# --- TimeAgent ---

def test_time_agent_returns_success():
    result = TimeAgent().execute()
    assert result['success'] is True


def test_time_agent_has_required_fields():
    data = TimeAgent().execute()['data']
    assert 'current_time' in data
    assert 'date' in data
    assert 'time' in data
    assert 'day_of_week' in data
    assert 'timestamp' in data


def test_time_agent_current_time_format():
    data = TimeAgent().execute()['data']
    assert re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', data['current_time'])


def test_time_agent_date_format():
    data = TimeAgent().execute()['data']
    assert re.match(r'\d{4}-\d{2}-\d{2}', data['date'])


def test_time_agent_day_of_week_is_valid():
    data = TimeAgent().execute()['data']
    days = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'}
    assert data['day_of_week'] in days


def test_time_agent_timestamp_is_float():
    data = TimeAgent().execute()['data']
    assert isinstance(data['timestamp'], float)


def test_time_agent_name():
    assert TimeAgent().name == "time"


# --- WeatherAgent ---

def _mock_weather_response(temp_c='20', temp_f='68', condition='Sunny'):
    mock_data = {
        'current_condition': [{
            'temp_C': temp_c,
            'temp_F': temp_f,
            'weatherDesc': [{'value': condition}],
            'humidity': '55',
            'windspeedKmph': '12',
            'FeelsLikeC': '19',
            'FeelsLikeF': '66'
        }]
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_data
    return mock_resp


def test_weather_agent_success():
    agent = WeatherAgent()
    with patch('requests.get', return_value=_mock_weather_response()):
        result = agent.execute(location='London')
    assert result['success'] is True
    assert result['data']['location'] == 'London'
    assert result['data']['condition'] == 'Sunny'
    assert result['data']['temperature_c'] == '20'


def test_weather_agent_default_location():
    agent = WeatherAgent()
    with patch('requests.get', return_value=_mock_weather_response()):
        result = agent.execute()
    assert result['success'] is True
    assert result['data']['location'] == 'auto'


def test_weather_agent_all_fields_present():
    agent = WeatherAgent()
    with patch('requests.get', return_value=_mock_weather_response()):
        data = agent.execute(location='Paris')['data']
    for key in ('location', 'temperature_c', 'temperature_f', 'condition', 'humidity', 'wind_speed_kmh', 'feels_like_c', 'feels_like_f'):
        assert key in data, f"Missing field: {key}"


def test_weather_agent_request_exception():
    agent = WeatherAgent()
    with patch('requests.get', side_effect=Exception("network error")):
        result = agent.execute(location='London')
    assert result['success'] is False
    assert 'Failed to fetch weather' in result['error']


def test_weather_agent_http_error():
    agent = WeatherAgent()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("404")
    with patch('requests.get', return_value=mock_resp):
        result = agent.execute(location='Nowhere')
    assert result['success'] is False


def test_weather_agent_name():
    assert WeatherAgent().name == "weather"


# --- WebSearchAgent ---

def _make_ddgs_class(news=None, text=None, text_raises=None):
    """Return a mock DDGS class that behaves as a context manager."""
    mock_d = MagicMock()
    mock_d.news.return_value = news or []
    if text_raises:
        mock_d.text.side_effect = text_raises
    else:
        mock_d.text.return_value = text or []
    mock_d.__enter__ = MagicMock(return_value=mock_d)
    mock_d.__exit__ = MagicMock(return_value=False)
    mock_cls = MagicMock(return_value=mock_d)
    return mock_cls


def test_web_search_agent_success_text_only():
    agent = WebSearchAgent()
    text_results = [
        {'title': 'Python Guide', 'body': 'Python is great', 'href': 'https://python.org', 'date': ''}
    ]
    mock_cls = _make_ddgs_class(text=text_results)
    with patch('ddgs.DDGS', mock_cls), patch.object(agent, '_fetch_page_text', return_value=None):
        result = agent.execute(query='Python')
    assert result['success'] is True
    assert result['data']['query'] == 'Python'
    assert len(result['data']['related_topics']) == 1


def test_web_search_agent_with_news():
    agent = WebSearchAgent()
    news = [{'title': 'AI News Today', 'body': 'AI advances quickly', 'url': 'https://news.com', 'date': '2024-01-15'}]
    text = [{'title': 'AI Wikipedia', 'body': 'Overview of AI', 'href': 'https://en.wikipedia.org/wiki/AI', 'date': ''}]
    mock_cls = _make_ddgs_class(news=news, text=text)
    with patch('ddgs.DDGS', mock_cls), patch.object(agent, '_fetch_page_text', return_value="Wikipedia content"):
        result = agent.execute(query='AI 2024', max_results=5)
    assert result['success'] is True
    assert 'FULL ARTICLE CONTENT' in result['data']['abstract']


def test_web_search_agent_empty_results():
    agent = WebSearchAgent()
    mock_cls = _make_ddgs_class()
    with patch('ddgs.DDGS', mock_cls), patch.object(agent, '_fetch_page_text', return_value=None):
        result = agent.execute(query='xyzunlikelykeyword123')
    assert result['success'] is True
    assert result['data']['abstract'] == ''


def test_web_search_agent_deduplication():
    agent = WebSearchAgent()
    # Same title appears twice
    text = [
        {'title': 'Python Guide', 'body': 'Python is great', 'href': 'https://a.com', 'date': ''},
        {'title': 'Python Guide', 'body': 'Python is great', 'href': 'https://b.com', 'date': ''},
    ]
    mock_cls = _make_ddgs_class(text=text)
    with patch('ddgs.DDGS', mock_cls), patch.object(agent, '_fetch_page_text', return_value=None):
        result = agent.execute(query='Python', max_results=5)
    assert result['success'] is True
    assert len(result['data']['related_topics']) == 1


def test_web_search_agent_max_results_respected():
    agent = WebSearchAgent()
    text = [
        {'title': f'Result {i}', 'body': f'Body {i}', 'href': f'https://ex{i}.com', 'date': ''}
        for i in range(10)
    ]
    mock_cls = _make_ddgs_class(text=text)
    with patch('ddgs.DDGS', mock_cls), patch.object(agent, '_fetch_page_text', return_value=None):
        result = agent.execute(query='test', max_results=3)
    assert result['success'] is True
    assert len(result['data']['related_topics']) <= 3


def test_web_search_agent_text_raises_exception():
    agent = WebSearchAgent()
    mock_cls = _make_ddgs_class(text_raises=Exception("Search failed"))
    with patch('ddgs.DDGS', mock_cls):
        result = agent.execute(query='test')
    assert result['success'] is False
    assert 'Search failed' in result['error']


def test_web_search_agent_news_exception_continues():
    """News fetch failure is swallowed; text search still runs."""
    agent = WebSearchAgent()
    mock_d = MagicMock()
    mock_d.news.side_effect = Exception("news unavailable")
    mock_d.text.return_value = [
        {'title': 'Text Result', 'body': 'Some body', 'href': 'https://ex.com', 'date': ''}
    ]
    mock_d.__enter__ = MagicMock(return_value=mock_d)
    mock_d.__exit__ = MagicMock(return_value=False)
    mock_cls = MagicMock(return_value=mock_d)
    with patch('ddgs.DDGS', mock_cls), patch.object(agent, '_fetch_page_text', return_value=None):
        result = agent.execute(query='test')
    assert result['success'] is True


def test_web_search_agent_prefers_wikipedia_fetch():
    agent = WebSearchAgent()
    text = [
        {'title': 'News Article', 'body': 'News', 'href': 'https://news.com', 'date': '2024-01-01'},
        {'title': 'Wikipedia Article', 'body': 'Wiki', 'href': 'https://en.wikipedia.org/wiki/Test', 'date': ''},
    ]
    mock_cls = _make_ddgs_class(text=text)
    fetched_urls = []
    def fake_fetch(url, max_chars=1500):
        fetched_urls.append(url)
        return "wiki content" if 'wikipedia' in url else None

    with patch('ddgs.DDGS', mock_cls), patch.object(agent, '_fetch_page_text', side_effect=fake_fetch):
        result = agent.execute(query='test', max_results=5)
    # Wikipedia should be tried first
    if fetched_urls:
        assert 'wikipedia' in fetched_urls[0]


def test_web_search_agent_name():
    assert WebSearchAgent().name == "web_search"


# --- WebSearchAgent._fetch_page_text ---

def test_fetch_page_text_success():
    agent = WebSearchAgent()
    html = '<html><body><p>This is a long enough paragraph for the text extractor filter.</p></body></html>'
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    with patch('requests.get', return_value=mock_resp):
        result = agent._fetch_page_text('https://example.com')
    assert result is not None
    assert 'long enough paragraph' in result


def test_fetch_page_text_non_200():
    agent = WebSearchAgent()
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch('requests.get', return_value=mock_resp):
        result = agent._fetch_page_text('https://example.com/missing')
    assert result is None


def test_fetch_page_text_request_exception():
    agent = WebSearchAgent()
    with patch('requests.get', side_effect=Exception("connection refused")):
        result = agent._fetch_page_text('https://bad-url.com')
    assert result is None


def test_fetch_page_text_strips_scripts():
    agent = WebSearchAgent()
    html = '<html><head><script>alert("evil");</script></head><body><p>Real article content that is long enough.</p></body></html>'
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    with patch('requests.get', return_value=mock_resp):
        result = agent._fetch_page_text('https://example.com')
    if result:
        assert 'alert' not in result


def test_fetch_page_text_strips_nav():
    agent = WebSearchAgent()
    html = '<html><body><nav>Skip nav skip nav</nav><p>Main content that is long enough to pass the check.</p></body></html>'
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    with patch('requests.get', return_value=mock_resp):
        result = agent._fetch_page_text('https://example.com')
    if result:
        assert 'Skip nav' not in result


def test_fetch_page_text_max_chars():
    agent = WebSearchAgent()
    long_text = ' '.join(['word'] * 2000)
    html = f'<html><body><p>{long_text}</p></body></html>'
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    with patch('requests.get', return_value=mock_resp):
        result = agent._fetch_page_text('https://example.com', max_chars=100)
    if result:
        assert len(result) <= 100


def test_fetch_page_text_empty_body_returns_none():
    agent = WebSearchAgent()
    html = '<html><body></body></html>'
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    with patch('requests.get', return_value=mock_resp):
        result = agent._fetch_page_text('https://example.com')
    assert result is None


# --- GmailAgent ---

def test_gmail_agent_no_service_returns_error():
    agent = GmailAgent()
    with patch.object(agent, '_get_gmail_service', return_value=None):
        result = agent.execute()
    assert result['success'] is False
    assert 'not authenticated' in result['error'].lower()


def test_gmail_agent_no_messages():
    agent = GmailAgent()
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {'messages': []}
    with patch.object(agent, '_get_gmail_service', return_value=mock_service):
        result = agent.execute()
    assert result['success'] is True
    assert result['data']['emails'] == []
    assert result['data']['count'] == 0


def test_gmail_agent_with_one_message():
    agent = GmailAgent()
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        'messages': [{'id': 'msg001'}]
    }
    mock_detail = {
        'payload': {'headers': [
            {'name': 'From', 'value': 'alice@example.com'},
            {'name': 'Subject', 'value': 'Hello World'},
            {'name': 'Date', 'value': 'Mon, 1 Jan 2024'},
        ]},
        'snippet': 'This is the email preview text'
    }
    mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = mock_detail
    with patch.object(agent, '_get_gmail_service', return_value=mock_service):
        result = agent.execute(max_emails=5, query='is:unread')
    assert result['success'] is True
    emails = result['data']['emails']
    assert len(emails) == 1
    assert emails[0]['from'] == 'alice@example.com'
    assert emails[0]['subject'] == 'Hello World'
    assert emails[0]['snippet'] == 'This is the email preview text'


def test_gmail_agent_query_passed_correctly():
    agent = GmailAgent()
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {'messages': []}
    with patch.object(agent, '_get_gmail_service', return_value=mock_service):
        result = agent.execute(max_emails=3, query='in:inbox')
    assert result['data']['query'] == 'in:inbox'
    mock_service.users.return_value.messages.return_value.list.assert_called_with(
        userId='me', q='in:inbox', maxResults=3
    )


def test_gmail_agent_api_exception():
    agent = GmailAgent()
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.list.return_value.execute.side_effect = Exception("API rate limit")
    with patch.object(agent, '_get_gmail_service', return_value=mock_service):
        result = agent.execute()
    assert result['success'] is False
    assert 'Gmail fetch failed' in result['error']


def test_gmail_get_service_no_token_no_credentials():
    agent = GmailAgent()
    with patch('agents.gmail_agent.os.path.exists', return_value=False):
        result = agent._get_gmail_service()
    assert result is None


def test_gmail_agent_name():
    assert GmailAgent().name == "gmail"


# --- agents/__init__.py ---

def test_get_agent_returns_correct_agent():
    agent = get_agent('calculator')
    assert agent.name == 'calculator'
    assert isinstance(agent, CalculatorAgent)


def test_get_agent_time():
    agent = get_agent('time')
    assert agent.name == 'time'


def test_get_agent_unknown_raises_key_error():
    with pytest.raises(KeyError):
        get_agent('nonexistent_agent_xyz_123')


def test_list_agents_returns_dict():
    agents = list_agents()
    assert isinstance(agents, dict)


def test_list_agents_contains_known_agents():
    agents = list_agents()
    assert 'calculator' in agents
    assert 'time' in agents
    assert 'weather' in agents


def test_list_agents_values_are_strings():
    agents = list_agents()
    for name, desc in agents.items():
        assert isinstance(desc, str), f"Description for {name} is not a string"


def test_discover_agents_returns_dict():
    agents = discover_agents()
    assert isinstance(agents, dict)


def test_discover_agents_non_empty():
    agents = discover_agents()
    assert len(agents) > 0


def test_discover_agents_all_are_base_agent_instances():
    agents = discover_agents()
    for name, agent in agents.items():
        assert isinstance(agent, BaseAgent), f"{name} is not a BaseAgent"
