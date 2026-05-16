#!/usr/bin/env python3
"""
Persistent Chatbot Agent with SQLite Memory
A chatbot that remembers all conversations using SQLite database
"""

import sqlite3
from typing import List, Dict, Optional, Any
import ollama
from sub_agents import AgentOrchestrator
import re
import time


class PersistentChatbot:
    """A chatbot with persistent memory using SQLite"""

    def __init__(self, db_path: str = "chatbot_memory.db", enable_sub_agents: bool = True, model: str = "qwen3:8b"):
        """
        Initialize the chatbot with SQLite database

        Args:
            db_path: Path to the SQLite database file
            enable_sub_agents: Enable sub-agent functionality for API queries
            model: Ollama model name to use for generation
        """
        self.db_path = db_path
        self.current_session_id = None
        self.conn = None
        self.enable_sub_agents = enable_sub_agents
        self.model = model
        self._last_agent_calls: list = []
        self.orchestrator = AgentOrchestrator() if enable_sub_agents else None
        self.initialize_database()

    def initialize_database(self):
        """Create database tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_name TEXT
            )
        """)

        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        self.conn.commit()

    def start_new_session(self, session_name: Optional[str] = None) -> int:
        """
        Start a new conversation session

        Args:
            session_name: Optional name for the session

        Returns:
            session_id: The ID of the newly created session
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (session_name) VALUES (?)",
            (session_name,)
        )
        self.conn.commit()
        self.current_session_id = cursor.lastrowid
        return self.current_session_id

    def load_session(self, session_id: int) -> bool:
        """
        Load an existing session

        Args:
            session_id: The ID of the session to load

        Returns:
            bool: True if session exists, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        result = cursor.fetchone()

        if result:
            self.current_session_id = session_id
            # Update last active timestamp
            cursor.execute(
                "UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE session_id = ?",
                (session_id,)
            )
            self.conn.commit()
            return True
        return False

    def save_message(self, role: str, content: str):
        """
        Save a message to the current session

        Args:
            role: Either 'user' or 'assistant'
            content: The message content
        """
        if not self.current_session_id:
            self.start_new_session()

        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (self.current_session_id, role, content)
        )
        self.conn.commit()

    def get_conversation_history(self, session_id: Optional[int] = None, limit: Optional[int] = None) -> List[Dict]:
        """
        Retrieve conversation history for a session

        Args:
            session_id: The session ID to retrieve (defaults to current session)
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries
        """
        if session_id is None:
            session_id = self.current_session_id

        if not session_id:
            return []

        cursor = self.conn.cursor()
        query = """
            SELECT role, content, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, (session_id,))
        messages = []

        for row in cursor.fetchall():
            messages.append({
                'role': row[0],
                'content': row[1],
                'timestamp': row[2]
            })

        return messages

    def list_sessions(self) -> List[Dict]:
        """
        List all conversation sessions

        Returns:
            List of session dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.session_id, s.session_name, s.created_at, s.last_active,
                   COUNT(m.message_id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON s.session_id = m.session_id
            GROUP BY s.session_id
            ORDER BY s.last_active DESC
        """)

        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'session_id': row[0],
                'session_name': row[1],
                'created_at': row[2],
                'last_active': row[3],
                'message_count': row[4]
            })

        return sessions

    def search_messages(self, query: str) -> List[Dict]:
        """
        Search for messages containing specific text

        Args:
            query: Text to search for

        Returns:
            List of matching messages with session info
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT m.session_id, m.role, m.content, m.timestamp, s.session_name
            FROM messages m
            JOIN sessions s ON m.session_id = s.session_id
            WHERE m.content LIKE ?
            ORDER BY m.timestamp DESC
        """, (f'%{query}%',))

        results = []
        for row in cursor.fetchall():
            results.append({
                'session_id': row[0],
                'role': row[1],
                'content': row[2],
                'timestamp': row[3],
                'session_name': row[4]
            })

        return results

    def get_context_summary(self, session_id: Optional[int] = None, last_n: int = 10) -> str:
        """
        Get a summary of recent conversation context

        Args:
            session_id: Session to summarize (defaults to current)
            last_n: Number of recent messages to include

        Returns:
            Formatted string with conversation context
        """
        messages = self.get_conversation_history(session_id, limit=last_n)

        if not messages:
            return "No conversation history found."

        context = []
        for msg in messages:
            context.append(f"{msg['role'].upper()}: {msg['content']}")

        return "\n".join(context)

    def respond(self, user_input: str, model: Optional[str] = None) -> str:
        """
        Generate a response to user input (with memory context)

        Args:
            user_input: The user's message
            model: Override the default model for this response

        Returns:
            The chatbot's response
        """
        self._last_agent_calls = []
        # Save user's message
        self.save_message('user', user_input)

        # Get conversation context
        history = self.get_conversation_history(limit=10)

        response = self._generate_response(user_input, history, model=model or self.model)

        # Save assistant's response
        self.save_message('assistant', response)

        return response

    def _generate_response(self, user_input: str, history: List[Dict], model: Optional[str] = None) -> str:
        """
        Generate a response using Ollama.
        Searches across all previous conversations for relevant context.
        Uses sub-agents to fetch real-time information when needed.

        Args:
            user_input: User's current message
            history: Conversation history
            model: Ollama model name to use

        Returns:
            Response string from Ollama
        """
        if model is None:
            model = self.model
        try:
            # Execute sub-agents if needed for real-time information
            agent_results = self._execute_sub_agents_if_needed(user_input)

            # Search for relevant information from previous sessions
            relevant_context = self._get_cross_session_context(user_input)

            # Format conversation history for Ollama
            messages = []

            # Build system message with cross-session context if available
            system_content = 'You are a helpful AI assistant with persistent memory across all conversations. '

            # Add sub-agent results if available
            if agent_results:
                system_content += f'\n\nREAL-TIME INFORMATION FROM WEB SEARCH (fetched just now, treat as current):\n{agent_results}\n\n'
                system_content += ('IMPORTANT: The web search results above are live and current. '
                                   'You MUST answer using only these results for any real-time or current-events questions. '
                                   'Do NOT fall back to your training data or say information is unavailable — '
                                   'extract the answer directly from the search results above. ')

            if relevant_context:
                system_content += f'\n\nRELEVANT INFORMATION FROM PREVIOUS CONVERSATIONS:\n{relevant_context}\n\n'
                system_content += 'Use this information from previous conversations when relevant to the current question. '

            system_content += 'Be conversational, helpful, and make use of all available context when appropriate.'

            messages.append({
                'role': 'system',
                'content': system_content
            })

            # Add conversation history (excluding the current user message which is already in history)
            for msg in history[:-1]:  # Exclude last message as it's the current user input
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

            # Add the current user message
            messages.append({
                'role': 'user',
                'content': user_input
            })

            response = ollama.chat(model=model, messages=messages)

            return response['message']['content']

        except Exception as e:
            return f"Error generating response: {str(e)}. Make sure Ollama is running and the model '{model}' is installed (run: ollama pull {model})"

    def _get_cross_session_context(self, user_input: str, max_results: int = 5) -> str:
        """
        Search across all previous sessions for relevant context

        Args:
            user_input: The user's current message
            max_results: Maximum number of relevant messages to include

        Returns:
            Formatted string with relevant context from previous conversations
        """
        # Keywords that suggest the user is asking about previously shared information
        memory_keywords = ['my name', 'my', 'i told you', 'remember', 'what did i',
                          'my interests', 'my hobbies', 'about me', 'i like', 'i am',
                          'who am i', 'what am i', 'i said', 'i mentioned']

        user_input_lower = user_input.lower()

        # Check if this seems like a query about previous information
        is_memory_query = any(keyword in user_input_lower for keyword in memory_keywords)

        # If current session has history, don't search for basic info already in current session
        # But do search if it's a direct memory query
        if not is_memory_query and len(self.get_conversation_history(limit=3)) > 2:
            return ""

        # Extract key terms for searching (simple approach)
        search_terms = []

        # Common personal info patterns
        if 'name' in user_input_lower:
            search_terms.extend(['my name is', 'i am', "i'm", 'call me'])
        if any(word in user_input_lower for word in ['interest', 'like', 'hobby', 'hobbies', 'enjoy']):
            search_terms.extend(['i like', 'i love', 'i enjoy', 'interested in', 'hobby', 'hobbies'])
        if 'job' in user_input_lower or 'work' in user_input_lower:
            search_terms.extend(['i work', 'my job', 'profession'])

        # If no specific terms, search for user's own statements
        if not search_terms:
            search_terms = ['my name is', 'i am', 'i like', 'i love', 'i enjoy', 'i work']

        # Search for relevant messages from ALL sessions
        relevant_messages = []
        for term in search_terms:
            try:
                results = self.search_messages(term)
                # Only include user messages (things the user told us about themselves)
                for result in results:
                    if result['role'] == 'user' and result['session_id'] != self.current_session_id:
                        relevant_messages.append(result)
                        if len(relevant_messages) >= max_results:
                            break
            except:
                continue

            if len(relevant_messages) >= max_results:
                break

        # Format the relevant context
        if not relevant_messages:
            return ""

        # Remove duplicates and format
        seen = set()
        unique_messages = []
        for msg in relevant_messages:
            if msg['content'] not in seen:
                seen.add(msg['content'])
                unique_messages.append(msg)

        context_parts = []
        for msg in unique_messages[:max_results]:
            context_parts.append(f"- User previously said: \"{msg['content']}\"")

        return '\n'.join(context_parts)

    def _execute_sub_agents_if_needed(self, user_input: str) -> str:
        """
        Detect if the user query needs sub-agents and execute them

        Args:
            user_input: User's message

        Returns:
            Formatted string with sub-agent results, or empty string
        """
        if not self.enable_sub_agents or not self.orchestrator:
            return ""

        user_input_lower = user_input.lower()
        agent_tasks = []

        # Detect weather queries
        weather_keywords = ['weather', 'temperature', 'forecast', 'hot', 'cold', 'rain', 'sunny']
        if any(keyword in user_input_lower for keyword in weather_keywords):
            # Extract location if mentioned
            location = self._extract_location(user_input)
            agent_tasks.append({
                'agent': 'weather',
                'params': {'location': location or 'auto'}
            })

        # Detect time/date queries
        time_keywords = ['time', 'date', 'today', 'what day', 'current time', 'now']
        if any(keyword in user_input_lower for keyword in time_keywords):
            agent_tasks.append({
                'agent': 'time',
                'params': {}
            })

        # Detect calculation queries
        calc_patterns = [r'\d+\s*[\+\-\*\/]\s*\d+', r'calculate', r'compute', r'what is \d+']
        if any(re.search(pattern, user_input_lower) for pattern in calc_patterns):
            # Extract the mathematical expression
            expression = self._extract_calculation(user_input)
            if expression:
                agent_tasks.append({
                    'agent': 'calculator',
                    'params': {'expression': expression}
                })

        # Detect Gmail queries
        gmail_keywords = ['my email', 'my emails', 'check email', 'check my email', 'inbox',
                         'unread email', 'unread emails', 'gmail', 'new email', 'new emails',
                         'email summary', 'summarize email', 'summarize my email']
        if any(keyword in user_input_lower for keyword in gmail_keywords):
            query = 'is:unread'
            if 'all' in user_input_lower or 'recent' in user_input_lower:
                query = 'in:inbox'
            agent_tasks.append({
                'agent': 'gmail',
                'params': {'max_emails': 10, 'query': query}
            })

        # Detect web search queries
        search_keywords = ['search for', 'search the web', 'look up', 'find information', 'what is', 'who is', 'tell me about']
        # Only search if not asking about personal info or memory
        personal_keywords = ['my name', 'i told you', 'remember me']
        if (any(keyword in user_input_lower for keyword in search_keywords) and
            not any(keyword in user_input_lower for keyword in personal_keywords)):
            # Extract search query
            query = self._extract_search_query(user_input)
            if query:
                agent_tasks.append({
                    'agent': 'web_search',
                    'params': {'query': query, 'max_results': 5}
                })

        # Execute agents if any were triggered
        if not agent_tasks:
            return ""

        start = time.time()
        try:
            results = self.orchestrator.execute_agents(agent_tasks, timeout=10)
            results = results or []
            elapsed_ms = int((time.time() - start) * 1000)
            # latency_ms is wall-clock time for the full parallel batch, not per-agent
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

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text for weather queries"""
        # Simple patterns for location extraction
        patterns = [
            r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "in Boston"
            r'at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "at London"
            r'for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', # "for Paris"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _extract_calculation(self, text: str) -> Optional[str]:
        """Extract mathematical expression from text"""
        # Look for mathematical expressions
        pattern = r'([\d\+\-\*\/\(\)\.\s%]+)'
        matches = re.findall(pattern, text)

        for match in matches:
            match = match.strip()
            # Basic validation - must have at least one operator and number
            if any(op in match for op in ['+', '-', '*', '/', '%']) and any(c.isdigit() for c in match):
                return match

        return None

    def _extract_search_query(self, text: str) -> Optional[str]:
        """Extract search query from user input"""
        text_lower = text.lower()

        # Remove common question starters
        query = text
        for prefix in ['search the web to get', 'search the web for', 'search the web', 'search for', 'look up', 'find information about', 'tell me about', 'what is', 'who is']:
            if prefix in text_lower:
                idx = text_lower.index(prefix)
                query = text[idx + len(prefix):].strip()
                break

        # Clean up the query
        query = query.strip('?.,!').strip()

        # Normalize common misnomers
        import re as _re
        query = _re.sub(r'(?i)\bbillboard\s+top\s+100\b', 'Billboard Hot 100', query)

        # Append current year for time-sensitive queries so search engines return fresh results
        time_sensitive = ['current', 'latest', 'now', 'today', 'this week', 'right now']
        if any(w in query.lower() for w in time_sensitive):
            from datetime import date as _date
            query = f"{query} {_date.today().year}"

        return query if len(query) > 2 else None

    def _format_agent_results(self, results: List[Dict[str, Any]]) -> str:
        """Format sub-agent results for inclusion in the AI prompt"""
        if not results:
            return ""

        formatted_parts = []

        for result in results:
            agent_name = result.get('agent', 'unknown')

            if not result.get('success'):
                formatted_parts.append(f"[{agent_name} failed: {result.get('error', 'unknown error')}]")
                continue

            data = result.get('data', {})

            if agent_name == 'weather':
                if 'data' in data:
                    weather = data['data']
                    formatted_parts.append(
                        f"Weather for {weather.get('location', 'unknown')}: "
                        f"{weather.get('condition', 'N/A')}, "
                        f"{weather.get('temperature_c', 'N/A')}°C ({weather.get('temperature_f', 'N/A')}°F), "
                        f"Feels like {weather.get('feels_like_c', 'N/A')}°C, "
                        f"Humidity: {weather.get('humidity', 'N/A')}%"
                    )

            elif agent_name == 'time':
                if 'data' in data:
                    time_info = data['data']
                    formatted_parts.append(
                        f"Current date and time: {time_info.get('current_time', 'N/A')} "
                        f"({time_info.get('day_of_week', 'N/A')})"
                    )

            elif agent_name == 'calculator':
                if 'data' in data:
                    calc = data['data']
                    formatted_parts.append(
                        f"Calculation: {calc.get('expression', 'N/A')} = {calc.get('result', 'N/A')}"
                    )

            elif agent_name == 'gmail':
                if 'data' in data:
                    gmail = data['data']
                    emails = gmail.get('emails', [])
                    if not emails:
                        formatted_parts.append(f"Gmail: No emails found for query '{gmail.get('query', '')}'.")
                    else:
                        lines = [f"Gmail ({gmail.get('count', 0)} emails, query: '{gmail.get('query', '')}'):"]
                        for i, email in enumerate(emails, 1):
                            lines.append(
                                f"{i}. From: {email['from']} | Subject: {email['subject']} | "
                                f"Date: {email['date']}\n   Preview: {email['snippet']}"
                            )
                        formatted_parts.append('\n'.join(lines))

            elif agent_name == 'web_search':
                if 'data' in data:
                    search = data['data']
                    parts = []
                    if search.get('abstract'):
                        parts.append(search['abstract'])
                    for t in search.get('related_topics', []):
                        if t.get('text') and t['text'] != search.get('abstract'):
                            parts.append(t['text'])
                    if parts:
                        formatted_parts.append(
                            f"Web search results for '{search.get('query', 'N/A')}':\n" +
                            '\n'.join(f"- {p}" for p in parts)
                        )

        return '\n'.join(formatted_parts) if formatted_parts else ""

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __del__(self):
        """Ensure database connection is closed"""
        self.close()


def main():
    """Main function to run the chatbot"""
    print("=" * 60)
    print("Persistent Chatbot Agent with Memory")
    print("=" * 60)
    print()

    chatbot = PersistentChatbot()

    # Check for existing sessions
    sessions = chatbot.list_sessions()

    if sessions:
        print("Existing sessions found:")
        for i, session in enumerate(sessions[:5], 1):
            session_name = session['session_name'] or f"Session {session['session_id']}"
            print(f"  {i}. {session_name} - {session['message_count']} messages (Last active: {session['last_active']})")

        print(f"\nOptions:")
        print("  - Press Enter to start a new session")
        print("  - Enter a session number (1-5) to continue an existing session")

        choice = input("\nYour choice: ").strip()

        if choice.isdigit() and 1 <= int(choice) <= min(5, len(sessions)):
            selected_session = sessions[int(choice) - 1]
            chatbot.load_session(selected_session['session_id'])
            print(f"\nLoaded session: {selected_session['session_name'] or selected_session['session_id']}")
            print("\nPrevious conversation:")
            print("-" * 60)
            history = chatbot.get_conversation_history(limit=5)
            for msg in history:
                print(f"{msg['role'].upper()}: {msg['content']}")
            print("-" * 60)
        else:
            session_name = input("Enter a name for this session (optional): ").strip() or None
            chatbot.start_new_session(session_name)
            print("\nStarted new session!")
    else:
        session_name = input("Enter a name for this session (optional): ").strip() or None
        chatbot.start_new_session(session_name)
        print("\nStarted new session!")

    print("\nCommands:")
    print("  - Type your message to chat")
    print("  - Type 'history' to see conversation history")
    print("  - Type 'search <query>' to search messages")
    print("  - Type 'quit' or 'exit' to end")
    print()

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nChatbot: Goodbye! I've saved our conversation.")
                break

            if user_input.lower() == 'history':
                print("\n--- Conversation History ---")
                history = chatbot.get_conversation_history()
                for msg in history:
                    print(f"[{msg['timestamp']}] {msg['role'].upper()}: {msg['content']}")
                print("---------------------------")
                continue

            if user_input.lower().startswith('search '):
                query = user_input[7:]
                results = chatbot.search_messages(query)
                print(f"\n--- Search Results for '{query}' ---")
                if results:
                    for result in results[:10]:
                        print(f"[Session {result['session_id']}] {result['role'].upper()}: {result['content']}")
                else:
                    print("No results found.")
                print("---------------------------")
                continue

            # Get response
            response = chatbot.respond(user_input)
            print(f"\nChatbot: {response}")

        except KeyboardInterrupt:
            print("\n\nChatbot: Goodbye! I've saved our conversation.")
            break
        except Exception as e:
            print(f"\nError: {e}")

    chatbot.close()
    print("\nSession saved. Run again to continue or start a new conversation!")


if __name__ == "__main__":
    main()
