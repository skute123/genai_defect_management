"""
Enhanced Search Module
Orchestrates all GenAI components for comprehensive defect search.
"""

import logging
import streamlit as st
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class EnhancedSearch:
    """
    Main orchestrator for the AI-enhanced defect search system.
    Combines defect similarity, document search, and AI generation.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern to reuse initialized services."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the enhanced search system."""
        if EnhancedSearch._initialized:
            return
        
        self.embedding_service = None
        self.vector_store = None
        self.defect_similarity = None
        self.document_search = None
        self.llm_service = None
        self.resolution_suggester = None
        self.context_summarizer = None
        
        self._initialize_services()
        EnhancedSearch._initialized = True
    
    def _initialize_services(self):
        """Initialize all GenAI services."""
        try:
            logger.info("Initializing GenAI services...")
            
            # Import services
            from .embedding_service import EmbeddingService
            from .vector_store import VectorStore
            from .defect_similarity import DefectSimilaritySearch
            from .document_search import DocumentSearch
            from .llm_service import LLMService
            from .resolution_suggester import ResolutionSuggester
            from .context_summarizer import ContextSummarizer
            
            # Initialize in order
            self.embedding_service = EmbeddingService()
            self.vector_store = VectorStore()
            self.defect_similarity = DefectSimilaritySearch(
                self.embedding_service, 
                self.vector_store
            )
            self.document_search = DocumentSearch(
                self.embedding_service,
                self.vector_store
            )
            self.llm_service = LLMService()
            self.resolution_suggester = ResolutionSuggester(self.llm_service)
            self.context_summarizer = ContextSummarizer(self.llm_service)
            
            logger.info("GenAI services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GenAI services: {e}")
            raise
    
    def index_data(
        self,
        defects_acc: pd.DataFrame = None,
        defects_sit: pd.DataFrame = None,
        index_documents: bool = True,
        force_reindex: bool = False
    ):
        """
        Index defects and documents for search.
        
        Args:
            defects_acc: ACC defects DataFrame.
            defects_sit: SIT defects DataFrame.
            index_documents: Whether to also index knowledge documents.
            force_reindex: If True, re-index defects from DB (clears cache). Use after DB dump update.
        """
        # Index defects (force_reindex=True when DB was updated)
        if defects_acc is not None or defects_sit is not None:
            self.defect_similarity.index_defects(defects_acc, defects_sit, force_reindex=force_reindex)
        
        # Index documents (skip when only defect reindex to save time)
        if index_documents and not force_reindex:
            self.document_search.load_and_index_documents()
    
    def search(
        self,
        query: str,
        defects_acc: pd.DataFrame = None,
        defects_sit: pd.DataFrame = None,
        n_similar_defects: int = 5,
        n_related_docs: int = 3,
        min_similarity: float = 0.5
    ) -> Dict[str, Any]:
        """
        Perform an enhanced AI-powered search.
        
        Args:
            query: Search query text.
            defects_acc: ACC defects DataFrame for current results.
            defects_sit: SIT defects DataFrame for current results.
            n_similar_defects: Number of similar defects to find.
            n_related_docs: Number of related documents to find.
            min_similarity: Minimum similarity threshold.
            
        Returns:
            Dictionary containing all search results.
        """
        results = {
            'query': query,
            'matching_defects': {'acc': [], 'sit': []},
            'similar_defects': [],
            'related_documents': [],
            'resolution_suggestions': {},
            'context_summary': {}
        }
        
        if not query or not query.strip():
            return results
        
        # Step 1: Find matching defects using AI similarity
        similar = self.defect_similarity.search_by_text(
            query,
            n_results=n_similar_defects * 2,
            min_similarity=min_similarity
        )
        
        # Separate by source
        for s in similar:
            source = s.get('metadata', {}).get('source', 'unknown')
            if source == 'ACC':
                results['matching_defects']['acc'].append(s)
            else:
                results['matching_defects']['sit'].append(s)
        
        # Step 2: Find related documents
        related_docs = self.document_search.search(
            query,
            n_results=n_related_docs
        )
        results['related_documents'] = related_docs
        
        # Steps 3 & 4: Resolution suggestions and context summary (run LLM parts in parallel to stay under 2 min)
        query_defect = {'Summary': query, 'Description': query}
        if similar:
            results['resolution_suggestions'] = self.resolution_suggester.suggest_resolutions(
                query_defect,
                similar[:5],
                skip_llm=True
            )
        else:
            results['resolution_suggestions'] = {}
        if similar or related_docs:
            resolution_data = results['resolution_suggestions']
            # Run LLM for resolution ai_suggestions and context summary in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_ai = executor.submit(
                    self.resolution_suggester.fill_ai_suggestions,
                    results['resolution_suggestions'],
                    query_defect,
                    similar[:5]
                )
                future_summary = executor.submit(
                    self.context_summarizer.generate_summary,
                    query_defect,
                    similar[:5],
                    related_docs,
                    resolution_data
                )
                future_ai.result()
                results['context_summary'] = future_summary.result()
        
        return results
    
    def analyze_defect(
        self,
        defect: Dict[str, Any],
        n_similar: int = 5,
        n_docs: int = 3
    ) -> Dict[str, Any]:
        """
        Perform comprehensive AI analysis on a specific defect.
        
        Args:
            defect: The defect to analyze.
            n_similar: Number of similar defects to find.
            n_docs: Number of related documents to find.
            
        Returns:
            Dictionary containing analysis results.
        """
        results = {
            'defect': defect,
            'similar_defects': [],
            'resolution_suggestions': {},
            'related_documents': [],
            'context_summary': {}
        }
        
        # Find similar defects
        similar = self.defect_similarity.find_similar(
            defect,
            n_results=n_similar,
            min_similarity=0.5,
            exclude_self=True
        )
        results['similar_defects'] = similar
        
        # Find related documents
        related_docs = self.document_search.search_by_defect(defect, n_results=n_docs)
        results['related_documents'] = related_docs
        
        # Generate resolution suggestions
        results['resolution_suggestions'] = self.resolution_suggester.suggest_resolutions(
            defect,
            similar
        )
        
        # Generate context summary
        results['context_summary'] = self.context_summarizer.generate_summary(
            defect,
            similar,
            related_docs,
            results['resolution_suggestions']
        )
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the GenAI system."""
        status = {
            'initialized': EnhancedSearch._initialized,
            'embedding_model': 'all-MiniLM-L6-v2',
            'llm_available': self.llm_service.is_available() if self.llm_service else False,
            'llm_model': self.llm_service.model_name if self.llm_service else 'N/A',
            'defects_indexed': 0,
            'documents_indexed': 0
        }
        
        if self.vector_store:
            stats = self.vector_store.get_collection_stats()
            status['defects_indexed'] = stats.get('defect_count', 0)
            status['documents_indexed'] = stats.get('document_count', 0)
        
        return status


def display_enhanced_results(results: Dict[str, Any]):
    """
    Display enhanced search results in Streamlit UI.
    
    Args:
        results: Results from EnhancedSearch.search() or analyze_defect().
    """
    # 1. Similar Defects Section
    similar = results.get('similar_defects', [])
    if similar:
        st.markdown("---")
        st.markdown("### 🔍 Similar Past Defects")
        
        for i, defect in enumerate(similar[:5], 1):
            metadata = defect.get('metadata', {})
            similarity = defect.get('similarity', 0)
            
            # Determine status styling
            status = metadata.get('status', 'Unknown')
            status_color = "🟢" if 'closed' in status.lower() or 'resolved' in status.lower() else "🟡"
            
            issue_key = metadata.get('issue_key', 'Unknown')
            jira_base_url = "https://jira.sp.vodafone.com/browse"
            jira_link = f"{jira_base_url}/{issue_key}"
            
            with st.expander(f"{status_color} {issue_key} ({similarity}% match) - {status}", expanded=(i==1)):
                # JIRA Link
                st.markdown(f'<a href="{jira_link}" target="_blank" style="color: #1a73e8; text-decoration: none;">🔗 Open in JIRA</a>', unsafe_allow_html=True)
                st.markdown(f"**Summary:** {metadata.get('summary', 'N/A')}")
                
                fix_desc = metadata.get('fix_description', '')
                if fix_desc and fix_desc.lower() not in ['nan', 'none', '']:
                    st.markdown(f"**Resolution:** {fix_desc}")
                
                wave = metadata.get('osf_wave', '')
                if wave and wave.lower() != 'nan':
                    st.markdown(f"**Fixed in:** {wave}")
                
                source = metadata.get('source', '')
                if source:
                    st.markdown(f"**Source:** {source}")
    
    # 2. Resolution Suggestions Section
    resolution = results.get('resolution_suggestions', {})
    if resolution.get('suggestions') or resolution.get('root_causes'):
        st.markdown("---")
        st.markdown("### ✅ AI Suggested Resolutions")
        
        # Suggestions
        for i, sugg in enumerate(resolution.get('suggestions', [])[:3], 1):
            confidence = sugg.get('confidence', 'low')
            emoji = {'high': '🟢', 'medium': '🟡', 'low': '🟠'}.get(confidence, '⚪')
            
            st.markdown(f"""
            {emoji} **Suggestion {i}** (from {sugg.get('source', 'analysis')})
            
            {sugg.get('text', 'N/A')}
            """)
        
        # Root causes
        root_causes = resolution.get('root_causes', [])
        if root_causes:
            st.markdown("**⚠️ Common Root Causes in Similar Defects:**")
            for rc in root_causes[:3]:
                st.markdown(f"- {rc['cause']} ({rc['percentage']}%)")
        
        # AI suggestions
        ai_sugg = resolution.get('ai_suggestions', '')
        if ai_sugg:
            st.markdown("**AI Analysis:**")
            st.markdown(ai_sugg)
    
    # 3. Related Documents Section
    docs = results.get('related_documents', [])
    if docs:
        st.markdown("---")
        st.markdown("### 📚 Related Knowledge Documents")
        
        # SharePoint document URL
        doc_base_url = "https://amdocs-my.sharepoint.com/:t:/r/personal/sudhikut_amdocs_com/Documents/Documents/GenAI/GenAI%20Defect%20Portal/genai_defect_management/DefectPortal/knowledge_base/documents"
        doc_query_params = "?csf=1&web=1"
        
        for doc in docs[:3]:
            metadata = doc.get('metadata', {})
            filename = metadata.get('filename', 'Unknown Document')
            relevance = doc.get('similarity', 0)
            section = metadata.get('section', '')
            content = doc.get('content', '')[:300]
            filepath = metadata.get('filepath', '')
            
            # Create document link using filename (URL encode spaces)
            filename_encoded = filename.replace(' ', '%20')
            doc_link = f"{doc_base_url}/{filename_encoded}{doc_query_params}"
            
            with st.expander(f"📄 {filename} ({relevance}% relevance)"):
                if section:
                    st.markdown(f"**Section:** {section}")
                st.markdown(f"**Preview:** {content}...")
                
                if filepath:
                    st.markdown(f'📎 **File Path:** <a href="{doc_link}" target="_blank" style="color: #1a73e8;">{filepath}</a>', unsafe_allow_html=True)
    
    # 4. Context Summary Section
    summary = results.get('context_summary', {})
    if summary:
        st.markdown("---")
        st.markdown("### 📝 AI Context Summary")
        
        full_summary = summary.get('full_summary', '')
        if full_summary:
            st.markdown(full_summary)
        
        # Historical insights
        insights = summary.get('historical_insights', {})
        if insights.get('total_similar', 0) > 0:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Similar Defects", insights.get('total_similar', 0))
            with col2:
                st.metric("Resolution Rate", f"{insights.get('resolution_rate', 0)}%")
            with col3:
                st.metric("Avg Similarity", f"{insights.get('avg_similarity', 0)}%")


def initialize_genai_system(defects_acc: pd.DataFrame = None, defects_sit: pd.DataFrame = None):
    """
    Initialize or get the GenAI system and optionally index data.
    
    Args:
        defects_acc: ACC defects DataFrame.
        defects_sit: SIT defects DataFrame.
        
    Returns:
        EnhancedSearch instance.
    """
    # Use session state to track initialization
    if 'genai_system' not in st.session_state:
        with st.spinner("🚀 Initializing AI Search System..."):
            try:
                enhanced_search = EnhancedSearch()
                st.session_state['genai_system'] = enhanced_search
                st.session_state['genai_indexed'] = False
            except Exception as e:
                st.error(f"Failed to initialize AI system: {e}")
                return None
    
    enhanced_search = st.session_state['genai_system']
    
    # Index data if not already done, or force reindex after DB update
    force_reindex = st.session_state.get('genai_force_reindex', False)
    if not st.session_state.get('genai_indexed', False) or force_reindex:
        if defects_acc is not None or defects_sit is not None:
            msg = "📊 Re-indexing defects from updated DB..." if force_reindex else "📊 Indexing defects for AI search..."
            with st.spinner(msg):
                try:
                    enhanced_search.index_data(
                        defects_acc, defects_sit,
                        index_documents=not force_reindex,
                        force_reindex=force_reindex
                    )
                    st.session_state['genai_indexed'] = True
                    if force_reindex:
                        st.session_state['genai_force_reindex'] = False
                except Exception as e:
                    st.warning(f"Could not index data: {e}")
    
    return enhanced_search
