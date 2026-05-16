# Quick Start Guide

Get your AI chatbot with persistent memory running in 5 minutes!

## 1. Prerequisites Check

Make sure you have these installed:

```bash
# Check Python version (need 3.8+)
python3 --version

# Check if Ollama is installed
ollama --version

# Check if qwen3:8b model is available
ollama list | grep qwen3
```

If you don't have Ollama or the model:
```bash
# Install Ollama from https://ollama.ai
# Then pull the model:
ollama pull qwen3:8b
```

## 2. Setup Environment

```bash
# Navigate to project directory
cd local-agent-with-memory

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## 3. Choose Your Interface

### Option A: Web Interface (Recommended)

```bash
python web_app.py
```

Then open: **http://localhost:7000**

✨ You'll get:
- Beautiful chat UI
- Session sidebar
- Search functionality
- Mobile-friendly design

### Option B: Command Line Interface

```bash
python3 chatbot_agent.py
```

Interactive terminal chat with full memory.

### Option C: Programmatic Usage

```python
from chatbot_agent import PersistentChatbot

chatbot = PersistentChatbot()
chatbot.start_new_session("My Chat")

response = chatbot.respond("Hello!")
print(response)

chatbot.close()
```

## 4. First Conversation

Try these to see the memory in action:

1. "Hi, my name is Alice and I love Python programming"
2. "What's my name?" → It remembers!
3. "What language do I like?" → It recalls!

## 5. Exploring Features

### Web Interface
- **New Chat**: Click "New Chat" button
- **Switch Sessions**: Click on any session in sidebar
- **Search**: Click search icon, type to find messages
- **History**: All messages automatically saved

### CLI Interface
- `history` - View conversation history
- `search <term>` - Search across all messages
- `quit` - Exit (conversation is saved)

## Common Tasks

### Start Fresh Session
```bash
# Web: Click "New Chat" button
# CLI: Start new run, or restart the app
```

### Search Old Conversations
```bash
# Web: Click search icon (magnifying glass)
# CLI: Type "search <your query>"
```

### Continue Previous Chat
```bash
# Web: Click the session in sidebar
# CLI: Select session number on startup
```

## Troubleshooting

### "Connection refused" / Ollama not responding

```bash
# Make sure Ollama is running
ollama serve

# In another terminal, test it:
ollama list
```

### "Module not found" errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "Port 7000 already in use"

```bash
# Find and kill the process
lsof -i :7000
kill -9 <PID>

# Or change port in web_app.py (line 200)
```

### Web interface not loading

```bash
# Check browser console (F12) for errors
# Make sure you're at http://localhost:7000 not https://
# Try a different browser
```

## Testing

Verify Ollama integration:

```bash
source venv/bin/activate
python3 tests/test_ollama.py
```

Run the full example script:

```bash
source venv/bin/activate
python3 cmd/example_usage.py
```

This demonstrates basic conversation, session management, search, and memory persistence.

## CLI Commands

When running the command line interface:

| Command | Action |
|---------|--------|
| *(any text)* | Chat with the bot |
| `history` | Display full conversation history |
| `search <query>` | Search messages across all sessions |
| `quit` / `exit` | End session |

## Next Steps

1. [Web Interface guide](WEB_INTERFACE.md) — deployment, customization, API endpoints
2. [Sub-Agents docs](SUB_AGENTS.md) — how real-time data fetching works
3. [Plugin Guide](PLUGIN_GUIDE.md) — create your own agents
4. [Reference](reference.md) — full API, database schema, extending with cloud providers
