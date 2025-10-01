import streamlit as st

PAGE_TITLE = "Construction Reporting"
PAGE_ICON = "📊"

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
st.session_state["page_title"] = PAGE_TITLE
st.session_state["page_header"] = f"{PAGE_ICON} {PAGE_TITLE}"

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

st.title(st.session_state.get("page_header", "Page"))

st.info("Placeholder page. We'll wire this up next.")
