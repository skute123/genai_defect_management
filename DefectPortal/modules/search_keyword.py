import streamlit as st
import pandas as pd
from modules.charts.osf_system import osf_system
from modules.charts.vendor_appln import vendor_appln
from modules.utilities import convert_df_to_csv, _clear_results
from modules.session_state_manager import initialize_session_state


initialize_session_state()
from utilities.logger_config import setup_logger

logger = setup_logger()

def search_keyword(defect_data_acc, defect_data_sit):
    # search using keyword

    searchable_columns = [
        "Summary", "Description", "Custom field (OSF-Fix Description)", "Comment"
    ]


    st.markdown("### Search Multiple Columns for Keyword")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        selected_columns = st.multiselect("Select columns to search in", searchable_columns, key="selected_columns", on_change=_clear_results)

    with col2:
        keyword = st.text_input("Enter keyword to search", value=st.session_state.keyword,key="keyword", on_change=_clear_results)
    
    try : 
        if st.button("Find Data"):
            if not selected_columns:
                st.warning("Please select at least one column to search in.")
                logger.warning("User clicked Find Data without selecting any columns")
            elif not keyword:
                st.warning("Please enter a keyword.")
                logger.warning("User clicked Find Data without entering a keyword")
            else:
                # Filter rows where the keyword appears in any selected column 
                # for acc
                mask_acc = pd.Series([False] * len(defect_data_acc))
                for col in selected_columns:
                    mask_acc = mask_acc | defect_data_acc[col].astype(str).str.contains(st.session_state.keyword, case=False, na=False)

                st.session_state.keyword_results_acc = defect_data_acc[mask_acc]
                logger.info("ACC search returned %d rows for keyword '%s'", len(st.session_state.keyword_results_acc), st.session_state.keyword)

                # for SIT
                mask_sit = pd.Series([False] * len(defect_data_sit))
                for col in selected_columns:
                    mask_sit = mask_sit | defect_data_sit[col].astype(str).str.contains(st.session_state.keyword, case=False, na=False)

                st.session_state.keyword_results_sit = defect_data_sit[mask_sit]
                logger.info("SIT search returned %d rows for keyword '%s'", len(st.session_state.keyword_results_sit), st.session_state.keyword)


                st.session_state.find_keyword = True


        # ✅ Always display results if available, even when another button is clicked
        if st.session_state.find_keyword :
            acc_df = st.session_state.keyword_results_acc
            sit_df = st.session_state.keyword_results_sit
            if acc_df is not None or sit_df is not None:
                st.success(
                    f" Found {len(acc_df)} rows in ACC and {len(sit_df)} rows in SIT "
                    f"for keyword '{st.session_state.keyword}'."
                )

                col_acc, col_sit = st.columns(2)

                with col_acc:
                    st.markdown("##### • ACC Results")
                    if acc_df is not None and not acc_df.empty:
                        out_acc = acc_df.copy().reset_index(drop=True)
                        out_acc.index = out_acc.index + 1
                        st.dataframe(out_acc, use_container_width=True)

                        csv_acc = convert_df_to_csv(acc_df)
                        st.download_button(
                            label="Download ACC CSV",
                            data=csv_acc,
                            file_name=f"ACC_keyword_results_{st.session_state.keyword}.csv",
                            mime="text/csv",
                            key="acc_results"
                        )
                    else:
                        st.info("No matching results found in ACC.")

                with col_sit:
                    st.markdown("##### • SIT Results")
                    if sit_df is not None and not sit_df.empty:
                        out_sit = sit_df.copy().reset_index(drop=True)
                        out_sit.index = out_sit.index + 1
                        st.dataframe(out_sit, use_container_width=True)

                        csv_sit = convert_df_to_csv(sit_df)
                        st.download_button(
                            label="Download SIT CSV",
                            data=csv_sit,
                            file_name=f"SIT_keyword_results_{st.session_state.keyword}.csv",
                            mime="text/csv",
                            key="sit_results"
                        )
                    else:
                        st.info("No matching results found in SIT.")

                st.markdown(
                    '<h3 style="color:#e74c3c; font-weight:bold;">Predicted Defect Analysis based on input</h3>',
                    unsafe_allow_html=True
                )

                osf_system(acc_df, sit_df)
                vendor_appln(acc_df, sit_df)
            else:
                st.info("No matching results found")

    except Exception as e:
        logger.error("Error searching keyword: %s", str(e))
        st.error("An error occurred while searching the keyword")