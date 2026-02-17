"""
Defect Similarity Search Module
Finds similar past defects using vector similarity.
"""

import logging
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class DefectSimilaritySearch:
    """
    Service for finding similar defects based on semantic similarity.
    Uses embeddings to find defects with 80-90% similarity.
    """
    
    def __init__(self, embedding_service, vector_store):
        """
        Initialize the defect similarity search.
        
        Args:
            embedding_service: EmbeddingService instance.
            vector_store: VectorStore instance.
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self._indexed = False
    
    def index_defects(self, defects_acc: pd.DataFrame, defects_sit: pd.DataFrame, force_reindex: bool = False):
        """
        Index all defects from ACC and SIT for similarity search.
        Skips re-indexing if defects are already cached (unless force_reindex=True).
        
        Args:
            defects_acc: DataFrame of ACC defects.
            defects_sit: DataFrame of SIT defects.
            force_reindex: Force re-indexing even if cache exists.
        """
        # Calculate total defect count
        total_defects = 0
        if defects_acc is not None and not defects_acc.empty:
            total_defects += len(defects_acc)
        if defects_sit is not None and not defects_sit.empty:
            total_defects += len(defects_sit)
        
        # Check if already indexed with same count (use cache)
        stats = self.vector_store.get_collection_stats()
        cached_count = stats.get('defect_count', 0)
        
        if not force_reindex and cached_count > 0 and cached_count >= total_defects * 0.95:
            # Already indexed (within 5% tolerance for minor data changes)
            logger.info(f"Using cached defect embeddings ({cached_count} defects already indexed)")
            self._indexed = True
            return
        
        logger.info("Indexing defects for similarity search...")
        
        all_defects = []
        all_texts = []
        
        # Process ACC defects
        if defects_acc is not None and not defects_acc.empty:
            for _, row in defects_acc.iterrows():
                defect = row.to_dict()
                defect['source'] = 'ACC'
                all_defects.append(defect)
                all_texts.append(self.embedding_service.create_defect_text(defect))
        
        # Process SIT defects
        if defects_sit is not None and not defects_sit.empty:
            for _, row in defects_sit.iterrows():
                defect = row.to_dict()
                defect['source'] = 'SIT'
                all_defects.append(defect)
                all_texts.append(self.embedding_service.create_defect_text(defect))
        
        if not all_defects:
            logger.warning("No defects to index")
            return
        
        # Clear existing defects before re-indexing
        if cached_count > 0:
            logger.info("Clearing old cache for fresh indexing...")
            self.vector_store.clear_defects()
        
        # Generate embeddings in batches (larger batch = faster indexing)
        logger.info(f"Generating embeddings for {len(all_defects)} defects...")
        batch_size = 256
        all_embeddings = []
        
        for i in range(0, len(all_texts), batch_size):
            batch_texts = all_texts[i:i + batch_size]
            batch_embeddings = self.embedding_service.generate_embeddings(batch_texts)
            all_embeddings.extend(batch_embeddings)
            logger.info(f"Processed {min(i + batch_size, len(all_texts))}/{len(all_texts)} defects")
        
        # Store in vector database
        self.vector_store.add_defects(all_defects, all_embeddings)
        self._indexed = True
        logger.info(f"Successfully indexed {len(all_defects)} defects")
    
    def find_similar(
        self,
        defect: Dict[str, Any],
        n_results: int = 5,
        min_similarity: float = 0.5,
        exclude_self: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find similar defects to the given defect.
        
        Args:
            defect: The defect to find similarities for.
            n_results: Maximum number of similar defects to return.
            min_similarity: Minimum similarity threshold (0-1, where 0.8 = 80%).
            exclude_self: Whether to exclude the same defect from results.
            
        Returns:
            List of similar defects with similarity scores.
        """
        # Create embedding for the query defect
        query_text = self.embedding_service.create_defect_text(defect)
        query_embedding = self.embedding_service.generate_embedding(query_text)
        
        # Search in vector store
        similar = self.vector_store.search_similar_defects(
            query_embedding,
            n_results=n_results + 1 if exclude_self else n_results,
            min_similarity=min_similarity
        )
        
        # Exclude self if needed
        if exclude_self:
            current_key = defect.get('Issue key', '')
            similar = [s for s in similar if s.get('issue_key') != current_key][:n_results]
        
        return similar
    
    def search_by_text(
        self,
        query_text: str,
        n_results: int = 5,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Search for defects similar to a text query.
        
        Args:
            query_text: Natural language search query.
            n_results: Maximum number of results.
            min_similarity: Minimum similarity threshold.
            
        Returns:
            List of matching defects with similarity scores.
        """
        if not query_text or not query_text.strip():
            return []
        
        # Generate embedding for query
        query_embedding = self.embedding_service.generate_embedding(query_text)
        
        # Search in vector store
        results = self.vector_store.search_similar_defects(
            query_embedding,
            n_results=n_results,
            min_similarity=min_similarity
        )
        
        return results
    
    def get_resolved_similar(
        self,
        defect: Dict[str, Any],
        n_results: int = 5,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Find similar defects that have been resolved.
        Useful for suggesting resolutions.
        
        Args:
            defect: The defect to find similarities for.
            n_results: Maximum number of results.
            min_similarity: Minimum similarity threshold.
            
        Returns:
            List of similar resolved defects.
        """
        # Get more results to filter for resolved ones
        similar = self.find_similar(
            defect,
            n_results=n_results * 3,
            min_similarity=min_similarity,
            exclude_self=True
        )
        
        # Filter for resolved/closed defects (use Status and DB Resolution column)
        resolved_keywords = ['closed', 'resolved', 'done', 'fixed', 'verified']
        resolved = []
        
        for s in similar:
            status = s.get('metadata', {}).get('status', '').lower()
            resolution = s.get('metadata', {}).get('resolution', '').lower()
            if any(rs in status for rs in resolved_keywords) or any(rs in resolution for rs in resolved_keywords):
                resolved.append(s)
                if len(resolved) >= n_results:
                    break
        
        return resolved
    
    def is_indexed(self) -> bool:
        """Check if defects have been indexed."""
        stats = self.vector_store.get_collection_stats()
        return stats.get('defect_count', 0) > 0
