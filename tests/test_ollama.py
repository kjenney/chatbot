#!/usr/bin/env python3
"""
Quick test script to verify Ollama integration
"""

from chatbot_agent import PersistentChatbot

def test_ollama_integration():
    """Test that the chatbot works with Ollama"""
    print("Testing Ollama integration with qwen3:8b model...")
    print("=" * 60)

    # Create chatbot instance
    chatbot = PersistentChatbot("test_ollama.db")

    # Start a new session
    session_id = chatbot.start_new_session("Ollama Test Session")
    print(f"\nStarted session: {session_id}")

    # Test conversations
    test_messages = [
        "Hello! What's your name?",
        "Can you remember that I like programming in Python?",
        "What programming language did I just mention?",
    ]

    for i, msg in enumerate(test_messages, 1):
        print(f"\n[Test {i}]")
        print(f"User: {msg}")
        print("Bot: ", end="", flush=True)

        response = chatbot.respond(msg)
        print(response)
        print("-" * 60)

    # Check conversation history
    print("\n\nConversation History:")
    print("=" * 60)
    history = chatbot.get_conversation_history()
    for msg in history:
        print(f"{msg['role'].upper()}: {msg['content']}")

    chatbot.close()
    print("\n✓ Ollama integration test completed successfully!")
    print("\nYou can now run: python3 chatbot_agent.py")

if __name__ == "__main__":
    test_ollama_integration()
