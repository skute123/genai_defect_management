    # if "show_all_defects" not in st.session_state:
    #     st.session_state.show_all_defects = False

    # if "find_keyword" not in st.session_state:
    #     st.session_state.find_keyword = False

    # # if "issue_key_results" not in st.session_state:
    # #     st.session_state.issue_key_results = None

    # if "issue_key_results_acc" not in st.session_state:
    #     st.session_state.issue_key_results_acc = None

    # if "issue_key_results_sit" not in st.session_state:
    #     st.session_state.issue_key_results_sit = None

    # if "invalid_issue_key" not in st.session_state:
    #     st.session_state.invalid_issue_key = False

    # if "issue_key_searched" not in st.session_state:
    #     st.session_state.issue_key_searched = False

    # if "keyword" not in st.session_state:
    #     st.session_state.keyword = ""

    # if "selected_columns" not in st.session_state:
    #     st.session_state.selected_columns = []

    # if "keyword_results" not in st.session_state:
    #     st.session_state.keyword_results = None

    # if "keyword_results_acc" not in st.session_state:
    #     st.session_state.keyword_results_acc = None

    # if "keyword_results_sit" not in st.session_state:
    #     st.session_state.keyword_results_sit = None

import streamlit as st
import logging

logger = logging.getLogger(__name__)



def initialize_session_state():
    """Initialize all Streamlit session state variables with default values."""
    defaults = {
        "show_all_defects": False,
        "find_keyword": False,
        "issue_key_results": None,
        "issue_key_results_acc": None,
        "issue_key_results_sit": None,
        "invalid_issue_key": False,
        "issue_key_searched": False,
        "keyword": "",
        "selected_columns": [],
        "keyword_results": None,
        "keyword_results_acc": None,
        "keyword_results_sit": None,
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
            logger.debug(f"Initialized session_state[{key}] = {default_value}")
