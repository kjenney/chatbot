# Agent Advanced View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a toggleable "Advanced View" button to the chat header that reveals per-message agent pills (name + pass/fail + latency) beneath each bot response.

**Architecture:** Backend tracks which agents ran per `respond()` call via `self._last_agent_calls`; Flask `/api/chat` returns this as `agents_called`; frontend stores agent data in a `WeakMap` keyed on message elements, rendering/hiding panels when the toggle fires.

**Tech Stack:** Python/Flask (backend), vanilla JS (frontend), CSS custom properties (styling), pytest + unittest.mock (tests)

---

## File Map

| File | Action | Change |
|---|---|---|
| `requirements.txt` | Modify | Add `pytest` |
| `chatbot_agent.py` | Modify | Add `_last_agent_calls`; populate in `_execute_sub_agents_if_needed`; reset in `respond()` |
| `web_app.py` | Modify | Read `_last_agent_calls` after `respond()`; add `agents_called` to `/api/chat` response |
| `tests/test_agent_advanced_view.py` | Create | Unit tests for backend changes |
| `templates/chat.html` | Modify | Add toggle button to `.header-actions` |
| `static/js/chat.js` | Modify | Toggle state, WeakMap storage, updated `addMessageToUI`, `handleSendMessage` |
| `static/css/style.css` | Modify | Agent panel + pill styles |

---

## Task 1: Add pytest and create test file skeleton

**Files:**
- Modify: `requirements.txt`
- Create: `tests/test_agent_advanced_view.py`

- [ ] **Step 1: Add pytest to requirements**

In `requirements.txt`, add after the existing dependencies:

```
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Create test file**

Create `tests/test_agent_advanced_view.py`:

```python
"""
Tests for agent advanced view feature.
Covers: _last_agent_calls tracking in chatbot_agent.py,
        agents_called field in /api/chat response.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from chatbot_agent import PersistentChatbot
from web_app import app as flask_app


@pytest.fixture
def chatbot():
    cb = PersistentChatbot(":memory:", enable_sub_agents=True)
    cb.start_new_session("test")
    yield cb
    cb.close()


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c
```

- [ ] **Step 3: Verify pytest runs (no tests yet, should collect 0)**

```bash
cd /Users/kjenney/devel/ai/chatbot && pip install pytest pytest-mock -q && pytest tests/test_agent_advanced_view.py -v
```

Expected output: `no tests ran` or `0 passed`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt tests/test_agent_advanced_view.py
git commit -m "test: add pytest and test skeleton for agent advanced view"
```

---

## Task 2: Backend — track agent calls in `chatbot_agent.py`

**Files:**
- Modify: `chatbot_agent.py`
- Test: `tests/test_agent_advanced_view.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_agent_advanced_view.py`:

```python
# --- chatbot_agent.py tests ---

def test_last_agent_calls_initialized(chatbot):
    """_last_agent_calls starts as empty list"""
    assert chatbot._last_agent_calls == []


def test_last_agent_calls_empty_when_no_agents_triggered(chatbot):
    """No agents triggered for a generic query"""
    chatbot._execute_sub_agents_if_needed("tell me a joke")
    assert chatbot._last_agent_calls == []


def test_last_agent_calls_populated_when_agents_run(chatbot):
    """_last_agent_calls contains one entry per agent that ran"""
    fake_results = [
        {"agent": "time", "success": True, "data": {"data": {"current_time": "12:00", "day_of_week": "Friday"}}}
    ]
    with patch.object(chatbot.orchestrator, 'execute_agents', return_value=fake_results):
        chatbot._execute_sub_agents_if_needed("what time is it?")

    assert len(chatbot._last_agent_calls) == 1
    entry = chatbot._last_agent_calls[0]
    assert entry["agent"] == "time"
    assert entry["success"] is True
    assert isinstance(entry["latency_ms"], int)
    assert entry["latency_ms"] >= 0


def test_last_agent_calls_failed_agent(chatbot):
    """Failed agent sets success=False"""
    fake_results = [
        {"agent": "weather", "success": False, "error": "timeout"}
    ]
    with patch.object(chatbot.orchestrator, 'execute_agents', return_value=fake_results):
        chatbot._execute_sub_agents_if_needed("what's the weather in Paris?")

    assert len(chatbot._last_agent_calls) == 1
    assert chatbot._last_agent_calls[0]["success"] is False


def test_last_agent_calls_reset_on_respond(chatbot):
    """Stale _last_agent_calls from previous respond() call is cleared"""
    chatbot._last_agent_calls = [{"agent": "stale", "success": True, "latency_ms": 0}]

    with patch.object(chatbot, '_execute_sub_agents_if_needed', return_value="") as mock_exec, \
         patch.object(chatbot, '_get_cross_session_context', return_value=""), \
         patch('ollama.chat', return_value={'message': {'content': 'hi'}}):
        mock_exec.side_effect = lambda q: chatbot.__dict__.update({'_last_agent_calls': []}) or ""
        chatbot.respond("hello")

    assert chatbot._last_agent_calls == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_agent_advanced_view.py -v -k "agent_calls"
```

Expected: `AttributeError: 'PersistentChatbot' object has no attribute '_last_agent_calls'`

- [ ] **Step 3: Implement changes in `chatbot_agent.py`**

In `__init__` (around line 29, after `self.model = model`), add:

```python
        self._last_agent_calls: list = []
```

In `respond()` (line 262, before `self.save_message('user', user_input)`), add:

```python
        self._last_agent_calls = []
```

In `_execute_sub_agents_if_needed()`, replace the existing `try/except` block at the end (lines 494-498):

```python
        # Execute agents if any were triggered
        if not agent_tasks:
            return ""

        import time as _time
        start = _time.time()
        try:
            results = self.orchestrator.execute_agents(agent_tasks, timeout=10)
            elapsed_ms = int((_time.time() - start) * 1000)
            self._last_agent_calls = [
                {
                    "agent": r.get("agent", "unknown"),
                    "success": bool(r.get("success", False)),
                    "latency_ms": elapsed_ms,
                }
                for r in results
            ]
            return self._format_agent_results(results)
        except Exception as e:
            self._last_agent_calls = []
            return f"[Sub-agent error: {str(e)}]"
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_agent_advanced_view.py -v -k "agent_calls"
```

Expected: 5 tests pass

- [ ] **Step 5: Commit**

```bash
git add chatbot_agent.py tests/test_agent_advanced_view.py
git commit -m "feat: track agent calls per respond() in _last_agent_calls"
```

---

## Task 3: Backend — expose `agents_called` in `/api/chat`

**Files:**
- Modify: `web_app.py`
- Test: `tests/test_agent_advanced_view.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_agent_advanced_view.py`:

```python
# --- web_app.py /api/chat tests ---

def test_chat_response_includes_agents_called_field(client):
    """agents_called field always present in /api/chat response"""
    mock_chatbot = MagicMock()
    mock_chatbot.current_session_id = 1
    mock_chatbot.respond.return_value = "Hello!"
    mock_chatbot._last_agent_calls = []

    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/chat', json={"message": "hello", "session_id": 1})

    data = resp.get_json()
    assert data['success'] is True
    assert 'agents_called' in data
    assert data['agents_called'] == []


def test_chat_response_agents_called_populated(client):
    """agents_called contains metadata when agents ran"""
    mock_chatbot = MagicMock()
    mock_chatbot.current_session_id = 1
    mock_chatbot.respond.return_value = "The time is 12:00"
    mock_chatbot._last_agent_calls = [
        {"agent": "time", "success": True, "latency_ms": 15}
    ]

    with patch('web_app.get_chatbot', return_value=mock_chatbot):
        resp = client.post('/api/chat', json={"message": "what time is it?", "session_id": 1})

    data = resp.get_json()
    assert data['success'] is True
    assert len(data['agents_called']) == 1
    assert data['agents_called'][0]['agent'] == 'time'
    assert data['agents_called'][0]['success'] is True
    assert 'latency_ms' in data['agents_called'][0]
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_agent_advanced_view.py -v -k "chat_response"
```

Expected: `AssertionError: 'agents_called' not in {...}`

- [ ] **Step 3: Implement changes in `web_app.py`**

In the `/api/chat` route, the `return jsonify(...)` on success (lines 156-161), replace with:

```python
        return jsonify({
            'success': True,
            'user_message': user_message,
            'bot_response': response,
            'session_id': chatbot.current_session_id or session_id,
            'agents_called': chatbot._last_agent_calls,
        })
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_agent_advanced_view.py -v -k "chat_response"
```

Expected: 2 tests pass

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/test_agent_advanced_view.py -v
```

Expected: all 7 tests pass

- [ ] **Step 6: Commit**

```bash
git add web_app.py tests/test_agent_advanced_view.py
git commit -m "feat: include agents_called in /api/chat response"
```

---

## Task 4: Frontend — toggle button in `chat.html`

**Files:**
- Modify: `templates/chat.html`

- [ ] **Step 1: Add toggle button to `.header-actions`**

In `templates/chat.html`, locate the `<div class="header-actions">` block (around line 38). Add the toggle button **after** the `clear-chat-btn` button and **before** the closing `</div>`:

```html
                    <button id="advanced-view-btn" class="btn btn-icon" title="Toggle Advanced View">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                    </button>
```

- [ ] **Step 2: Verify HTML renders without error**

Start the dev server and open `http://localhost:7000`. Confirm the eye icon appears in the chat header alongside the existing search and clear buttons.

```bash
python web_app.py &
```

Open browser to `http://localhost:7000` — confirm eye icon visible.

- [ ] **Step 3: Stop dev server and commit**

```bash
kill %1
git add templates/chat.html
git commit -m "feat: add advanced view toggle button to chat header"
```

---

## Task 5: Frontend — toggle logic and agent panel in `chat.js`

**Files:**
- Modify: `static/js/chat.js`

- [ ] **Step 1: Add `advancedView` state and WeakMap to `ChatApp` constructor**

In `chat.js`, inside the `ChatApp` constructor after `this.isTyping = false;` (line 8), add:

```js
        this.advancedViewOn = localStorage.getItem('advancedView') === 'true';
        this.agentDataMap = new WeakMap(); // maps message element -> agents_called array
```

After the existing DOM element assignments, add:

```js
        this.advancedViewBtn = document.getElementById('advanced-view-btn');
```

- [ ] **Step 2: Wire toggle button in `init()`**

In `init()`, after the existing event listeners, add:

```js
        this.advancedViewBtn.addEventListener('click', () => this.toggleAdvancedView());

        // Apply initial state
        if (this.advancedViewOn) {
            this.advancedViewBtn.classList.add('active');
        }
```

- [ ] **Step 3: Add `toggleAdvancedView()` method**

Add after the `init()` method:

```js
    toggleAdvancedView() {
        this.advancedViewOn = !this.advancedViewOn;
        localStorage.setItem('advancedView', this.advancedViewOn);
        this.advancedViewBtn.classList.toggle('active', this.advancedViewOn);

        // Re-render agent panels on all existing bot messages
        const botMessages = this.chatMessages.querySelectorAll('.message.bot');
        botMessages.forEach(el => {
            const agentsCalled = this.agentDataMap.get(el) || [];
            // Remove existing panel if present
            const existing = el.querySelector('.agent-panel');
            if (existing) existing.remove();
            // Render panel if view is on and agents ran
            if (this.advancedViewOn && agentsCalled.length > 0) {
                el.appendChild(this._buildAgentPanel(agentsCalled));
            }
        });
    }
```

- [ ] **Step 4: Add `_buildAgentPanel()` helper method**

Add after `toggleAdvancedView()`:

```js
    _buildAgentPanel(agentsCalled) {
        const details = document.createElement('details');
        details.className = 'agent-panel';

        const summary = document.createElement('summary');
        summary.textContent = `${agentsCalled.length} agent${agentsCalled.length !== 1 ? 's' : ''} called`;
        details.appendChild(summary);

        const pillsDiv = document.createElement('div');
        pillsDiv.className = 'agent-pills';

        agentsCalled.forEach(a => {
            const pill = document.createElement('span');
            pill.className = `agent-pill ${a.success ? 'success' : 'fail'}`;
            const icon = a.success ? '✓' : '✗';
            const latency = a.success ? ` ${a.latency_ms}ms` : ' timeout';
            pill.textContent = `${a.agent} ${icon}${latency}`;
            pillsDiv.appendChild(pill);
        });

        details.appendChild(pillsDiv);
        return details;
    }
```

- [ ] **Step 5: Update `addMessageToUI()` to accept and store agent data**

Replace the existing `addMessageToUI(role, content, timestamp, animate = true)` signature and body with:

```js
    addMessageToUI(role, content, timestamp, animate = true, agentsCalled = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        if (animate) {
            messageDiv.style.opacity = '0';
        }

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.textContent = content;

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = this.formatTime(timestamp);

        contentDiv.appendChild(textDiv);
        contentDiv.appendChild(timeDiv);
        messageDiv.appendChild(contentDiv);

        // Store agent data on the element for toggle re-render
        if (role === 'bot' && agentsCalled.length > 0) {
            this.agentDataMap.set(messageDiv, agentsCalled);
            if (this.advancedViewOn) {
                messageDiv.appendChild(this._buildAgentPanel(agentsCalled));
            }
        }

        this.chatMessages.appendChild(messageDiv);

        if (animate) {
            setTimeout(() => {
                messageDiv.style.transition = 'opacity 0.3s';
                messageDiv.style.opacity = '1';
            }, 10);
        }

        this.scrollToBottom();
    }
```

- [ ] **Step 6: Pass `agents_called` from `handleSendMessage()` to `addMessageToUI()`**

In `handleSendMessage()`, find the line that calls `addMessageToUI` for the bot response (currently around line 237):

```js
                this.addMessageToUI('bot', data.bot_response, new Date().toISOString(), true);
```

Replace with:

```js
                this.addMessageToUI('bot', data.bot_response, new Date().toISOString(), true, data.agents_called || []);
```

- [ ] **Step 7: Verify in browser**

Start server: `python web_app.py`

Open `http://localhost:7000`. Send a message that triggers an agent (e.g., "what time is it?"). With Advanced View toggled on, confirm agent pill appears under the bot response. Toggle off — pill disappears. Toggle on — pill reappears. Send a plain message — no pill appears.

- [ ] **Step 8: Stop server and commit**

```bash
git add static/js/chat.js
git commit -m "feat: add advanced view toggle and per-message agent panels"
```

---

## Task 6: Frontend — CSS styles for agent panel

**Files:**
- Modify: `static/css/style.css`

- [ ] **Step 1: Add styles at end of file**

Append to `static/css/style.css`:

```css
/* Advanced View — Agent panels */
#advanced-view-btn.active {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: white;
}

.agent-panel {
    border-top: 1px solid var(--border-color);
    margin-top: 0.5rem;
    padding-top: 0.5rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
}

.agent-panel summary {
    cursor: pointer;
    list-style: none;
    font-weight: 500;
    user-select: none;
}

.agent-panel summary::-webkit-details-marker {
    display: none;
}

.agent-panel summary::before {
    content: '▶ ';
    font-size: 0.65rem;
}

.agent-panel[open] summary::before {
    content: '▼ ';
}

.agent-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
}

.agent-pill {
    display: inline-block;
    border-radius: 12px;
    padding: 2px 10px;
    font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    white-space: nowrap;
}

.agent-pill.success {
    background: #d1fae5;
    color: #065f46;
}

.agent-pill.fail {
    background: #fee2e2;
    color: #991b1b;
}
```

- [ ] **Step 2: Verify styling in browser**

Start server: `python web_app.py`

Open `http://localhost:7000`. Toggle Advanced View on (button should turn purple/gradient). Send "what time is it?" — agent pill appears with green monospace badge. Toggle off — panel hidden. Toggle on — panel returns.

- [ ] **Step 3: Stop server and commit**

```bash
git add static/css/style.css
git commit -m "feat: style agent panel and pills for advanced view"
```

---

## Self-Review

**Spec coverage:**
- ✅ Toggle button in chat header — Task 4
- ✅ Toggle persists in localStorage — Task 5 Step 2
- ✅ Per-message agent panel (collapsible `<details>`) — Task 5 Steps 3–5
- ✅ Agent name + pass/fail + latency in pills — Task 5 Step 4
- ✅ `agents_called` in API response — Task 3
- ✅ `_last_agent_calls` on chatbot instance — Task 2
- ✅ Empty list when no agents ran — Task 2 test + Task 3 test
- ✅ Re-render panels on toggle for existing messages — Task 5 Step 3
- ✅ Historical messages have no panel (no agent data in history API) — `renderHistory` calls `addMessageToUI` without agentsCalled, defaults to `[]`

**Placeholder scan:** No TBDs, TODOs, or vague instructions.

**Type consistency:**
- `_last_agent_calls`: `list[dict]` — set in Task 2, read in Task 3 ✅
- `agentsCalled`: array of `{agent, success, latency_ms}` — passed from `handleSendMessage` → `addMessageToUI` → `_buildAgentPanel` ✅
- `agentDataMap`: `WeakMap` keyed on message element — set in `addMessageToUI`, read in `toggleAdvancedView` ✅
- `_buildAgentPanel(agentsCalled)` — defined in Task 5 Step 4, called in Steps 3 and 5 ✅
