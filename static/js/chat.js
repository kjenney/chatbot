// Persistent Chatbot - Web Interface JavaScript
// Handles all chat interactions, session management, and UI updates

class ChatApp {
    constructor() {
        this.currentSessionId = null;
        this.isTyping = false;
        this.advancedViewOn = localStorage.getItem('advancedView') === 'true';
        this.agentDataMap = new WeakMap(); // maps message element -> agents_called array

        // DOM elements
        this.chatMessages = document.getElementById('chat-messages');
        this.chatForm = document.getElementById('chat-form');
        this.userInput = document.getElementById('user-input');
        this.sendBtn = document.getElementById('send-btn');
        this.sessionsList = document.getElementById('sessions-list');
        this.newSessionBtn = document.getElementById('new-session-btn');
        this.clearChatBtn = document.getElementById('clear-chat-btn');
        this.searchBtn = document.getElementById('search-btn');
        this.searchModal = document.getElementById('search-modal');
        this.closeSearchModal = document.getElementById('close-search-modal');
        this.searchInput = document.getElementById('search-input');
        this.searchResults = document.getElementById('search-results');
        this.modelSelect = document.getElementById('model-select');
        this.advancedViewBtn = document.getElementById('advanced-view-btn');

        this.init();
    }

    init() {
        // Load models and sessions on startup
        this.loadModels();
        this.loadSessions();

        // Event listeners
        this.chatForm.addEventListener('submit', (e) => this.handleSendMessage(e));
        this.newSessionBtn.addEventListener('click', () => this.createNewSession());
        this.clearChatBtn.addEventListener('click', () => this.clearChatView());
        this.searchBtn.addEventListener('click', () => this.openSearchModal());
        this.closeSearchModal.addEventListener('click', () => this.closeSearchModalHandler());
        this.searchInput.addEventListener('input', (e) => this.handleSearch(e));

        // Auto-resize textarea
        this.userInput.addEventListener('input', () => this.autoResizeTextarea());

        // Handle Enter key (send) vs Shift+Enter (new line)
        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.chatForm.dispatchEvent(new Event('submit'));
            }
        });

        // Close modal on outside click
        this.searchModal.addEventListener('click', (e) => {
            if (e.target === this.searchModal) {
                this.closeSearchModalHandler();
            }
        });

        this.advancedViewBtn.addEventListener('click', () => this.toggleAdvancedView());

        // Apply initial state
        if (this.advancedViewOn) {
            this.advancedViewBtn.classList.add('active');
        }
    }

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

    async loadModels() {
        try {
            const response = await fetch('/api/models');
            const data = await response.json();
            const models = data.models || [];

            if (models.length === 0) {
                this.modelSelect.innerHTML = '<option value="">No models found</option>';
                return;
            }

            const defaultModel = 'qwen3:8b';
            this.modelSelect.innerHTML = models.map(m => `
                <option value="${m}" ${m === defaultModel ? 'selected' : ''}>${m}</option>
            `).join('');

            // If default not in list, select first
            if (!models.includes(defaultModel)) {
                this.modelSelect.selectedIndex = 0;
            }
        } catch (error) {
            console.error('Error loading models:', error);
            this.modelSelect.innerHTML = '<option value="">Error loading models</option>';
        }
    }

    autoResizeTextarea() {
        this.userInput.style.height = 'auto';
        this.userInput.style.height = Math.min(this.userInput.scrollHeight, 150) + 'px';
    }

    async loadSessions() {
        try {
            const response = await fetch('/api/sessions');
            const data = await response.json();

            if (data.success) {
                this.renderSessions(data.sessions);
            } else {
                console.error('Failed to load sessions:', data.error);
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
            this.sessionsList.innerHTML = '<div class="loading">Error loading sessions</div>';
        }
    }

    renderSessions(sessions) {
        if (sessions.length === 0) {
            this.sessionsList.innerHTML = '<div class="loading">No sessions yet. Start a new chat!</div>';
            return;
        }

        this.sessionsList.innerHTML = sessions.map(session => `
            <div class="session-item ${session.session_id === this.currentSessionId ? 'active' : ''}"
                 data-session-id="${session.session_id}"
                 onclick="chatApp.loadSession(${session.session_id})">
                <div class="session-name">${this.escapeHtml(session.session_name || 'Chat ' + session.session_id)}</div>
                <div class="session-meta">
                    <span>${session.message_count || 0} messages</span>
                    <span>${this.formatDate(session.last_active)}</span>
                </div>
            </div>
        `).join('');
    }

    async loadSession(sessionId) {
        try {
            const response = await fetch(`/api/sessions/${sessionId}`);
            const data = await response.json();

            if (data.success) {
                this.currentSessionId = sessionId;
                this.clearChatView();
                this.renderHistory(data.history);
                this.loadSessions(); // Refresh to update active state
            } else {
                alert('Failed to load session: ' + data.error);
            }
        } catch (error) {
            console.error('Error loading session:', error);
            alert('Error loading session');
        }
    }

    async createNewSession() {
        const sessionName = prompt('Enter a name for this session (optional):');

        try {
            const response = await fetch('/api/sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: sessionName || undefined
                })
            });

            const data = await response.json();

            if (data.success) {
                this.currentSessionId = data.session_id;
                this.clearChatView();
                this.loadSessions();
            } else {
                alert('Failed to create session: ' + data.error);
            }
        } catch (error) {
            console.error('Error creating session:', error);
            alert('Error creating session');
        }
    }

    clearChatView() {
        this.chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">💬</div>
                <h2>Ready to Chat!</h2>
                <p>Start a conversation below. I'll remember everything we discuss.</p>
            </div>
        `;
    }

    renderHistory(history) {
        this.chatMessages.innerHTML = '';

        history.forEach(msg => {
            this.addMessageToUI(msg.role, msg.content, msg.timestamp, false);
        });

        this.scrollToBottom();
    }

    async handleSendMessage(e) {
        e.preventDefault();

        const message = this.userInput.value.trim();
        if (!message || this.isTyping) return;

        // Clear input and reset height
        this.userInput.value = '';
        this.userInput.style.height = 'auto';

        // Add user message to UI
        this.addMessageToUI('user', message, new Date().toISOString(), true);

        // Show typing indicator
        this.showTypingIndicator();
        this.isTyping = true;
        this.sendBtn.disabled = true;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message,
                    session_id: this.currentSessionId,
                    model: this.modelSelect.value || undefined
                })
            });

            const data = await response.json();

            // Remove typing indicator
            this.removeTypingIndicator();

            if (data.success) {
                // Update current session if it changed
                if (data.session_id !== this.currentSessionId) {
                    this.currentSessionId = data.session_id;
                    this.loadSessions();
                }

                // Add bot response to UI
                this.addMessageToUI('bot', data.bot_response, new Date().toISOString(), true, data.agents_called || []);
            } else {
                alert('Error: ' + data.error);
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.removeTypingIndicator();
            alert('Error sending message. Please try again.');
        } finally {
            this.isTyping = false;
            this.sendBtn.disabled = false;
            this.userInput.focus();
        }
    }

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

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot';
        typingDiv.id = 'typing-indicator';

        typingDiv.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;

        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    openSearchModal() {
        this.searchModal.classList.remove('hidden');
        this.searchInput.focus();
    }

    closeSearchModalHandler() {
        this.searchModal.classList.add('hidden');
        this.searchInput.value = '';
        this.searchResults.innerHTML = '<div class="search-placeholder">Enter a search term to find messages across all conversations</div>';
    }

    async handleSearch(e) {
        const query = e.target.value.trim();

        if (!query) {
            this.searchResults.innerHTML = '<div class="search-placeholder">Enter a search term to find messages across all conversations</div>';
            return;
        }

        if (query.length < 2) {
            this.searchResults.innerHTML = '<div class="search-placeholder">Type at least 2 characters to search</div>';
            return;
        }

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query })
            });

            const data = await response.json();

            if (data.success) {
                this.renderSearchResults(data.results);
            } else {
                this.searchResults.innerHTML = `<div class="search-placeholder">Error: ${data.error}</div>`;
            }
        } catch (error) {
            console.error('Error searching:', error);
            this.searchResults.innerHTML = '<div class="search-placeholder">Error performing search</div>';
        }
    }

    renderSearchResults(results) {
        if (results.length === 0) {
            this.searchResults.innerHTML = '<div class="search-placeholder">No results found</div>';
            return;
        }

        this.searchResults.innerHTML = results.map(result => `
            <div class="search-result-item" onclick="chatApp.loadSessionFromSearch(${result.session_id})">
                <div class="search-result-role">${result.role.toUpperCase()}</div>
                <div class="search-result-content">${this.escapeHtml(result.content)}</div>
                <div class="search-result-meta">
                    Session: ${this.escapeHtml(result.session_name || 'Session ' + result.session_id)} •
                    ${this.formatDate(result.timestamp)}
                </div>
            </div>
        `).join('');
    }

    loadSessionFromSearch(sessionId) {
        this.closeSearchModalHandler();
        this.loadSession(sessionId);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    }

    formatTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}

// Initialize the app when DOM is ready
let chatApp;
document.addEventListener('DOMContentLoaded', () => {
    chatApp = new ChatApp();
});
