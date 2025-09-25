import streamlit as st
st.session_state['page_title']='What\'s Been Added Today'
st.session_state['page_header']='📝 What\'s Been Added Today'

import streamlit as st

# Gate: require login and admin access
if not st.session_state.get("authenticated", False):
    st.warning("Please sign in on the Home page first.")
    st.stop()

user_type = st.session_state.get("user_type", "User")
if user_type.upper() != "ADMIN":
    st.error("Access denied: Admin access required for this page.")
    st.info("This page is only available to administrators.")
    st.stop()

user = st.session_state.get("user_email")
st.sidebar.info(f"Signed in as: {user}")

st.set_page_config(page_title=st.session_state.get("page_title", "PTW"), layout="wide")
st.title(st.session_state.get("page_header", "Page"))

st.info("Placeholder page. We'll wire this up next.")
