#!/usr/bin/env python3
"""
Web Interface for Persistent Chatbot Agent
Flask-based web application with modern chat UI
"""

from flask import Flask, render_template, request, jsonify, session, g
from chatbot_agent import PersistentChatbot
import os
from datetime import datetime
import ollama

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management


def get_chatbot():
    """Get a chatbot instance for the current request context"""
    if 'chatbot' not in g:
        g.chatbot = PersistentChatbot("web_chatbot.db")
    return g.chatbot


@app.teardown_appcontext
def close_chatbot(error):
    """Close the chatbot connection at the end of each request"""
    chatbot = g.pop('chatbot', None)
    if chatbot is not None:
        chatbot.close()


@app.route('/')
def index():
    """Render the main chat interface"""
    return render_template('chat.html')


@app.route('/api/models', methods=['GET'])
def get_models():
    """Get available Ollama models"""
    try:
        result = ollama.list()
        models = [m.model for m in result.models]
        return jsonify({'success': True, 'models': models})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'models': []}), 500


@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all conversation sessions"""
    try:
        chatbot = get_chatbot()
        sessions = chatbot.list_sessions()
        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new conversation session"""
    try:
        chatbot = get_chatbot()
        data = request.get_json()
        session_name = data.get('name', f'Chat {datetime.now().strftime("%Y-%m-%d %H:%M")}')

        session_id = chatbot.start_new_session(session_name)
        session['current_session_id'] = session_id

        return jsonify({
            'success': True,
            'session_id': session_id,
            'session_name': session_name
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sessions/<int:session_id>', methods=['GET'])
def load_session(session_id):
    """Load a specific session and get its history"""
    try:
        chatbot = get_chatbot()
        success = chatbot.load_session(session_id)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        session['current_session_id'] = session_id
        history = chatbot.get_conversation_history(session_id)

        return jsonify({
            'success': True,
            'session_id': session_id,
            'history': history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Send a message and get a response"""
    try:
        chatbot = get_chatbot()
        data = request.get_json()
        user_message = data.get('message', '').strip()
        model = data.get('model') or None

        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Message cannot be empty'
            }), 400

        # Ensure we have an active session
        session_id = data.get('session_id') or session.get('current_session_id')
        if session_id:
            chatbot.load_session(session_id)
        else:
            session_id = chatbot.start_new_session(f'Chat {datetime.now().strftime("%Y-%m-%d %H:%M")}')
            session['current_session_id'] = session_id

        # Get response from chatbot
        response = chatbot.respond(user_message, model=model)

        return jsonify({
            'success': True,
            'user_message': user_message,
            'bot_response': response,
            'session_id': chatbot.current_session_id or session_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get conversation history for current session"""
    try:
        chatbot = get_chatbot()
        session_id = session.get('current_session_id') or chatbot.current_session_id

        if not session_id:
            return jsonify({
                'success': True,
                'history': []
            })

        history = chatbot.get_conversation_history(session_id)

        return jsonify({
            'success': True,
            'history': history,
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/search', methods=['POST'])
def search():
    """Search through all messages"""
    try:
        chatbot = get_chatbot()
        data = request.get_json()
        query = data.get('query', '').strip()

        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query cannot be empty'
            }), 400

        results = chatbot.search_messages(query)

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session (optional feature for future implementation)"""
    # This would require adding a delete method to the chatbot class
    return jsonify({
        'success': False,
        'error': 'Delete functionality not yet implemented'
    }), 501


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    print("=" * 60)
    print("Persistent Chatbot - Web Interface")
    print("=" * 60)
    print("\nStarting web server...")
    print("Open your browser and navigate to: http://localhost:7000")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=7000)
