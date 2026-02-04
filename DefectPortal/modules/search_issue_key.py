import streamlit as st
from modules.utilities import format_comments
from utilities.logger_config import setup_logger

logger = setup_logger()

def search_issue_key(defect_data_acc, defect_data_sit):
    """
    search the unique issue key from the defect data tables.
    """
    # --- Issue Key Search Section ---
    st.markdown("### Search Defect by Issue Key")
    col1, col2 = st.columns([1, 2])
    with col1:
        issue_key_input = st.text_input("Enter Issue Key", placeholder="E.g., OS-1234 or Z_INC1234")
    
    with col2:
        # Add empty space to align button with text box
        st.markdown('<div class="issue_key_btn">', unsafe_allow_html=True)
        if st.button("Search-Defect"):
            if issue_key_input:
                # filtered = defect_data[defect_data['Issue key'].astype(str).str.strip().str.upper() == issue_key_input.strip().upper()]
                issue_key_input_value = issue_key_input.strip().upper()
                st.session_state.issue_key_input_val = issue_key_input_value
                st.session_state.issue_key_searched = True
                logger.info("User searched for Issue Key: %s", issue_key_input_value)

                # Search in ACC
                filtered_acc = defect_data_acc[
                    defect_data_acc['Issue key'].astype(str).str.strip().str.upper() == issue_key_input_value
                ]
                st.session_state.issue_key_results_acc = filtered_acc

                # Search in SIT
                filtered_sit = defect_data_sit[
                    defect_data_sit['Issue key'].astype(str).str.strip().str.upper() == issue_key_input_value
                ]
                st.session_state.issue_key_results_sit = filtered_sit
            else:
                st.session_state.issue_key_input_val = ""
                st.session_state.issue_key_results_acc = None
                st.session_state.issue_key_results_sit = None
                st.session_state.issue_key_searched = False
                st.session_state.invalid_issue_key = True
                logger.warning("User clicked Search-Defect without entering an Issue Key")
        st.markdown('</div>', unsafe_allow_html=True)

    # Show warning in full width (outside button wrapper)
    if "invalid_issue_key" in st.session_state and st.session_state.invalid_issue_key:
        logger.warning("Displayed warning: 'Please enter Issue Key'")
        st.warning("Please enter Issue Key")
        st.session_state.invalid_issue_key = False

    # store it in session state so that results dont toggle when we click on another btn
    if st.session_state.issue_key_results_acc is not None and not st.session_state.issue_key_results_acc.empty:
        filtered_acc = st.session_state.issue_key_results_acc
        issue_key_input_value = st.session_state.issue_key_input_val

        st.markdown('<h3 style="color:#e74c3c; font-weight:bold;">ACC Results</h3>',unsafe_allow_html=True)
        if not filtered_acc.empty:
            st.success(f"✅ Defect found for Issue Key: `{issue_key_input_value}`")
            logger.info("Displaying ACC defect details for Issue Key: %s", issue_key_input_value)
            st.markdown("#### 📝 Defect Details")
            filtered_display = filtered_acc.T.rename(columns={filtered_acc.index[0]: "Value"}).reset_index()
            filtered_display.columns = ["Field", "Value"]

            for i, row in filtered_display.iterrows():
                if row["Field"].lower() == "comment":
                    filtered_display.at[i, "Value"] = format_comments(row["Value"])

            st.dataframe(filtered_display, use_container_width=True, hide_index=True)

    if st.session_state.issue_key_results_sit is not None and not st.session_state.issue_key_results_sit.empty:
        filtered_sit = st.session_state.issue_key_results_sit
        issue_key_input_value = st.session_state.issue_key_input_val

        st.markdown('<h3 style="color: #E3BB10; font-weight:bold;">SIT Results</h3>',unsafe_allow_html=True)
        if not filtered_sit.empty:
            st.success(f"✅ Defect found for Issue Key: `{issue_key_input_value}`")
            logger.info("Displaying SIT defect details for Issue Key: %s", issue_key_input_value)
            st.markdown("#### 📝 Defect Details")
            filtered_display = filtered_sit.T.rename(columns={filtered_sit.index[0]: "Value"}).reset_index()
            filtered_display.columns = ["Field", "Value"]

            for i, row in filtered_display.iterrows():
                if row["Field"].lower() == "comment":
                    filtered_display.at[i, "Value"] = format_comments(row["Value"])

            st.dataframe(filtered_display, use_container_width=True, hide_index=True)

    if st.session_state.issue_key_searched:
        if (st.session_state.issue_key_results_acc is None or st.session_state.issue_key_results_acc.empty) and (st.session_state.issue_key_results_sit is None or st.session_state.issue_key_results_sit.empty):
            st.warning("No defect found with that Issue Key.")