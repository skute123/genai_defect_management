import streamlit as st
import pandas as pd
import altair as alt
from utilities.logger_config import setup_logger

logger = setup_logger()
def osf_system(acc_df, sit_df):
    # Chart for OSF-System
                # -- for acc
                if (st.session_state.keyword_results_acc is not None and not st.session_state.keyword_results_acc.empty):
                    if 'Custom field (OSF-System)' in acc_df.columns:
                        logger.info("Generating OSF-System chart for ACC with %d categories", acc_df['Custom field (OSF-System)'].nunique())
                        st.write("##### 📈 OSF-System (ACC)")
                        # 👉 Create count + percentage DataFrame
                        osf_counts_acc = acc_df['Custom field (OSF-System)'].value_counts().reset_index()
                        osf_counts_acc.columns = ['Value', 'Count']
                        osf_counts_acc['Percentage'] = (osf_counts_acc['Count'] / osf_counts_acc['Count'].sum()) * 100

                        osf_counts_acc.index = range(1, len(osf_counts_acc) + 1)
                        osf_counts_acc['Percentage'] = osf_counts_acc['Percentage'].round(2)
                        

                        col_chart, col_table = st.columns([2,1])
                        # 👉 Altair bar chart with Percentage as Y, Count as tooltip
                        with col_chart:
                            bar_chart_acc = alt.Chart(osf_counts_acc).mark_bar(color='#e74c3c').encode(
                                x=alt.X('Value:N', sort='-y', title='Category'),
                                y=alt.Y('Percentage:Q', title='Percentage of Defects'),
                                tooltip=[
                                    alt.Tooltip('Value:N', title='Category'),
                                    alt.Tooltip('Count:Q', title='Defect Count'),
                                    alt.Tooltip('Percentage:Q', title='Percentage', format='.2f')
                                ]
                            ).properties(
                                width='container',
                                height=300
                            ).configure_axis(
                                labelColor='black',
                                titleColor='black'
                            )

                            st.altair_chart(bar_chart_acc, use_container_width=True)

                        with col_table:
                            # 👉 Show Table: Count + Percentage side by side
                            osf_counts_acc['Percentage'] = osf_counts_acc['Percentage'].astype(str) + '%'
                            osf_counts_reordered_acc = osf_counts_acc[['Value', 'Percentage', 'Count']]

                            osf_counts_reordered_acc = osf_counts_reordered_acc.copy()
                            with st.container():
                                st.dataframe(osf_counts_reordered_acc, use_container_width=True)
                            # st.dataframe(osf_counts_reordered_acc, use_container_width=True)
                    else:
                        st.warning("Column 'Custom field (OSF-System)' not found in the data for ACC.")


                # -- for SIT
                if (st.session_state.keyword_results_sit is not None and not st.session_state.keyword_results_sit.empty):
                    if 'Custom field (OSF-System)' in sit_df.columns:
                        logger.info("Generating OSF-System chart for SIT with %d categories", sit_df['Custom field (OSF-System)'].nunique())
                        st.write("##### 📈 OSF-System (SIT)")
                        # 👉 Create count + percentage DataFrame
                        osf_counts_sit = sit_df['Custom field (OSF-System)'].value_counts().reset_index()
                        osf_counts_sit.columns = ['Value', 'Count']
                        osf_counts_sit['Percentage'] = (osf_counts_sit['Count'] / osf_counts_sit['Count'].sum()) * 100

                        osf_counts_sit.index = range(1, len(osf_counts_sit) + 1)
                        osf_counts_sit['Percentage'] = osf_counts_sit['Percentage'].round(2)

                        col_chart, col_table = st.columns([2,1])
                        # 👉 Altair bar chart with Percentage as Y, Count as tooltip
                        with col_chart:
                            bar_chart_sit = alt.Chart(osf_counts_sit).mark_bar(color='#E3BB10').encode(
                                x=alt.X('Value:N', sort='-y', title='Category'),
                                y=alt.Y('Percentage:Q', title='Percentage of Defects'),
                                tooltip=[
                                    alt.Tooltip('Value:N', title='Category'),
                                    alt.Tooltip('Count:Q', title='Defect Count'),
                                    alt.Tooltip('Percentage:Q', title='Percentage', format='.2f')
                                ]
                            ).properties(
                                width='container',
                                height=300
                            ).configure_axis(
                                labelColor='black',
                                titleColor='black'
                            )

                            st.altair_chart(bar_chart_sit, use_container_width=True)

                        # 👉 Show Table: Count + Percentage side by side
                        with col_table:
                            osf_counts_sit['Percentage'] = osf_counts_sit['Percentage'].astype(str) + '%'
                            osf_counts_reordered_sit = osf_counts_sit[['Value', 'Percentage', 'Count']]

                            osf_counts_reordered_sit = osf_counts_reordered_sit.copy()
                            with st.container():
                                st.dataframe(osf_counts_reordered_sit, use_container_width=True)
                            # st.dataframe(osf_counts_reordered_sit, use_container_width=True)
                    else:
                        st.warning("Column 'Custom field (OSF-System)' not found in the data for SIT.")