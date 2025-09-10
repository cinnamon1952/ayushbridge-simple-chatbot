"""
Simple Flask app for AyushBridge Chatbot deployment on Render.
No vector database required - uses direct README.md content.
"""

import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from simple_chatbot import SimpleAyushBridgeChatbot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ayushbridge-simple-chatbot-2025')
CORS(app)

# Global chatbot instance
chatbot = None


def initialize_chatbot():
    """Initialize the simple chatbot."""
    global chatbot
    
    try:
        api_key = os.getenv('OPENROUTER_API_KEY')
        model_name = os.getenv('MODEL_NAME', 'deepseek/deepseek-chat-v3.1:free')
        
        if not api_key:
            logger.error("OpenRouter API key not configured")
            return False
        
        chatbot = SimpleAyushBridgeChatbot(api_key)
        chatbot.openrouter_client.model = model_name
        
        if chatbot.is_initialized:
            logger.info("✅ Simple chatbot initialized successfully")
            return True
        else:
            logger.error("❌ Failed to initialize chatbot")
            return False
            
    except Exception as e:
        logger.error(f"Error initializing chatbot: {str(e)}")
        return False


@app.route('/')
def index():
    """Main page with chatbot interface."""
    if 'session_id' not in session:
        session['session_id'] = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    
    chatbot_available = chatbot is not None and chatbot.is_initialized
    return render_template('simple_index.html', 
                         chatbot_available=chatbot_available,
                         session_id=session['session_id'])


@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """Chat API endpoint."""
    try:
        if not chatbot or not chatbot.is_initialized:
            return jsonify({
                'error': 'Chatbot is not available. Please check the configuration.',
                'success': False
            }), 503
        
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No data provided',
                'success': False
            }), 400
        
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({
                'error': 'Empty message',
                'success': False
            }), 400
        
        temperature = float(data.get('temperature', 0.7))
        
        # Debug: test context finding
        debug_context = chatbot._find_relevant_sections(user_message)
        logger.info(f"Debug - Context length: {len(debug_context)}")
        logger.info(f"Debug - First 200 chars: {debug_context[:200]}")
        
        # Get response from chatbot
        response = chatbot.chat(user_message, temperature=temperature)
        response['success'] = True
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': f'Internal server error: {str(e)}',
            'success': False
        }), 500


@app.route('/api/suggestions', methods=['GET'])
def suggestions_endpoint():
    """Get suggested questions."""
    suggestions = [
        "What is AyushBridge?",
        "How do I install and set up AyushBridge?",
        "What are the key features of AyushBridge?",
        "How does code translation work?",
        "What are the API endpoints available?",
        "How do I implement FHIR Bundle uploads?",
        "What are the authentication requirements?",
        "How does the auto-complete search work?",
        "What is the architecture of AyushBridge?",
        "How do I configure the database?",
        "What are the monitoring features?",
        "How do I contribute to the project?",
        "What are the compliance requirements?",
        "How does NAMASTE to ICD-11 translation work?",
        "What programming languages are supported?"
    ]
    
    return jsonify({
        'suggestions': suggestions,
        'success': True
    })


@app.route('/api/stats', methods=['GET'])
def stats_endpoint():
    """Get chatbot statistics."""
    try:
        if not chatbot:
            return jsonify({
                'stats': {
                    'is_initialized': False,
                    'error': 'Chatbot not available'
                },
                'success': True
            })
        
        stats = chatbot.get_stats()
        return jsonify({
            'stats': stats,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in stats endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/api/reset', methods=['POST'])
def reset_endpoint():
    """Reset conversation history."""
    try:
        if chatbot:
            chatbot.reset_conversation()
        
        return jsonify({
            'message': 'Conversation reset successfully',
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in reset endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/health')
def health_check():
    """Health check endpoint for Render."""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'chatbot_available': chatbot is not None and chatbot.is_initialized if chatbot else False,
        'version': '2.0.0-simple'
    }
    
    return jsonify(health_status)


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Endpoint not found',
        'success': False
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'success': False
    }), 500


if __name__ == '__main__':
    # Initialize chatbot on startup
    logger.info("🚀 Starting AyushBridge Simple Chatbot...")
    
    chatbot_ready = initialize_chatbot()
    if not chatbot_ready:
        logger.warning("⚠️ Chatbot initialization failed, but starting web server anyway")
    
    # Get configuration
    port = int(os.getenv('PORT', 5000))  # Render uses PORT env var
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
