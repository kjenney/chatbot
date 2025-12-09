# Persistent Chatbot Agent with Memory

An AI chatbot agent that has persistent memory using SQLite database. The chatbot remembers all conversations across sessions and can recall previous interactions.

**🚀 New: Beautiful Web Interface Available!** See [Quick Start](#quick-start) below.

## Features

- **AI-Powered Responses**: Uses Ollama with Qwen3:8b model for intelligent conversations
- **Persistent Memory**: All conversations are stored in SQLite database
- **Cross-Session Memory**: Remembers information across different conversation sessions
- **Sub-Agent Framework**: Plugin-based system that spawns separate processes to query APIs
  - **Auto-discovery**: Drop agent files in `agents/` directory - no code changes needed
  - Weather information (wttr.in)
  - Current time/date
  - Mathematical calculations
  - Web search (DuckDuckGo)
  - **Extensible**: Create custom agents in minutes
- **Session Management**: Create, load, and manage multiple conversation sessions
- **Conversation History**: Retrieve and display past conversations
- **Search Functionality**: Search through all messages across sessions
- **Context-Aware**: Automatically provides full conversation history to the AI model
- **Local & Private**: Runs completely offline using local Ollama models

## Installation

### Prerequisites

1. **Python 3.8+** (SQLite3 is included in Python standard library)
2. **Ollama** - Download and install from [ollama.ai](https://ollama.ai)
3. **Qwen3:8b model** - Pull the model with: `ollama pull qwen3:8b`

### Setup

```bash
# Clone or navigate to the project directory
cd local-agent-with-memory

# Create a virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Verify Ollama Installation

```bash
# Check if Ollama is running
ollama list

# If qwen3:8b is not installed, pull it
ollama pull qwen3:8b
```

## Quick Start

### Web Interface (Recommended)

Launch the modern web interface:

```bash
./run_web.sh
```

Then open your browser to: **http://localhost:7000**

Features:
- Beautiful, responsive chat UI
- Session management with sidebar
- Global search across all conversations
- Real-time typing indicators
- Works on desktop and mobile

See [WEB_INTERFACE.md](WEB_INTERFACE.md) for detailed documentation.

### Command Line Interface

Run the chatbot in interactive CLI mode:

**Note**: The chatbot includes sub-agent capabilities for real-time information:
- Ask about weather: "What's the weather in London?"
- Request calculations: "Calculate 42 * 17"
- Check time: "What time is it?"
- Web searches: "Tell me about Python programming"

```bash
# Option 1: Use the convenience script
./run.sh

# Option 2: Manually activate venv and run
source venv/bin/activate
python3 chatbot_agent.py
```

This will start an interactive chat session where you can:
- Continue previous conversations
- Start new sessions
- View conversation history
- Search through past messages

### Programmatic Usage

Use the chatbot in your own Python code:

```python
from chatbot_agent import PersistentChatbot

# Create a chatbot instance
chatbot = PersistentChatbot("my_chatbot.db")

# Start a new session
session_id = chatbot.start_new_session("My First Chat")

# Chat with the bot
response = chatbot.respond("Hello!")
print(response)

# View conversation history
history = chatbot.get_conversation_history()
for msg in history:
    print(f"{msg['role']}: {msg['content']}")

# Close the connection
chatbot.close()
```

## API Reference

### PersistentChatbot Class

#### Methods

- `__init__(db_path: str)`: Initialize chatbot with database path
- `start_new_session(session_name: str)`: Create a new conversation session
- `load_session(session_id: int)`: Load an existing session
- `save_message(role: str, content: str)`: Save a message to current session
- `get_conversation_history(session_id: int, limit: int)`: Get conversation history
- `list_sessions()`: List all conversation sessions
- `search_messages(query: str)`: Search for messages containing text
- `respond(user_input: str)`: Get chatbot response (saves both user input and response)
- `close()`: Close database connection

## Project Structure

```
local-agent-with-memory/
├── chatbot_agent.py       # Core chatbot with SQLite memory
├── sub_agents.py          # Sub-agent orchestrator
├── web_app.py             # Flask web server
├── run_web.sh             # Web interface launcher
├── run.sh                 # CLI launcher
├── agents/                # 🔌 Plugin directory
│   ├── __init__.py        # Auto-discovery system
│   ├── base_agent.py      # Base agent class
│   ├── weather_agent.py   # Weather plugin
│   ├── time_agent.py      # Time/date plugin
│   ├── calculator_agent.py # Calculator plugin
│   ├── web_search_agent.py # Search plugin
│   └── README.md          # Agent documentation
├── templates/
│   └── chat.html          # Web UI HTML template
├── static/
│   ├── css/style.css      # Web UI styling
│   └── js/chat.js         # Web UI JavaScript
├── example_usage.py       # Programmatic usage examples
├── test_ollama.py         # Test Ollama integration
├── test_sub_agents.py     # Test sub-agent functionality
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── PLUGIN_GUIDE.md        # Guide to creating custom agents
├── SUB_AGENTS.md          # Sub-agent documentation
├── WEB_INTERFACE.md       # Web interface documentation
├── QUICKSTART.md          # Quick start guide
└── *.db                   # SQLite databases (auto-created)
```

## Examples and Testing

### Quick Test

Verify that Ollama integration is working:

```bash
source venv/bin/activate
python3 test_ollama.py
```

This will run a quick test conversation to ensure the AI model is responding correctly.

### Full Examples

Run the example script to see all features in action:

```bash
source venv/bin/activate
python3 example_usage.py
```

This demonstrates:
- Basic conversation
- Session management
- Search functionality
- Memory persistence across restarts

**Note:** The example script uses simple rule-based responses. For AI-powered responses, use the main chatbot (`chatbot_agent.py`) or the test script (`test_ollama.py`).

## Database Schema

The chatbot uses two tables:

### sessions
- `session_id`: Primary key
- `created_at`: Session creation timestamp
- `last_active`: Last activity timestamp
- `session_name`: Optional session name

### messages
- `message_id`: Primary key
- `session_id`: Foreign key to sessions
- `role`: Either 'user' or 'assistant'
- `content`: Message content
- `timestamp`: Message timestamp

## Extending the Chatbot

The chatbot currently uses Ollama with the Qwen3:8b model. You can customize it in several ways:

### 1. Using a Different Ollama Model

Edit `chatbot_agent.py` line 303 to use a different model:

```python
response = ollama.chat(
    model='llama3.2',  # or 'mistral', 'gemma3:12b', etc.
    messages=messages
)
```

Available models: Run `ollama list` to see installed models, or visit [ollama.ai/library](https://ollama.ai/library)

### 2. Switching to Cloud AI Providers

Replace the `_generate_response()` method to use OpenAI, Anthropic, or other providers:

**OpenAI Example:**
```python
import openai

def _generate_response(self, user_input: str, history: List[Dict]) -> str:
    messages = [{"role": msg['role'], "content": msg['content']} for msg in history]
    messages.append({"role": "user", "content": user_input})

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages
    )
    return response.choices[0].message.content
```

**Anthropic Claude Example:**
```python
import anthropic

def _generate_response(self, user_input: str, history: List[Dict]) -> str:
    client = anthropic.Anthropic(api_key="your-api-key")
    messages = [{"role": msg['role'], "content": msg['content']} for msg in history]

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=messages
    )
    return response.content[0].text
```

### 3. Customizing System Prompts

Modify the system message in `chatbot_agent.py` line 284 to change the chatbot's personality or behavior:

```python
messages.append({
    'role': 'system',
    'content': 'You are a helpful coding assistant specialized in Python...'
})
```

### 4. Adding RAG (Retrieval-Augmented Generation)

Use the search functionality to retrieve relevant past conversations:

```python
def _generate_response(self, user_input: str, history: List[Dict]) -> str:
    # Search for relevant past conversations
    relevant = self.search_messages(user_input)

    # Include relevant context in system message
    context = "\n".join([f"{r['role']}: {r['content']}" for r in relevant[:5]])
    # ... use context in your prompt
```

## Commands (Interactive Mode)

- Type your message to chat with the bot
- `history` - Display full conversation history
- `search <query>` - Search for messages containing query
- `quit` or `exit` - End the session

## License

This project is open source and available for educational and commercial use.