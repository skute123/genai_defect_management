import streamlit as st
from modules.pop_up_waves_acc import popup_acc
from modules.pop_up_waves_sit import popup_sit
from utilities.logger_config import setup_logger
from modules.database_connection import get_db_engine
from modules.display_defects import display_defects
from modules.utilities import get_base64
from modules.ui_config import load_css, load_font_css, load_navbar
from modules.search_issue_key import search_issue_key
from modules.search_keyword import search_keyword
from modules.session_state_manager import initialize_session_state


logger = setup_logger()

from sqlalchemy import create_engine

# Streamlit UI
def main():
    logger.info("Streamlit app started")
    st.set_page_config(page_title="DefectSearch", layout="centered",initial_sidebar_state="collapsed")

    initialize_session_state()

    # Load UI
    load_css()
    load_font_css()
    load_navbar()

    # --- Database Connection ---    
    engine = get_db_engine()

    # show the popup first
    col1, col2 = st.columns(2)
    with col1:
        popup_acc()
    with col2:
        popup_sit()

    # --- Load Data from DB ---
    defect_data_acc, defect_data_sit = display_defects(engine)


    # --- Issue Key Search Section ---
    search_issue_key(defect_data_acc, defect_data_sit)

    # # search using keyword

    search_keyword(defect_data_acc,defect_data_sit)

if __name__ == "__main__":
    main()

# --- Footer ---
    st.markdown(
        """
        <div style="
            background-color: #f0f2f6;
            padding: 20px 10px;
            text-align: center;
            font-size: 14px;
            color: #666666;
            margin-top: 50px;
            border-top: 1px solid #ddd;
            border-radius: 8px;
        ">
            &copy; <strong>Defect Search & Analysis Portal</strong> | Amdocs
        </div>
        """,
        unsafe_allow_html=True
    )
