"""
Core chatbot logic with RAG (Retrieval Augmented Generation) functionality.
Integrates document processing, vector search, and OpenRouter chat completions.
"""

import os
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from document_processor import DocumentProcessor
from openrouter_client import OpenRouterClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AyushBridgeChatbot:
    def __init__(self, 
                 openrouter_api_key: str,
                 vector_db_path: str = "./vector_db",
                 model_name: str = "openai/gpt-3.5-turbo",
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 top_k_retrieval: int = 5,
                 similarity_threshold: float = 0.7):
        """
        Initialize the AyushBridge chatbot.
        
        Args:
            openrouter_api_key: OpenRouter API key
            vector_db_path: Path to the vector database
            model_name: OpenRouter model name
            embedding_model: Embedding model name
            top_k_retrieval: Number of chunks to retrieve
            similarity_threshold: Minimum similarity for retrieval
        """
        self.vector_db_path = vector_db_path
        self.top_k_retrieval = top_k_retrieval
        self.similarity_threshold = similarity_threshold
        
        # Initialize components
        self.document_processor = None
        self.openrouter_client = None
        self.conversation_history = []
        self.is_initialized = False
        
        # Initialize document processor
        try:
            self.document_processor = DocumentProcessor(
                embedding_model=embedding_model,
                vector_db_path=vector_db_path
            )
            
            # Try to load existing vector database
            if not self.document_processor.load_vector_database():
                logger.warning("Vector database not found. Please run document processing first.")
            else:
                logger.info("Vector database loaded successfully")
                
        except Exception as e:
            logger.error(f"Error initializing document processor: {str(e)}")
            raise
        
        # Initialize OpenRouter client
        try:
            self.openrouter_client = OpenRouterClient(
                api_key=openrouter_api_key,
                model=model_name
            )
            
            if self.openrouter_client.validate_connection():
                logger.info("OpenRouter client initialized successfully")
                self.is_initialized = True
            else:
                logger.error("Failed to validate OpenRouter connection")
                
        except Exception as e:
            logger.error(f"Error initializing OpenRouter client: {str(e)}")
            raise
    
    def retrieve_relevant_chunks(self, query: str) -> List[Tuple[str, float, Dict]]:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            query: User query
            
        Returns:
            List of relevant chunks with metadata
        """
        if not self.document_processor or not self.document_processor.vector_store:
            logger.warning("Vector database not available")
            return []
        
        try:
            results = self.document_processor.search_similar_chunks(
                query=query,
                top_k=self.top_k_retrieval,
                similarity_threshold=self.similarity_threshold
            )
            
            logger.info(f"Retrieved {len(results)} relevant chunks for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            return []
    
    def format_retrieved_context(self, retrieved_chunks: List[Tuple[str, float, Dict]]) -> str:
        """
        Format retrieved chunks into context for the LLM.
        
        Args:
            retrieved_chunks: List of retrieved chunks with metadata
            
        Returns:
            Formatted context string
        """
        if not retrieved_chunks:
            return "No relevant information found in the documentation."
        
        context_parts = []
        for i, (content, score, metadata) in enumerate(retrieved_chunks, 1):
            section = metadata.get('section', 'Unknown Section')
            # Clean up content for better presentation
            clean_content = content.replace('Section: ', '').strip()
            
            context_parts.append(
                f"[Chunk {i} - {section} (relevance: {score:.2f})]:\n{clean_content}"
            )
        
        return "\n\n" + "="*50 + "\n\n".join(context_parts)
    
    def chat(self, 
             user_message: str, 
             include_history: bool = True,
             temperature: float = 0.7) -> Dict[str, any]:
        """
        Main chat function with RAG capability.
        
        Args:
            user_message: User's message
            include_history: Whether to include conversation history
            temperature: LLM temperature setting
            
        Returns:
            Response dictionary with answer and metadata
        """
        if not self.is_initialized:
            return {
                "answer": "I apologize, but the chatbot is not properly initialized. Please check the configuration.",
                "sources": [],
                "error": "Chatbot not initialized"
            }
        
        try:
            start_time = datetime.now()
            
            # Retrieve relevant chunks
            retrieved_chunks = self.retrieve_relevant_chunks(user_message)
            
            # Format context
            context = self.format_retrieved_context(retrieved_chunks)
            
            # Prepare conversation history
            history = self.conversation_history if include_history else []
            
            # Get response from OpenRouter - ONLY use README.md content
            if retrieved_chunks:
                # Use RAG with README.md context
                chunk_contents = [chunk[0] for chunk in retrieved_chunks]
                response = self.openrouter_client.chat_with_rag(
                    user_message=user_message,
                    retrieved_chunks=chunk_contents,
                    conversation_history=history,
                    temperature=temperature
                )
            else:
                # NO fallback - only answer if information is in README.md
                response = "I apologize, but I couldn't find information about your question in the AyushBridge documentation (README.md). Please try asking about topics covered in the documentation, such as:\n\n" + \
                          "• AyushBridge features and capabilities\n" + \
                          "• Installation and setup instructions\n" + \
                          "• API endpoints and usage\n" + \
                          "• NAMASTE and ICD-11 integration\n" + \
                          "• Configuration and deployment\n" + \
                          "• Technical architecture\n\n" + \
                          "Or try rephrasing your question with different keywords."
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Keep only last 20 messages (10 exchanges)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            # Prepare sources information
            sources = []
            for content, score, metadata in retrieved_chunks:
                sources.append({
                    "section": metadata.get('section', 'Unknown'),
                    "relevance_score": score,
                    "chunk_index": metadata.get('chunk_index', 0),
                    "preview": content[:200] + "..." if len(content) > 200 else content
                })
            
            return {
                "answer": response,
                "sources": sources,
                "response_time": response_time,
                "chunks_retrieved": len(retrieved_chunks),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in chat function: {str(e)}")
            return {
                "answer": f"I apologize, but I encountered an error while processing your request: {str(e)}",
                "sources": [],
                "error": str(e)
            }
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the current conversation.
        
        Returns:
            Conversation summary
        """
        if not self.conversation_history:
            return "No conversation history available."
        
        try:
            # Prepare conversation for summarization
            conversation_text = ""
            for msg in self.conversation_history[-10:]:  # Last 5 exchanges
                role = msg["role"].title()
                content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
                conversation_text += f"{role}: {content}\n\n"
            
            summary_prompt = f"""Please provide a brief summary of this conversation about AyushBridge:

{conversation_text}

Summary:"""
            
            summary = self.openrouter_client.simple_chat(
                user_message=summary_prompt,
                system_message="You are a helpful assistant that creates concise conversation summaries.",
                temperature=0.3
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {str(e)}")
            return "Unable to generate conversation summary."
    
    def reset_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []
        logger.info("Conversation history reset")
    
    def get_chatbot_stats(self) -> Dict[str, any]:
        """
        Get chatbot statistics and status.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "is_initialized": self.is_initialized,
            "conversation_length": len(self.conversation_history),
            "vector_db_available": self.document_processor and self.document_processor.vector_store is not None,
            "total_chunks": len(self.document_processor.document_chunks) if self.document_processor else 0,
            "embedding_model": self.document_processor.embedding_model_name if self.document_processor else None,
            "llm_model": self.openrouter_client.model if self.openrouter_client else None,
            "settings": {
                "top_k_retrieval": self.top_k_retrieval,
                "similarity_threshold": self.similarity_threshold,
                "vector_db_path": self.vector_db_path
            }
        }
        
        return stats
    
    def suggest_questions(self) -> List[str]:
        """
        Suggest relevant questions users might ask.
        
        Returns:
            List of suggested questions
        """
        suggestions = [
            "What is AyushBridge and what does it do?",
            "How do I install and set up AyushBridge?",
            "What are the key features of AyushBridge?",
            "How does the NAMASTE to ICD-11 translation work?",
            "What are the API endpoints available?",
            "How do I implement FHIR Bundle uploads?",
            "What are the authentication requirements?",
            "How do I search for NAMASTE terms?",
            "What is the architecture of AyushBridge?",
            "How do I configure the database?",
            "What are the monitoring and analytics features?",
            "How do I contribute to the project?",
            "What are the compliance requirements?",
            "How does the auto-complete search work?",
            "What programming languages are supported?"
        ]
        
        return suggestions


def main():
    """Test the chatbot functionality."""
    from dotenv import load_dotenv
    load_dotenv('.env_chatbot')
    
    # Get configuration
    api_key = os.getenv('OPENROUTER_API_KEY')
    vector_db_path = os.getenv('VECTOR_DB_PATH', './vector_db')
    model_name = os.getenv('MODEL_NAME', 'openai/gpt-3.5-turbo')
    embedding_model = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    top_k = int(os.getenv('TOP_K_RETRIEVAL', 5))
    threshold = float(os.getenv('SIMILARITY_THRESHOLD', 0.7))
    
    try:
        # Initialize chatbot
        print("🤖 Initializing AyushBridge Chatbot...")
        chatbot = AyushBridgeChatbot(
            openrouter_api_key=api_key,
            vector_db_path=vector_db_path,
            model_name=model_name,
            embedding_model=embedding_model,
            top_k_retrieval=top_k,
            similarity_threshold=threshold
        )
        
        if chatbot.is_initialized:
            print("✅ Chatbot initialized successfully!")
            
            # Get stats
            stats = chatbot.get_chatbot_stats()
            print(f"📊 Chatbot Stats:")
            print(f"   - Vector DB available: {stats['vector_db_available']}")
            print(f"   - Total chunks: {stats['total_chunks']}")
            print(f"   - LLM model: {stats['llm_model']}")
            
            # Test chat
            print("\n🔍 Testing chatbot...")
            
            test_questions = [
                "What is AyushBridge?",
                "How do I install AyushBridge?",
                "What are the API endpoints?"
            ]
            
            for question in test_questions:
                print(f"\n❓ Question: {question}")
                response = chatbot.chat(question)
                print(f"🤖 Answer: {response['answer'][:200]}...")
                print(f"📚 Sources found: {response['chunks_retrieved']}")
                print(f"⏱️ Response time: {response['response_time']:.2f}s")
                
        else:
            print("❌ Failed to initialize chatbot")
            
    except Exception as e:
        print(f"❌ Error testing chatbot: {str(e)}")


if __name__ == "__main__":
    main()
