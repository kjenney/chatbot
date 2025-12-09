#!/usr/bin/env python3
"""
Persistent Chatbot Agent with SQLite Memory
A chatbot that remembers all conversations using SQLite database
"""

import sqlite3
from typing import List, Dict, Optional
import ollama


class PersistentChatbot:
    """A chatbot with persistent memory using SQLite"""

    def __init__(self, db_path: str = "chatbot_memory.db"):
        """
        Initialize the chatbot with SQLite database

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.current_session_id = None
        self.conn = None
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

    def respond(self, user_input: str) -> str:
        """
        Generate a response to user input (with memory context)

        Args:
            user_input: The user's message

        Returns:
            The chatbot's response
        """
        # Save user's message
        self.save_message('user', user_input)

        # Get conversation context
        history = self.get_conversation_history(limit=10)

        # Simple response logic (can be replaced with AI model)
        response = self._generate_response(user_input, history)

        # Save assistant's response
        self.save_message('assistant', response)

        return response

    def _generate_response(self, user_input: str, history: List[Dict]) -> str:
        """
        Generate a response using Ollama with qwen3:8b model
        Searches across all previous conversations for relevant context

        Args:
            user_input: User's current message
            history: Conversation history

        Returns:
            Response string from Ollama
        """
        try:
            # Search for relevant information from previous sessions
            relevant_context = self._get_cross_session_context(user_input)

            # Format conversation history for Ollama
            messages = []

            # Build system message with cross-session context if available
            system_content = 'You are a helpful AI assistant with persistent memory across all conversations. '

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

            # Call Ollama API with qwen3:8b model
            response = ollama.chat(
                model='qwen3:8b',
                messages=messages
            )

            return response['message']['content']

        except Exception as e:
            # Fallback response if Ollama fails
            return f"I apologize, but I encountered an error generating a response: {str(e)}. Please make sure Ollama is running and the qwen3:8b model is installed (run: ollama pull qwen3:8b)"

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
