#!/usr/bin/env python3
"""
Demo script for AyushBridge Chatbot.
Shows the complete workflow and capabilities.
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env_chatbot')

def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"🤖 {title}")
    print("="*60)

def print_step(step, description):
    """Print a step with formatting."""
    print(f"\n📋 Step {step}: {description}")
    print("-" * 40)

def demo_document_processing():
    """Demonstrate document processing and vector database creation."""
    print_step(1, "Document Processing & Vector Database Creation")
    
    try:
        from document_processor import DocumentProcessor
        
        # Initialize processor
        processor = DocumentProcessor()
        
        # Check if vector database exists
        if processor.load_vector_database():
            print("✅ Vector database already exists and loaded successfully")
            print(f"📊 Total chunks: {len(processor.document_chunks)}")
            
            # Test search
            test_query = "What is AyushBridge?"
            print(f"\n🔍 Testing search with query: '{test_query}'")
            results = processor.search_similar_chunks(test_query, top_k=3)
            
            for i, (content, score, metadata) in enumerate(results, 1):
                print(f"\n   Result {i} (Score: {score:.3f}):")
                print(f"   Section: {metadata['section']}")
                print(f"   Preview: {content[:100]}...")
                
        else:
            print("📦 Creating new vector database...")
            success = processor.process_document("README.md")
            if success:
                print("✅ Vector database created successfully!")
            else:
                print("❌ Failed to create vector database")
                return False
                
    except Exception as e:
        print(f"❌ Error in document processing: {e}")
        return False
    
    return True

def demo_openrouter_client():
    """Demonstrate OpenRouter client functionality."""
    print_step(2, "OpenRouter Client Testing")
    
    try:
        from openrouter_client import OpenRouterClient
        
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key or api_key == "your_openrouter_api_key_here":
            print("⚠️  OpenRouter API key not configured")
            print("   Please set OPENROUTER_API_KEY in .env_chatbot file")
            return False
        
        # Initialize client
        client = OpenRouterClient(api_key=api_key)
        
        # Test connection
        if client.validate_connection():
            print("✅ OpenRouter connection successful")
            
            # Test simple chat
            print("\n💬 Testing simple chat...")
            response = client.simple_chat(
                "Hello! Can you briefly explain what you do?",
                system_message="You are a helpful AI assistant."
            )
            print(f"🤖 Response: {response[:200]}...")
            
        else:
            print("❌ OpenRouter connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing OpenRouter: {e}")
        return False
    
    return True

def demo_chatbot_core():
    """Demonstrate core chatbot functionality."""
    print_step(3, "Chatbot Core RAG System")
    
    try:
        from chatbot_core import AyushBridgeChatbot
        
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key or api_key == "your_openrouter_api_key_here":
            print("⚠️  Skipping chatbot demo - API key not configured")
            return False
        
        # Initialize chatbot
        print("🔄 Initializing chatbot...")
        chatbot = AyushBridgeChatbot(openrouter_api_key=api_key)
        
        if not chatbot.is_initialized:
            print("❌ Chatbot initialization failed")
            return False
        
        print("✅ Chatbot initialized successfully")
        
        # Get statistics
        stats = chatbot.get_chatbot_stats()
        print(f"\n📊 Chatbot Statistics:")
        print(f"   Vector DB Available: {stats['vector_db_available']}")
        print(f"   Total Chunks: {stats['total_chunks']}")
        print(f"   LLM Model: {stats['llm_model']}")
        
        # Demo questions
        demo_questions = [
            "What is AyushBridge?",
            "How do I install AyushBridge?",
            "What are the main API endpoints?",
            "How does the NAMASTE to ICD-11 translation work?"
        ]
        
        print(f"\n💬 Testing chatbot with sample questions...")
        
        for i, question in enumerate(demo_questions[:2], 1):  # Test first 2 questions
            print(f"\n❓ Question {i}: {question}")
            
            start_time = time.time()
            response = chatbot.chat(question)
            end_time = time.time()
            
            if 'error' not in response:
                print(f"🤖 Answer: {response['answer'][:200]}...")
                print(f"📚 Sources found: {response['chunks_retrieved']}")
                print(f"⏱️  Response time: {end_time - start_time:.2f}s")
            else:
                print(f"❌ Error: {response['error']}")
        
        # Show suggestions
        print(f"\n💡 Available suggestions:")
        suggestions = chatbot.suggest_questions()
        for i, suggestion in enumerate(suggestions[:5], 1):
            print(f"   {i}. {suggestion}")
            
    except Exception as e:
        print(f"❌ Error testing chatbot core: {e}")
        return False
    
    return True

def demo_web_interface():
    """Demonstrate web interface setup."""
    print_step(4, "Web Interface Setup")
    
    try:
        from app import app
        
        print("✅ Flask app imported successfully")
        print("🌐 Web interface components:")
        print("   - REST API endpoints (/api/chat, /api/stats, etc.)")
        print("   - HTML template with modern UI")
        print("   - Real-time chat interface")
        print("   - Conversation management")
        print("   - Source citations")
        
        print(f"\n🚀 To start the web server:")
        print(f"   python app.py")
        print(f"   python run_chatbot.py  # Production mode")
        print(f"\n🌐 Then visit: http://localhost:5000")
        
    except Exception as e:
        print(f"❌ Error checking web interface: {e}")
        return False
    
    return True

def show_file_structure():
    """Show the created file structure."""
    print_step(5, "Generated Files")
    
    files = [
        ("requirements_chatbot.txt", "Python dependencies"),
        (".env_chatbot", "Environment configuration"),
        ("document_processor.py", "Vector database creation"),
        ("openrouter_client.py", "OpenRouter API client"),
        ("chatbot_core.py", "Core RAG chatbot logic"),
        ("app.py", "Flask web application"),
        ("templates/index.html", "Web interface template"),
        ("setup_chatbot.py", "Automated setup script"),
        ("run_chatbot.py", "Production runner"),
        ("CHATBOT_README.md", "Comprehensive documentation"),
        ("vector_db/", "FAISS vector database (created)"),
        ("logs/", "Application logs (created)")
    ]
    
    for filename, description in files:
        status = "✅" if os.path.exists(filename) else "📄"
        print(f"   {status} {filename:<25} - {description}")

def main():
    """Run the complete demo."""
    print_header("AyushBridge AI Chatbot Demo")
    
    print("🎯 This demo will showcase the complete chatbot system:")
    print("   1. Document processing and vector database")
    print("   2. OpenRouter API integration")
    print("   3. RAG-powered chatbot functionality")
    print("   4. Web interface setup")
    print("   5. File structure overview")
    
    input("\n🎬 Press Enter to start the demo...")
    
    # Run demonstrations
    success_count = 0
    
    if demo_document_processing():
        success_count += 1
    
    if demo_openrouter_client():
        success_count += 1
    
    if demo_chatbot_core():
        success_count += 1
    
    if demo_web_interface():
        success_count += 1
    
    show_file_structure()
    
    # Final summary
    print_header("Demo Summary")
    print(f"✅ Successfully demonstrated {success_count}/4 components")
    
    if success_count == 4:
        print("🎉 All components working perfectly!")
        print("\n🚀 Next steps:")
        print("   1. Configure your OpenRouter API key in .env_chatbot")
        print("   2. Run: python run_chatbot.py")
        print("   3. Open: http://localhost:5000")
        print("   4. Start chatting about AyushBridge!")
    else:
        print("⚠️  Some components need configuration:")
        print("   - Set OPENROUTER_API_KEY in .env_chatbot")
        print("   - Run: python setup_chatbot.py")
        print("   - Check the logs for detailed error information")
    
    print("\n📚 For detailed documentation, see CHATBOT_README.md")
    print("💬 Happy chatting with AyushBridge AI!")

if __name__ == "__main__":
    main()
