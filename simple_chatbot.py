"""
Simple AyushBridge Chatbot without vector database.
Uses direct README.md content as context for RAG.
Now uses Ollama/Groq instead of OpenRouter.
"""

import os
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from ollama_groq_client import OllamaGroqClient

# Load environment variables
load_dotenv('.env_simple')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleAyushBridgeChatbot:
    def __init__(self, api_key: Optional[str] = None, readme_path: str = "README.md"):
        # Initialize Ollama/Groq client
        self.api_key = api_key
        self.model = os.getenv('MODEL_NAME', 'llama3-8b-8192')
        self.base_url = os.getenv('GROQ_BASE_URL', 'https://api.groq.com/openai/v1')
        self.use_groq = os.getenv('USE_GROQ', 'true').lower() == 'true'
        
        self.ollama_groq_client = OllamaGroqClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            use_groq=self.use_groq
        )
        
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
    
    def _find_relevant_sections(self, query: str, max_chars: int = 4000) -> str:
        """Find relevant sections from README based on query keywords with improved matching."""
        query_lower = query.lower()
        query_keywords = re.findall(r'\b\w+\b', query_lower)
        
        # Enhanced keyword mapping for better context matching
        keyword_mappings = {
            'what': ['overview', 'solution', 'description', 'about', 'problem statement'],
            'how': ['installation', 'setup', 'usage', 'guide', 'steps', 'quick start'],
            'install': ['installation', 'setup', 'prerequisites', 'quick start', 'docker'],
            'setup': ['installation', 'configuration', 'environment', 'prerequisites'],
            'features': ['key features', 'capabilities', 'functionality', 'terminology management', 'search', 'translation', 'security', 'analytics'],
            'api': ['endpoints', 'api', 'rest', 'swagger', 'openapi'],
            'architecture': ['architecture', 'design', 'components', 'technical stack'],
            'security': ['authentication', 'oauth', 'abha', 'jwt', 'compliance'],
            'database': ['mongodb', 'postgresql', 'redis', 'storage', 'elasticsearch'],
            'deployment': ['docker', 'kubernetes', 'production', 'deploy', 'containerization'],
            'terminology': ['namaste', 'icd-11', 'fhir', 'codes', 'who', 'traditional medicine'],
            'translation': ['mapping', 'translation', 'conversion', 'bridge', 'bidirectional'],
            'search': ['auto-complete', 'search', 'discovery', 'lookup', 'faceted'],
            'namaste': ['namaste', 'national ayush', 'standardized terminologies', 'electronic'],
            'key': ['key features', 'key terminologies', 'core capabilities']
        }
        
        # Expand query keywords with related terms
        expanded_keywords = set(query_keywords)
        for keyword in query_keywords:
            if keyword in keyword_mappings:
                expanded_keywords.update(keyword_mappings[keyword])
        
        # Split README into sections (improved splitting)
        sections = re.split(r'\n(?=#{1,3}\s)', self.readme_content)
        scored_sections = []
        
        for section in sections:
            if len(section.strip()) < 50:  # Skip very short sections
                continue
                
            section_lower = section.lower()
            score = 0
            
            # Score based on expanded keyword matches
            for keyword in expanded_keywords:
                if len(keyword) > 2:  # Only consider meaningful keywords
                    # Higher weight for exact matches
                    if keyword in section_lower:
                        score += section_lower.count(keyword) * (len(keyword) + 5)
            
            # Boost score for exact phrase matches
            if query_lower in section_lower:
                score += 100
            
            # Boost score for section headers that match query intent
            section_header = section.split('\n')[0].lower()
            for keyword in expanded_keywords:
                if keyword in section_header:
                    score += 50
                    
            # Special boost for key sections with emojis
            if '✨' in section_header and 'features' in expanded_keywords:
                score += 100
            if '🏗️' in section_header and 'architecture' in expanded_keywords:
                score += 100
            if '🚀' in section_header and any(kw in ['overview', 'solution', 'what'] for kw in expanded_keywords):
                score += 100
            if '🎯' in section_header and 'problem' in expanded_keywords:
                score += 100
            
            # Boost score for code blocks and examples
            if '```' in section and any(kw in ['install', 'setup', 'usage', 'example'] for kw in expanded_keywords):
                score += 30
                
            # Boost score for sections with specific terminology
            if any(term in section_lower for term in ['namaste', 'icd-11', 'fhir', 'terminology']) and any(kw in ['terminology', 'namaste', 'codes'] for kw in expanded_keywords):
                score += 40
            
            if score > 0:
                scored_sections.append((score, section))
        
        # Sort by score and combine top sections
        scored_sections.sort(reverse=True, key=lambda x: x[0])
        
        relevant_content = ""
        for score, section in scored_sections[:6]:  # Top 6 sections
            if len(relevant_content) + len(section) > max_chars:
                break
            relevant_content += f"\n\n=== SECTION (Score: {score}) ===\n{section}"
        
        # If no relevant sections found, return the beginning of README with key info
        if not relevant_content:
            # Extract key information from the beginning
            intro_sections = sections[:3]  # First 3 sections usually contain overview
            relevant_content = "\n\n".join(intro_sections)[:max_chars]
        
        return relevant_content[:max_chars]
    
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
            system_message = """You are AyushBridge AI Assistant, an expert on the AyushBridge terminology microservice. You help users understand and work with AyushBridge, which is a FHIR R4-compliant terminology microservice for NAMASTE & ICD-11 TM2 integration.

ABOUT AYUSHBRIDGE:
- It's a terminology microservice that bridges NAMASTE codes, WHO International Terminologies for Ayurveda, and WHO ICD-11 classifications
- It provides FHIR R4-compliant terminology resources and bidirectional code translation
- It supports traditional medicine EMR systems in India's Ayush sector
- It includes features like auto-complete search, secure FHIR Bundle uploads, and real-time synchronization

INSTRUCTIONS:
1. Use ONLY the information provided in the AyushBridge documentation below
2. Be helpful, detailed, and accurate when answering questions about AyushBridge
3. If the information is not in the documentation, say "I don't have that specific information in the AyushBridge documentation, but I can help you with what's available"
4. Quote directly from the documentation when possible
5. Provide step-by-step instructions when asked about installation, setup, or usage
6. Explain technical concepts clearly and concisely
7. Always be specific about AyushBridge features and capabilities

You are an expert on AyushBridge and should provide comprehensive, accurate answers based on the documentation."""
            
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
            response = self.ollama_groq_client.chat_completion(messages, temperature)
            
            # Extract content based on provider
            if self.use_groq:
                response_content = response['choices'][0]['message']['content']
            else:
                # Local Ollama format
                response_content = response['message']['content']
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": response_content})
            
            # Keep only last 10 messages
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "answer": response_content,
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
            "model": self.model,
            "provider": "groq" if self.use_groq else "ollama",
            "base_url": self.base_url
        }


# Test function
def test_simple_chatbot():
    """Test the simple chatbot."""
    api_key = os.getenv('GROQ_API_KEY')
    use_groq = os.getenv('USE_GROQ', 'true').lower() == 'true'
    
    if use_groq and (not api_key or api_key == "your_groq_api_key_here"):
        print("❌ Please configure GROQ_API_KEY in .env_simple")
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
