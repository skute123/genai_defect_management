import pandas as pd
from sqlalchemy import create_engine
from utilities.logger_config import setup_logger
import streamlit as st

logger = setup_logger()

def get_db_engine():
    """
    connects to our mysql database and returns a SQLAlchemy engine object.
    """
    # --- Database Connection ---     
    try:
        # Define SQLAlchemy connection string
        username = 'root'
        password = 'admin'
        host = 'localhost'
        database = 'defect_db'

        # Use URL encoding for special characters in password (like @)
        from urllib.parse import quote_plus
        encoded_password = quote_plus(password)

        # Using mysql-connector-python which has native support for caching_sha2_password
        engine = create_engine(f"mysql+mysqlconnector://{username}:{encoded_password}@{host}/{database}")
        logger.info(" Database connection established successfully")
        return engine
        
    except Exception as e:
        logger.error(" Database connection failed: %s", e)
        st.error(f"Database connection error: {e}")
        st.stop()