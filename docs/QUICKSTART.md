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
./run_web.sh
```

Then open: **http://localhost:7000**

✨ You'll get:
- Beautiful chat UI
- Session sidebar
- Search functionality
- Mobile-friendly design

### Option B: Command Line Interface

```bash
./run.sh
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

## Next Steps

1. **Customize the AI**: Edit `chatbot_agent.py` line 303 to use different Ollama models
2. **Change appearance**: Edit `static/css/style.css` for web UI colors
3. **Add features**: Check out `WEB_INTERFACE.md` for deployment options
4. **Switch AI providers**: See README for OpenAI/Anthropic examples

## Need Help?

- 📖 Full docs: [README.md](README.md)
- 🌐 Web interface guide: [WEB_INTERFACE.md](WEB_INTERFACE.md)
- 💻 Code examples: `example_usage.py` and `test_ollama.py`

## File Structure

```
local-agent-with-memory/
├── chatbot_agent.py      # Core chatbot logic
├── web_app.py            # Flask web server
├── run_web.sh            # Web interface launcher
├── run.sh                # CLI launcher
├── templates/
│   └── chat.html         # Web UI template
├── static/
│   ├── css/style.css     # Styling
│   └── js/chat.js        # Frontend logic
└── *.db                  # SQLite databases (auto-created)
```

Happy chatting! 🚀
