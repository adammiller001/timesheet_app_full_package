import streamlit as st
st.session_state['page_title']='Admin'
st.session_state['page_header']='⚙️ Admin'

import streamlit as st

# Gate: require login from landing page
user = st.session_state.get("user_email", "user@ptwenergy.com")
if not user:
    st.session_state["user_email"] = "user@ptwenergy.com"
    user = "user@ptwenergy.com"
st.sidebar.info(f"Signed in as: {user}")

st.set_page_config(page_title=st.session_state.get("page_title", "PTW"), layout="wide")
st.title(st.session_state.get("page_header", "Page"))

st.info("Placeholder page. We'll wire this up next.")
