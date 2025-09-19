from dataclasses import dataclass, asdict
import streamlit as st
from app.config import get_default_xlsx_path

@dataclass
class AppState:
    whoami_email: str = ""
    entered_app: bool = False
    is_admin: bool = True
    xlsx_path: str = ""

def init_state():
    # Initialize keys once
    if "initialized" in st.session_state:
        return
    st.session_state.initialized = True
    s = AppState()
    s.xlsx_path = get_default_xlsx_path()
    for k, v in asdict(s).items():
        setattr(st.session_state, k, v)
