# Sub-Agent Framework Documentation

## Overview

The chatbot now includes a powerful sub-agent framework that allows it to **spawn separate processes** to query APIs and collect real-time information. This gives the chatbot capabilities beyond just conversation history - it can now fetch live data from the internet and perform calculations.

## Features

### ✨ Automatic Tool Detection

The chatbot automatically detects when you need real-time information and spawns the appropriate sub-agents:

**Weather Queries**
- "What's the weather like?"
- "Is it going to rain today?"
- "What's the temperature in London?"

**Time/Date Queries**
- "What time is it?"
- "What day is today?"
- "What's the current date?"

**Calculations**
- "Calculate 42 * 17 + 8"
- "What is 100 / 5?"
- "Compute 2 ** 10"

**Web Searches**
- "Search for machine learning"
- "Tell me about Python programming"
- "Who is Alan Turing?"

### 🚀 Parallel Execution

Sub-agents run in **separate processes** for:
- Fast parallel execution
- No blocking of the main chatbot
- Process isolation for safety
- Automatic timeout handling (10 seconds default)

### 🔌 Available Sub-Agents

1. **WeatherAgent** - Fetches current weather data using wttr.in API
2. **TimeAgent** - Gets current date/time information
3. **CalculatorAgent** - Performs mathematical calculations safely
4. **WebSearchAgent** - Searches the web using DuckDuckGo API

## Architecture

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Chatbot       │
│  (Main Process) │
└────────┬────────┘
         │
         ├──> Detects: Weather query
         ├──> Detects: Calculation
         └──> Detects: Time query
         │
         ▼
┌─────────────────┐
│ AgentOrchestrator│
└────────┬────────┘
         │
    ┌────┴────────────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌─────────┐
│ Weather │         │  Time   │  (Separate Processes)
│ Agent   │         │ Agent   │
└────┬────┘         └────┬────┘
     │                   │
     └─────────┬─────────┘
               │
               ▼
      ┌────────────────┐
      │  Results Queue │
      └────────┬───────┘
               │
               ▼
      ┌────────────────┐
      │  AI Response   │
      └────────────────┘
```

## Usage

### Automatic (Default)

Sub-agents are **enabled by default**. Just ask questions naturally:

```bash
python web_app.py
```

```
You: What's the weather in Tokyo?
Bot: The weather in Tokyo is currently partly cloudy with a
     temperature of 18°C (64°F)...

You: Calculate 156 * 23
Bot: The calculation 156 × 23 equals 3,588.
```

### Programmatic Usage

```python
from chatbot_agent import PersistentChatbot

# Enable sub-agents (default)
chatbot = PersistentChatbot(enable_sub_agents=True)
chatbot.start_new_session("Test")

# Automatic sub-agent execution
response = chatbot.respond("What's the weather like?")
print(response)  # Uses WeatherAgent automatically

# Disable sub-agents
chatbot_no_tools = PersistentChatbot(enable_sub_agents=False)
```

### Direct Sub-Agent Execution

```python
from sub_agents import execute_agent, AgentOrchestrator

# Execute a single agent
result = execute_agent('weather', location='Paris')
print(result['data'])

# Execute multiple agents in parallel
orchestrator = AgentOrchestrator()
results = orchestrator.execute_agents([
    {'agent': 'weather', 'params': {'location': 'Tokyo'}},
    {'agent': 'time', 'params': {}},
    {'agent': 'calculator', 'params': {'expression': '100 / 5'}}
], timeout=10)
```

## Creating Custom Sub-Agents

You can easily create your own sub-agents:

```python
from sub_agents import SubAgent
from typing import Dict, Any

class CustomAgent(SubAgent):
    def __init__(self):
        super().__init__(
            name="custom",
            description="My custom agent"
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Your custom logic here"""
        try:
            # Fetch data, call APIs, etc.
            result = do_something()

            return {
                'success': True,
                'data': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Register your agent
from sub_agents import AgentOrchestrator

orchestrator = AgentOrchestrator()
orchestrator.agents['custom'] = CustomAgent()
```

## How It Works

### 1. Query Detection

When you send a message, the chatbot analyzes it for keywords:

```python
# chatbot_agent.py
def _execute_sub_agents_if_needed(self, user_input: str) -> str:
    # Detect weather keywords
    if 'weather' in user_input.lower():
        agent_tasks.append({'agent': 'weather', 'params': {...}})

    # Detect time keywords
    if 'time' in user_input.lower():
        agent_tasks.append({'agent': 'time', 'params': {}})

    # Execute agents in parallel
    results = self.orchestrator.execute_agents(agent_tasks)
```

### 2. Parallel Execution

Each sub-agent runs in its own process:

```python
# sub_agents.py
def execute_agents(self, agent_tasks: List[Dict]) -> List[Dict]:
    processes = []
    result_queue = Queue()

    for task in agent_tasks:
        process = Process(
            target=agent.run_in_process,
            args=(result_queue,),
            kwargs=params
        )
        process.start()
        processes.append(process)

    # Collect results with timeout
    results = []
    for _ in processes:
        result = result_queue.get(timeout=10)
        results.append(result)

    return results
```

### 3. Result Integration

Sub-agent results are added to the AI's context:

```python
system_content = """
You are a helpful AI assistant.

REAL-TIME INFORMATION FROM SUB-AGENTS:
Weather for London: Partly cloudy, 14°C (57°F)
Current date and time: 2025-12-09 08:25:32 (Tuesday)

Use this information to answer the user's question accurately.
"""
```

## Testing

Run the comprehensive test suite:

```bash
source venv/bin/activate
python3 test_sub_agents.py
```

This tests:
- ✅ Individual agent execution
- ✅ Parallel agent execution
- ✅ Agent detection logic
- ✅ Full chatbot integration

## Performance

- **Parallel Execution**: Multiple agents run simultaneously
- **Timeout Protection**: Default 10-second timeout prevents hanging
- **Process Isolation**: Crashes in one agent don't affect others
- **Automatic Cleanup**: Processes are properly terminated

## API Keys

Current sub-agents use **free, public APIs** that don't require keys:
- Weather: wttr.in (free, no key needed)
- Web Search: DuckDuckGo (free, no key needed)
- Time: Local system time
- Calculator: Local Python evaluation

To add APIs that require keys, use environment variables:

```python
import os

class CustomAPIAgent(SubAgent):
    def execute(self, **kwargs):
        api_key = os.environ.get('MY_API_KEY')
        # Use api_key...
```

## Security

**Calculator Safety**: The calculator agent restricts allowed characters to prevent code injection:
```python
allowed_chars = set('0123456789+-*/().%** ')
if not all(c in allowed_chars for c in expression):
    return {'success': False, 'error': 'Invalid characters'}
```

**Process Isolation**: Each agent runs in a separate process, preventing:
- Memory corruption between agents
- Shared state issues
- One agent crashing affecting others

## Troubleshooting

### Sub-agents not triggering

Check that they're enabled:
```python
chatbot = PersistentChatbot(enable_sub_agents=True)
```

### Timeout errors

Increase the timeout:
```python
orchestrator.execute_agents(tasks, timeout=20)  # 20 seconds
```

### API failures

Sub-agents fail gracefully. The chatbot will still respond, just without the real-time data:
```
[weather failed: Connection timeout]
```

## Examples

### Weather Query
```
User: What's the weather in Paris?
Sub-Agent: WeatherAgent fetches data from wttr.in
Response: "The weather in Paris is partly cloudy, 15°C (59°F)..."
```

### Multi-Agent Query
```
User: What time is it and what's the weather?
Sub-Agents: TimeAgent + WeatherAgent (parallel)
Response: "It's currently 8:25 AM on Tuesday. The weather is
          partly cloudy with a temperature of 23°C..."
```

### Calculation
```
User: Calculate 42 * 17 + 8
Sub-Agent: CalculatorAgent evaluates expression
Response: "The calculation 42 × 17 + 8 equals 722."
```

## Future Enhancements

Potential additions:
- News API agent
- Stock price agent
- Translation agent
- Image generation agent
- Database query agent
- File system agent

The framework is extensible - you can add any agent that fits the `SubAgent` interface!
