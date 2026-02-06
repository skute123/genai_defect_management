"""
Embedding Service using sentence-transformers (free, runs locally)
Generates vector embeddings for defects and documents.
"""

import logging
from typing import List, Union
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service for generating text embeddings using sentence-transformers.
    Uses the all-MiniLM-L6-v2 model which is lightweight and effective.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence-transformer model to use.
                       Default is 'all-MiniLM-L6-v2' (384 dimensions, fast).
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence-transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise ImportError("Please install sentence-transformers: pip install sentence-transformers")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: The text to embed.
            
        Returns:
            List of floats representing the embedding vector.
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * 384  # Default dimension for all-MiniLM-L6-v2
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * 384
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of texts to embed.
            
        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []
        
        # Clean texts
        cleaned_texts = [t if t and t.strip() else " " for t in texts]
        
        try:
            embeddings = self.model.encode(cleaned_texts, convert_to_numpy=True, show_progress_bar=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return [[0.0] * 384 for _ in texts]
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector.
            embedding2: Second embedding vector.
            
        Returns:
            Similarity score between 0 and 1.
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(max(0.0, min(1.0, similarity)))  # Clamp to [0, 1]
        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            return 0.0
    
    def create_defect_text(self, defect: dict) -> str:
        """
        Create a searchable text representation of a defect.
        Combines key fields for embedding.
        
        Args:
            defect: Dictionary containing defect fields.
            
        Returns:
            Combined text for embedding.
        """
        fields = [
            defect.get('Summary', ''),
            defect.get('Description', ''),
            defect.get('Custom field (OSF-Fix Description)', ''),
            defect.get('OSF-System', ''),
            defect.get('Comment', '')
        ]
        
        # Filter and join non-empty fields
        text_parts = [str(f).strip() for f in fields if f and str(f).strip() and str(f).lower() != 'nan']
        return " ".join(text_parts)
