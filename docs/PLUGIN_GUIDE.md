# Plugin Guide: Creating Custom Sub-Agents

## Quick Start

Creating a new agent is as simple as creating a single Python file in the `agents/` directory!

### 3-Step Process

1. **Create file**: `agents/your_agent.py`
2. **Inherit from BaseAgent**
3. **Implement `execute()`**

That's it! The agent is **automatically discovered** and ready to use.

## Example: Stock Price Agent

Let's create an agent that fetches stock prices:

```python
# agents/stock_agent.py
"""
Stock Agent
Fetches current stock prices
"""

from typing import Dict, Any
import requests
from agents.base_agent import BaseAgent


class StockAgent(BaseAgent):
    """Fetches stock prices"""

    def __init__(self):
        super().__init__(
            name="stock",  # This is how the agent is called
            description="Fetches current stock prices"
        )

    def execute(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch stock price

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
        """
        try:
            # Example API call (use your preferred stock API)
            url = f"https://api.example.com/stock/{symbol}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'data': {
                    'symbol': symbol,
                    'price': data['price'],
                    'change': data['change'],
                    'percent_change': data['percent_change']
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to fetch stock price: {str(e)}"
            }
```

**Save the file** - your agent is now live! No imports, no registration, no restarts needed.

## Testing Your Agent

### Method 1: Direct Execution

```python
from sub_agents import execute_agent

result = execute_agent('stock', symbol='AAPL')
print(result)
```

### Method 2: Through Chatbot

Just ask: "What's the stock price of AAPL?"

The chatbot will automatically detect and use your agent!

## File Structure

```
agents/
├── __init__.py              # Auto-discovery magic ✨
├── base_agent.py            # Base class (don't modify)
├── README.md                # Agent documentation
├── weather_agent.py         # Example agent
├── time_agent.py            # Example agent
├── calculator_agent.py      # Example agent
├── web_search_agent.py      # Example agent
└── your_new_agent.py        # Your custom agent! 🎉
```

## Naming Conventions

| Component | Format | Example |
|-----------|--------|---------|
| **File name** | `*_agent.py` | `stock_agent.py` |
| **Class name** | `*Agent` (CamelCase) | `StockAgent` |
| **Agent name** | lowercase, no spaces | `"stock"` |

## Agent Template

Copy-paste this template to create new agents:

```python
"""
[Agent Name] Agent
[One-line description]
"""

from typing import Dict, Any
from agents.base_agent import BaseAgent


class MyAgent(BaseAgent):
    """[Detailed description]"""

    def __init__(self):
        super().__init__(
            name="my_agent",  # Change this
            description="[Agent description]"  # Change this
        )

    def execute(self, param1: str, param2: int = 10, **kwargs) -> Dict[str, Any]:
        """
        [Method description]

        Args:
            param1: [Description]
            param2: [Description] (default: 10)
        """
        try:
            # Your logic here
            result = do_something(param1, param2)

            # Return success
            return {
                'success': True,
                'data': {
                    'your_key': result
                }
            }

        except Exception as e:
            # Return failure
            return {
                'success': False,
                'error': str(e)
            }
```

## Return Format

Your `execute()` method **must** return a dictionary with these keys:

### Success Response
```python
{
    'success': True,
    'data': {
        # Your result data goes here
        'key1': 'value1',
        'key2': 123
    }
}
```

### Error Response
```python
{
    'success': False,
    'error': 'Description of what went wrong'
}
```

## Auto-Detection in Chatbot

To make your agent trigger automatically, update `src/chatbot_agent.py`:

```python
# In _execute_sub_agents_if_needed() method

# Add detection for your agent
stock_keywords = ['stock', 'share price', 'ticker']
if any(keyword in user_input_lower for keyword in stock_keywords):
    # Extract the stock symbol
    symbol = extract_stock_symbol(user_input)  # Implement this
    agent_tasks.append({
        'agent': 'stock',
        'params': {'symbol': symbol}
    })
```

## Real-World Examples

### Example 1: News Agent

```python
# agents/news_agent.py
from typing import Dict, Any
import requests
from agents.base_agent import BaseAgent


class NewsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="news",
            description="Fetches latest news headlines"
        )

    def execute(self, category: str = "general", **kwargs) -> Dict[str, Any]:
        try:
            # Using NewsAPI (requires API key)
            api_key = os.environ.get('NEWS_API_KEY')
            if not api_key:
                return {
                    'success': False,
                    'error': 'NEWS_API_KEY environment variable not set'
                }

            url = f"https://newsapi.org/v2/top-headlines"
            params = {'category': category, 'apiKey': api_key}

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            headlines = [
                {
                    'title': article['title'],
                    'source': article['source']['name'],
                    'url': article['url']
                }
                for article in data['articles'][:5]
            ]

            return {
                'success': True,
                'data': {
                    'category': category,
                    'headlines': headlines
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
```

### Example 2: Translation Agent

```python
# agents/translation_agent.py
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
            # Using a translation library
            from googletrans import Translator

            translator = Translator()
            translation = translator.translate(text, dest=target_lang)

            return {
                'success': True,
                'data': {
                    'original_text': text,
                    'translated_text': translation.text,
                    'source_lang': translation.src,
                    'target_lang': target_lang
                }
            }
        except ImportError:
            return {
                'success': False,
                'error': 'googletrans not installed. Run: pip install googletrans==4.0.0-rc1'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
```

### Example 3: Database Query Agent

```python
# agents/database_agent.py
from typing import Dict, Any
import sqlite3
from agents.base_agent import BaseAgent


class DatabaseAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="database",
            description="Queries SQLite database"
        )

    def execute(self, query: str, db_path: str = "data.db", **kwargs) -> Dict[str, Any]:
        try:
            # Security: Only allow SELECT queries
            if not query.strip().upper().startswith('SELECT'):
                return {
                    'success': False,
                    'error': 'Only SELECT queries are allowed'
                }

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            conn.close()

            # Format results
            formatted_results = [
                dict(zip(columns, row))
                for row in results
            ]

            return {
                'success': True,
                'data': {
                    'query': query,
                    'results': formatted_results,
                    'count': len(formatted_results)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Database query failed: {str(e)}"
            }
```

## Best Practices

### 1. Timeout Handling
Keep `execute()` under 10 seconds (orchestrator timeout):

```python
response = requests.get(url, timeout=5)  # Good!
```

### 2. Error Handling
Always catch exceptions:

```python
try:
    result = risky_operation()
    return {'success': True, 'data': result}
except SpecificError as e:
    return {'success': False, 'error': f'Specific error: {e}'}
except Exception as e:
    return {'success': False, 'error': str(e)}
```

### 3. Input Validation
Validate parameters:

```python
def execute(self, email: str, **kwargs):
    if '@' not in email:
        return {'success': False, 'error': 'Invalid email format'}
    # Continue...
```

### 4. Environment Variables
Use environment variables for API keys:

```python
import os

api_key = os.environ.get('MY_API_KEY')
if not api_key:
    return {'success': False, 'error': 'MY_API_KEY not set'}
```

### 5. Graceful Degradation
Handle missing dependencies:

```python
try:
    import optional_package
except ImportError:
    optional_package = None

def execute(self, **kwargs):
    if optional_package is None:
        return {
            'success': False,
            'error': 'Install optional_package: pip install optional_package'
        }
```

## Testing

### Unit Test Your Agent

```python
# test_my_agent.py
from agents import get_agent

def test_my_agent():
    agent = get_agent('my_agent')

    # Test success case
    result = agent.execute(param1='test')
    assert result['success'] == True
    assert 'data' in result

    # Test error case
    result = agent.execute(param1='invalid')
    assert result['success'] == False
    assert 'error' in result

if __name__ == "__main__":
    test_my_agent()
    print("✓ All tests passed!")
```

### Integration Test

```python
from sub_agents import execute_agent

# Test through orchestrator
result = execute_agent('my_agent', param1='test')
print(result)
```

## Debugging

### Check if Agent is Loaded

```python
from agents import available_agents, list_agents

# List all agents
print("Available:", available_agents.keys())

# Get agent details
print("Details:", list_agents())
```

### Test Execution

```python
from agents import get_agent

agent = get_agent('my_agent')
result = agent.execute(test_param='value')
print(result)
```

### Common Issues

1. **Agent not found**: Check file name ends with `_agent.py`
2. **Import errors**: Check all dependencies are installed
3. **Timeout**: Reduce execution time or increase orchestrator timeout
4. **Process errors**: Check `run_in_process()` isn't overridden

## Advanced: Custom Processing

If you need custom multiprocessing behavior, override `run_in_process()`:

```python
def run_in_process(self, result_queue: Queue, **kwargs):
    try:
        # Custom pre-processing
        kwargs = preprocess(kwargs)

        # Execute
        result = self.execute(**kwargs)

        # Custom post-processing
        result = postprocess(result)

        result_queue.put({
            'agent': self.name,
            'success': True,
            'data': result
        })
    except Exception as e:
        result_queue.put({
            'agent': self.name,
            'success': False,
            'error': str(e)
        })
```

## FAQ

**Q: Do I need to restart the server after adding an agent?**
A: No! Agents are auto-discovered on import. Just reload the module in development.

**Q: Can I have multiple agents in one file?**
A: Yes, but each should be in its own file for clarity. All agents in a file will be discovered.

**Q: How do I pass complex parameters?**
A: Use `**kwargs` and extract what you need:
```python
def execute(self, **kwargs):
    config = kwargs.get('config', {})
    items = kwargs.get('items', [])
```

**Q: Can agents call other agents?**
A: Not directly (process isolation), but the orchestrator can run multiple agents in parallel.

**Q: How do I handle rate limiting?**
A: Implement retry logic or caching in your agent:
```python
import time

def execute(self, **kwargs):
    for attempt in range(3):
        try:
            return call_api()
        except RateLimitError:
            time.sleep(2 ** attempt)
    return {'success': False, 'error': 'Rate limited'}
```

## Resources

- **Base Agent**: `agents/base_agent.py`
- **Examples**: `agents/*_agent.py`
- **Tests**: `test_sub_agents.py`
- **Documentation**: `agents/README.md`
- **Architecture**: `SUB_AGENTS.md`

## Support

Create agents and they'll just work! The plugin system handles:
- ✅ Auto-discovery
- ✅ Registration
- ✅ Process isolation
- ✅ Parallel execution
- ✅ Timeout handling
- ✅ Error handling
- ✅ Cleanup

Focus on your agent logic - the framework does the rest! 🚀
