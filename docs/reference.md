# Reference

## API — PersistentChatbot

```python
from chatbot_agent import PersistentChatbot
```

### Constructor

```python
PersistentChatbot(db_path: str = "chatbot_memory.db", enable_sub_agents: bool = True)
```

### Methods

| Method | Description |
|--------|-------------|
| `start_new_session(session_name)` | Create a new conversation session, returns `session_id` |
| `load_session(session_id)` | Load an existing session, returns `bool` |
| `save_message(role, content)` | Save a message (`"user"` or `"assistant"`) to current session |
| `get_conversation_history(session_id, limit)` | Get messages for a session |
| `list_sessions()` | List all sessions with message counts |
| `search_messages(query)` | Full-text search across all sessions |
| `respond(user_input)` | Generate and save a response, returns `str` |
| `close()` | Close the database connection |

### Example

```python
from chatbot_agent import PersistentChatbot

chatbot = PersistentChatbot("my_chatbot.db")
session_id = chatbot.start_new_session("My First Chat")

response = chatbot.respond("Hello!")
print(response)

history = chatbot.get_conversation_history()
for msg in history:
    print(f"{msg['role']}: {msg['content']}")

chatbot.close()
```

---

## Database Schema

### sessions

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | INTEGER PK | Auto-increment primary key |
| `created_at` | TIMESTAMP | Session creation time |
| `last_active` | TIMESTAMP | Last message time |
| `session_name` | TEXT | Optional display name |

### messages

| Column | Type | Description |
|--------|------|-------------|
| `message_id` | INTEGER PK | Auto-increment primary key |
| `session_id` | INTEGER FK | References `sessions.session_id` |
| `role` | TEXT | `"user"` or `"assistant"` |
| `content` | TEXT | Message body |
| `timestamp` | TIMESTAMP | Message time |

---

## Project Structure

```
chatbot/
├── chatbot_agent.py       # Core chatbot — memory, session, sub-agent dispatch
├── sub_agents.py          # Agent orchestrator (multiprocessing)
├── web_app.py             # Flask web server
├── agents/                # Plugin directory — drop files here to add agents
│   ├── __init__.py        # Auto-discovery
│   ├── base_agent.py      # Base class for all agents
│   ├── weather_agent.py
│   ├── time_agent.py
│   ├── calculator_agent.py
│   └── web_search_agent.py
├── templates/
│   └── chat.html          # Web UI template
├── static/
│   ├── css/style.css
│   └── js/chat.js
├── tests/
│   ├── test_ollama.py
│   ├── test_sub_agents.py
│   └── test_cross_session_memory.py
├── docs/                  # MkDocs source
├── mkdocs.yml
├── requirements.txt
└── docs-requirements.txt
```

---

## CLI Commands

When running `python3 chatbot_agent.py` interactively:

| Command | Action |
|---------|--------|
| *(any text)* | Chat with the bot |
| `history` | Display full conversation history |
| `search <query>` | Search messages across all sessions |
| `quit` / `exit` | End session |

---

## Extending the Chatbot

### Switch Ollama Model

Edit `chatbot_agent.py` — change the model name in `_generate_response`:

```python
response = ollama.chat(
    model='llama3.2',  # or 'mistral', 'gemma3:12b', etc.
    messages=messages
)
```

Run `ollama list` to see installed models, or browse [ollama.ai/library](https://ollama.ai/library).

### Use a Cloud Provider

Replace `_generate_response()` in `chatbot_agent.py`:

=== "OpenAI"

    ```python
    import openai

    def _generate_response(self, user_input, history):
        messages = [{"role": m['role'], "content": m['content']} for m in history]
        messages.append({"role": "user", "content": user_input})
        response = openai.chat.completions.create(model="gpt-4o", messages=messages)
        return response.choices[0].message.content
    ```

=== "Anthropic Claude"

    ```python
    import anthropic

    def _generate_response(self, user_input, history):
        client = anthropic.Anthropic()
        messages = [{"role": m['role'], "content": m['content']} for m in history]
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=messages,
        )
        return response.content[0].text
    ```

### Customize the System Prompt

Edit the system message in `_generate_response`:

```python
system_content = 'You are a helpful coding assistant specialized in Python.'
```

### Add RAG

Use `search_messages` to pull relevant context from past sessions:

```python
relevant = self.search_messages(user_input)
context = "\n".join([f"{r['role']}: {r['content']}" for r in relevant[:5]])
# append context to system_content
```
