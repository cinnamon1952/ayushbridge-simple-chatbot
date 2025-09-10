#!/usr/bin/env python3
"""
Setup script for AyushBridge Chatbot.
Handles installation, configuration, and initialization of the chatbot system.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        return False
    logger.info(f"Python version: {sys.version}")
    return True


def install_dependencies():
    """Install required Python packages."""
    logger.info("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_chatbot.txt"])
        logger.info("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install dependencies: {e}")
        return False


def setup_environment():
    """Set up environment configuration."""
    logger.info("Setting up environment configuration...")
    
    env_file = ".env_chatbot"
    if os.path.exists(env_file):
        logger.info(f"Environment file {env_file} already exists")
        return True
    
    # Copy from template
    try:
        with open(env_file, 'w') as f:
            f.write("""# OpenRouter API Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Model Configuration
MODEL_NAME=openai/gpt-3.5-turbo
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Vector Database Configuration
VECTOR_DB_PATH=./vector_db
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Flask Configuration
FLASK_PORT=5000
FLASK_DEBUG=True
FLASK_SECRET_KEY=ayushbridge-chatbot-secret-key-2025

# RAG Configuration
TOP_K_RETRIEVAL=5
SIMILARITY_THRESHOLD=0.7""")
        
        logger.info(f"✅ Created environment file: {env_file}")
        logger.warning("⚠️  Please update the OPENROUTER_API_KEY in the .env_chatbot file")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create environment file: {e}")
        return False


def create_vector_database():
    """Create the vector database from README.md."""
    logger.info("Creating vector database from README.md...")
    
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        logger.error(f"❌ README.md not found at {readme_path}")
        return False
    
    try:
        # Import and run document processor
        from document_processor import main as process_document
        process_document()
        logger.info("✅ Vector database created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create vector database: {e}")
        logger.info("You can create it manually by running: python document_processor.py")
        return False


def test_components():
    """Test individual components."""
    logger.info("Testing components...")
    
    # Test document processor
    try:
        from document_processor import DocumentProcessor
        processor = DocumentProcessor()
        if processor.load_vector_database():
            logger.info("✅ Document processor and vector database working")
        else:
            logger.warning("⚠️  Vector database not found or corrupted")
    except Exception as e:
        logger.error(f"❌ Document processor test failed: {e}")
    
    # Test OpenRouter client (if API key is configured)
    try:
        from dotenv import load_dotenv
        load_dotenv('.env_chatbot')
        
        api_key = os.getenv('OPENROUTER_API_KEY')
        if api_key and api_key != "your_openrouter_api_key_here":
            from openrouter_client import OpenRouterClient
            client = OpenRouterClient(api_key=api_key)
            if client.validate_connection():
                logger.info("✅ OpenRouter client working")
            else:
                logger.warning("⚠️  OpenRouter connection failed")
        else:
            logger.warning("⚠️  OpenRouter API key not configured")
    except Exception as e:
        logger.error(f"❌ OpenRouter client test failed: {e}")
    
    # Test chatbot core
    try:
        from chatbot_core import AyushBridgeChatbot
        logger.info("✅ Chatbot core imports working")
    except Exception as e:
        logger.error(f"❌ Chatbot core test failed: {e}")


def create_directories():
    """Create necessary directories."""
    directories = [
        "vector_db",
        "templates",
        "static",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"📁 Created directory: {directory}")


def display_next_steps():
    """Display next steps for the user."""
    print("\n" + "="*60)
    print("🎉 AyushBridge Chatbot Setup Complete!")
    print("="*60)
    print()
    print("📋 Next Steps:")
    print()
    print("1. 🔑 Configure your OpenRouter API key:")
    print("   - Edit .env_chatbot file")
    print("   - Replace 'your_openrouter_api_key_here' with your actual API key")
    print("   - Get your API key from: https://openrouter.ai/")
    print()
    print("2. 🗄️  Create the vector database (if not already done):")
    print("   python document_processor.py")
    print()
    print("3. 🧪 Test the components:")
    print("   python openrouter_client.py  # Test OpenRouter connection")
    print("   python chatbot_core.py       # Test chatbot functionality")
    print()
    print("4. 🚀 Start the web application:")
    print("   python app.py")
    print()
    print("5. 🌐 Open your browser and visit:")
    print("   http://localhost:5000")
    print()
    print("📚 Documentation:")
    print("   - README.md contains comprehensive information about AyushBridge")
    print("   - Each Python file has detailed docstrings")
    print("   - Check the logs/ directory for application logs")
    print()
    print("⚠️  Troubleshooting:")
    print("   - Ensure all dependencies are installed")
    print("   - Check that your OpenRouter API key is valid")
    print("   - Verify that the vector database was created successfully")
    print("   - Check the Flask logs for any errors")
    print()
    print("="*60)


def main():
    """Main setup function."""
    print("🤖 AyushBridge Chatbot Setup")
    print("="*40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        logger.error("❌ Setup failed at dependency installation")
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        logger.error("❌ Setup failed at environment configuration")
        sys.exit(1)
    
    # Create vector database
    create_vector_database()  # Non-blocking
    
    # Test components
    test_components()
    
    # Display next steps
    display_next_steps()


if __name__ == "__main__":
    main()
