"""
Ollama/Groq API client for chat completions.
Handles communication with both local Ollama and Groq API for various language models.
"""

import os
import json
import requests
import logging
from typing import List, Dict, Optional, Generator
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OllamaGroqClient:
    def __init__(self, 
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.groq.com/openai/v1",
                 model: str = "llama3-8b-8192",
                 timeout: int = 30,
                 use_groq: bool = True):
        """
        Initialize Ollama/Groq client.
        
        Args:
            api_key: API key (required for Groq, optional for local Ollama)
            base_url: API base URL (Groq or local Ollama)
            model: Model name to use for completions
            timeout: Request timeout in seconds
            use_groq: Whether to use Groq API (True) or local Ollama (False)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.use_groq = use_groq
        
        # Validate API key for Groq
        if self.use_groq and (not self.api_key or self.api_key == "your_groq_api_key_here"):
            raise ValueError("Please set a valid Groq API key in the environment")
        
        # Set up headers
        if self.use_groq:
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        else:
            # Local Ollama doesn't require API key
            self.headers = {
                "Content-Type": "application/json"
            }
    
    def get_available_models(self) -> List[Dict]:
        """
        Get list of available models.
        
        Returns:
            List of model information dictionaries
        """
        try:
            if self.use_groq:
                # Groq API models endpoint
                response = requests.get(
                    f"{self.base_url}/models",
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json().get('data', [])
            else:
                # Local Ollama models endpoint
                response = requests.get(
                    f"{self.base_url}/api/tags",
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                models_data = response.json()
                return models_data.get('models', [])
        except Exception as e:
            logger.error(f"Error fetching models: {str(e)}")
            return []
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: Optional[int] = None,
                       stream: bool = False) -> Dict:
        """
        Create a chat completion.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Response dictionary
        """
        if self.use_groq:
            # Groq API format
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            endpoint = f"{self.base_url}/chat/completions"
        else:
            # Local Ollama API format
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "temperature": temperature
                }
            }
            
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
            
            endpoint = f"{self.base_url}/api/chat"
        
        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_streaming_response(response)
            else:
                return response.json()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise
    
    def _handle_streaming_response(self, response) -> Generator[Dict, None, None]:
        """
        Handle streaming response.
        
        Args:
            response: Streaming response object
            
        Yields:
            Response chunks
        """
        try:
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data.strip() == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            raise
    
    def simple_chat(self, 
                   user_message: str,
                   system_message: Optional[str] = None,
                   context: Optional[str] = None,
                   temperature: float = 0.7) -> str:
        """
        Simple chat interface for single messages.
        
        Args:
            user_message: User's message
            system_message: Optional system message
            context: Optional context information
            temperature: Sampling temperature
            
        Returns:
            Assistant's response
        """
        messages = []
        
        # Add system message if provided
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        # Add context if provided
        if context:
            context_message = f"Context information:\n{context}\n\nPlease answer the following question based on the context provided:"
            messages.append({"role": "system", "content": context_message})
        
        # Add user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.chat_completion(messages, temperature=temperature)
            
            if self.use_groq:
                return response['choices'][0]['message']['content']
            else:
                # Local Ollama format
                return response['message']['content']
        except Exception as e:
            logger.error(f"Error in simple chat: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def chat_with_rag(self, 
                     user_message: str,
                     retrieved_chunks: List[str],
                     conversation_history: Optional[List[Dict[str, str]]] = None,
                     temperature: float = 0.7) -> str:
        """
        Chat with Retrieval Augmented Generation (RAG).
        
        Args:
            user_message: User's question
            retrieved_chunks: Retrieved relevant text chunks
            conversation_history: Previous conversation messages
            temperature: Sampling temperature
            
        Returns:
            Assistant's response
        """
        # Prepare context from retrieved chunks
        context = "\n\n".join([f"Document chunk {i+1}:\n{chunk}" 
                              for i, chunk in enumerate(retrieved_chunks)])
        
        # System message for RAG - STRICT README.md only
        system_message = """You are AyushBridge AI Assistant. You MUST ONLY answer questions using the information provided in the document chunks below. Do NOT use any external knowledge or make assumptions.

STRICT RULES:
1. ONLY answer based on the provided document chunks from the AyushBridge README.md
2. If information is not in the provided context, say "I don't have that information in the AyushBridge documentation"
3. Do NOT make up or infer information not explicitly stated in the chunks
4. Quote directly from the documentation when possible
5. If asked about topics not covered in the chunks, politely decline and suggest what IS covered
6. Always cite which sections of the documentation you're referencing
7. Do NOT use your general knowledge about FHIR, healthcare, or programming

You are strictly limited to the AyushBridge documentation provided below. Stay within these bounds."""
        
        messages = []
        
        # Add system message
        messages.append({"role": "system", "content": system_message})
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Keep last 10 messages
        
        # Add context and user message
        context_prompt = f"""Based on the following documentation about AyushBridge:

{context}

Please answer the user's question: {user_message}"""
        
        messages.append({"role": "user", "content": context_prompt})
        
        try:
            response = self.chat_completion(messages, temperature=temperature)
            
            if self.use_groq:
                return response['choices'][0]['message']['content']
            else:
                # Local Ollama format
                return response['message']['content']
        except Exception as e:
            logger.error(f"Error in RAG chat: {str(e)}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    def validate_connection(self) -> bool:
        """
        Validate connection to API.
        
        Returns:
            True if connection is successful
        """
        try:
            models = self.get_available_models()
            if models:
                if self.use_groq:
                    logger.info(f"Successfully connected to Groq. Found {len(models)} models.")
                else:
                    logger.info(f"Successfully connected to local Ollama. Found {len(models)} models.")
                return True
            else:
                if self.use_groq:
                    logger.warning("Connected to Groq but no models found.")
                else:
                    logger.warning("Connected to local Ollama but no models found.")
                return False
        except Exception as e:
            if self.use_groq:
                logger.error(f"Failed to connect to Groq: {str(e)}")
            else:
                logger.error(f"Failed to connect to local Ollama: {str(e)}")
            return False
    
    def get_usage_stats(self) -> Dict:
        """
        Get usage statistics (if supported).
        
        Returns:
            Usage statistics dictionary
        """
        try:
            if self.use_groq:
                # Groq doesn't have a direct usage stats endpoint in the same way
                return {"provider": "groq", "model": self.model}
            else:
                # Local Ollama stats
                response = requests.get(
                    f"{self.base_url}/api/version",
                    headers=self.headers,
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    version_info = response.json()
                    return {"provider": "ollama", "version": version_info.get("version", "unknown")}
                else:
                    return {"error": f"Status code: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error fetching usage stats: {str(e)}")
            return {"error": str(e)}


def main():
    """Test the Ollama/Groq client."""
    from dotenv import load_dotenv
    load_dotenv('.env_simple')
    
    # Get configuration
    api_key = os.getenv('GROQ_API_KEY')
    base_url = os.getenv('GROQ_BASE_URL', 'https://api.groq.com/openai/v1')
    model = os.getenv('MODEL_NAME', 'llama3-8b-8192')
    use_groq = os.getenv('USE_GROQ', 'true').lower() == 'true'
    
    try:
        # Initialize client
        client = OllamaGroqClient(
            api_key=api_key, 
            base_url=base_url, 
            model=model,
            use_groq=use_groq
        )
        
        # Test connection
        if client.validate_connection():
            provider = "Groq" if use_groq else "local Ollama"
            print(f"✅ Successfully connected to {provider}!")
            
            # Test simple chat
            response = client.simple_chat(
                "Hello! Can you briefly explain what AyushBridge is?",
                system_message="You are a helpful AI assistant."
            )
            print(f"\n🤖 Test Response:\n{response}")
            
            # Get usage stats
            stats = client.get_usage_stats()
            print(f"\n📊 Usage Stats: {stats}")
            
        else:
            provider = "Groq" if use_groq else "local Ollama"
            print(f"❌ Failed to connect to {provider}")
            
    except Exception as e:
        print(f"❌ Error testing Ollama/Groq client: {str(e)}")


if __name__ == "__main__":
    main()
