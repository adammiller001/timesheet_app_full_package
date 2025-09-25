
import streamlit as st
import pandas as pd
from datetime import date

# Gate: require login
user = st.session_state.get("user_email")
if not user:
    st.warning("Please sign in on the Home page first.")
    if hasattr(st, "page_link"):
        st.page_link("streamlit_app.py", label="ÃƒÂ¢Ã¢â‚¬Â Ã‚Â Go to Home")
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
    job_choice = st.selectbox(
        "Job Number - Area Number - Description",
        options=jobs,
        index=None,
        placeholder="Select a job...",
    )
with c2:
    code_choice = st.selectbox(
        "Cost code - Description",
        options=codes,
        index=None,
        placeholder="Select a cost code...",
    )

st.markdown("---")

# Employees
st.subheader("Employees (from Excel)")
employees = load_employee_list()
if not employees:
    st.error("Could not find employees in `" + EXCEL_FILENAME + "` (same folder as the app root).")

sel_emps = st.multiselect("Choose employees", employees, default=[])

# Bulk entry
st.markdown("### Add Hours For Selected Employees")
bc1, bc2, bc3 = st.columns([1,1,2])
with bc1:
    bulk_rt = st.number_input("RT Hours (all selected)", min_value=0.0, step=0.25, value=8.0)
with bc2:
    bulk_ot = st.number_input("OT Hours (all selected)", min_value=0.0, step=0.25, value=0.0)
with bc3:
    notes = st.text_area("Notes (optional, multi-line)))", value="", placeholder="Enter notes...", height=120)

if "hours_rows" not in st.session_state:
    st.session_state["hours_rows"] = []

def _append_rows():
    details_df = load_employee_details(sel_emps)
    for _, row in details_df.iterrows():
        st.session_state["hours_rows"].append({
            "Employee": row.get("Employee",""),
            "Person Number": row.get("Person Number",""),
            "Trade Class": row.get("Trade Class",""),
            "Night Shift": row.get("Night Shift",""),
            "Premium Rate": row.get("Premium Rate",""),
            "RT Hours": float(bulk_rt),
            "OT Hours": float(bulk_ot),
            "Notes": notes,
            "Job": job_choice or "",
            "Cost Code": code_choice or "",
            "Date": str(chosen_date),
        })

enter_disabled = not (sel_emps and job_choice and code_choice)
if enter_disabled:
    st.caption("Select **employees**, a **job**, and a **cost code** to enable the Enter button.")

if st.button("Enter", type="primary", disabled=enter_disabled):
    _append_rows()

st.markdown("---")

# Hours Entered (read-only)
st.subheader("Hours Entered")
cols = [
    "Employee", "Person Number", "Trade Class", "Night Shift", "Premium Rate",
    "RT Hours", "OT Hours", "Notes", "Job", "Cost Code", "Date"
]
entered_df = pd.DataFrame(st.session_state.get("hours_rows", []), columns=cols)
st.dataframe(entered_df, use_container_width=True, hide_index=True)

# ---- Delete controls ----
if not entered_df.empty:
    st.markdown("#### Remove Rows")
    # Build options: Delete All + unique employees currently present
    emp_options = sorted({r.get("Employee","") for r in st.session_state["hours_rows"] if r.get("Employee")})
    delete_choice = st.selectbox("Choose what to delete", options=["Delete All"] + emp_options, index=0)
    if st.button("Delete", type="secondary"):
        if delete_choice == "Delete All":
            st.session_state["hours_rows"].clear()
            st.success("All rows deleted.")
        else:
            st.session_state["hours_rows"] = [r for r in st.session_state["hours_rows"] if r.get("Employee") != delete_choice]
            st.success(f"Deleted rows for: {delete_choice}")
        st.rerun()

# Export
st.markdown("---")
col_l, _ = st.columns([1, 2])
with col_l:
    if st.button("Export Daily Time", use_container_width=True):
        if entered_df.empty:
            st.error("Please add at least one row before exporting.")
        else:
            try:
                # Call your exporter. If yours requires args, wire them here.
                ret = export_daily_time(chosen_date, entered_df)

                # Normalize return to Path(s)
                from pathlib import Path

                def _to_path(x):
                    return Path(str(x))

                extra_job_paths = []
                if isinstance(ret, (list, tuple)):
                    out_path = _to_path(ret[0]) if ret else None
                    if len(ret) > 1 and ret[1]:
                        extra_job_paths = [_to_path(p) for p in ret[1]]
                else:
                    out_path = _to_path(ret)

                if not out_path:
                    raise RuntimeError("Exporter returned no path.")

                # Daily Time file
                st.success(f"Exported Daily Time to: {out_path.name}")
                if out_path.exists():
                    st.download_button(
                        "Download the Daily Time export",
                        data=out_path.read_bytes(),
                        file_name=out_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_daily_time_from_timesheet",
                    )

                # Per-job Daily Import files (if any)
                if extra_job_paths:
                    st.subheader("Per-job Daily Import files")
                    for i, p in enumerate(extra_job_paths):
                        if not p.exists():
                            st.warning(f"Expected file not found: {p}")
                            continue
                        st.download_button(
                            f"Download {p.name}",
                            data=p.read_bytes(),
                            file_name=p.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_job_{i}_{p.name}",
                        )
                else:
                    st.info("No per-job files were created. Ensure each row has a Job and that TimeEntries.xlsx is present/closed.")

            except FileNotFoundError as e:
                st.error(str(e))
            except Exception as e:
                st.exception(e)
