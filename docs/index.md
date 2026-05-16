# AI Chatbot with Memory

An AI chatbot with persistent memory, a real-time sub-agent framework, and a modern web interface — running entirely locally via Ollama.

## Features

| Feature | Description |
|---------|-------------|
| **Persistent Memory** | All conversations stored in SQLite across sessions |
| **Cross-Session Recall** | Remembers user details from past conversations |
| **Sub-Agent Framework** | Spawns parallel processes to fetch real-time data |
| **Web Interface** | Modern chat UI with session sidebar and search |
| **Extensible** | Drop a file in `agents/` to add a new capability |
| **Local & Private** | Runs fully offline via Ollama — no data leaves your machine |

## Built-in Sub-Agents

- **WeatherAgent** — current conditions via wttr.in
- **TimeAgent** — current date and time
- **CalculatorAgent** — safe math evaluation
- **WebSearchAgent** — live web search via DuckDuckGo

## Quick Links

- [Quick Start](QUICKSTART.md) — up and running in 5 minutes
- [Web Interface](WEB_INTERFACE.md) — UI features, API reference, deployment
- [Sub-Agents](SUB_AGENTS.md) — architecture and how agents work
- [Plugin Guide](PLUGIN_GUIDE.md) — create your own agents

## Tech Stack

- **LLM**: [Ollama](https://ollama.ai) with `qwen3:8b`
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
