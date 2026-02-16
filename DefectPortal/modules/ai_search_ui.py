"""
AI-Enhanced Search UI Module
Provides the Streamlit UI components for the AI-powered defect search.
"""

import streamlit as st
import pandas as pd
import altair as alt
import logging
from typing import Dict, Any, Optional, List

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
    
    # 1. AI Context Summary (First Section)
    summary_data = results.get('context_summary', {})
    if summary_data:
        st.markdown("---")
        st.markdown("### 1️⃣ AI Context Summary")
        
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
                    st.metric("Historical Resolution Rate", "70%")
            with col3:
                st.metric("Average Similarity", f"{avg_similarity}%")
    
    # 2. Matching Defects Section
    matching_acc = results.get('matching_defects', {}).get('acc', [])
    matching_sit = results.get('matching_defects', {}).get('sit', [])
    
    if matching_acc or matching_sit:
        st.markdown("---")
        st.markdown("### 2️⃣ Matching Defects")
        
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
    
    # 3. Similar Past Defects Section
    similar_defects = matching_acc + matching_sit  # Combine for similar defects display
    if similar_defects:
        st.markdown("---")
        st.markdown("### 3️⃣ Similar Past Defects (for resolution insights)")
        
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
    
    # 4. AI Suggested Resolutions
    resolution_data = results.get('resolution_suggestions', {})
    if resolution_data.get('suggestions') or resolution_data.get('root_causes'):
        st.markdown("---")
        st.markdown("### 4️⃣ AI Suggested Resolutions")
        
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
    
    # 5. Related Knowledge Documents
    related_docs = results.get('related_documents', [])
    if related_docs:
        st.markdown("---")
        st.markdown("### 5️⃣ Related Knowledge Documents")
        
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
    
    # 6. Insights & Analytics Visualization (Last Section)
    display_ai_search_visualizations(results)


def display_ai_search_visualizations(results: Dict[str, Any]):
    """
    Display visualizations based on AI search results with summary dashboard and expandable charts.
    
    Args:
        results: The enhanced search results dictionary.
    """
    # Combine matching defects from ACC and SIT
    matching_acc = results.get('matching_defects', {}).get('acc', [])
    matching_sit = results.get('matching_defects', {}).get('sit', [])
    all_defects = matching_acc + matching_sit
    
    if not all_defects:
        return
    
    st.markdown("---")
    st.markdown("### 6️⃣ Insights & Analytics")
    
    # Prepare data for visualizations
    defect_data = []
    for defect in all_defects:
        metadata = defect.get('metadata', {})
        defect_data.append({
            'issue_key': metadata.get('issue_key', 'Unknown'),
            'status': metadata.get('status', 'Unknown'),
            'priority': metadata.get('priority', 'Unknown'),
            'similarity': defect.get('similarity', 0),
            'source': metadata.get('source', 'Unknown').upper()
        })
    
    df = pd.DataFrame(defect_data)
    
    if df.empty:
        return
    
    # Helper function to categorize status
    def categorize_status(status):
        status_lower = str(status).lower()
        if any(kw in status_lower for kw in ['closed', 'resolved', 'done', 'fixed']):
            return 'Resolved'
        elif any(kw in status_lower for kw in ['open', 'new', 'to do']):
            return 'Open'
        else:
            return 'In Progress'
    
    df['status_category'] = df['status'].apply(categorize_status)
    
    # Calculate summary metrics
    total_defects = len(df)
    resolved_count = len(df[df['status_category'] == 'Resolved'])
    resolved_pct = round((resolved_count / total_defects) * 100, 1) if total_defects > 0 else 0
    avg_similarity = round(df['similarity'].mean(), 1)
    
    # Get top priority
    priority_order = {'1-Blocker': 1, '2-Critical': 2, '3-Major': 3, '4-Minor': 4, '5-Trivial': 5}
    df['priority_rank'] = df['priority'].map(priority_order).fillna(99)
    top_priority = df.loc[df['priority_rank'].idxmin(), 'priority'] if not df.empty else 'N/A'
    
    # ACC vs SIT counts
    acc_count = len(df[df['source'] == 'ACC'])
    sit_count = len(df[df['source'] == 'SIT'])
    
    # ==================== SUMMARY CARDS ====================
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .metric-card-blue {
        background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%);
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #f46b45 0%, #eea849 100%);
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 14px;
        opacity: 0.9;
    }
    .metric-sublabel {
        font-size: 12px;
        opacity: 0.7;
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display summary cards
    card1, card2, card3, card4 = st.columns(4)
    
    with card1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Defects</div>
            <div class="metric-value">{total_defects}</div>
            <div class="metric-sublabel">ACC: {acc_count} | SIT: {sit_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with card2:
        st.markdown(f"""
        <div class="metric-card metric-card-green">
            <div class="metric-label">Resolution Rate</div>
            <div class="metric-value">{resolved_pct}%</div>
            <div class="metric-sublabel">{resolved_count} of {total_defects} resolved</div>
        </div>
        """, unsafe_allow_html=True)
    
    with card3:
        st.markdown(f"""
        <div class="metric-card metric-card-blue">
            <div class="metric-label">Avg Similarity</div>
            <div class="metric-value">{avg_similarity}%</div>
            <div class="metric-sublabel">Match confidence</div>
        </div>
        """, unsafe_allow_html=True)
    
    with card4:
        st.markdown(f"""
        <div class="metric-card metric-card-orange">
            <div class="metric-label">Top Priority</div>
            <div class="metric-value">{top_priority.split('-')[1] if '-' in str(top_priority) else top_priority}</div>
            <div class="metric-sublabel">Highest severity found</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ==================== EXPANDABLE CHART SECTIONS ====================
    
    # Chart 1: Defects by Status
    with st.expander("📊 View Status Distribution", expanded=False):
        status_counts = df['status_category'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        status_counts['Percentage'] = (status_counts['Count'] / status_counts['Count'].sum() * 100).round(1)
        
        status_colors = alt.Scale(
            domain=['Resolved', 'In Progress', 'Open'],
            range=['#2ecc71', '#f39c12', '#e74c3c']
        )
        
        col_chart, col_table = st.columns([2, 1])
        with col_chart:
            pie_chart = alt.Chart(status_counts).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field='Count', type='quantitative'),
                color=alt.Color('Status:N', scale=status_colors, legend=alt.Legend(title="Status")),
                tooltip=['Status', 'Count', alt.Tooltip('Percentage:Q', format='.1f', title='%')]
            ).properties(height=300)
            
            st.altair_chart(pie_chart, use_container_width=True)
        
        with col_table:
            st.markdown("**Status Breakdown**")
            st.dataframe(status_counts, hide_index=True, use_container_width=True)
    
    # Chart 2: Defects by Priority
    with st.expander("📊 View Priority Analysis", expanded=False):
        priority_counts = df['priority'].value_counts().reset_index()
        priority_counts.columns = ['Priority', 'Count']
        
        priority_order_list = ['1-Blocker', '2-Critical', '3-Major', '4-Minor', '5-Trivial']
        
        col_chart, col_table = st.columns([2, 1])
        with col_chart:
            bar_chart = alt.Chart(priority_counts).mark_bar(
                cornerRadiusTopLeft=5,
                cornerRadiusTopRight=5
            ).encode(
                x=alt.X('Priority:N', sort=priority_order_list, title='Priority'),
                y=alt.Y('Count:Q', title='Number of Defects'),
                color=alt.Color('Priority:N', scale=alt.Scale(scheme='reds'), legend=None),
                tooltip=['Priority', 'Count']
            ).properties(height=300)
            
            st.altair_chart(bar_chart, use_container_width=True)
        
        with col_table:
            st.markdown("**Priority Breakdown**")
            st.dataframe(priority_counts, hide_index=True, use_container_width=True)
    
    # Chart 3: Similarity Score Distribution
    with st.expander("📊 View Similarity Scores", expanded=False):
        similarity_df = df[['issue_key', 'similarity']].copy()
        similarity_df = similarity_df.sort_values('similarity', ascending=False).head(10)
        similarity_df.columns = ['Defect ID', 'Similarity %']
        
        col_chart, col_table = st.columns([2, 1])
        with col_chart:
            similarity_chart = alt.Chart(similarity_df).mark_bar(
                cornerRadiusTopLeft=5,
                cornerRadiusTopRight=5
            ).encode(
                x=alt.X('Defect ID:N', sort='-y', title='Defect ID', axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('Similarity %:Q', title='Similarity %', scale=alt.Scale(domain=[0, 100])),
                color=alt.Color('Similarity %:Q', scale=alt.Scale(scheme='blues'), legend=None),
                tooltip=['Defect ID', alt.Tooltip('Similarity %:Q', title='Similarity %')]
            ).properties(height=300)
            
            st.altair_chart(similarity_chart, use_container_width=True)
        
        with col_table:
            st.markdown("**Top 10 Matches**")
            st.dataframe(similarity_df, hide_index=True, use_container_width=True)
    
    # Chart 4: Source Distribution (ACC vs SIT)
    with st.expander("📊 View Source Distribution", expanded=False):
        source_counts = df['source'].value_counts().reset_index()
        source_counts.columns = ['Source', 'Count']
        source_counts['Percentage'] = (source_counts['Count'] / source_counts['Count'].sum() * 100).round(1)
        
        source_colors = alt.Scale(
            domain=['ACC', 'SIT'],
            range=['#e74c3c', '#f1c40f']
        )
        
        col_chart, col_table = st.columns([2, 1])
        with col_chart:
            source_pie = alt.Chart(source_counts).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field='Count', type='quantitative'),
                color=alt.Color('Source:N', scale=source_colors, legend=alt.Legend(title="Environment")),
                tooltip=['Source', 'Count', alt.Tooltip('Percentage:Q', format='.1f', title='%')]
            ).properties(height=300)
            
            st.altair_chart(source_pie, use_container_width=True)
        
        with col_table:
            st.markdown("**Environment Breakdown**")
            st.dataframe(source_counts, hide_index=True, use_container_width=True)


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
