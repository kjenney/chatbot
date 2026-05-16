# AI Chatbot with Memory

An AI chatbot with persistent memory, a real-time sub-agent framework, and a modern web interface — running entirely locally via Ollama.

## Features

- **AI-Powered Responses** — Ollama with selectable models (defaults to `qwen3:8b`)
- **Persistent Memory** — all conversations stored in SQLite across sessions
- **Cross-Session Memory** — recalls user details from past conversations
- **Sub-Agent Framework** — plugin-based system spawning parallel processes to query APIs
    - Auto-discovery: drop agent files in `agents/` — no code changes needed
    - Weather information (wttr.in)
    - Current time/date
    - Mathematical calculations
    - Web search (DuckDuckGo)
    - Extensible: create custom agents in minutes
- **Session Management** — create, load, and manage multiple conversation sessions
- **Conversation History** — retrieve and display past conversations
- **Search** — search all messages across all sessions
- **Context-Aware** — full conversation history sent to the model automatically
- **Local & Private** — runs completely offline via local Ollama models

## Built-in Sub-Agents

| Agent | Capability | API Used |
|-------|-----------|----------|
| WeatherAgent | Current conditions | wttr.in (free, no key) |
| TimeAgent | Current date/time | System clock |
| CalculatorAgent | Safe math evaluation | Local Python |
| WebSearchAgent | Live web search + page fetch | DuckDuckGo (free, no key) |

## Quick Links

- [Quick Start](QUICKSTART.md) — up and running in 5 minutes
- [Web Interface](WEB_INTERFACE.md) — UI features, API endpoints, deployment
- [Sub-Agents](SUB_AGENTS.md) — architecture and how agents work
- [Plugin Guide](PLUGIN_GUIDE.md) — create your own agents
- [Reference](reference.md) — API, database schema, project structure

## Tech Stack

- **LLM**: [Ollama](https://ollama.ai) — any locally installed model, selectable from the UI
- **Backend**: Python + Flask
- **Storage**: SQLite (standard library, zero config)
- **Search**: DuckDuckGo via `ddgs`
- **Frontend**: Vanilla JS + CSS

## Installation

```bash
git clone https://github.com/kjenney/chatbot.git
cd chatbot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
ollama pull qwen3:8b
python3 web_app.py
```

Then open **http://localhost:7000**.
