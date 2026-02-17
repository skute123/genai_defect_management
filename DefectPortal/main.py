import streamlit as st
from datetime import datetime
from modules.pop_up_waves_acc import popup_acc
from modules.pop_up_waves_sit import popup_sit
from utilities.logger_config import setup_logger
from modules.database_connection import get_db_engine
from modules.display_defects import display_defects
from modules.utilities import get_base64
from modules.ui_config import load_css, load_font_css, load_navbar
from modules.search_issue_key import search_issue_key
from modules.session_state_manager import initialize_session_state

# Import AI Search UI module
from modules.ai_search_ui import render_ai_search_section, render_genai_sidebar

logger = setup_logger()

from sqlalchemy import create_engine

# Streamlit UI
def main():
    logger.info("Streamlit app started")
    st.set_page_config(
        page_title="DefectDNA AI", 
        layout="wide",  # Changed to wide for better AI results display
        initial_sidebar_state="collapsed",
        page_icon="🔍"
    )

    initialize_session_state()

    # Load UI
    load_css()
    load_font_css()
    load_navbar()

    # --- Database Connection ---    
    engine = get_db_engine()

    # AI sidebar (Re-index Data, Index Knowledge Base)
    render_genai_sidebar()

    # Show the popup first
    col1, col2 = st.columns(2)
    with col1:
        popup_acc()
    with col2:
        popup_sit()

    # --- Load Data from DB ---
    defect_data_acc, defect_data_sit = display_defects(engine)

    # ===========================================
    # TRADITIONAL SEARCH SECTION
    # ===========================================
    st.markdown("---")
    st.markdown("## 🔎 Quick Defect Search")

    # --- Issue Key Search Section ---
    search_issue_key(defect_data_acc, defect_data_sit)

    # ===========================================
    # AI-ENHANCED SEARCH SECTION
    # ===========================================
    try:
        render_ai_search_section(defect_data_acc, defect_data_sit)
    except Exception as e:
        logger.warning(f"AI Search not available: {e}")
        st.info("💡 AI-Enhanced Search is being initialized. Install required packages for full functionality.")

    # --- Enhanced Footer ---
    current_year = datetime.now().year
    
    st.markdown(
        f"""
        <div class="custom-footer">
            <div class="footer-content">
                <span class="footer-section copyright">
                    &copy; {current_year} DefectDNA
                </span>
                <span class="footer-section powered-by">
                    Powered by AI
                </span>
                <span class="footer-section company">
                    Amdocs
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
