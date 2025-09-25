
import streamlit as st
import pandas as pd
from datetime import date

# Gate: require login
user = st.session_state.get("user_email")
if not user:
    st.warning("Please sign in on the Home page first.")
    if hasattr(st, "page_link"):
        st.page_link("streamlit_app.py", label="ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Go to Home")
    st.stop()
st.sidebar.info(f"Signed in as: {user}")

from app.config import APP_NAME, EXCEL_FILENAME
from app.data.employee_loader import load_employee_list
from app.data.employee_details import load_employee_details
from app.data.reference_loader import load_job_options, load_costcode_options
from app.features.export_daily_time import export_daily_time

st.set_page_config(page_title=f"{APP_NAME}", layout="wide")
st.title("Timesheet Entry")

st.caption("Heartbeat: UI rendered. If this disappears after selecting an employee, tell me.")

# Date
col_date, _ = st.columns([1, 3])
with col_date:
    chosen_date = st.date_input("Date", value=date.today())

st.markdown("---")

# Job & Cost Code selectors
st.subheader("Job & Cost Code")

@st.cache_data(show_spinner=False)
def _jobs_cached():
    try:
        return load_job_options()
    except Exception:
        return []

@st.cache_data(show_spinner=False)
def _codes_cached():
    try:
        return load_costcode_options()
    except Exception:
        return []

jobs = _jobs_cached()
codes = _codes_cached()

c1, c2 = st.columns(2)
with c1:
    job_choice = job_options = (locals().get("job_display")
               or locals().get("job_options")
               or locals().get("jobs_display")
               or [])
job_options = (locals().get("job_display") or locals().get("job_options") or locals().get("jobs_display") or [])
job_choice  = st.selectbox("Job Number - Area Number - Description", job_options, key="job_choice")