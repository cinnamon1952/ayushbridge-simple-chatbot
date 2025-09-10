# Migration from OpenRouter to Ollama/Groq

This document describes the migration of the AyushBridge Simple Chatbot from OpenRouter to Ollama/Groq integration.

## Changes Made

### 1. New Ollama/Groq Client (`ollama_groq_client.py`)
- Created a unified client that supports both Groq API and local Ollama
- Compatible with OpenAI API format for easy integration
- Supports streaming and non-streaming responses
- Handles both Groq and local Ollama response formats

### 2. Updated Simple Chatbot (`simple_chatbot.py`)
- Replaced `SimpleOpenRouterClient` with `OllamaGroqClient`
- Updated initialization to use new environment variables
- Modified response handling to work with both Groq and Ollama formats
- Updated statistics to show provider information

### 3. Updated Flask App (`simple_app.py`)
- Modified initialization to use Groq API key instead of OpenRouter
- Updated error messages and logging to reflect new provider
- Added support for both Groq and local Ollama modes

### 4. Environment Configuration (`.env_simple`)
- Replaced OpenRouter configuration with Groq/Ollama settings
- Added `USE_GROQ` flag to switch between Groq API and local Ollama
- Configured default model to `llama3-8b-8192` (Groq's fast model)
- Added comments for local Ollama configuration

### 5. Requirements (`requirements_simple.txt`)
- No new dependencies needed (Groq uses OpenAI-compatible API)
- Added comment explaining compatibility

## Configuration Options

### Groq API (Recommended for Production)
```env
USE_GROQ=true
GROQ_API_KEY=your_groq_api_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=llama3-8b-8192
```

### Local Ollama (For Development)
```env
USE_GROQ=false
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=llama3
```

## Available Groq Models

- `llama3-8b-8192` - Fast, efficient model (default)
- `llama3-70b-8192` - More capable but slower
- `mixtral-8x7b-32768` - Mixture of experts model
- `gemma-7b-it` - Google's Gemma model

## Benefits of Migration

1. **Cost Efficiency**: Groq offers competitive pricing
2. **Speed**: Groq's infrastructure is optimized for fast inference
3. **Flexibility**: Can switch between cloud (Groq) and local (Ollama)
4. **OpenAI Compatibility**: Uses standard OpenAI API format
5. **No Vendor Lock-in**: Easy to switch between providers

## Testing

To test the new integration:

```bash
# Test with Groq API
python simple_chatbot.py

# Test the client directly
python ollama_groq_client.py
```

## Deployment Notes

1. Set `GROQ_API_KEY` environment variable in your deployment platform
2. Ensure `USE_GROQ=true` for cloud deployment
3. For local development, you can use `USE_GROQ=false` with local Ollama
4. The application will automatically detect and use the configured provider

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure `GROQ_API_KEY` is set correctly
2. **Connection Error**: Check internet connectivity for Groq API
3. **Model Not Found**: Verify the model name is available in your Groq account
4. **Local Ollama**: Ensure Ollama is running on the specified URL

### Debug Mode

Set `FLASK_DEBUG=True` in `.env_simple` for detailed error logging.
