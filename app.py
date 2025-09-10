"""
Flask web application for AyushBridge Chatbot.
Provides a web interface for interacting with the RAG-powered chatbot.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
from chatbot_core import AyushBridgeChatbot

# Load environment variables
load_dotenv('.env_chatbot')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ayushbridge-chatbot-secret-key-2025')
CORS(app)

# Global chatbot instance
chatbot = None


def initialize_chatbot():
    """Initialize the chatbot with configuration from environment."""
    global chatbot
    
    try:
        # Get configuration
        api_key = os.getenv('OPENROUTER_API_KEY')
        vector_db_path = os.getenv('VECTOR_DB_PATH', './vector_db')
        model_name = os.getenv('MODEL_NAME', 'openai/gpt-3.5-turbo')
        embedding_model = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        top_k = int(os.getenv('TOP_K_RETRIEVAL', 5))
        threshold = float(os.getenv('SIMILARITY_THRESHOLD', 0.7))
        
        # Check if API key is provided
        if not api_key or api_key == "your_openrouter_api_key_here":
            logger.error("OpenRouter API key not configured properly")
            return False
        
        # Initialize chatbot
        chatbot = AyushBridgeChatbot(
            openrouter_api_key=api_key,
            vector_db_path=vector_db_path,
            model_name=model_name,
            embedding_model=embedding_model,
            top_k_retrieval=top_k,
            similarity_threshold=threshold
        )
        
        if chatbot.is_initialized:
            logger.info("Chatbot initialized successfully")
            return True
        else:
            logger.error("Failed to initialize chatbot")
            return False
            
    except Exception as e:
        logger.error(f"Error initializing chatbot: {str(e)}")
        return False


@app.route('/')
def index():
    """Main page with chatbot interface."""
    # Initialize session if needed
    if 'session_id' not in session:
        session['session_id'] = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    
    # Check if chatbot is available
    chatbot_available = chatbot is not None and chatbot.is_initialized
    
    return render_template('index.html', 
                         chatbot_available=chatbot_available,
                         session_id=session['session_id'])


@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """Chat API endpoint."""
    try:
        # Check if chatbot is available
        if not chatbot or not chatbot.is_initialized:
            return jsonify({
                'error': 'Chatbot is not available. Please check the configuration.',
                'success': False
            }), 503
        
        # Get request data
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
        
        # Optional parameters
        include_history = data.get('include_history', True)
        temperature = float(data.get('temperature', 0.7))
        
        # Get response from chatbot
        response = chatbot.chat(
            user_message=user_message,
            include_history=include_history,
            temperature=temperature
        )
        
        # Add success flag
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
    try:
        if not chatbot:
            return jsonify({
                'suggestions': [
                    "What is AyushBridge?",
                    "How do I get started?",
                    "What are the main features?"
                ],
                'success': True
            })
        
        suggestions = chatbot.suggest_questions()
        return jsonify({
            'suggestions': suggestions,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in suggestions endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


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
        
        stats = chatbot.get_chatbot_stats()
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


@app.route('/api/summary', methods=['GET'])
def summary_endpoint():
    """Get conversation summary."""
    try:
        if not chatbot:
            return jsonify({
                'summary': 'No conversation available',
                'success': True
            })
        
        summary = chatbot.get_conversation_summary()
        return jsonify({
            'summary': summary,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in summary endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/health')
def health_check():
    """Health check endpoint."""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'chatbot_available': chatbot is not None and chatbot.is_initialized if chatbot else False,
        'version': '1.0.0'
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
    logger.info("Starting AyushBridge Chatbot Web Application...")
    
    chatbot_ready = initialize_chatbot()
    if not chatbot_ready:
        logger.warning("Chatbot initialization failed, but starting web server anyway")
    
    # Get Flask configuration
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
