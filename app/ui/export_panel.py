import datetime as dt
import streamlit as st
from app.exports.timeentries_export import per_job_exports
from app.reports.daily_time import daily_time_report

def export_panel():
    export_date = st.date_input("Export Date", dt.date.today(), key="export_date")
    if st.button("Create Export"):
        month_folder = export_date.strftime("%B")
        # Per‑job
        n_files = 0
        for file_name, file_bytes in per_job_exports(st.session_state.xlsx_path, export_date):
            st.download_button(f"Download {file_name}", data=file_bytes, file_name=file_name, use_container_width=True)
            n_files += 1
        if n_files == 0:
            st.info("No per‑job files were created (no REG/OT hours).")
        # Daily
        out = daily_time_report(st.session_state.xlsx_path, export_date)
        if out:
            daily_name = f"{export_date.strftime('%m-%d-%Y')} – Daily Time.xlsx"
            st.download_button(f"Download {daily_name}", data=out, file_name=daily_name, use_container_width=True)
