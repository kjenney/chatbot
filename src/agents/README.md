# Agents Directory

This directory contains all sub-agent plugins. Each agent is a self-contained module that can perform specific tasks.

## Plugin Architecture

The system **automatically discovers** all agents in this directory. To add a new agent:

1. Create a new file with the pattern `*_agent.py`
2. Import `BaseAgent` from `agents.base_agent`
3. Create a class that inherits from `BaseAgent`
4. Implement the `execute()` method
5. That's it! No other code changes needed.

## Example: Creating a New Agent

```python
# agents/news_agent.py
"""
News Agent
Fetches latest news headlines
"""

from typing import Dict, Any
import requests
from agents.base_agent import BaseAgent


class NewsAgent(BaseAgent):
    """Fetches latest news headlines"""

    def __init__(self):
        super().__init__(
            name="news",
            description="Fetches latest news headlines"
        )

    def execute(self, topic: str = "general", **kwargs) -> Dict[str, Any]:
        """
        Fetch news headlines

        Args:
            topic: News topic/category
        """
        try:
            # Your API call here
            # ...

            return {
                'success': True,
                'data': {
                    'headlines': [...]
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
```

Save this file and the agent is **automatically available** - no imports, no registration needed!

## Current Agents

### weather_agent.py
Fetches current weather information using wttr.in API
- **Trigger keywords**: weather, temperature, forecast, rain, sunny
- **Parameters**: `location` (city name or "auto")

### time_agent.py
Gets current date and time information
- **Trigger keywords**: time, date, today, now
- **Parameters**: None

### calculator_agent.py
Performs mathematical calculations safely
- **Trigger keywords**: calculate, compute, math expressions
- **Parameters**: `expression` (mathematical expression)

### web_search_agent.py
Searches the web using DuckDuckGo
- **Trigger keywords**: search for, tell me about, what is, who is
- **Parameters**: `query` (search query), `max_results` (default: 5)

## Base Agent API

All agents must inherit from `BaseAgent` and implement:

```python
def execute(self, **kwargs) -> Dict[str, Any]:
    """
    Execute the agent's task

    Returns:
        Dict with required keys:
        - 'success': bool - Whether the task succeeded
        - 'data': any - The result data (if success=True)
        - 'error': str - Error message (if success=False)
    """
    pass
```

### Return Format

**Success:**
```python
{
    'success': True,
    'data': {
        'your': 'data',
        'goes': 'here'
    }
}
```

**Failure:**
```python
{
    'success': False,
    'error': 'Description of what went wrong'
}
```

## Process Isolation

Each agent runs in a **separate process** for:
- Safety: Crashes don't affect other agents
- Performance: True parallel execution
- Timeout: Agents that hang are automatically terminated
- Security: Isolated memory space

## Testing Your Agent

```python
from agents import get_agent

# Get your agent
agent = get_agent('news')

# Test it
result = agent.execute(topic='technology')
print(result)
```

Or use the orchestrator:

```python
from sub_agents import execute_agent

result = execute_agent('news', topic='technology')
print(result)
```

## Auto-Discovery

The `__init__.py` file automatically:
1. Scans for all `*_agent.py` files
2. Imports each module
3. Finds classes that inherit from `BaseAgent`
4. Instantiates and registers them
5. Makes them available via `available_agents` dict

## Agent Naming Convention

- File: `*_agent.py` (required for auto-discovery)
- Class: `*Agent` (CamelCase)
- Agent name: Set in `__init__` (lowercase, no spaces)

Example:
- File: `stock_agent.py`
- Class: `StockAgent`
- Name: `"stock"`

## Dependencies

If your agent needs external packages:
1. Add them to `requirements.txt` in the project root
2. Document them in your agent's docstring
3. Handle import errors gracefully

Example:
```python
try:
    import some_package
except ImportError:
    some_package = None

class MyAgent(BaseAgent):
    def execute(self, **kwargs):
        if some_package is None:
            return {
                'success': False,
                'error': 'some_package not installed. Run: pip install some_package'
            }
        # ...
```

## Best Practices

1. **Timeout**: Keep `execute()` under 10 seconds
2. **Error Handling**: Always catch exceptions and return error dict
3. **Parameters**: Use `**kwargs` to accept optional parameters
4. **Documentation**: Add clear docstrings
5. **Testing**: Test your agent independently before integration
6. **Validation**: Validate input parameters
7. **Security**: Never execute untrusted code
8. **API Keys**: Use environment variables, not hardcoded keys

## Example: Adding a Translation Agent

```bash
# Create the file
touch agents/translation_agent.py
```

```python
# agents/translation_agent.py
"""Translation Agent - Translates text between languages"""

from typing import Dict, Any
from agents.base_agent import BaseAgent

class TranslationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="translate",
            description="Translates text between languages"
        )

    def execute(self, text: str, target_lang: str = "en", **kwargs) -> Dict[str, Any]:
        try:
            # Your translation logic here
            translated = translate_text(text, target_lang)

            return {
                'success': True,
                'data': {
                    'original': text,
                    'translated': translated,
                    'target_language': target_lang
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Translation failed: {str(e)}"
            }
```

Now your agent is automatically available:
```python
from sub_agents import execute_agent

result = execute_agent('translate', text='Hello', target_lang='es')
```

No other changes needed! 🎉
