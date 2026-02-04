from modules.utilities import fetch_defects
import streamlit as st
from utilities.logger_config import setup_logger

logger = setup_logger()

def display_defects(engine):
    """
    Displays all the defects from the database (SIT and ACC both) in a table format 
    on front main page.
    """
    # --- Load Data from DB ---
    try:
        defect_data_acc = fetch_defects(engine, "defects_table_acc")
        # Handle all types of nulls or 'nan' string values
        defect_data_acc = defect_data_acc.fillna("").replace("nan", "").replace("NaN", "")
        logger.info("Loaded ACC defects: %d rows", len(defect_data_acc))

        defect_data_sit = fetch_defects(engine, "defects_table_sit")
        # Handle all types of nulls or 'nan' string values
        defect_data_sit = defect_data_sit.fillna("").replace("nan", "").replace("NaN", "")
        logger.info("Loaded SIT defects: %d rows", len(defect_data_sit))
    except Exception as e:
        logger.error("Database fetch error: %s", e)
        st.error(f"Database error: {e}")
        st.stop()

    # showing all defects...
    st.session_state.show_all_defects = not st.session_state.show_all_defects

    col1, col2 = st.columns(2)

    with col1 : 
        st.markdown("##### - ACC Defects")
        defect_data_display_acc = defect_data_acc.reset_index(drop=True)
        # display data starting from 1
        defect_data_display_acc.index += 1
        st.dataframe(defect_data_display_acc, use_container_width=True)
        logger.info("Displayed ACC defects table with %d rows", len(defect_data_display_acc))

    with col2 : 
        st.markdown("##### - SIT Defects")
        defect_data_display_sit = defect_data_sit.reset_index(drop=True)
        # display data starting from 1
        defect_data_display_sit.index += 1
        st.dataframe(defect_data_display_sit, use_container_width=True)
        logger.info("Displayed SIT defects table with %d rows", len(defect_data_display_sit))

    return defect_data_acc, defect_data_sit