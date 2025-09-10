"""
Simple AyushBridge Chatbot without vector database.
Uses direct README.md content as context for RAG.
"""

import os
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()  # Will load .env file or environment variables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleOpenRouterClient:
    def __init__(self, api_key: str, model: str = "deepseek/deepseek-r1"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ayushbridge.in",
            "X-Title": "AyushBridge Simple Chatbot"
        }
    
    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Create a chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"OpenRouter API error: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}"


class SimpleAyushBridgeChatbot:
    def __init__(self, openrouter_api_key: str, readme_path: str = "README.md"):
        self.openrouter_client = SimpleOpenRouterClient(openrouter_api_key)
        self.readme_content = ""
        self.conversation_history = []
        self.is_initialized = False
        
        # Load README content
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                self.readme_content = f.read()
            
            # Clean and prepare the content
            self.readme_content = self._clean_readme_content(self.readme_content)
            self.is_initialized = True
            logger.info(f"✅ Simple chatbot initialized with README content ({len(self.readme_content)} chars)")
            
        except Exception as e:
            logger.error(f"❌ Failed to load README: {str(e)}")
    
    def _clean_readme_content(self, content: str) -> str:
        """Clean and prepare README content for better context."""
        # Remove excessive markdown formatting for cleaner context
        content = re.sub(r'```[\w]*\n(.*?)\n```', r'[CODE]\n\1\n[/CODE]', content, flags=re.DOTALL)
        content = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', content)  # Remove badges
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Remove excessive newlines
        return content.strip()
    
    def _find_relevant_sections(self, query: str, max_chars: int = 3000) -> str:
        """Find relevant sections from README based on query keywords."""
        query_lower = query.lower()
        query_keywords = re.findall(r'\b\w+\b', query_lower)
        
        # Split README into sections
        sections = re.split(r'\n(?=#{1,3}\s)', self.readme_content)
        scored_sections = []
        
        for section in sections:
            if len(section.strip()) < 50:  # Skip very short sections
                continue
                
            section_lower = section.lower()
            score = 0
            
            # Score based on keyword matches
            for keyword in query_keywords:
                if len(keyword) > 2:  # Only consider meaningful keywords
                    score += section_lower.count(keyword) * len(keyword)
            
            # Boost score for exact phrase matches
            if query_lower in section_lower:
                score += 50
            
            if score > 0:
                scored_sections.append((score, section))
        
        # Sort by score and combine top sections
        scored_sections.sort(reverse=True, key=lambda x: x[0])
        
        relevant_content = ""
        for score, section in scored_sections[:5]:  # Top 5 sections
            if len(relevant_content) + len(section) > max_chars:
                break
            relevant_content += f"\n\n=== SECTION ===\n{section}"
        
        return relevant_content[:max_chars] if relevant_content else self.readme_content[:max_chars]
    
    def chat(self, user_message: str, temperature: float = 0.7) -> Dict[str, any]:
        """Chat with the user using README context."""
        if not self.is_initialized:
            return {
                "answer": "I apologize, but the chatbot is not properly initialized.",
                "error": "Chatbot not initialized"
            }
        
        try:
            start_time = datetime.now()
            
            # Find relevant sections
            relevant_context = self._find_relevant_sections(user_message)
            
            # Create system message
            system_message = """You are AyushBridge AI Assistant. You MUST ONLY answer questions using the information provided in the AyushBridge documentation below. 

STRICT RULES:
1. ONLY use information from the provided AyushBridge documentation
2. If information is not in the documentation, say "I don't have that information in the AyushBridge documentation"
3. Do NOT use external knowledge or make assumptions
4. Quote directly from the documentation when possible
5. Be helpful and detailed when the information IS available in the docs
6. Always specify that your answer is based on the AyushBridge documentation

You are strictly limited to the AyushBridge documentation provided below."""
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Based on this AyushBridge documentation:\n\n{relevant_context}\n\nQuestion: {user_message}"}
            ]
            
            # Add conversation history (last 4 messages)
            if self.conversation_history:
                history_messages = self.conversation_history[-4:]
                messages = [messages[0]] + history_messages + [messages[1]]
            
            # Get response
            response = self.openrouter_client.chat_completion(messages, temperature)
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Keep only last 10 messages
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "answer": response,
                "response_time": response_time,
                "context_length": len(relevant_context),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return {
                "answer": f"I apologize, but I encountered an error: {str(e)}",
                "error": str(e)
            }
    
    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        logger.info("Conversation history reset")
    
    def get_stats(self) -> Dict[str, any]:
        """Get chatbot statistics."""
        return {
            "is_initialized": self.is_initialized,
            "conversation_length": len(self.conversation_history),
            "readme_content_length": len(self.readme_content),
            "model": self.openrouter_client.model
        }


# Test function
def test_simple_chatbot():
    """Test the simple chatbot."""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key or api_key == "your_openrouter_api_key_here":
        print("❌ Please configure OPENROUTER_API_KEY in .env_chatbot")
        return
    
    chatbot = SimpleAyushBridgeChatbot(api_key)
    
    if chatbot.is_initialized:
        print("✅ Simple chatbot initialized successfully!")
        
        # Test questions
        test_questions = [
            "What is AyushBridge?",
            "How does code translation work?",
            "What are the main features?"
        ]
        
        for question in test_questions:
            print(f"\n❓ {question}")
            response = chatbot.chat(question)
            print(f"🤖 {response['answer'][:200]}...")
            print(f"⏱️ Response time: {response['response_time']:.2f}s")
    else:
        print("❌ Failed to initialize chatbot")


if __name__ == "__main__":
    test_simple_chatbot()
