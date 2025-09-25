# app/main.py
import streamlit as st
from app.state import init_state

st.set_page_config(page_title="Daily Timesheet (Diag)", page_icon="—‚ï¸", layout="centered")
st.set_option("client.showErrorDetails", True)

# Initialize robustly (entered_app forced True in diagnostics)
init_state()

# ---------- DIAGNOSTIC, SELF-CONTAINED UI (no other imports) ----------
st.title("Timesheet Entry - Diagnostic Shell")

# Always show a heartbeat so you never get a blank screen
st.info("Heartbeat: UI rendered. If this disappears after selecting an employee, tell me.")

# Compact session snapshot on every rerun
with st.expander("Session snapshot", expanded=False):
    st.json({
        "initialized": st.session_state.get("initialized"),
        "entered_app": st.session_state.get("entered_app"),
        "whoami_email": st.session_state.get("whoami_email"),
        "xlsx_path": st.session_state.get("xlsx_path"),
        "sel_emps": st.session_state.get("sel_emps"),
        "date_val": str(st.session_state.get("date_val", "")),
    })

# Minimal widgets with STABLE KEYS only
date_val = st.date_input("Date", key="date_val")
options = ["ADAM MILLER", "JANE DOE", "JOHN SMITH", "PAT TAYLOR"]

sel_emps = st.multiselect(
    "Employees (pure UI test - no Excel)",
    options=options,
    key="sel_emps",
)

st.write("Selected employees:", sel_emps)

if st.button("Submit (demo)", key="submit_demo"):
    st.success(f"Would add {len(sel_emps)} rows (demo only).")

# Show the raw state of the widgets at the end of the script too
st.caption("End-of-script snapshot:")
st.json({
    "sel_emps": st.session_state.get("sel_emps"),
    "date_val": str(st.session_state.get("date_val", "")),
})
