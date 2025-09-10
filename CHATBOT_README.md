# AyushBridge AI Chatbot

A powerful RAG (Retrieval Augmented Generation) chatbot built using FAISS vector database and OpenRouter API to answer questions about the AyushBridge FHIR R4-compliant terminology microservice.

## 🚀 Features

- **RAG-Powered Responses**: Uses FAISS vector database for intelligent document retrieval
- **OpenRouter Integration**: Leverages OpenRouter API for access to multiple LLM models
- **Beautiful Web Interface**: Modern, responsive UI built with Bootstrap 5
- **Real-time Chat**: Interactive chat interface with conversation history
- **Source Citations**: Shows relevant document sections for each response
- **Conversation Management**: Reset, summarize, and track chat statistics
- **Intelligent Suggestions**: Context-aware question suggestions
- **Production Ready**: Comprehensive logging, error handling, and monitoring

## 📋 Prerequisites

- Python 3.8 or higher
- OpenRouter API account and API key
- At least 4GB RAM (for embedding models)
- 2GB disk space (for models and vector database)

## 🛠️ Installation

### Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
python setup_chatbot.py
```

### Option 2: Manual Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements_chatbot.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env_chatbot.example .env_chatbot
   # Edit .env_chatbot and add your OpenRouter API key
   ```

3. **Create Vector Database**
   ```bash
   python document_processor.py
   ```

4. **Test Components**
   ```bash
   python openrouter_client.py
   python chatbot_core.py
   ```

## ⚙️ Configuration

### Environment Variables (.env_chatbot)

```bash
# OpenRouter API Configuration
OPENROUTER_API_KEY=your_api_key_here          # Required: Get from openrouter.ai
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=openai/gpt-3.5-turbo               # Model to use for chat

# Embedding Configuration  
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Vector Database
VECTOR_DB_PATH=./vector_db                     # Path to store FAISS database
CHUNK_SIZE=1000                                # Text chunk size
CHUNK_OVERLAP=200                              # Overlap between chunks

# RAG Settings
TOP_K_RETRIEVAL=5                              # Number of chunks to retrieve
SIMILARITY_THRESHOLD=0.7                       # Minimum similarity score

# Flask Web Server
FLASK_PORT=5000                                # Web server port
FLASK_DEBUG=True                               # Debug mode
FLASK_SECRET_KEY=your-secret-key               # Session secret
```

### Supported Models (OpenRouter)

- `openai/gpt-3.5-turbo` (Recommended for speed/cost)
- `openai/gpt-4` (Best quality, higher cost)
- `anthropic/claude-3-haiku` (Good balance)
- `meta-llama/llama-2-70b-chat` (Open source)
- And many more available on OpenRouter

## 🚀 Usage

### Quick Start

```bash
# Run the application
python run_chatbot.py

# Or use the basic Flask app
python app.py
```

Then open your browser to `http://localhost:5000`

### API Usage

The chatbot also provides REST API endpoints:

#### Chat Endpoint
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is AyushBridge?",
    "include_history": true,
    "temperature": 0.7
  }'
```

#### Get Suggestions
```bash
curl http://localhost:5000/api/suggestions
```

#### Get Statistics
```bash
curl http://localhost:5000/api/stats
```

#### Reset Conversation
```bash
curl -X POST http://localhost:5000/api/reset
```

### Programmatic Usage

```python
from chatbot_core import AyushBridgeChatbot

# Initialize chatbot
chatbot = AyushBridgeChatbot(
    openrouter_api_key="your-api-key",
    model_name="openai/gpt-3.5-turbo"
)

# Chat with the bot
response = chatbot.chat("How do I install AyushBridge?")
print(response['answer'])
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Interface │────│   Flask App      │────│   Chatbot Core  │
│   (HTML/JS)     │    │   (app.py)       │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   OpenRouter    │────│   OpenRouter     │    │   Document      │
│   API           │    │   Client         │    │   Processor     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                               ┌─────────────────┐
                                               │   FAISS Vector  │
                                               │   Database      │
                                               └─────────────────┘
```

### Components

1. **Document Processor** (`document_processor.py`)
   - Processes README.md into chunks
   - Generates embeddings using SentenceTransformers
   - Creates and manages FAISS vector database

2. **OpenRouter Client** (`openrouter_client.py`)
   - Handles communication with OpenRouter API
   - Supports multiple models and streaming
   - Error handling and retry logic

3. **Chatbot Core** (`chatbot_core.py`)
   - Main RAG logic
   - Retrieves relevant chunks for queries
   - Manages conversation history
   - Formats responses with source citations

4. **Flask Web App** (`app.py`)
   - REST API endpoints
   - Session management
   - Error handling and logging

5. **Web Interface** (`templates/index.html`)
   - Modern, responsive UI
   - Real-time chat interface
   - Statistics and controls

## 📊 Performance

### Benchmarks (Typical Performance)

| Metric | Value |
|--------|--------|
| Response Time (avg) | 2-5 seconds |
| Embedding Generation | 100ms per chunk |
| Vector Search | <50ms |
| Memory Usage | 1-2GB |
| Disk Usage | 500MB-1GB |

### Optimization Tips

1. **Reduce Response Time**
   - Use faster models (gpt-3.5-turbo vs gpt-4)
   - Reduce `TOP_K_RETRIEVAL` value
   - Increase `SIMILARITY_THRESHOLD`

2. **Improve Accuracy**
   - Use better models (gpt-4, claude-3)
   - Increase `TOP_K_RETRIEVAL`
   - Reduce `CHUNK_SIZE` for more precise retrieval

3. **Reduce Memory Usage**
   - Use smaller embedding models
   - Reduce vector database size
   - Clear conversation history regularly

## 🔧 Troubleshooting

### Common Issues

1. **"Chatbot not initialized" Error**
   ```bash
   # Check OpenRouter API key
   python openrouter_client.py
   
   # Verify vector database
   python document_processor.py
   ```

2. **Slow Response Times**
   - Check internet connection
   - Try different OpenRouter models
   - Reduce TOP_K_RETRIEVAL value

3. **Vector Database Issues**
   ```bash
   # Recreate vector database
   rm -rf vector_db/
   python document_processor.py
   ```

4. **Memory Issues**
   - Use smaller embedding models
   - Reduce CHUNK_SIZE
   - Close other applications

### Logs and Debugging

- Check `logs/` directory for detailed logs
- Enable DEBUG mode in Flask for verbose output
- Use `python -v` for import debugging

### Getting Help

1. Check the logs in `logs/` directory
2. Verify environment configuration
3. Test each component individually
4. Check OpenRouter API status
5. Ensure sufficient system resources

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OpenRouter** for providing access to multiple LLM APIs
- **FAISS** by Facebook AI for efficient vector similarity search
- **SentenceTransformers** for high-quality embeddings
- **Flask** for the web framework
- **Bootstrap** for the UI components

---

## 📞 Support

For issues and support:

1. Check this documentation
2. Review the logs
3. Test individual components
4. Create an issue with detailed error information

**Happy chatting with AyushBridge AI! 🤖**
