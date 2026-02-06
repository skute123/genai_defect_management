"""
Vector Store Service - In-Memory Implementation
Uses numpy for similarity search (compatible with Python 3.14)
"""

import logging
import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class VectorStore:
    """
    In-memory vector database for defects and documents.
    Uses numpy for similarity calculations.
    Saves/loads from JSON files for persistence.
    """
    
    def __init__(self, persist_directory: str = None):
        """
        Initialize the vector store.
        
        Args:
            persist_directory: Directory to persist the vector database.
        """
        if persist_directory is None:
            base_path = Path(__file__).parent.parent.parent
            persist_directory = str(base_path / "knowledge_base" / "vector_store")
        
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # In-memory storage
        self.defect_embeddings = []  # List of numpy arrays
        self.defect_metadata = []    # List of metadata dicts
        self.defect_documents = []   # List of document texts
        self.defect_ids = []         # List of IDs
        
        self.document_embeddings = []
        self.document_metadata = []
        self.document_texts = []
        self.document_ids = []
        
        # Load persisted data if exists
        self._load_from_disk()
        
        logger.info(f"Vector store initialized at {self.persist_directory}")
        logger.info(f"Defects loaded: {len(self.defect_ids)}")
        logger.info(f"Documents loaded: {len(self.document_ids)}")
    
    def _load_from_disk(self):
        """Load persisted data from disk."""
        defect_file = os.path.join(self.persist_directory, "defects.json")
        doc_file = os.path.join(self.persist_directory, "documents.json")
        
        if os.path.exists(defect_file):
            try:
                with open(defect_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.defect_ids = data.get('ids', [])
                    self.defect_embeddings = [np.array(e) for e in data.get('embeddings', [])]
                    self.defect_metadata = data.get('metadata', [])
                    self.defect_documents = data.get('documents', [])
            except Exception as e:
                logger.warning(f"Could not load defects: {e}")
        
        if os.path.exists(doc_file):
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.document_ids = data.get('ids', [])
                    self.document_embeddings = [np.array(e) for e in data.get('embeddings', [])]
                    self.document_metadata = data.get('metadata', [])
                    self.document_texts = data.get('documents', [])
            except Exception as e:
                logger.warning(f"Could not load documents: {e}")
    
    def _save_to_disk(self):
        """Save data to disk."""
        defect_file = os.path.join(self.persist_directory, "defects.json")
        doc_file = os.path.join(self.persist_directory, "documents.json")
        
        try:
            with open(defect_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'ids': self.defect_ids,
                    'embeddings': [e.tolist() for e in self.defect_embeddings],
                    'metadata': self.defect_metadata,
                    'documents': self.defect_documents
                }, f)
        except Exception as e:
            logger.error(f"Could not save defects: {e}")
        
        try:
            with open(doc_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'ids': self.document_ids,
                    'embeddings': [e.tolist() for e in self.document_embeddings],
                    'metadata': self.document_metadata,
                    'documents': self.document_texts
                }, f)
        except Exception as e:
            logger.error(f"Could not save documents: {e}")
    
    def add_defects(self, defects: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Add defects to the vector store.
        
        Args:
            defects: List of defect dictionaries.
            embeddings: Corresponding embedding vectors.
        """
        if not defects or not embeddings:
            return
        
        # Clear existing defects (upsert behavior)
        self.defect_ids = []
        self.defect_embeddings = []
        self.defect_metadata = []
        self.defect_documents = []
        
        for i, defect in enumerate(defects):
            issue_key = str(defect.get('Issue key', f'defect_{i}'))
            
            self.defect_ids.append(issue_key)
            self.defect_embeddings.append(np.array(embeddings[i]))
            
            # Create document text
            doc_text = f"{defect.get('Summary', '')} {defect.get('Description', '')}"
            self.defect_documents.append(doc_text[:5000])
            
            # Store metadata
            metadata = {
                'issue_key': issue_key,
                'summary': str(defect.get('Summary', ''))[:500],
                'status': str(defect.get('Status', '')),
                'priority': str(defect.get('Priority', '')),
                'osf_wave': str(defect.get('OSF-Wave', '')),
                'osf_system': str(defect.get('OSF-System', '')),
                'resolution': str(defect.get('Resolution', '')),
                'fix_description': str(defect.get('Custom field (OSF-Fix Description)', ''))[:1000],
                'source': str(defect.get('source', 'unknown'))
            }
            self.defect_metadata.append(metadata)
        
        self._save_to_disk()
        logger.info(f"Added {len(defects)} defects to vector store")
    
    def add_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Add knowledge documents to the vector store.
        
        Args:
            documents: List of document chunk dictionaries.
            embeddings: Corresponding embedding vectors.
        """
        if not documents or not embeddings:
            return
        
        # Clear existing documents
        self.document_ids = []
        self.document_embeddings = []
        self.document_metadata = []
        self.document_texts = []
        
        for i, doc in enumerate(documents):
            doc_id = doc.get('id', f'doc_{i}')
            
            self.document_ids.append(doc_id)
            self.document_embeddings.append(np.array(embeddings[i]))
            self.document_texts.append(doc.get('content', '')[:5000])
            
            metadata = {
                'filename': doc.get('filename', ''),
                'filepath': doc.get('filepath', ''),
                'section': doc.get('section', ''),
                'page': str(doc.get('page', '')),
                'chunk_index': str(doc.get('chunk_index', i))
            }
            self.document_metadata.append(metadata)
        
        self._save_to_disk()
        logger.info(f"Added {len(documents)} document chunks to vector store")
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def search_similar_defects(
        self, 
        query_embedding: List[float], 
        n_results: int = 5,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar defects.
        
        Args:
            query_embedding: Query vector.
            n_results: Maximum number of results.
            min_similarity: Minimum similarity threshold (0-1).
            
        Returns:
            List of similar defects with similarity scores.
        """
        if not self.defect_embeddings:
            logger.warning("No defects indexed")
            return []
        
        query_vec = np.array(query_embedding)
        
        # Calculate similarities
        similarities = []
        for i, emb in enumerate(self.defect_embeddings):
            sim = self._cosine_similarity(query_vec, emb)
            if sim >= min_similarity:
                similarities.append((i, sim))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Build results
        results = []
        for idx, sim in similarities[:n_results]:
            results.append({
                'issue_key': self.defect_ids[idx],
                'similarity': round(sim * 100, 1),
                'metadata': self.defect_metadata[idx],
                'document': self.defect_documents[idx]
            })
        
        return results
    
    def search_documents(
        self,
        query_embedding: List[float],
        n_results: int = 3,
        min_similarity: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant knowledge documents.
        
        Args:
            query_embedding: Query vector.
            n_results: Maximum number of results.
            min_similarity: Minimum similarity threshold (0-1).
            
        Returns:
            List of relevant documents with similarity scores.
        """
        if not self.document_embeddings:
            logger.warning("No documents indexed")
            return []
        
        query_vec = np.array(query_embedding)
        
        # Calculate similarities
        similarities = []
        for i, emb in enumerate(self.document_embeddings):
            sim = self._cosine_similarity(query_vec, emb)
            if sim >= min_similarity:
                similarities.append((i, sim))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Build results
        results = []
        for idx, sim in similarities[:n_results]:
            results.append({
                'id': self.document_ids[idx],
                'similarity': round(sim * 100, 1),
                'content': self.document_texts[idx],
                'metadata': self.document_metadata[idx]
            })
        
        return results
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about the vector store."""
        return {
            'defect_count': len(self.defect_ids),
            'document_count': len(self.document_ids)
        }
    
    def clear_defects(self):
        """Clear all defects from the collection."""
        self.defect_ids = []
        self.defect_embeddings = []
        self.defect_metadata = []
        self.defect_documents = []
        self._save_to_disk()
        logger.info("Cleared defect collection")
    
    def clear_documents(self):
        """Clear all documents from the collection."""
        self.document_ids = []
        self.document_embeddings = []
        self.document_metadata = []
        self.document_texts = []
        self._save_to_disk()
        logger.info("Cleared document collection")
