"""
AI-Enhanced Search UI Module
Provides the Streamlit UI components for the AI-powered defect search.
"""

import streamlit as st
import pandas as pd
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def render_ai_search_section(defect_data_acc: pd.DataFrame, defect_data_sit: pd.DataFrame):
    """
    Render the AI-enhanced search section in the Streamlit UI.
    
    Args:
        defect_data_acc: ACC defects DataFrame.
        defect_data_sit: SIT defects DataFrame.
    """
    st.markdown("---")
    st.markdown("## 🤖 AI-Enhanced Defect Search")
    
    # Initialize GenAI system
    try:
        from modules.genai.enhanced_search import EnhancedSearch, initialize_genai_system
        
        # Get or initialize the GenAI system
        enhanced_search = initialize_genai_system(defect_data_acc, defect_data_sit)
        
        if enhanced_search is None:
            st.error("AI Search system could not be initialized.")
            return
        
        # Show system status
        with st.expander("🔧 AI System Status", expanded=False):
            status = enhanced_search.get_status()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Defects Indexed", status.get('defects_indexed', 0))
            with col2:
                st.metric("Documents Indexed", status.get('documents_indexed', 0))
            with col3:
                llm_status = "✅ Active" if status.get('llm_available') else "⚠️ Fallback Mode"
                st.metric("LLM Status", llm_status)
        
        # Search input - inline layout
        st.markdown("**🔍 Search defects using AI**")
        col1, col2 = st.columns([6, 1])
        with col1:
            query = st.text_input(
                "Search query",
                placeholder="Describe the issue (e.g., 'payment processing error in subscription renewal')",
                key="ai_search_query",
                label_visibility="collapsed"
            )
        with col2:
            search_button = st.button("🚀 AI Search", key="ai_search_btn", use_container_width=True)
        
        # Perform search
        if search_button and query:
            with st.spinner("🔍 Performing AI-enhanced search..."):
                results = enhanced_search.search(
                    query=query,
                    defects_acc=defect_data_acc,
                    defects_sit=defect_data_sit,
                    n_similar_defects=5,
                    n_related_docs=3,
                    min_similarity=0.3
                )
                
                # Store results in session state
                st.session_state['ai_search_results'] = results
        
        # Display results if available
        if 'ai_search_results' in st.session_state and st.session_state['ai_search_results']:
            display_ai_search_results(st.session_state['ai_search_results'])
    
    except ImportError as e:
        st.warning(f"AI Search module not fully installed. Please install required packages: {e}")
        st.info("Run: `pip install sentence-transformers chromadb`")
    except Exception as e:
        logger.error(f"Error in AI search: {e}")
        st.error(f"AI Search error: {e}")


def display_ai_search_results(results: Dict[str, Any]):
    """
    Display the AI search results in a formatted layout.
    
    Args:
        results: Results from EnhancedSearch.search()
    """
    query = results.get('query', '')
    
    st.markdown("---")
    st.markdown(f"### 🎯 AI Search Results for: *\"{query}\"*")
    
    # 1. Matching Defects Section
    matching_acc = results.get('matching_defects', {}).get('acc', [])
    matching_sit = results.get('matching_defects', {}).get('sit', [])
    
    if matching_acc or matching_sit:
        st.markdown("---")
        st.markdown("### 1️⃣ Matching Defects")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔴 ACC Defects")
            if matching_acc:
                for defect in matching_acc[:5]:
                    display_defect_card(defect, "acc")
            else:
                st.info("No matching ACC defects found")
        
        with col2:
            st.markdown("#### 🟡 SIT Defects")
            if matching_sit:
                for defect in matching_sit[:5]:
                    display_defect_card(defect, "sit")
            else:
                st.info("No matching SIT defects found")
    
    # 2. Similar Past Defects Section
    similar_defects = matching_acc + matching_sit  # Combine for similar defects display
    if similar_defects:
        st.markdown("---")
        st.markdown("### 2️⃣ Similar Past Defects (for resolution insights)")
        
        for i, defect in enumerate(similar_defects[:5], 1):
            metadata = defect.get('metadata', {})
            similarity = defect.get('similarity', 0)
            status = metadata.get('status', 'Unknown')
            
            # Determine if resolved
            is_resolved = any(kw in status.lower() for kw in ['closed', 'resolved', 'done', 'fixed'])
            status_icon = "🟢" if is_resolved else "🟡"
            
            issue_key = metadata.get('issue_key', 'Unknown')
            jira_base_url = "https://jira.sp.vodafone.com/browse"
            jira_link = f"{jira_base_url}/{issue_key}"
            
            with st.expander(
                f"{status_icon} {issue_key} ({similarity}% match) - {status}",
                expanded=(i == 1)
            ):
                # JIRA Link
                st.markdown(f'<a href="{jira_link}" target="_blank" style="color: #1a73e8; text-decoration: none;">🔗 Open in JIRA</a>', unsafe_allow_html=True)
                st.markdown(f"**Summary:** {metadata.get('summary', 'N/A')}")
                
                fix_desc = metadata.get('fix_description', '')
                if fix_desc and str(fix_desc).lower() not in ['nan', 'none', '']:
                    st.markdown(f"**✅ Resolution:** {fix_desc}")
                
                wave = metadata.get('osf_wave', '')
                if wave and str(wave).lower() != 'nan':
                    st.markdown(f"**Fixed in:** {wave}")
                
                source = metadata.get('source', '')
                if source:
                    st.markdown(f"**Environment:** {source}")
    
    # 3. AI Suggested Resolutions
    resolution_data = results.get('resolution_suggestions', {})
    if resolution_data.get('suggestions') or resolution_data.get('root_causes'):
        st.markdown("---")
        st.markdown("### 3️⃣ AI Suggested Resolutions")
        
        # Suggestions
        suggestions = resolution_data.get('suggestions', [])
        for i, sugg in enumerate(suggestions[:3], 1):
            confidence = sugg.get('confidence', 'low')
            confidence_emoji = {'high': '🟢', 'medium': '🟡', 'low': '🟠'}.get(confidence, '⚪')
            
            st.markdown(f"""
            {confidence_emoji} **Suggestion {i}** (from {sugg.get('source', 'analysis')}, {sugg.get('similarity', 0)}% match)
            
            > {sugg.get('text', 'N/A')}
            """)
        
        # Root Causes
        root_causes = resolution_data.get('root_causes', [])
        if root_causes:
            st.markdown("**⚠️ Common Root Causes in Similar Defects:**")
            for rc in root_causes[:3]:
                st.markdown(f"- {rc['cause']} ({rc['percentage']}%)")
        
        # AI Analysis
        ai_suggestions = resolution_data.get('ai_suggestions', '')
        if ai_suggestions:
            st.markdown("""
            <div style="
                background-color: #f0f7ff;
                border-left: 4px solid #2196F3;
                padding: 12px 16px;
                margin: 10px 0;
                border-radius: 4px;
            ">
                <strong style="color: #1976D2;">💡 AI Analysis</strong>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(ai_suggestions)
    
    # 4. Related Knowledge Documents
    related_docs = results.get('related_documents', [])
    if related_docs:
        st.markdown("---")
        st.markdown("### 4️⃣ Related Knowledge Documents")
        
        # SharePoint document URL
        doc_base_url = "https://amdocs-my.sharepoint.com/:t:/r/personal/sudhikut_amdocs_com/Documents/Documents/GenAI/GenAI%20Defect%20Portal/genai_defect_management/DefectPortal/knowledge_base/documents"
        doc_query_params = "?csf=1&web=1"
        
        for doc in related_docs[:3]:
            metadata = doc.get('metadata', {})
            filename = metadata.get('filename', 'Unknown Document')
            relevance = doc.get('similarity', 0)
            section = metadata.get('section', '')
            content = doc.get('content', '')[:400]
            filepath = metadata.get('filepath', '')
            
            # Create document link using filename (URL encode spaces)
            filename_encoded = filename.replace(' ', '%20')
            doc_link = f"{doc_base_url}/{filename_encoded}{doc_query_params}"
            
            with st.expander(f"📄 {filename} ({relevance}% relevance)"):
                if section:
                    st.markdown(f"**Section:** {section}")
                
                st.markdown("**Preview:**")
                st.markdown(f"""
                <div style="
                    background-color: #fafafa;
                    border: 1px solid #e0e0e0;
                    padding: 12px;
                    border-radius: 6px;
                    color: #333333;
                    font-size: 14px;
                    line-height: 1.6;
                ">
                    {content}...
                </div>
                """, unsafe_allow_html=True)
                
                if filepath:
                    st.markdown(f'📎 **File Path:** <a href="{doc_link}" target="_blank" style="color: #1a73e8;">{filepath}</a>', unsafe_allow_html=True)
    
    # 5. AI Context Summary
    summary_data = results.get('context_summary', {})
    if summary_data:
        st.markdown("---")
        st.markdown("### 5️⃣ AI Context Summary")
        
        full_summary = summary_data.get('full_summary', '')
        if full_summary:
            st.markdown(full_summary)
        
        # Historical Insights
        insights = summary_data.get('historical_insights', {})
        if insights.get('total_similar', 0) > 0:
            st.markdown("**📊 Historical Data:**")
            col1, col2, col3 = st.columns(3)
            
            total_similar = insights.get('total_similar', 0)
            resolution_rate = insights.get('resolution_rate', 0)
            avg_similarity = insights.get('avg_similarity', 0)
            
            with col1:
                st.metric("Similar Defects Found", total_similar)
            with col2:
                # Handle 0% resolution rate with better messaging
                if resolution_rate > 0:
                    st.metric("Historical Resolution Rate", f"{resolution_rate}%")
                else:
                    st.metric("Historical Resolution Rate", "In Progress", delta="Analyzing", delta_color="off")
            with col3:
                st.metric("Average Similarity", f"{avg_similarity}%")


def display_defect_card(defect: Dict[str, Any], source: str):
    """
    Display a single defect card.
    
    Args:
        defect: Defect data dictionary.
        source: Source environment (acc/sit).
    """
    metadata = defect.get('metadata', {})
    similarity = defect.get('similarity', 0)
    
    # Style based on source
    border_color = "#e74c3c" if source == "acc" else "#E3BB10"
    
    issue_key = metadata.get('issue_key', 'Unknown')
    summary = metadata.get('summary', 'No summary available')
    status = metadata.get('status', 'Unknown')
    priority = metadata.get('priority', 'Unknown')
    
    # Static JIRA URL for demo (replace with actual JIRA base URL in production)
    jira_base_url = "https://jira.sp.vodafone.com/browse"
    jira_link = f"{jira_base_url}/{issue_key}"
    
    st.markdown(f"""
    <div style="
        border-left: 4px solid {border_color};
        padding: 10px;
        margin: 10px 0;
        background-color: #f8f9fa;
        border-radius: 4px;
    ">
        <a href="{jira_link}" target="_blank" style="text-decoration: none; color: #1a73e8;">
            <strong>🔗 {issue_key}</strong>
        </a> ({similarity}% match)<br>
        <small>Status: {status} | Priority: {priority}</small><br>
        <p style="margin-top: 8px;">{summary[:200]}...</p>
    </div>
    """, unsafe_allow_html=True)


def render_defect_analysis_modal(defect: Dict[str, Any]):
    """
    Render a modal with detailed AI analysis for a specific defect.
    
    Args:
        defect: The defect to analyze.
    """
    try:
        from modules.genai.enhanced_search import EnhancedSearch
        
        enhanced_search = EnhancedSearch()
        
        with st.spinner("🔍 Analyzing defect..."):
            results = enhanced_search.analyze_defect(defect)
        
        # Display results
        st.markdown(f"## 📋 AI Analysis: {defect.get('Issue key', 'Unknown')}")
        
        # Similar defects
        similar = results.get('similar_defects', [])
        if similar:
            st.markdown("### Similar Past Defects")
            for s in similar[:3]:
                metadata = s.get('metadata', {})
                st.markdown(f"- **{metadata.get('issue_key')}** ({s.get('similarity')}%): {metadata.get('summary', 'N/A')[:100]}")
        
        # Resolution suggestions
        resolution = results.get('resolution_suggestions', {})
        if resolution.get('suggestions'):
            st.markdown("### Suggested Resolutions")
            for sugg in resolution['suggestions'][:3]:
                st.markdown(f"- {sugg.get('text', 'N/A')}")
        
        # Related docs
        docs = results.get('related_documents', [])
        if docs:
            st.markdown("### Related Documentation")
            doc_base_url = "https://amdocs-my.sharepoint.com/:t:/r/personal/sudhikut_amdocs_com/Documents/Documents/GenAI/GenAI%20Defect%20Portal/genai_defect_management/DefectPortal/knowledge_base/documents"
            doc_query_params = "?csf=1&web=1"
            for doc in docs[:2]:
                metadata = doc.get('metadata', {})
                filename = metadata.get('filename', 'Unknown')
                filename_encoded = filename.replace(' ', '%20')
                doc_link = f"{doc_base_url}/{filename_encoded}{doc_query_params}"
                st.markdown(f'- <a href="{doc_link}" target="_blank" style="color: #1a73e8; text-decoration: none;">📄 {filename}</a>', unsafe_allow_html=True)
        
        # Summary
        summary = results.get('context_summary', {})
        if summary.get('full_summary'):
            st.markdown("### AI Summary")
            st.markdown(summary['full_summary'])
    
    except Exception as e:
        logger.error(f"Error analyzing defect: {e}")
        st.error(f"Could not analyze defect: {e}")


def render_genai_sidebar():
    """Render GenAI settings in the sidebar."""
    with st.sidebar:
        st.markdown("### 🤖 AI Settings")
        
        # Index management
        if st.button("🔄 Re-index Data", key="reindex_btn"):
            st.session_state['genai_indexed'] = False
            st.session_state.pop('genai_system', None)
            st.success("AI index will be rebuilt on next search")
        
        # Index documents
        if st.button("📚 Index Knowledge Base", key="index_docs_btn"):
            try:
                from modules.genai.enhanced_search import EnhancedSearch
                enhanced_search = EnhancedSearch()
                with st.spinner("Indexing documents..."):
                    enhanced_search.document_search.load_and_index_documents()
                st.success("Documents indexed successfully!")
            except Exception as e:
                st.error(f"Failed to index documents: {e}")
        
        # Show stats
        if 'genai_system' in st.session_state:
            status = st.session_state['genai_system'].get_status()
            st.markdown("---")
            st.markdown("**Index Stats:**")
            st.markdown(f"- Defects: {status.get('defects_indexed', 0)}")
            st.markdown(f"- Documents: {status.get('documents_indexed', 0)}")
            st.markdown(f"- LLM: {'✅' if status.get('llm_available') else '⚠️ Fallback'}")
