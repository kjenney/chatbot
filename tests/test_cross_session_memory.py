#!/usr/bin/env python3
"""
Test script to verify cross-session memory functionality
"""

from chatbot_agent import PersistentChatbot
import os

def test_cross_session_memory():
    """Test that the chatbot remembers information across different sessions"""

    # Clean up any existing test database
    test_db = "test_cross_session.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    print("=" * 60)
    print("Testing Cross-Session Memory")
    print("=" * 60)

    # Session 1: User introduces themselves
    print("\n📝 SESSION 1: User introduces themselves")
    print("-" * 60)
    chatbot = PersistentChatbot(test_db)
    session1_id = chatbot.start_new_session("Introduction Session")

    intro_message = "Hi. My name is Ken. I like to learn new things and I like to stay active and healthy."
    print(f"User: {intro_message}")

    response1 = chatbot.respond(intro_message)
    print(f"Bot: {response1}")

    chatbot.close()

    # Session 2: User asks about their information (NEW SESSION)
    print("\n\n📝 SESSION 2: User asks about previously shared info")
    print("-" * 60)
    chatbot2 = PersistentChatbot(test_db)
    session2_id = chatbot2.start_new_session("Memory Test Session")

    query_message = "What is my name and what are my interests?"
    print(f"User: {query_message}")

    response2 = chatbot2.respond(query_message)
    print(f"Bot: {response2}")

    # Check if the response includes the expected information
    print("\n" + "=" * 60)
    print("VERIFICATION:")
    print("-" * 60)

    response_lower = response2.lower()
    has_name = 'ken' in response_lower
    has_interests = ('learn' in response_lower or 'active' in response_lower or
                     'healthy' in response_lower or 'health' in response_lower)

    if has_name and has_interests:
        print("✅ SUCCESS: Bot remembered name and interests from previous session!")
    elif has_name:
        print("⚠️  PARTIAL: Bot remembered name but not interests")
    elif has_interests:
        print("⚠️  PARTIAL: Bot mentioned interests but not name")
    else:
        print("❌ FAILED: Bot did not recall information from previous session")

    print(f"\nName 'Ken' found: {has_name}")
    print(f"Interests mentioned: {has_interests}")

    chatbot2.close()

    # Cleanup
    print("\n" + "=" * 60)
    if os.path.exists(test_db):
        os.remove(test_db)
        print("✓ Test database cleaned up")

    print("\nTest complete!")

if __name__ == "__main__":
    test_cross_session_memory()
