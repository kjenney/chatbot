#!/usr/bin/env python3
"""
Example usage of the Persistent Chatbot Agent
Demonstrates programmatic interaction with the chatbot
"""

from chatbot_agent import PersistentChatbot


def demo_basic_usage():
    """Demonstrate basic chatbot usage"""
    print("=== Basic Usage Demo ===\n")

    # Create a chatbot instance
    chatbot = PersistentChatbot("demo_chatbot.db")

    # Start a new session
    session_id = chatbot.start_new_session("Demo Session 1")
    print(f"Started session: {session_id}\n")

    # Have a conversation
    messages = [
        "Hello!",
        "My name is Alice",
        "I love programming in Python",
        "What did I say about Python?",
    ]

    for msg in messages:
        print(f"User: {msg}")
        response = chatbot.respond(msg)
        print(f"Bot: {response}\n")

    chatbot.close()


def demo_session_management():
    """Demonstrate session management"""
    print("\n=== Session Management Demo ===\n")

    chatbot = PersistentChatbot("demo_chatbot.db")

    # Create multiple sessions
    session1 = chatbot.start_new_session("Morning Chat")
    chatbot.respond("Good morning!")
    chatbot.respond("I had coffee today")

    session2 = chatbot.start_new_session("Evening Chat")
    chatbot.respond("Good evening!")
    chatbot.respond("I'm working on a project")

    # List all sessions
    print("All Sessions:")
    sessions = chatbot.list_sessions()
    for session in sessions:
        print(f"  - Session {session['session_id']}: {session['session_name']} "
              f"({session['message_count']} messages)")

    # Load and view a previous session
    print(f"\nLoading session {session1}...")
    chatbot.load_session(session1)
    history = chatbot.get_conversation_history()

    print("\nConversation history:")
    for msg in history:
        print(f"  {msg['role'].upper()}: {msg['content']}")

    chatbot.close()


def demo_search():
    """Demonstrate search functionality"""
    print("\n=== Search Demo ===\n")

    chatbot = PersistentChatbot("demo_chatbot.db")

    # Search for messages containing specific keywords
    search_query = "Python"
    results = chatbot.search_messages(search_query)

    print(f"Search results for '{search_query}':")
    if results:
        for result in results:
            print(f"  [{result['session_name']}] {result['role']}: {result['content']}")
    else:
        print("  No results found")

    chatbot.close()


def demo_memory_persistence():
    """Demonstrate memory persistence across sessions"""
    print("\n=== Memory Persistence Demo ===\n")

    # First interaction
    print("First run:")
    chatbot1 = PersistentChatbot("demo_chatbot.db")
    session_id = chatbot1.start_new_session("Persistence Test")
    chatbot1.respond("Remember: The secret code is 12345")
    chatbot1.close()

    # Second interaction (simulating app restart)
    print("\nSecond run (after 'restart'):")
    chatbot2 = PersistentChatbot("demo_chatbot.db")
    chatbot2.load_session(session_id)

    print("Conversation history loaded:")
    history = chatbot2.get_conversation_history()
    for msg in history:
        print(f"  {msg['role'].upper()}: {msg['content']}")

    print("\nMemory persisted successfully!")
    chatbot2.close()


if __name__ == "__main__":
    print("Persistent Chatbot Agent - Example Usage\n")
    print("=" * 60)

    demo_basic_usage()
    demo_session_management()
    demo_search()
    demo_memory_persistence()

    print("\n" + "=" * 60)
    print("Demo complete! Check demo_chatbot.db for stored data.")
    print("\nTo run the interactive chatbot, use:")
    print("  python3 chatbot_agent.py")
