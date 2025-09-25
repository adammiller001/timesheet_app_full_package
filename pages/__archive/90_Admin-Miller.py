import streamlit as st
st.session_state['page_title']='Admin'
st.session_state['page_header']='âš™ï¸ Admin'

import streamlit as st

# Gate: require login from landing page
user = st.session_state.get("user_email")
if not user:
    st.warning("Please sign in on the Home page first.")
    if hasattr(st, "page_link"):
        st.page_link("streamlit_app.py", label="â† Go to Home")
    st.stop()
st.sidebar.info(f"Signed in as: {user}")

st.set_page_config(page_title=st.session_state.get("page_title", "PTW"), layout="wide")
st.title(st.session_state.get("page_header", "Page"))

st.info("Placeholder page. We'll wire this up next.")
