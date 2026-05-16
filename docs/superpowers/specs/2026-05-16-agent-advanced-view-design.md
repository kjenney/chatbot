# Agent Advanced View — Design Spec

**Date:** 2026-05-16  
**Status:** Approved

## Overview

Add a toggleable "Advanced View" to the chat page that reveals which sub-agents were called for each prompt, along with their pass/fail status and latency. Hidden by default; zero visual noise when off.

## Backend

### `chatbot_agent.py`

`_execute_sub_agents_if_needed()` currently returns only a formatted string for LLM injection. Change to also capture per-agent metadata:

```python
# Each entry in agent_metadata:
{"agent": "web_search", "success": True, "latency_ms": 342}
```

Wrap `orchestrator.execute_agents()` with `time.time()` to compute total latency per agent. Store metadata on the instance as `self._last_agent_calls: list` (reset to `[]` at the start of each `respond()` call).

`respond()` reads `self._last_agent_calls` after `_execute_sub_agents_if_needed()` — no signature change needed.

### `web_app.py`

`/api/chat` response adds `agents_called` field:

```json
{
  "success": true,
  "bot_response": "...",
  "session_id": 1,
  "agents_called": [
    {"agent": "web_search", "success": true, "latency_ms": 342},
    {"agent": "time", "success": true, "latency_ms": 12}
  ]
}
```

Empty list `[]` when no agents ran. Field is always present so the frontend can rely on it unconditionally.

## Frontend

### `chat.html`

Add toggle button to `.header-actions` (after the existing icon buttons):

```html
<button id="advanced-view-btn" class="btn btn-icon" title="Toggle Advanced View">
  <!-- eye SVG icon -->
</button>
```

### `chat.js`

- On init: restore toggle state from `localStorage.getItem('advancedView')` (`'true'`/`'false'`).
- Toggle handler: flip state, persist to `localStorage`, re-render agent panels on all existing messages.
- `addMessageToUI(role, content, timestamp, animate, agentsCalled)` — new optional `agentsCalled` param (default `[]`).
- Store `agentsCalled` on each bot message DOM node (via a `WeakMap` keyed on the element) so toggle can re-render without a round-trip.
- When advanced view is on and `agentsCalled.length > 0`, append agent panel to message. When off, remove panels.
- `handleSendMessage()` passes `data.agents_called` to `addMessageToUI()` for bot responses.
- `renderHistory()` has no agent data (history API doesn't store it) — no panel rendered for historical messages.

### Agent panel HTML (injected per bot message)

```html
<details class="agent-panel">
  <summary>2 agents called</summary>
  <div class="agent-pills">
    <span class="agent-pill success">web_search ✓ 342ms</span>
    <span class="agent-pill fail">weather ✗ timeout</span>
  </div>
</details>
```

`<details>`/`<summary>` handles expand/collapse natively — no JS required.

## Styling (`static/css/style.css`)

| Selector | Purpose |
|---|---|
| `.agent-panel` | Subtle `border-top`, `font-size: 0.75rem`, muted color |
| `.agent-panel summary` | `cursor: pointer`, `list-style: none`, styled as subtle link |
| `.agent-pills` | `display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px` |
| `.agent-pill` | `border-radius: 12px`, monospace font, `padding: 2px 8px` |
| `.agent-pill.success` | Green-tinted background (`#d1fae5` / `#065f46` text) |
| `.agent-pill.fail` | Red-tinted background (`#fee2e2` / `#991b1b` text) |
| `#advanced-view-btn.active` | Highlighted state matching existing `.btn-primary` palette |

No layout changes — panel sits inside existing message bubble, expands downward.

## Data Flow

```
User sends message
  → POST /api/chat
    → chatbot.respond()
      → _execute_sub_agents_if_needed()  [sets self._last_agent_calls]
      → LLM generates response
    → web_app reads self._last_agent_calls
    → returns agents_called in JSON
  → chat.js addMessageToUI(role, content, ts, animate, agents_called)
    → if advancedView ON and agents_called.length > 0: render .agent-panel
    → store agents_called in WeakMap for toggle re-render
```

## Out of Scope

- Agent data in conversation history (history API returns no agent metadata)
- Full result data from agents (only name, success, latency)
- Per-message toggle (global toggle only)
