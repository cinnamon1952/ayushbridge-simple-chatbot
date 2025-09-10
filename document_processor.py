"""
Document processor for creating FAISS vector database from README content.
Handles text chunking, embedding generation, and vector storage.
"""

import os
import re
import pickle
import numpy as np
import faiss
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self, 
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 vector_db_path: str = "./vector_db"):
        """
        Initialize the document processor.
        
        Args:
            embedding_model: HuggingFace model name for embeddings
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            vector_db_path: Path to store vector database
        """
        self.embedding_model_name = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vector_db_path = vector_db_path
        
        # Initialize components
        self.embedding_model = None
        self.text_splitter = None
        self.vector_store = None
        self.document_chunks = []
        self.chunk_metadata = []
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize the embedding model and text splitter."""
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def preprocess_markdown(self, text: str) -> str:
        """
        Preprocess markdown text to improve chunking and retrieval.
        
        Args:
            text: Raw markdown text
            
        Returns:
            Preprocessed text
        """
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Clean up code blocks for better readability
        text = re.sub(r'```[\w]*\n(.*?)\n```', r'\n[CODE BLOCK]\n\1\n[/CODE BLOCK]\n', text, flags=re.DOTALL)
        
        # Simplify headers for better context
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        
        # Remove badges and links that don't add content
        text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', text)
        text = re.sub(r'\[.*?\]\(https?://.*?\)', '', text)
        
        return text.strip()
    
    def extract_sections(self, text: str) -> List[Dict[str, str]]:
        """
        Extract sections from markdown text with metadata.
        
        Args:
            text: Preprocessed markdown text
            
        Returns:
            List of section dictionaries with content and metadata
        """
        sections = []
        lines = text.split('\n')
        current_section = {'title': 'Introduction', 'content': '', 'level': 1}
        
        for line in lines:
            # Check if line is a header - look for # at start or ## etc
            header_match = re.match(r'^(#{1,6})\s*(.*)', line.strip())
            if header_match:
                # Save previous section if it has content
                if current_section['content'].strip():
                    sections.append(current_section.copy())
                
                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                # Clean up title (remove emoji and extra chars)
                title = re.sub(r'[🎯🚀✨🔍🔄🔐📊🛠️🏗️💡📚🔧💬🤝📄🙏📞]', '', title).strip()
                
                current_section = {
                    'title': title if title else f'Section Level {level}',
                    'content': '',
                    'level': level
                }
            else:
                # Add line to current section
                current_section['content'] += line + '\n'
        
        # Add the last section
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections
    
    def create_chunks_with_context(self, sections: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Create chunks from sections while preserving context.
        
        Args:
            sections: List of document sections
            
        Returns:
            List of chunks with metadata
        """
        chunks = []
        
        for section in sections:
            # Create context from section title
            section_context = f"Section: {section['title']}\n\n"
            section_content = section['content'].strip()
            
            if not section_content:
                continue
            
            # Split long sections into smaller chunks
            if len(section_content) > self.chunk_size:
                text_chunks = self.text_splitter.split_text(section_content)
                for i, chunk in enumerate(text_chunks):
                    chunk_with_context = section_context + chunk
                    chunks.append({
                        'content': chunk_with_context,
                        'section': section['title'],
                        'chunk_index': i,
                        'total_chunks': len(text_chunks),
                        'level': section['level']
                    })
            else:
                # Keep entire section as one chunk
                chunk_with_context = section_context + section_content
                chunks.append({
                    'content': chunk_with_context,
                    'section': section['title'],
                    'chunk_index': 0,
                    'total_chunks': 1,
                    'level': section['level']
                })
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            Numpy array of embeddings
        """
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        return embeddings.astype('float32')
    
    def create_vector_store(self, embeddings: np.ndarray) -> faiss.IndexFlatIP:
        """
        Create FAISS vector store from embeddings.
        
        Args:
            embeddings: Numpy array of embeddings
            
        Returns:
            FAISS index
        """
        dimension = embeddings.shape[1]
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create FAISS index (Inner Product for normalized vectors = cosine similarity)
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)
        
        logger.info(f"Created FAISS index with {index.ntotal} vectors of dimension {dimension}")
        return index
    
    def process_document(self, file_path: str) -> bool:
        """
        Process a document and create vector database.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Success status
        """
        try:
            # Read the document
            logger.info(f"Reading document from {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
            
            # Preprocess the text
            logger.info("Preprocessing document...")
            processed_text = self.preprocess_markdown(raw_text)
            
            # Extract sections
            logger.info("Extracting sections...")
            sections = self.extract_sections(processed_text)
            logger.info(f"Extracted {len(sections)} sections")
            
            # Create chunks with context
            logger.info("Creating chunks with context...")
            chunks = self.create_chunks_with_context(sections)
            logger.info(f"Created {len(chunks)} chunks")
            
            # Store chunks and metadata
            self.document_chunks = [chunk['content'] for chunk in chunks]
            self.chunk_metadata = chunks
            
            # Generate embeddings
            embeddings = self.generate_embeddings(self.document_chunks)
            
            # Create vector store
            self.vector_store = self.create_vector_store(embeddings)
            
            # Save to disk
            self.save_vector_database()
            
            logger.info("Document processing completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return False
    
    def save_vector_database(self):
        """Save the vector database and metadata to disk."""
        os.makedirs(self.vector_db_path, exist_ok=True)
        
        # Save FAISS index
        index_path = os.path.join(self.vector_db_path, "faiss_index.bin")
        faiss.write_index(self.vector_store, index_path)
        
        # Save chunks and metadata
        chunks_path = os.path.join(self.vector_db_path, "chunks.pkl")
        metadata_path = os.path.join(self.vector_db_path, "metadata.pkl")
        
        with open(chunks_path, 'wb') as f:
            pickle.dump(self.document_chunks, f)
        
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.chunk_metadata, f)
        
        # Save configuration
        config = {
            'embedding_model': self.embedding_model_name,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'total_chunks': len(self.document_chunks)
        }
        
        config_path = os.path.join(self.vector_db_path, "config.pkl")
        with open(config_path, 'wb') as f:
            pickle.dump(config, f)
        
        logger.info(f"Vector database saved to {self.vector_db_path}")
    
    def load_vector_database(self) -> bool:
        """
        Load the vector database from disk.
        
        Returns:
            Success status
        """
        try:
            # Load FAISS index
            index_path = os.path.join(self.vector_db_path, "faiss_index.bin")
            self.vector_store = faiss.read_index(index_path)
            
            # Load chunks and metadata
            chunks_path = os.path.join(self.vector_db_path, "chunks.pkl")
            metadata_path = os.path.join(self.vector_db_path, "metadata.pkl")
            
            with open(chunks_path, 'rb') as f:
                self.document_chunks = pickle.load(f)
            
            with open(metadata_path, 'rb') as f:
                self.chunk_metadata = pickle.load(f)
            
            logger.info(f"Loaded vector database with {len(self.document_chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error loading vector database: {str(e)}")
            return False
    
    def search_similar_chunks(self, query: str, top_k: int = 5, similarity_threshold: float = 0.7) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar chunks in the vector database.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of tuples (chunk_content, similarity_score, metadata)
        """
        if self.vector_store is None:
            logger.error("Vector store not loaded")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search in vector store
        similarities, indices = self.vector_store.search(query_embedding, top_k)
        
        results = []
        for similarity, idx in zip(similarities[0], indices[0]):
            if similarity >= similarity_threshold:
                chunk_content = self.document_chunks[idx]
                metadata = self.chunk_metadata[idx]
                results.append((chunk_content, float(similarity), metadata))
        
        return results


def main():
    """Main function to process the README document."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('.env_chatbot')
    
    # Configuration
    vector_db_path = os.getenv('VECTOR_DB_PATH', './vector_db')
    chunk_size = int(os.getenv('CHUNK_SIZE', 1000))
    chunk_overlap = int(os.getenv('CHUNK_OVERLAP', 200))
    embedding_model = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    
    # Initialize processor
    processor = DocumentProcessor(
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        vector_db_path=vector_db_path
    )
    
    # Process README.md
    readme_path = "/Users/hridayshah/SIH2025/README.md"
    success = processor.process_document(readme_path)
    
    if success:
        print("✅ Vector database created successfully!")
        print(f"📁 Saved to: {vector_db_path}")
        print(f"📊 Total chunks: {len(processor.document_chunks)}")
        
        # Test search
        test_query = "What is AyushBridge?"
        results = processor.search_similar_chunks(test_query, top_k=3)
        print(f"\n🔍 Test search for '{test_query}':")
        for i, (content, score, metadata) in enumerate(results, 1):
            print(f"{i}. Score: {score:.3f} | Section: {metadata['section']}")
            print(f"   Preview: {content[:100]}...")
    else:
        print("❌ Failed to create vector database")


if __name__ == "__main__":
    main()
