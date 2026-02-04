import re
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import mysql.connector
import altair as alt
import base64
import os
import io
import math

from utilities.logger_config import setup_logger

logger = setup_logger()

from sqlalchemy import create_engine

# Streamlit UI
def main():
    logger.info("Streamlit app started")
    st.set_page_config(page_title="DefectSearch", layout="centered",initial_sidebar_state="collapsed")

    if "show_all_defects" not in st.session_state:
        st.session_state.show_all_defects = False

    if "find_keyword" not in st.session_state:
        st.session_state.find_keyword = False

    # if "issue_key_results" not in st.session_state:
    #     st.session_state.issue_key_results = None

    if "issue_key_results_acc" not in st.session_state:
        st.session_state.issue_key_results_acc = None

    if "issue_key_results_sit" not in st.session_state:
        st.session_state.issue_key_results_sit = None

    if "invalid_issue_key" not in st.session_state:
        st.session_state.invalid_issue_key = False

    if "issue_key_searched" not in st.session_state:
        st.session_state.issue_key_searched = False

    if "keyword" not in st.session_state:
        st.session_state.keyword = ""

    if "selected_columns" not in st.session_state:
        st.session_state.selected_columns = []

    if "keyword_results" not in st.session_state:
        st.session_state.keyword_results = None

    if "keyword_results_acc" not in st.session_state:
        st.session_state.keyword_results_acc = None

    if "keyword_results_sit" not in st.session_state:
        st.session_state.keyword_results_sit = None

    # Function to convert image to base64
    def get_base64(image_file):
        file_path = os.path.join(os.path.dirname(__file__), image_file)
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    logo_base64 = get_base64("assets/logo.png")
    regular_font = get_base64("font/Poppins/Poppins-Regular.ttf")
    bold_font = get_base64("font/Poppins/Poppins-Bold.ttf")

    def _clear_results():
        st.session_state.keyword_results = None
        st.session_state.find_keyword = False

    def convert_df_to_csv(df):
        return df.to_csv(index=False).encode('utf-8')

    # --- Custom CSS Styling ---
    hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stDeployButton {display:none;}

        /* App background */
        .stApp {
            background: linear-gradient(to bottom right, #f2f2f2, #ffffff);
            color: #333;
        }
        
        /* Remove gradient line on top */
        [data-testid="stDecoration"] {
            display: none;
        }

        /* Force full width app */
        .block-container {
            max-width: 100% !important;
            padding-left: 5rem;
            padding-right: 5rem;
            padding-bottom: 0rem !important;
        }

        /* Navbar full-width fixed */
        .navbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            width: 100%;
            z-index: 1000;
            background-color: #1e1e1e;
            padding: 15px 30px;
            color: white;
            font-size: 24px;
            font-weight: bold;
            border-bottom: 4px solid #ff4b4b;
            border-radius: 10px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* Navbar title */
        .navbar-title {
            font-size: 20px;
            font-weight: bold;
            color: white;
        }

        /* Navbar logo */
        .navbar-logo img {
            height: 50px !important;
            margin-left: 15px;
        }

        /* Push content down to avoid overlap */
        .app-content {
            margin-top: 80px;
        }

        /* Headings */
        h1, h2, h3, h4 {
            color: #e74c3c;
            font-size: 1rem;
        }

        /* Hide the little anchor/link icon in Streamlit headers */
        .css-10trblm a, .css-1q8dd3e a, h1 a, h2 a, h3 a, h4 a {
            display: none !important;
        }

        /* Input fields */
        .stTextInput > div > input, .stSelectbox > div, .stTextArea > div > textarea {
            background-color: #ffffff !important;
            color: black !important;
            border: 1px solid #ccc;
            border-radius: 6px;
            padding: 6px;
        }

        /* DataFrames and Tables */
        .stDataFrame, .stTable {
            background-color: white !important;
            color: black !important;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }

        /* Buttons */
        .stButton > button {
            background-color: #e74c3c;
            color: white;
            font-weight: bold;
            padding: 0.5em 1.5em;
            border: none;
            border-radius: 6px;
            transition: background-color 0.3s ease;
            margin-top: 10px;
        }

        .stButton > button:hover {
            background-color: #c0392b;
            color: white;
        }

        .stDownloadButton > button {
            background-color: #e74c3c;
            color: white;
            font-weight: bold;
        }

        .issue_key_btn
        {
            margin-top: 10px;
        }


        /* Scrollable container */
        .scroll-container {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            background-color: white;
            color: black;
            border-radius: 8px;
        }

        .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f0f2f6;
        color: #666666;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        border-top: 1px solid #dddddd;
    }
    </style>
    """

    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    navbar_html = f"""
    <div class="navbar">
        <div class="navbar-title">Defect Search & Analysis</div>
        <div class="navbar-logo">
            <img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height:40px;">
        </div>
    </div>
    """  
    st.markdown(navbar_html, unsafe_allow_html=True)

    # Inject custom font
    st.markdown(f"""
        <style>
        @font-face {{
            font-family: 'Poppins';
            src: url(data:font/ttf;base64,{regular_font}) format('truetype');
            font-weight: normal;
        }}
        @font-face {{
            font-family: 'Poppins';
            src: url(data:font/ttf;base64,{bold_font}) format('truetype');
            font-weight: bold;
        }}

        /* Apply it everywhere */
        html, body, [class*="css"]  {{
            font-family: 'Poppins', sans-serif !important;
        }}

        h1, h2, h3, h4, h5 {{
            font-family: 'Poppins', sans-serif !important;
            font-weight: bold !important;
        }}

        # input, textarea {{
        #     font-family: 'Poppins', sans-serif !important;
        # }}
        .navbar-title{{
            font-family: 'Poppins', sans-serif !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- Database Connection ---    

    
    try:
        # Define SQLAlchemy connection string
        username = 'root'
        password = 'asmi@123'
        host = 'localhost'
        database = 'defect_db'

        # Use URL encoding for special characters in password (like @)
        from urllib.parse import quote_plus
        encoded_password = quote_plus(password)

        engine = create_engine(f"mysql+pymysql://{username}:{encoded_password}@{host}/{database}")
        logger.info(" Database connection established successfully")

        # Use engine directly with read_sql
        def fetch_defects(table_name):
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql(query, con=engine)
            return df
        
    except Exception as e:
        logger.error(" Database connection failed: %s", e)
        st.error(f"Database connection error: {e}")
        st.stop()

    # --- Load Data from DB ---
    try:
        defect_data_acc = fetch_defects("defects_table_acc")
        # Handle all types of nulls or 'nan' string values
        defect_data_acc = defect_data_acc.fillna("").replace("nan", "").replace("NaN", "")
        logger.info("Loaded ACC defects: %d rows", len(defect_data_acc))

        defect_data_sit = fetch_defects("defects_table_sit")
        # Handle all types of nulls or 'nan' string values
        defect_data_sit = defect_data_sit.fillna("").replace("nan", "").replace("NaN", "")
        logger.info("Loaded SIT defects: %d rows", len(defect_data_sit))
    except Exception as e:
        logger.error("Database fetch error: %s", e)
        st.error(f"Database error: {e}")
        st.stop()

    def format_comments(text):
        if not text:
            return ""
        import re
        pattern = r'(\d{2}/[A-Za-z]{3}/\d{2} \d{1,2}:\d{2} [AP]M)'
        parts = re.split(pattern, text)
        if len(parts) <= 1:
            return f"• {text.strip()}"
        
        comments = []
        for i in range(1, len(parts), 2):
            date = parts[i].strip()
            content = parts[i+1].strip().replace("\n", " ").replace(";;;", "")
            comments.append(f"• **{date}** – {content}")
        return "\n\n".join(comments)

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

                            st.dataframe(osf_counts_reordered_acc, use_container_width=True)
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

                            st.dataframe(osf_counts_reordered_sit, use_container_width=True)
                    else:
                        st.warning("Column 'Custom field (OSF-System)' not found in the data for SIT.")

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

            else :
                st.info("No matching results found")

            
    except Exception as e:
        st.error(f"An error occurred: {e}")

            

            

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
