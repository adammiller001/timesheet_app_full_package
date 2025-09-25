# app/state.py
import streamlit as st
from dataclasses import dataclass, asdict

@dataclass
class AppState:
    whoami_email: str = ""
    entered_app: bool = True    # <- force TRUE for diagnostics so landing is bypassed
    is_admin: bool = True
    xlsx_path: str = ""

REQUIRED = ("whoami_email", "entered_app", "is_admin", "xlsx_path", "initialized")

def init_state():
    """Initialize session_state only once; never clobber values on rerun."""
    if "initialized" not in st.session_state:
        s = AppState()
        for k, v in asdict(s).items():
            st.session_state[k] = v
        st.session_state.initialized = True
        return

    # Ensure keys exist (don't overwrite if present)
    if "whoami_email" not in st.session_state:
        st.session_state.whoami_email = ""
    if "entered_app" not in st.session_state:
        st.session_state.entered_app = True  # keep true for diagnostics
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = True
    if "xlsx_path" not in st.session_state:
        st.session_state.xlsx_path = ""
    st.session_state.initialized = True
