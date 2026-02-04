import base64
import os
import pandas as pd
import streamlit as st 
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

def convert_df_to_csv(df):
        return df.to_csv(index=False).encode('utf-8')

# Function to convert image to base64
def get_base64(image_file):
    file_path = os.path.join(os.path.dirname(__file__), image_file)
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# Use engine directly with read_sql
def fetch_defects(engine, table_name):
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, con=engine)
    return df

def _clear_results():
        st.session_state.keyword_results = None
        st.session_state.find_keyword = False