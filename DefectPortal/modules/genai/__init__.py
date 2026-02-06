"""
GenAI Module for DefectPortal
Provides AI-powered defect search, similarity matching, and knowledge base integration.
Uses open-source models: sentence-transformers for embeddings, ChromaDB for vector storage, Ollama for LLM.
"""

from .embedding_service import EmbeddingService
from .vector_store import VectorStore
from .defect_similarity import DefectSimilaritySearch
from .document_search import DocumentSearch
from .llm_service import LLMService
from .resolution_suggester import ResolutionSuggester
from .context_summarizer import ContextSummarizer
from .enhanced_search import EnhancedSearch

__all__ = [
    'EmbeddingService',
    'VectorStore', 
    'DefectSimilaritySearch',
    'DocumentSearch',
    'LLMService',
    'ResolutionSuggester',
    'ContextSummarizer',
    'EnhancedSearch'
]
