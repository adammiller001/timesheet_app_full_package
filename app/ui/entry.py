import datetime as dt
import pandas as pd
import streamlit as st
from app.data.workbook import (
    get_employees, get_jobs, get_cost_codes, append_time_row, only_active_cost_codes, pad_job_area
)

def entry_form():
    xlsx_path = st.session_state.xlsx_path
    employees = get_employees(xlsx_path)
    jobs = get_jobs(xlsx_path)
    costcodes = get_cost_codes(xlsx_path)

    date_val = st.date_input("Date", dt.date.today())

    emp_opts = employees["name"].tolist()
    sel_emps = st.multiselect("Employees", emp_opts)

    job_opts = jobs["job_num"].unique().tolist()
    sel_job  = st.selectbox("Job Number", [""] + job_opts)

    # Areas bound to job
    areas = jobs[jobs["job_num"].astype(str) == str(sel_job)][["area_code","area_desc"]].copy() if sel_job else pd.DataFrame(columns=["area_code","area_desc"])
    if not areas.empty:
        areas["label"] = areas.apply(lambda r: f"{r.area_code} - {r.area_desc}" if r.area_desc else r.area_code, axis=1)
    sel_area_label = st.selectbox("Job Area", [""] + (areas["label"].tolist() if not areas.empty else []))
    sel_area_code = ""
    if sel_area_label and not areas.empty:
        sel_area_code = areas.loc[areas["label"] == sel_area_label, "area_code"].iloc[0]

    # Active cost codes
    active_codes = only_active_cost_codes(costcodes)
    if not active_codes.empty:
        active_codes["label"] = active_codes.apply(lambda r: f"{r.cost_code} - {r.cost_desc}" if r.cost_desc else r.cost_code, axis=1)
    sel_code_label = st.selectbox("Class Type (Cost Code)", [""] + (active_codes["label"].tolist() if not active_codes.empty else []))
    sel_code_code = ""
    if sel_code_label and not active_codes.empty:
        sel_code_code = active_codes.loc[active_codes["label"] == sel_code_label, "cost_code"].iloc[0]

    rt_hours = st.number_input("RT Hours (per employee)", min_value=0.0, max_value=24.0, step=0.5, value=0.0)
    ot_hours = st.number_input("OT Hours (per employee)", min_value=0.0, max_value=24.0, step=0.5, value=0.0)
    desc     = st.text_area("Comments (optional)", "", height=100)

    if st.button("Submit"):
        if not sel_emps:
            st.warning("Select at least one employee."); return
        if not sel_job or not sel_area_code or not sel_code_code:
            st.warning("Select Job, Area, and Class Type."); return
        successes = 0
        for emp_name in sel_emps:
            ok = append_time_row(
                xlsx_path,
                payload={
                    "Job Number": str(sel_job),
                    "Job Area": pad_job_area(sel_area_code),
                    "Date": date_val.strftime("%Y-%m-%d"),
                    "Name": emp_name,
                    "Class Type": sel_code_code,
                    "Comments": desc,
                    "RT Hours": float(rt_hours),
                    "OT Hours": float(ot_hours),
                }
            )
            if ok: successes += 1
        if successes:
            st.success(f"Added {successes} row(s) to 'Time Data'.")
