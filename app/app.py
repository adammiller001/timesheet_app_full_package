import streamlit as st
from app.ui.landing import landing
from app.ui.entry import entry_form
from app.ui.day_view import day_view
from app.ui.export_panel import export_panel
from app.state import init_state
from app.style_utils import apply_app_theme, apply_watermark

st.set_page_config(page_title="Daily Timesheet", page_icon=":open_file_folder:", layout="wide")
apply_app_theme()
apply_watermark()
init_state()

# Landing
if not st.session_state.entered_app:
    landing()
    st.stop()

# Main sections
st.header("Timesheet Entry")
entry_form()

st.divider()
st.header("Construction Reporting")
day_view()

st.divider()
st.header("Export Day → TimeEntries + Daily Report")
export_panel()

