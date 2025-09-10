#!/usr/bin/env python3
"""
Production runner for AyushBridge Chatbot.
Handles production deployment with proper logging and error handling.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env_chatbot')

# Create logs directory
Path("logs").mkdir(exist_ok=True)

# Configure logging
log_filename = f"logs/chatbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def check_environment():
    """Check if environment is properly configured."""
    logger.info("Checking environment configuration...")
    
    required_env_vars = [
        'OPENROUTER_API_KEY',
        'MODEL_NAME',
        'EMBEDDING_MODEL',
        'VECTOR_DB_PATH'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        value = os.getenv(var)
        if not value or value == "your_openrouter_api_key_here":
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing or invalid environment variables: {missing_vars}")
        logger.error("Please configure .env_chatbot file properly")
        return False
    
    logger.info("✅ Environment configuration looks good")
    return True


def check_dependencies():
    """Check if all required dependencies are available."""
    logger.info("Checking dependencies...")
    
    required_modules = [
        'faiss',
        'sentence_transformers',
        'flask',
        'numpy',
        'transformers',
        'torch'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        logger.error(f"Missing required modules: {missing_modules}")
        logger.error("Please install dependencies: pip install -r requirements_chatbot.txt")
        return False
    
    logger.info("✅ All dependencies are available")
    return True


def check_vector_database():
    """Check if vector database exists and is accessible."""
    logger.info("Checking vector database...")
    
    vector_db_path = os.getenv('VECTOR_DB_PATH', './vector_db')
    required_files = [
        'faiss_index.bin',
        'chunks.pkl',
        'metadata.pkl',
        'config.pkl'
    ]
    
    missing_files = []
    for file in required_files:
        file_path = os.path.join(vector_db_path, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
    
    if missing_files:
        logger.warning(f"Missing vector database files: {missing_files}")
        logger.warning("Vector database not found. Creating it now...")
        
        try:
            from document_processor import main as create_vector_db
            create_vector_db()
            logger.info("✅ Vector database created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create vector database: {e}")
            return False
    else:
        logger.info("✅ Vector database is available")
    
    return True


def initialize_chatbot():
    """Initialize the chatbot system."""
    logger.info("Initializing chatbot system...")
    
    try:
        from chatbot_core import AyushBridgeChatbot
        
        # Get configuration
        api_key = os.getenv('OPENROUTER_API_KEY')
        vector_db_path = os.getenv('VECTOR_DB_PATH', './vector_db')
        model_name = os.getenv('MODEL_NAME', 'openai/gpt-3.5-turbo')
        embedding_model = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        top_k = int(os.getenv('TOP_K_RETRIEVAL', 5))
        threshold = float(os.getenv('SIMILARITY_THRESHOLD', 0.7))
        
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
            logger.info("✅ Chatbot initialized successfully")
            
            # Get and log stats
            stats = chatbot.get_chatbot_stats()
            logger.info(f"Chatbot stats: {stats}")
            
            return chatbot
        else:
            logger.error("❌ Chatbot initialization failed")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error initializing chatbot: {e}")
        return None


def run_production_server():
    """Run the production Flask server."""
    logger.info("Starting production server...")
    
    try:
        from app import app
        
        # Get Flask configuration
        host = os.getenv('FLASK_HOST', '0.0.0.0')
        port = int(os.getenv('FLASK_PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        
        logger.info(f"Server configuration:")
        logger.info(f"  Host: {host}")
        logger.info(f"  Port: {port}")
        logger.info(f"  Debug: {debug}")
        
        # Run the application
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"❌ Error running server: {e}")
        sys.exit(1)


def main():
    """Main function to run the chatbot application."""
    logger.info("="*60)
    logger.info("🤖 Starting AyushBridge Chatbot Application")
    logger.info("="*60)
    
    # Pre-flight checks
    if not check_environment():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    if not check_vector_database():
        logger.warning("⚠️  Continuing without vector database (limited functionality)")
    
    # Initialize chatbot (this will be done in Flask app as well)
    chatbot = initialize_chatbot()
    if not chatbot:
        logger.warning("⚠️  Continuing without chatbot initialization (limited functionality)")
    
    # Start the web server
    logger.info("🌐 Starting web server...")
    logger.info(f"📁 Log file: {log_filename}")
    
    try:
        run_production_server()
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
    except Exception as e:
        logger.error(f"💥 Server crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
