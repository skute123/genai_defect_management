"""
AI-Enhanced Search UI Module
Provides the Streamlit UI components for the AI-powered defect search.
"""

import html
import streamlit as st
import pandas as pd
import altair as alt
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Path to Recommended Logs Excel (under DefectPortal/data/)
RECOMMENDED_LOGS_EXCEL = Path(__file__).resolve().parent.parent / "data" / "Recommended_Logs_for_Investigation.xlsx"
# Knowledge base documents folder (for resolving current filenames after renames)
KNOWLEDGE_BASE_DOCUMENTS = Path(__file__).resolve().parent.parent / "knowledge_base" / "documents"


def _resolve_document_display_name(metadata: Dict[str, Any]) -> str:
    """
    Resolve the display filename from the file system so renames in knowledge_base/documents
    are reflected in the GUI without re-indexing when possible.
    """
    stored_name = metadata.get('filename') or 'Unknown Document'
    filepath = metadata.get('filepath', '')
    if not filepath:
        return stored_name
    path = Path(filepath)
    if path.is_file():
        return path.name
    # File was moved/renamed: if directory exists, look for single file with same extension
    parent = path.parent
    ext = path.suffix.lower()
    if parent.is_dir() and ext:
        try:
            same_ext = [f.name for f in parent.iterdir() if f.is_file() and f.suffix.lower() == ext]
            if len(same_ext) == 1:
                return same_ext[0]
        except OSError:
            pass
    return stored_name


def _load_recommended_logs_for_query(query: str) -> pd.DataFrame:
    """Load Recommended Logs Excel and filter rows where Error Description matches the AI search query."""
    if not query or not query.strip():
        return pd.DataFrame()
    if not RECOMMENDED_LOGS_EXCEL.exists():
        logger.warning("Recommended Logs Excel not found: %s", RECOMMENDED_LOGS_EXCEL)
        return pd.DataFrame()
    try:
        df = pd.read_excel(RECOMMENDED_LOGS_EXCEL)
        if df.empty or "Error Description" not in df.columns:
            return df
        q = str(query).strip().lower()
        err_col = df["Error Description"].astype(str).str.lower()
        # Match rows where query appears in Error Description
        mask = err_col.str.contains(q, na=False, regex=False)
        # Also match if any significant token from query (e.g. KIAS-SetMarketingPermissions) is in error
        skip_words = {"error", "was", "while", "invoking", "encountered", "this", "that", "with", "for", "the", "and"}
        for part in q.split():
            if len(part) > 3 and part not in skip_words:
                mask = mask | err_col.str.contains(part, na=False, regex=False)
        return df.loc[mask].drop_duplicates().reset_index(drop=True)
    except Exception as e:
        logger.error("Failed to load Recommended Logs Excel: %s", e)
        return pd.DataFrame()

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
            display_ai_search_results(
                st.session_state['ai_search_results'],
                defect_data_acc=defect_data_acc,
                defect_data_sit=defect_data_sit,
            )
    
    except ImportError as e:
        st.warning(f"AI Search module not fully installed. Please install required packages: {e}")
        st.info("Run: `pip install sentence-transformers chromadb`")
    except Exception as e:
        logger.error(f"Error in AI search: {e}")
        st.error(f"AI Search error: {e}")


def _get_fix_description_from_db(
    issue_key: str,
    defect_data_acc: Optional[pd.DataFrame],
    defect_data_sit: Optional[pd.DataFrame],
    fix_desc_column: str = "Custom field (OSF-Fix Description)",
) -> str:
    """Look up fix description for a defect by issue_key in ACC/SIT data. Returns empty string if not found."""
    if not issue_key or issue_key == "Unknown":
        return ""
    for df in (defect_data_acc, defect_data_sit):
        if df is None or df.empty or fix_desc_column not in df.columns:
            continue
        key_col = "Issue key"
        if key_col not in df.columns:
            continue
        match = df[df[key_col].astype(str).str.strip().str.upper() == str(issue_key).strip().upper()]
        if not match.empty:
            val = match[fix_desc_column].iloc[0]
            if pd.notna(val) and str(val).strip().lower() not in ("", "nan", "none"):
                return str(val).strip()[:1000]
    return ""


def display_ai_search_results(
    results: Dict[str, Any],
    defect_data_acc: Optional[pd.DataFrame] = None,
    defect_data_sit: Optional[pd.DataFrame] = None,
):
    """
    Display the AI search results in a formatted layout.
    
    Args:
        results: Results from EnhancedSearch.search()
        defect_data_acc: Optional ACC defects DataFrame for resolving fix description from DB when missing in cache.
        defect_data_sit: Optional SIT defects DataFrame for resolving fix description from DB when missing in cache.
    """
    query = results.get('query', '')
    
    # 1. AI Context Summary (combined with AI Analysis, styled like AI Analysis callout)
    summary_data = results.get('context_summary', {})
    resolution_data = results.get('resolution_suggestions', {})
    if summary_data or resolution_data.get('ai_suggestions'):
        st.markdown("---")
        st.markdown("### 1️⃣ AI Context Summary")
        
        # Build structured bulleted summary (skip generic "Unknown" overview; no **; user-friendly)
        bullet_items = []
        
        if summary_data:
            overview = summary_data.get('overview', '').strip()
            # Skip generic placeholder like "This is a Unknown priority defect in Unknown system, currently Unknown."
            if overview and not ('unknown priority' in overview.lower() and 'unknown system' in overview.lower()):
                bullet_items.append(('summary', overview))
            elif query and not bullet_items:
                # When overview was skipped, use search query as context so the summary has clear defect context
                bullet_items.append(('summary', f"Defect context: {query}"))
            
            full_summary = summary_data.get('full_summary', '').strip()
            if full_summary:
                bullet_items.append(('summary', full_summary))
            
            likely_cause = summary_data.get('likely_cause', '').strip()
            if likely_cause:
                bullet_items.append(('cause', likely_cause))
            
            recommended = summary_data.get('recommended_action', '').strip()
            if recommended:
                bullet_items.append(('action', recommended))
        
        ai_suggestions = resolution_data.get('ai_suggestions', '').strip()
        if ai_suggestions:
            bullet_items.append(('ai', ai_suggestions))
        
        ai_sub_lines = [ln.strip() for ln in ai_suggestions.splitlines() if ln.strip()] if ai_suggestions else []
        
        if bullet_items:
            def esc(t):
                return html.escape(str(t)).replace('\n', ' ')
            
            lines = []
            for kind, text in bullet_items:
                if not text and kind != 'ai':
                    continue
                if kind == 'summary':
                    if text.strip().lower().startswith('defect context:'):
                        rest = text.strip()[16:].strip()  # after "Defect context:"
                        lines.append(f"<li style='margin-bottom: 8px;'><span style='color: #1565c0; font-weight: 600;'>Defect context:</span> <span style='color: #37474f;'>{esc(rest)}</span></li>")
                    else:
                        lines.append(f"<li style='margin-bottom: 8px;'><span style='color: #37474f;'>{esc(text)}</span></li>")
                elif kind == 'cause':
                    lines.append(f"<li style='margin-bottom: 8px;'><span style='color: #1565c0; font-weight: 600;'>Likely cause:</span> <span style='color: #37474f;'>{esc(text)}</span></li>")
                elif kind == 'action':
                    lines.append(f"<li style='margin-bottom: 8px;'><span style='color: #1565c0; font-weight: 600;'>Recommended action:</span> <span style='color: #37474f;'>{esc(text)}</span></li>")
                elif kind == 'ai':
                    if ai_sub_lines:
                        sub = "".join(f"<li style='margin-bottom: 4px;'>{esc(ln)}</li>" for ln in ai_sub_lines)
                        lines.append(f"<li style='margin-bottom: 4px;'><span style='color: #1565c0; font-weight: 600;'>Resolution suggestions:</span><ul style='margin: 6px 0 0 18px; padding-left: 12px;'>{sub}</ul></li>")
                    else:
                        lines.append(f"<li style='margin-bottom: 8px;'><span style='color: #1565c0; font-weight: 600;'>Resolution suggestions:</span> <span style='color: #37474f;'>{esc(ai_suggestions)}</span></li>")
            
            if lines:
                list_html = "<ul style='margin: 0; padding-left: 20px; list-style-type: disc;'>" + "".join(lines) + "</ul>"
                st.markdown(f"""
                <div style="
                    background-color: #e3f2fd;
                    border-left: 4px solid #1976d2;
                    padding: 16px 20px;
                    margin: 12px 0 28px 0;
                    border-radius: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                ">
                    <strong style="color: #1565c0; font-size: 1.2rem;">💡 AI Context Summary & Analysis</strong>
                    <div style="color: #37474f; line-height: 1.6; margin-top: 12px;">{list_html}</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Historical Insights
        insights = (summary_data or {}).get('historical_insights', {})
        if insights.get('total_similar', 0) > 0:
            st.markdown("**📊 Historical Data:**")
            col1, col2, col3 = st.columns(3)
            
            total_similar = insights.get('total_similar', 0)
            resolution_rate = insights.get('resolution_rate', 0)
            avg_similarity = insights.get('avg_similarity', 0)
            
            with col1:
                st.metric("Similar Defects Found", total_similar)
            with col2:
                st.metric("Historical Resolution Rate", f"{resolution_rate}%")
            with col3:
                st.metric("Average Similarity", f"{avg_similarity}%")
    
    # 2. Matching Defects Section (symmetric: cap SIT by ACC count so columns align)
    matching_acc = results.get('matching_defects', {}).get('acc', [])
    matching_sit = results.get('matching_defects', {}).get('sit', [])
    
    if matching_acc or matching_sit:
        st.markdown("---")
        st.markdown("### 2️⃣ Matching Defects")
        
        n_acc = min(5, len(matching_acc))
        # Symmetry: when ACC has fewer than 5, cap SIT by ACC count; when ACC is empty, SIT shows up to 5; if SIT has less, take as is
        n_sit = min(n_acc, len(matching_sit)) if (matching_sit and n_acc > 0) else (min(5, len(matching_sit)) if matching_sit else 0)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔴 ACC Defects")
            if matching_acc:
                for defect in matching_acc[:n_acc]:
                    display_defect_card(defect, "acc")
            else:
                st.info("No matching ACC defects found")
        
        with col2:
            st.markdown("#### 🟡 SIT Defects")
            if matching_sit:
                for defect in matching_sit[:n_sit]:
                    display_defect_card(defect, "sit")
            else:
                st.info("No matching SIT defects found")
    
    # 3. Similar Past Defects Section – top 5 by similarity from both ACC and SIT
    combined = matching_acc + matching_sit
    similar_defects = sorted(combined, key=lambda d: d.get('similarity', 0), reverse=True)[:5]
    if similar_defects:
        st.markdown("---")
        st.markdown("### 3️⃣ Similar Past Defects (for resolution insights)")
        
        for i, defect in enumerate(similar_defects, 1):
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
                expanded=False
            ):
                # JIRA Link
                st.markdown(f'<a href="{jira_link}" target="_blank" style="color: #1a73e8; text-decoration: none;">🔗 Open in JIRA</a>', unsafe_allow_html=True)
                st.markdown(f"**Summary:** {metadata.get('summary', 'N/A')}")
                
                fix_desc = metadata.get('fix_description', '') or ''
                if not fix_desc or str(fix_desc).strip().lower() in ('nan', 'none', ''):
                    # Fallback: look up current fix description from DB (e.g. OS-77008 has resolution in DB but not in vector cache)
                    fix_desc = _get_fix_description_from_db(issue_key, defect_data_acc, defect_data_sit)
                if fix_desc and str(fix_desc).strip().lower() not in ('nan', 'none', ''):
                    st.markdown(f"**✅ Resolution:** {fix_desc}")
                
                wave = metadata.get('osf_wave', '')
                if wave and str(wave).lower() != 'nan':
                    st.markdown(f"**Fixed in:** {wave}")
                
                source = metadata.get('source', '')
                if source:
                    st.markdown(f"**Environment:** {source}")
    
    # 4. AI Suggested Resolutions (suggestion cards + root causes; AI analysis text is in section 1)
    resolution_data = results.get('resolution_suggestions', {})
    if resolution_data.get('suggestions') or resolution_data.get('root_causes'):
        st.markdown("---")
        st.markdown("### 4️⃣ AI Suggested Resolutions")
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

        # Suggestions – stacked cards (match level from similarity %)
        suggestions = resolution_data.get('suggestions', [])
        for i, sugg in enumerate(suggestions[:3], 1):
            similarity = sugg.get('similarity', 0)
            # Derive HIGH/MEDIUM/LOW from match percentage
            if similarity >= 60:
                match_level, match_color = 'high', '#2e7d32'
            elif similarity >= 40:
                match_level, match_color = 'medium', '#ed6c02'
            else:
                match_level, match_color = 'low', '#f9a825'
            source_key = html.escape(str(sugg.get('source', 'analysis')))
            text = html.escape(str(sugg.get('text', 'N/A'))).replace('\n', '<br/>')
            st.markdown(f"""
            <div style="
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 14px 18px;
                margin-bottom: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            ">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap;">
                    <span style="
                        background-color: {match_color};
                        color: white;
                        font-size: 0.7rem;
                        padding: 2px 8px;
                        border-radius: 12px;
                        font-weight: 600;
                    ">{match_level.upper()}</span>
                    <span style="color: #424242; font-weight: 600;">From {source_key}</span>
                    <span style="
                        background-color: #e3f2fd;
                        color: #1565c0;
                        font-size: 0.75rem;
                        padding: 2px 8px;
                        border-radius: 12px;
                    ">{similarity}% match</span>
                </div>
                <div style="color: #616161; line-height: 1.5; font-size: 0.95rem;">{text}</div>
            </div>
            """, unsafe_allow_html=True)

        # Root Causes – single common root cause from matched defects (amber styling)
        root_causes = resolution_data.get('root_causes', [])
        if root_causes:
            single = root_causes[0]
            cause_text = str(single.get('cause', '')).strip()
            pct = single.get('percentage', 0)
            if cause_text and cause_text.lower() == 'investigation needed':
                display_text = "No common root cause could be determined from similar defects; review resolution suggestions above."
            else:
                display_text = f"<strong>{html.escape(cause_text)}</strong> — {pct}%"
            with st.expander("📋 Common Root Cause in Similar Defects", expanded=False):
                st.markdown(f"""
                <div style="
                    background-color: #fff8e7;
                    border-left: 4px solid #ed6c02;
                    padding: 14px 18px;
                    border-radius: 6px;
                    margin: 8px 0;
                ">
                    <ul style="margin: 0; padding-left: 20px; color: #5d4037;">
                        <li style='margin-bottom: 6px;'>{display_text}</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

        # AI Analysis is now combined into AI Context Summary (section 1)
    
    # 5. Two sections in one row: Related Documents (narrow) | Recommended Logs (wider, all info visible)
    st.markdown("---")
    st.markdown("### 5️⃣ Related Knowledge Documents & Recommended Logs for Investigation")
    st.markdown("")
    related_docs = results.get('related_documents', [])
    search_query = results.get('query', '')
    logs_df = _load_recommended_logs_for_query(search_query)

    # Narrower col for docs, thin separator, wider col for logs table
    col_docs, col_sep, col_logs = st.columns([1, 0.03, 2])

    with col_docs:
        st.markdown("**📄 Related Knowledge Documents**")
        if related_docs:
            doc_base_url = "https://amdocs-my.sharepoint.com/:t:/r/personal/sudhikut_amdocs_com/Documents/Documents/GenAI/GenAI%20Defect%20Portal/genai_defect_management/DefectPortal/knowledge_base/documents"
            doc_query_params = "?csf=1&web=1"
            for doc in related_docs[:3]:
                metadata = doc.get('metadata', {})
                filename = _resolve_document_display_name(metadata)
                relevance = doc.get('similarity', 0)
                section = metadata.get('section', '')
                content = doc.get('content', '')[:400]
                filepath = metadata.get('filepath', '')
                filename_encoded = filename.replace(' ', '%20')
                doc_link = f"{doc_base_url}/{filename_encoded}{doc_query_params}"
                with st.expander(f"📄 {filename} ({relevance}% relevance)"):
                    if section:
                        st.markdown(f"**Section:** {section}")
                    st.markdown("**Preview:**")
                    content_safe = html.escape(str(content)).replace('\n', '<br/>')
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
                        {content_safe}...
                    </div>
                    """, unsafe_allow_html=True)
                    if filepath:
                        st.markdown(f'📎 **File Path:** <a href="{doc_link}" target="_blank" style="color: #1a73e8;">{html.escape(filename)}</a>', unsafe_allow_html=True)
        else:
            st.info("No related documents found for this search.")

    with col_sep:
        st.markdown(
            "<div style='"
            "width: 4px; min-height: 200px; margin: 0 auto; "
            "background: linear-gradient(90deg, #e85c4a 0%, #d94a3d 85%, #c43d32 100%); "
            "box-shadow: 1px 0 2px rgba(0,0,0,0.15); "
            "border-radius: 1px;"
            "'></div>",
            unsafe_allow_html=True,
        )

    with col_logs:
        st.markdown("**🔍 Recommended Logs for Investigation**")
        # st.markdown("")
        if not logs_df.empty:
            # Use column_config so long Error Description text wraps and stays visible
            st.dataframe(
                logs_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Error Description": st.column_config.TextColumn("Error Description", width="large"),
                    "OSE Logs API": st.column_config.TextColumn("OSE Logs API"),
                    "OGW Logs API": st.column_config.TextColumn("OGW Logs API"),
                    "OGW server": st.column_config.TextColumn("OGW server"),
                    "Environment": st.column_config.TextColumn("Environment"),
                },
            )
        else:
            st.info("No recommended logs found for this search. Try a more specific error message (e.g. service or error code).")

    # 6. Insights & Analytics Visualization (Last Section)
    display_ai_search_visualizations(results)


def display_ai_search_visualizations(results: Dict[str, Any]):
    """
    Display visualizations based on AI search results with summary dashboard and expandable charts.
    Uses the same symmetric subset as Matching Defects (cap SIT by ACC count) so insights match what is displayed.
    """
    matching_acc = results.get('matching_defects', {}).get('acc', [])
    matching_sit = results.get('matching_defects', {}).get('sit', [])
    
    # Use same counts as Matching Defects section so Insights reflect displayed data
    n_acc = min(5, len(matching_acc))
    n_sit = min(n_acc, len(matching_sit)) if (matching_sit and n_acc > 0) else (min(5, len(matching_sit)) if matching_sit else 0)
    all_defects = matching_acc[:n_acc] + matching_sit[:n_sit]
    
    if not all_defects:
        return
    
    st.markdown("---")
    st.markdown("### 6️⃣ Insights & Analytics")
    
    # Prepare data for visualizations (include Resolution column from DB for resolution rate)
    defect_data = []
    for defect in all_defects:
        metadata = defect.get('metadata', {})
        defect_data.append({
            'issue_key': metadata.get('issue_key', 'Unknown'),
            'status': metadata.get('status', 'Unknown'),
            'resolution': metadata.get('resolution', ''),  # DB column Resolution
            'priority': metadata.get('priority', 'Unknown'),
            'similarity': defect.get('similarity', 0),
            'source': metadata.get('source', 'Unknown').upper()
        })
    
    df = pd.DataFrame(defect_data)
    
    if df.empty:
        return
    
    # Helper: treat as resolved if Status or Resolution column indicates it (DB Resolution column)
    def categorize_status(row):
        status_lower = str(row.get('status', '')).lower()
        resolution_lower = str(row.get('resolution', '')).lower()
        resolved_keywords = ['closed', 'resolved', 'done', 'fixed', 'verified', 'complete']
        if any(kw in status_lower for kw in resolved_keywords) or any(kw in resolution_lower for kw in resolved_keywords):
            return 'Resolved'
        if any(kw in status_lower for kw in ['open', 'new', 'to do']):
            return 'Open'
        return 'In Progress'
    
    df['status_category'] = df.apply(categorize_status, axis=1)
    
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
        # Dark red for 1-Blocker, then progressively lighter shades
        priority_colors = ['#8B0000', '#b71c1c', '#c62828', '#e57373', '#ffcdd2']
        
        col_chart, col_table = st.columns([2, 1])
        with col_chart:
            bar_chart = alt.Chart(priority_counts).mark_bar(
                cornerRadiusTopLeft=5,
                cornerRadiusTopRight=5
            ).encode(
                x=alt.X('Priority:N', sort=priority_order_list, title='Priority'),
                y=alt.Y('Count:Q', title='Number of Defects'),
                color=alt.Color(
                    'Priority:N',
                    scale=alt.Scale(domain=priority_order_list, range=priority_colors),
                    legend=None
                ),
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
            st.session_state['genai_force_reindex'] = True
            st.session_state.pop('genai_system', None)
            st.success("Defects will be re-indexed from DB on next load. Refresh the page.")
        
        st.caption("Add new .docx, .pdf, .md, .txt to **knowledge_base/documents** and click below to index them for the Related Documents section.")
        # Index documents (force_reindex=True so new .docx and other files in knowledge_base/documents are included)
        if st.button("📚 Index Knowledge Base", key="index_docs_btn"):
            try:
                from modules.genai.enhanced_search import EnhancedSearch
                enhanced_search = EnhancedSearch()
                with st.spinner("Indexing documents (including any new .docx, .pdf, .md, .txt in knowledge_base/documents)..."):
                    enhanced_search.document_search.load_and_index_documents(force_reindex=True)
                st.success("Documents indexed successfully! New documents will appear in Related Knowledge Documents when relevant.")
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
