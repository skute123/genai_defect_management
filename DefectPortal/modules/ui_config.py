import streamlit as st

from modules.utilities import get_base64

def load_css(css_path="assets/style.css"):
    """Inject custom CSS file."""
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def load_font_css():
    """Inject custom fonts (Poppins Regular + Bold)."""
    regular_font = get_base64("../font/Poppins/Poppins-Regular.ttf")
    bold_font = get_base64("../font/Poppins/Poppins-Bold.ttf")

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
        html, body, [class*="css"] {{
            font-family: 'Poppins', sans-serif !important;
        }}
        h1, h2, h3, h4, h5 {{
            font-family: 'Poppins', sans-serif !important;
            font-weight: bold !important;
        }}
        .navbar-title {{
            font-family: 'Poppins', sans-serif !important;
        }}
        </style>
    """, unsafe_allow_html=True)

def load_navbar():
    """Inject the fixed top navbar."""
    logo_base64 = get_base64("../assets/logo.png")

    navbar_html = f"""
    <div class="navbar">
        <div class="navbar-title">DefectDNA</div>
        <div class="navbar-logo">
            <img src="data:image/png;base64,{logo_base64}" alt="Logo">
        </div>
    </div>
    """
    st.markdown(navbar_html, unsafe_allow_html=True)
