"""
OpenRouter API client for chat completions.
Handles communication with OpenRouter API for various language models.
"""

import os
import json
import requests
import logging
from typing import List, Dict, Optional, Generator
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self, 
                 api_key: str,
                 base_url: str = "https://openrouter.ai/api/v1",
                 model: str = "openai/gpt-3.5-turbo",
                 timeout: int = 30):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key
            base_url: OpenRouter API base URL
            model: Model name to use for completions
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        
        # Validate API key
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            raise ValueError("Please set a valid OpenRouter API key in the environment")
        
        # Set up headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ayushbridge.in",  # Your site URL
            "X-Title": "AyushBridge Chatbot"  # Your app name
        }
    
    def get_available_models(self) -> List[Dict]:
        """
        Get list of available models from OpenRouter.
        
        Returns:
            List of model information dictionaries
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get('data', [])
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
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
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
        Handle streaming response from OpenRouter.
        
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
            return response['choices'][0]['message']['content']
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
            return response['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Error in RAG chat: {str(e)}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    def validate_connection(self) -> bool:
        """
        Validate connection to OpenRouter API.
        
        Returns:
            True if connection is successful
        """
        try:
            models = self.get_available_models()
            if models:
                logger.info(f"Successfully connected to OpenRouter. Found {len(models)} models.")
                return True
            else:
                logger.warning("Connected to OpenRouter but no models found.")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to OpenRouter: {str(e)}")
            return False
    
    def get_usage_stats(self) -> Dict:
        """
        Get usage statistics (if supported by OpenRouter).
        
        Returns:
            Usage statistics dictionary
        """
        try:
            response = requests.get(
                f"{self.base_url}/auth/key",
                headers=self.headers,
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status code: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error fetching usage stats: {str(e)}")
            return {"error": str(e)}


def main():
    """Test the OpenRouter client."""
    from dotenv import load_dotenv
    load_dotenv('.env_chatbot')
    
    # Get configuration
    api_key = os.getenv('OPENROUTER_API_KEY')
    base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    model = os.getenv('MODEL_NAME', 'openai/gpt-3.5-turbo')
    
    try:
        # Initialize client
        client = OpenRouterClient(api_key=api_key, base_url=base_url, model=model)
        
        # Test connection
        if client.validate_connection():
            print("✅ Successfully connected to OpenRouter!")
            
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
            print("❌ Failed to connect to OpenRouter")
            
    except Exception as e:
        print(f"❌ Error testing OpenRouter client: {str(e)}")


if __name__ == "__main__":
    main()
