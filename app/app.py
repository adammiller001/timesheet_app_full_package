import streamlit as st
from app.ui.landing import landing
from app.ui.entry import entry_form
from app.ui.day_view import day_view
from app.ui.export_panel import export_panel
from app.state import init_state

st.set_page_config(page_title="Daily Timesheet", page_icon="🗂️", layout="centered")
init_state()

# Landing
if not st.session_state.entered_app:
    landing()
    st.stop()

# Main sections
st.header("Timesheet Entry")
entry_form()

st.divider()
st.header("What's been added for this day")
day_view()

st.divider()
st.header("Export Day → TimeEntries + Daily Report")
export_panel()
