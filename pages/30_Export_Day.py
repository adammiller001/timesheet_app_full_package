import datetime as _dt
from pathlib import Path
import pandas as pd
import streamlit as st

from app.features.export_daily_time import export_daily_time

# Gate: require login
if not st.session_state.get("authenticated", False):
    st.warning("Please sign in on the Home page first.")
    st.stop()

user = st.session_state.get("user_email")
st.sidebar.info(f"Signed in as: {user}")

ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="Export Day", page_icon="📤", layout="wide")
st.title("Export Day")

# ---------- helpers ----------
def _find_hours_df():
    # First check for our session time data
    if "session_time_data" in st.session_state and st.session_state.session_time_data is not None:
        df = st.session_state.session_time_data
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df.copy()

    # Then check other candidates
    candidates = [
        "hours_entered_df","hours_df","entered_rows_df","rows_df",
        "hours_table_df","hours_table_data","rows",
    ]
    for k in candidates:
        if k in st.session_state and st.session_state[k] is not None:
            obj = st.session_state[k]
            if isinstance(obj, pd.DataFrame):
                return obj.copy()
            if isinstance(obj, list) and obj and isinstance(obj[0], dict):
                return pd.DataFrame(obj).copy()
    for v in st.session_state.values():
        if isinstance(v, pd.DataFrame):
            return v.copy()
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return pd.DataFrame(v).copy()
    return None

def _coerce_hours_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["Employee","Person Number","Trade Class","Premium Rate",
                "Job","Cost Code","RT Hours","OT Hours","Notes","Night Shift"]:
        if col not in df.columns: df[col] = ""
    return df

def _templates_missing():
    missing = []
    for name in ("Daily Time.xlsx", "TimeEntries.xlsx"):
        if not (ROOT / name).exists():
            missing.append(name)
    return missing

def _to_path(obj) -> Path:
    """Robustly turn anything (path/str/tuple with 1 element) into a Path."""
    # Unwrap one level of tuple/list if needed
    if isinstance(obj, (list, tuple)) and obj:
        obj = obj[0]
    return Path(str(obj))

def _normalize_export_return(ret):
    """
    Accepts:
    - Path/str           -> (Path, [])
    - (path, [paths...]) -> (Path, [Path...])
    - Any nested tuples/lists are unwrapped.
    """
    if isinstance(ret, (list, tuple)):
        if len(ret) == 0:
            return None, []
        primary = _to_path(ret[0])
        job_paths_raw = ret[1] if len(ret) > 1 else []
        paths = []
        if isinstance(job_paths_raw, (list, tuple)):
            for p in job_paths_raw:
                if p is None: 
                    continue
                paths.append(_to_path(p))
        elif job_paths_raw:
            paths.append(_to_path(job_paths_raw))
        return primary, paths
    # Single path/str case
    return _to_path(ret), []

# ---------- date & template checks ----------
c1, c2 = st.columns([1,3])
with c1:
    date_val = st.session_state.get("date_val")
    if isinstance(date_val, str):
        try: date_val = _dt.date.fromisoformat(date_val)
        except Exception: date_val = None
    if not isinstance(date_val, _dt.date):
        date_val = _dt.date.today()
    date_val = st.date_input("Export date", value=date_val)

with c2:
    miss = _templates_missing()
    if miss:
        st.warning("Missing required files in app root (and they must be closed in Excel): " + ", ".join(miss))
    else:
        st.info("Templates detected. Ready to export.")

hours_df = _find_hours_df()
if hours_df is None or hours_df.empty:
    st.error("No 'Hours Entered' data found. Add rows in **Timesheet Entry** first.")
    st.stop()

hours_df = _coerce_hours_df(hours_df)

with st.expander("Preview rows to export", expanded=False):
    st.dataframe(hours_df, use_container_width=True, hide_index=True)

st.divider()
if st.button("Export Daily Time", type="primary"):
    try:
        raw_ret = export_daily_time(date_val, hours_df)
        daily_path, job_paths = _normalize_export_return(raw_ret)

        if daily_path is None:
            st.error("Exporter returned no path. Please update export_daily_time.py.")
            st.stop()

        # Daily Time download
        st.success(f"Exported Daily Time to: {daily_path.name}")
        if daily_path.exists():
            with open(daily_path, "rb") as f:
                st.download_button(
                    "Download the Daily Time export",
                    data=f.read(),
                    file_name=daily_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_daily_time_main",
                )
        else:
            st.warning(f"Daily Time file not found on disk: {daily_path}")

        # Per-job downloads
        if job_paths:
            st.subheader("Per-job Daily Import files")
            for i, p in enumerate(job_paths):
                if not p.exists():
                    st.warning(f"Expected file not found: {p}")
                    continue
                with open(p, "rb") as f:
                    st.download_button(
                        f"Download {p.name}",
                        data=f.read(),
                        file_name=p.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_job_{i}_{p.name}",
                    )
        else:
            st.info("No per-job files were created. Check that each row has a Job and that TimeEntries.xlsx is present and closed.")

    except FileNotFoundError as e:
        st.error(str(e))
    except Exception as e:
        st.exception(e)
