# app/ui/entry.py  - TEMP DIAGNOSTIC (no Excel access)
import datetime as dt
import streamlit as st

def entry_form():
    """
    Minimal entry that can't crash from Excel/pandas.
    If selecting an employee still blanks the page, the issue is UI/state.
    If this works, the issue is in the data layer (workbook reads, etc.).
    """
    st.caption("DIAGNOSTIC ENTRY - static options, no Excel")

    # show key session items so we can see if they reset
    with st.expander("Session snapshot", expanded=False):
        st.json({
            "entered_app": st.session_state.get("entered_app"),
            "whoami_email": st.session_state.get("whoami_email"),
            "xlsx_path": st.session_state.get("xlsx_path"),
            "sel_emps": st.session_state.get("sel_emps"),
        })

    # date (simple)
    _ = st.date_input("Date", dt.date.today(), key="date_val")

    # static employee options (no file IO)
    options = ["ADAM MILLER", "JANE DOE", "JOHN SMITH", "PAT TAYLOR"]
    sel = st.multiselect("Employees (static demo)", options, key="sel_emps")

    # mirror selection + a heartbeat so you always see content
    st.write("Selected employees:", sel)
    st.info("This line should always remain visible after any selection.")

    # simple submit just to exercise a button
    if st.button("Submit (demo)", key="submit_demo"):
        st.success(f"Would add {len(sel)} rows (demo only; no Excel).")
