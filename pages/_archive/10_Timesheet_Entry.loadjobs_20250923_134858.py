
import streamlit as st
# ---- Fallback options loader (added) ----
# If job_options / cost_options were not created earlier, try to build them
# from "Timesheet Apps.xlsx" using common sheet/column names.
try:
    import pandas as _pd
    from pathlib import Path as _Path

    def _load_xlsx_df(_xlsx, candidates, needed_cols):
        try:
            xl = _pd.ExcelFile(_xlsx)
        except Exception:
            return None
        for nm in candidates:
            if nm in xl.sheet_names:
                try:
                    df = xl.parse(nm)
                    # normalize column names for matching
                    cols_norm = {c.strip(): c for c in df.columns if isinstance(c, str)}
                    # do we have a superset of the columns we need?
                    if all(any(k.lower() == want.lower() for k in cols_norm) for want in needed_cols):
                        return df
                except Exception:
                    continue
        return None

    # workbook next to the project root file locations
    _root = _Path(__file__).resolve().parents[1]
    _xlsx = _root / "Timesheet Apps.xlsx"

    # Build jobs if missing or empty
    if "job_options" not in locals() or not job_options:
        _jobs_df = _load_xlsx_df(
            _xlsx,
            ["Jobs", "Job List", "Jobs List", "JobsList"],
            ["Job Number", "Area Number", "Description"],
        )
        job_options = []
        if _jobs_df is not None and not _jobs_df.empty:
            # Be tolerant to header variants by matching case-insensitively
            def _col(df, name):
                for c in df.columns:
                    if isinstance(c, str) and c.strip().lower() == name.lower():
                        return c
                return name  # best-effort
            jn = _col(_jobs_df, "Job Number")
            an = _col(_jobs_df, "Area Number")
            ds = _col(_jobs_df, "Description")
            # stringify and build display text
            _tmp = _jobs_df[[jn, an, ds]].astype(str).fillna("")
            job_options = (_tmp[jn] + " - " + _tmp[an] + " - " + _tmp[ds]).tolist()

    # Build cost codes if missing or empty
    if "cost_options" not in locals() or not cost_options:
        _cost_df = _load_xlsx_df(
            _xlsx,
            ["Cost Codes", "Cost Code List", "Codes", "CostCodes"],
            ["Cost code", "Description"],
        )
        cost_options = []
        if _cost_df is not None and not _cost_df.empty:
            def _col(df, name):
                for c in df.columns:
                    if isinstance(c, str) and c.strip().lower() == name.lower():
                        return c
                return name
            cc = _col(_cost_df, "Cost code")
            ds = _col(_cost_df, "Description")
            _tmp = _cost_df[[cc, ds]].astype(str).fillna("")
            cost_options = (_tmp[cc] + " - " + _tmp[ds]).tolist()
except Exception:
    # Don’t crash the page if workbook/sheets aren’t available
    pass
# ---- End fallback options loader ----

import pandas as pd
from datetime import date

# Gate: require login
user = st.session_state.get("user_email")
if not user:
    st.warning("Please sign in on the Home page first.")
    if hasattr(st, "page_link"):
        st.page_link("streamlit_app.py", label="ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â Go to Home")
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