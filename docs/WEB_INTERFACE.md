# Web Interface Guide

## Quick Start

Launch the web interface with one command:

```bash
python3 src/web_app.py
```

Then open your browser to: **http://localhost:7000**

## Features

### Modern Chat UI
- Clean, responsive design that works on desktop and mobile
- Real-time message updates
- Typing indicators while the AI is responding
- Auto-scrolling to latest messages
- Textarea auto-resize

### Model Selector
- Dropdown in the header lists all models installed in Ollama
- Switch models per-message — no restart required
- Defaults to `qwen3:8b` when available; falls back to the first installed model

### Session Management
- **Sidebar** showing all your conversation sessions
- Click any session to load and continue that conversation
- Create new sessions with custom names
- See message count and last activity time for each session

### Search Functionality
- **Global search** across all conversations
- Click the search icon in the header
- Search results show matching messages with context
- Click any result to jump to that session

### Keyboard Shortcuts
- **Enter**: Send message
- **Shift+Enter**: New line in message

## Architecture

### Backend (Flask)
- `src/web_app.py` - Main Flask application
- RESTful API endpoints for all chat operations
- Session management with Flask sessions
- Integrates with `src/chatbot_agent.py`

### Frontend
- `templates/chat.html` - Main HTML template
- `static/css/style.css` - Modern CSS styling
- `static/js/chat.js` - JavaScript for interactivity

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main chat interface |
| `/api/models` | GET | List installed Ollama models |
| `/api/sessions` | GET | List all sessions |
| `/api/sessions` | POST | Create new session |
| `/api/sessions/<id>` | GET | Load specific session |
| `/api/chat` | POST | Send message and get response (accepts optional `model` field) |
| `/api/history` | GET | Get current session history |
| `/api/search` | POST | Search all messages |
| `/benchmarks` | GET | Benchmark Reports UI |
| `/api/benchmarks/runs` | GET | List all benchmark runs with summary stats |
| `/api/benchmarks/runs/<run_id>` | GET | Case-level results for a specific run |

## Customization

### Change Colors
Edit `static/css/style.css` and modify the CSS variables:

```css
:root {
    --primary-color: #667eea;  /* Main theme color */
    --secondary-color: #764ba2; /* Gradient color */
    --bg-main: #f7fafc;         /* Background */
    /* ... more variables ... */
}
```

### Change Port
Edit `src/web_app.py` line 200:

```python
app.run(debug=True, host='0.0.0.0', port=7000)  # Change 7000 to your desired port
```

### Add Authentication
Add Flask-Login or similar to protect the interface:

```python
from flask_login import LoginManager, login_required

@app.route('/')
@login_required
def index():
    return render_template('chat.html')
```

### Enable HTTPS
Use a production WSGI server like Gunicorn with SSL:

```bash
pip install gunicorn
gunicorn --certfile=cert.pem --keyfile=key.pem -b 0.0.0.0:443 src.web_app:app
```

## Deployment

### Local Network Access
The web server runs on `0.0.0.0:7000`, making it accessible from other devices on your network.

Find your local IP:
```bash
# macOS/Linux
ifconfig | grep "inet "
# Then access from another device: http://YOUR_IP:7000
```

### Production Deployment

For production use, consider:

1. **Gunicorn** (Production WSGI server)
```bash
pip install gunicorn
PYTHONPATH=src gunicorn -w 4 -b 0.0.0.0:7000 web_app:app
```

2. **Nginx** (Reverse proxy)
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:7000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. **Docker** (Containerization)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV PYTHONPATH=/app/src
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:7000", "web_app:app"]
```

### Environment Variables
Set `FLASK_ENV=production` for production deployments:

```bash
export FLASK_ENV=production
python3 src/web_app.py
```

## Troubleshooting

### Port Already in Use
Change the port in `src/web_app.py` or kill the process using port 7000:

```bash
# Find process on port 7000
lsof -i :7000

# Kill it
kill -9 <PID>
```

### Ollama Not Responding
Make sure Ollama is running:

```bash
ollama list  # Should show installed models
ollama serve # Start Ollama if not running
```

### Database Locked
If you get database locked errors, make sure you're not running both the CLI and web interface simultaneously with the same database file. They use different databases by default:
- CLI: `chatbot_memory.db`
- Web: `web_chatbot.db`

## Security Notes

⚠️ **Important for production:**

1. Change the secret key in `src/web_app.py`:
```python
app.secret_key = 'your-secure-random-key-here'
```

2. Add authentication if exposing to the internet
3. Use HTTPS in production
4. Set proper CORS policies if needed
5. Implement rate limiting to prevent abuse

## Browser Compatibility

Tested and working on:
- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers (iOS Safari, Chrome Android)

Requires JavaScript enabled.
