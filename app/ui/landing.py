from pathlib import Path
import streamlit as st
from app.config import APP_DIR

def landing():
    jpgs = sorted((APP_DIR.parent).glob("*.jpg"))
    logo_path = str(jpgs[0]) if jpgs else None
    st.markdown("<div style='height:5vh'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1,2,1])
    with mid:
        if logo_path:
            st.image(logo_path, width=300)
        email = st.text_input("Your work email", st.session_state.get("whoami_email",""), placeholder="name@ptwenergy.com")
        if st.button("Enter"):
            st.session_state.whoami_email = (email or "").strip()
            st.session_state.entered_app = True
            st.rerun()
