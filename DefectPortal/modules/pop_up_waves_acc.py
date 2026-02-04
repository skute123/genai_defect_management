import streamlit as st
from streamlit_modal import Modal

def popup_acc():
    """
    Displays a button that opens a modal showing ACC wave numbers.
    The modal appears near the top of the Streamlit page.
    """

    # --- CSS: position modal toward the top ---
    st.markdown("""
    <style>
    /* --- Adjust modal position --- */
    div[data-modal-container='true'][key='popup_key_acc'] {
        position: fixed !important;
        top: 5% !important;                /* pushes it higher on the screen */
        left: 0 !important;
        width: 100vw !important;
        display: flex !important;
        justify-content: center !important;
        align-items: flex-start !important; /* aligns to top */
        z-index: 999992 !important;
    }

    /* --- Modal content box --- */
    div[data-modal-container='true'][key='popup_key_acc'] > div:first-child > div:first-child {
        background-color: white !important;
        border-radius: 10px !important;
        padding: 20px !important;
        box-shadow: 0px 6px 25px rgba(0, 0, 0, 0.3) !important;
        max-height: 80vh !important;
        overflow-y: auto !important;
    }

    /* --- Optional: close button style --- */
    div[data-modal-container='true'][key='popup_key_acc'] button[kind='primary'] {
        background-color: #E74C3C !important;
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
        font-weight: 600 !important;
        padding: 6px 12px !important;
    }

    div[data-modal-container='true'][key='popup_key_acc'] button[kind='primary']:hover {
        background-color: #C0392B !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Modal setup ---
    acc_modal = Modal("Waves Included for ACC...", key="popup_key_acc")

    # --- Trigger button ---
    open_acc = st.button("ACC Wave Numbers", key="open_waves_acc")

    # --- Open modal if button clicked ---
    if open_acc:
        acc_modal.open()

    # --- Define waves list ---
    waves = [
        "Wave 8.0", "Wave 8.1.5", "Wave 8.2.1", "Wave 8.2.2", "Wave 8.2.3",
        "Wave 8.2", "Wave 9.0", "Wave 9.0.2", "Wave 9.1.1", "Wave 9.1.2",
        "Wave 9.1", "Wave 9.2.2", "Wave 10.0", "Wave 10.1",
        "Wave 10.0.1", "Wave 10.0.2"
    ]

    # --- Display modal content ---
    if acc_modal.is_open():
        with acc_modal.container():
            st.markdown(
                "\n".join([f"- {w}" for w in waves]),
                unsafe_allow_html=True
            )
