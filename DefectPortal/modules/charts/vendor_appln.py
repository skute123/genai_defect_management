import streamlit as st
import pandas as pd
import altair as alt
from utilities.logger_config import setup_logger

logger = setup_logger()

def vendor_appln(acc_df, sit_df):
    # vendor + application
                # for ACC
                if (st.session_state.keyword_results_acc is not None and not st.session_state.keyword_results_acc.empty):
                    if 'Custom field (Vendor + Application)' in acc_df.columns:
                        logger.info("Generating vendor+application chart for ACC with %d categories", acc_df['Custom field (Vendor + Application)'].nunique())
                        st.write("##### 📈 Vendor + Application (ACC)")

                        # Calculate count and percentage distribution
                        value_counts_acc = acc_df['Custom field (Vendor + Application)'].value_counts()
                        percentage_acc = (value_counts_acc / value_counts_acc.sum() * 100).reset_index()
                        percentage_acc.columns = ['Vendor + Application', 'Percentage']
                        percentage_acc['Count'] = value_counts_acc.values
                        percentage_acc['Percentage'] = percentage_acc['Percentage'].round(2)
                        percentage_acc.index = range(1, len(percentage_acc) + 1)

                        # Long color palette (extend as needed)
                        extended_colors_acc = [
                            '#e74c3c', '#c0392b', '#7f8c8d', '#2c3e50',
                            '#d35400', '#34495e', '#8e44ad', '#95a5a6',
                            '#1abc9c', '#f39c12', '#2980b9', '#9b59b6',
                            '#16a085', '#e67e22', '#bdc3c7', '#27ae60',
                            '#f1c40f', '#3498db', '#e84393', '#6c5ce7',
                            '#00cec9', '#fd79a8', '#fab1a0', '#74b9ff'
                        ]
                        num_values_acc = len(percentage_acc)
                        colors_acc = extended_colors_acc[:num_values_acc]

                        # Dynamically calculate height for legend spacing
                        chart_height = max(300, num_values_acc * 22)

                        col_chart, col_table = st.columns([2,1])
                        # Create Altair pie chart (donut-style) with count and percentage in tooltip
                        with col_chart:
                            pie_chart_acc = alt.Chart(percentage_acc).mark_arc(innerRadius=50).encode(
                                theta=alt.Theta(field="Percentage", type="quantitative"),
                                color=alt.Color(field="Vendor + Application", type="nominal",
                                                scale=alt.Scale(domain=percentage_acc['Vendor + Application'].tolist(),
                                                                range=colors_acc),legend=alt.Legend(orient='bottom',columns=5,title='Vendor + Application(ACC)',labelLimit=400
                                                                )),
                                tooltip=[
                                    alt.Tooltip('Vendor + Application:N', title='Vendor + App'),
                                    alt.Tooltip('Percentage:Q', title='Percentage', format='.2f'),
                                    alt.Tooltip('Count:Q', title='Defect Count')
                                ]
                            ).properties(
                                width=400,
                                height=400
                            ).configure_legend(
                                orient='right',
                                labelFontSize=12,
                                titleFontSize=14,
                                labelLimit=1000,
                                symbolLimit=1000
                            )

                            # Display chart
                            st.altair_chart(pie_chart_acc, use_container_width=True)

                        # Reorder columns: Vendor + Application | Percentage | Count
                        with col_table:
                            percentage_acc['Percentage'] = percentage_acc['Percentage'].astype(str) + '%'
                            reordered_acc = percentage_acc[['Vendor + Application', 'Percentage', 'Count']]
                            st.dataframe(reordered_acc, use_container_width=True)

                    else:
                        st.warning("Column 'Custom field (Vendor + Application)' not found in the data for ACC.")

                # For SIT
                if (st.session_state.keyword_results_sit is not None and not st.session_state.keyword_results_sit.empty):
                    if 'Custom field (Vendor + Application)' in sit_df.columns:
                        logger.info("Generating vendor+application chart for SIT with %d categories", sit_df['Custom field (Vendor + Application)'].nunique())
                        st.write("##### 📈 Vendor + Application (SIT)")

                        # Calculate count and percentage distribution
                        value_counts_sit = sit_df['Custom field (Vendor + Application)'].value_counts()
                        percentage_sit = (value_counts_sit / value_counts_sit.sum() * 100).reset_index()
                        percentage_sit.columns = ['Vendor + Application', 'Percentage']
                        percentage_sit['Count'] = value_counts_sit.values
                        percentage_sit['Percentage'] = percentage_sit['Percentage'].round(2)
                        percentage_sit.index = range(1, len(percentage_sit) + 1)

                        # Long color palette (extend as needed)
                        extended_colors_sit = [
                            "#E3BB10","#FF6F61","#6B5B95","#88B04B","#009B77","#5B5EA6","#F7CAC9","#92A8D1","#955251","#B565A7","#009688","#F4A300","#2E86AB","#C94C4C","#3E5F8A","#9A6324","#7B3F00","#BF9000"
                        ]
                        num_values_sit = len(percentage_sit)
                        colors_sit = extended_colors_sit[:num_values_sit]

                        # Dynamically calculate height for legend spacing
                        chart_height = max(300, num_values_sit * 22)

                        col_chart, col_table = st.columns([2,1])
                        # Create Altair pie chart (donut-style) with count and percentage in tooltip
                        with col_chart:
                            pie_chart_sit = alt.Chart(percentage_sit).mark_arc(innerRadius=50).encode(
                                theta=alt.Theta(field="Percentage", type="quantitative"),
                                color=alt.Color(field="Vendor + Application", type="nominal",
                                                scale=alt.Scale(domain=percentage_sit['Vendor + Application'].tolist(),
                                                                range=colors_sit),legend=alt.Legend(orient='bottom',columns=5,title='Vendor + Application(SIT)',labelLimit=400
                                                                )),
                                tooltip=[
                                    alt.Tooltip('Vendor + Application:N', title='Vendor + App'),
                                    alt.Tooltip('Percentage:Q', title='Percentage', format='.2f'),
                                    alt.Tooltip('Count:Q', title='Defect Count')
                                ]
                            ).properties(
                                width=400,
                                height=400
                            ).configure_legend(
                                orient='right',
                                labelFontSize=12,
                                titleFontSize=14,
                                labelLimit=1000,
                                symbolLimit=1000
                            )

                            # Display chart
                            st.altair_chart(pie_chart_sit, use_container_width=True)

                        # Reorder columns: Vendor + Application | Percentage | Count
                        with col_table:
                            percentage_sit['Percentage'] = percentage_sit['Percentage'].astype(str) + '%'
                            reordered_sit = percentage_sit[['Vendor + Application', 'Percentage', 'Count']]
                            st.dataframe(reordered_sit, use_container_width=True)

                    else:
                        st.warning("Column 'Custom field (Vendor + Application)' not found in the data for SIT.")