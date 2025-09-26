import streamlit as st
import pandas as pd
from pathlib import Path
import io
import zipfile
import os
import re
import tempfile
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
import openpyxl.styles
from shutil import copyfile
from time import sleep
import time
from app.style_utils import apply_watermark
from datetime import datetime, date

apply_watermark()

# Try to use your helpers; fall back gracefully if not present
try:
    from utils_jobs import (
        load_jobs_active,
        build_job_options,
        load_cost_options,
    )
    HAVE_UTILS = True
except Exception:
    HAVE_UTILS = False

# Import Google Sheets integration
try:
    from app.integrations.google_sheets import read_timesheet_data, get_sheets_manager
    HAVE_GOOGLE_SHEETS = True
except Exception:
    HAVE_GOOGLE_SHEETS = False

# Gate: require login
if not st.session_state.get("authenticated", False):
    st.warning("Please sign in on the Home page first.")
    st.stop()

user = st.session_state.get("user_email")
user_type = st.session_state.get("user_type", "User")
st.sidebar.info(f"Signed in as: {user} ({user_type})")

# Initialize automatic data refresh trigger for truly dynamic dropdowns
if "auto_fresh_data" not in st.session_state:
    st.session_state.auto_fresh_data = True

XLSX = Path(__file__).resolve().parent.parent / "TimeSheet Apps.xlsx"

# File modification time monitoring for automatic reloads
def check_file_modified():
    """Check if Excel file has been modified and force reload if needed"""
    try:
        if not XLSX.exists():
            return False

        current_mtime = XLSX.stat().st_mtime
        last_mtime = st.session_state.get("xlsx_last_mtime", 0)

        if current_mtime > last_mtime:
            st.session_state.xlsx_last_mtime = current_mtime
            if last_mtime > 0:  # Don't show on first load
                st.success(f"📁 Excel file updated - Reloading dropdowns automatically")
                st.rerun()
            return True
        return False
    except Exception:
        return False

# Check for file modifications
check_file_modified()

# Completely disable pandas caching
pd.set_option('io.hdf.default_format','table')
if hasattr(pd.io.common, '_maybe_convert_usecols'):
    pd.io.common._maybe_convert_usecols = lambda x: x  # Disable column caching

def safe_read_excel_force_fresh(file_path, sheet_name):
    """Force fresh read without any caching"""
    # Clear any potential pandas caching
    if hasattr(pd, '_cache'):
        pd._cache.clear()
    return _safe_read_excel_internal(file_path, sheet_name)

def _safe_read_excel_internal(file_path, sheet_name):
    """Internal function that does the actual Excel reading"""
    try:
        # Force completely fresh file read by copying to unique temp file every time
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        # Always create temp file to bypass any caching
        import tempfile
        import shutil
        with tempfile.NamedTemporaryFile(suffix=f'_{int(time.time() * 1000)}.xlsx', delete=False) as tmp:
            shutil.copy2(file_path, tmp.name)
            result = pd.read_excel(tmp.name, sheet_name=sheet_name)
            try:
                os.unlink(tmp.name)  # Clean up
            except:
                pass  # Ignore cleanup errors
            return result
    except PermissionError:
        import tempfile
        import shutil
        try:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                shutil.copy2(file_path, tmp.name)
                result = pd.read_excel(tmp.name, sheet_name=sheet_name)
                os.unlink(tmp.name)
                return result
        except Exception as e:
            st.error(f"Could not read Excel file. Please close Excel and try again. Error: {e}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False, ttl=60)
def _cached_sheet_data(sheet_name: str, cache_token: int, force_refresh: bool):
    try:
        df = read_timesheet_data(sheet_name, force_refresh=force_refresh)
        if isinstance(df, pd.DataFrame):
            return df
    except Exception as e:
        st.warning(f"Google Sheets read issue for {sheet_name}: {e}")
    return pd.DataFrame()


def smart_read_data(sheet_name, force_refresh=False):
    """Smart data reader that minimizes Google Sheets requests and falls back gracefully"""
    try:
        cache_token = st.session_state.get("sheet_cache_token", 0)
        if force_refresh:
            cache_token += 1
            st.session_state["sheet_cache_token"] = cache_token

        df = _cached_sheet_data(sheet_name, cache_token, force_refresh)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df.copy()

        # Fallback to Excel file if Google Sheets unavailable or empty
        return safe_read_excel(XLSX, sheet_name, force_refresh=True)
    except Exception as e:
        st.error(f"Failed to load {sheet_name}: {e}")
        return pd.DataFrame()

def get_available_worksheets(file_path):
    """Get list of available worksheets in Excel file"""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheets = wb.sheetnames
        wb.close()
        return sheets
    except Exception:
        return []

def safe_read_excel(file_path, sheet_name, force_refresh=False):
    """Safely read Excel file with optional force refresh"""
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            st.error(f"Excel file not found: {file_path}")
            return pd.DataFrame()

        # Always use fresh read for truly dynamic dropdowns
        # Check for auto refresh trigger or manual force refresh
        if (force_refresh or
            st.session_state.get("force_fresh_data", False) or
            st.session_state.get("auto_fresh_data", False)):
            return safe_read_excel_force_fresh(str(file_path), sheet_name)
        else:
            # Fallback to fresh read anyway
            return safe_read_excel_force_fresh(str(file_path), sheet_name)
    except Exception as e:
        available_sheets = get_available_worksheets(file_path)
        if available_sheets:
            st.error(f"Error accessing worksheet '{sheet_name}'. Available worksheets: {', '.join(available_sheets)}")
        else:
            st.error(f"Error accessing Excel file: {e}")
        return pd.DataFrame()

def get_time_data_from_session(_date_filter=None):
    """Get time data from session state with optional date filtering"""
    try:
        data = st.session_state.session_time_data.copy()

        if _date_filter and "Date" in data.columns and not data.empty:
            data["Date"] = pd.to_datetime(data["Date"])
            data = data[data["Date"].dt.strftime("%Y-%m-%d") == _date_filter]

        return data
    except Exception as e:
        st.error(f"Error reading session time data: {e}")
        return pd.DataFrame()

def _normalize_sheet_value(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return ''
        return ("{0:.15g}".format(float(value))).rstrip('.0') if float(value).is_integer() else "{0:.15g}".format(float(value))
    if isinstance(value, pd.Timestamp):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    try:
        if pd.isna(value):
            return ''
    except Exception:
        pass
    return str(value).strip()


def _build_sheet_row(row_dict, headers):
    normalized = []
    for header in headers:
        value = row_dict.get(header)
        normalized.append(_normalize_sheet_value(value))
    return normalized


def _sync_time_data_to_google(new_data_df: pd.DataFrame) -> bool:
    """Push new time data rows to Google Sheets when available"""
    if new_data_df.empty:
        return True

    if not (
        HAVE_GOOGLE_SHEETS
        and "google_sheets_id" in st.secrets
        and st.secrets["google_sheets_id"]
    ):
        return True

    try:
        sheet_id = st.secrets["google_sheets_id"]
        manager = get_sheets_manager()
        sheet_candidates = ("Time Data", "TimeData")
        worksheet, actual_title = manager.find_worksheet(sheet_candidates, sheet_id)

        if not worksheet or not actual_title:
            st.warning("Time Data worksheet not found in Google Sheets. Please ensure a tab named 'Time Data' exists.")
            return False

        df_to_sync = new_data_df.copy()
        if df_to_sync.empty:
            return True

        df_to_sync.columns = [str(col).strip() for col in df_to_sync.columns]
        df_to_sync = df_to_sync[[col for col in df_to_sync.columns if col]]
        df_to_sync = df_to_sync.where(pd.notnull(df_to_sync), None)

        header_values = worksheet.row_values(1)
        headers = [str(cell).strip() for cell in header_values if str(cell).strip()]

        if not headers:
            all_values = worksheet.get_all_values()
            for row in all_values:
                cleaned = [str(cell).strip() for cell in row if str(cell).strip()]
                if cleaned:
                    headers = [str(cell).strip() for cell in row if str(cell).strip()]
                    break

        if not headers:
            manager.write_worksheet(actual_title, df_to_sync, sheet_id)
            return True

        def _norm(col_name: str) -> str:
            return ''.join(ch for ch in str(col_name).strip().lower() if ch.isalnum())

        df_lookup = {_norm(col): col for col in df_to_sync.columns}
        rows_to_append = []

        for _, row in df_to_sync.iterrows():
            row_values = []
            for header in headers:
                source_col = df_lookup.get(_norm(header))
                value = row[source_col] if source_col else None
                if pd.isna(value):
                    value = None
                elif isinstance(value, pd.Timestamp):
                    value = value.strftime("%Y-%m-%d")
                elif hasattr(value, "item") and not isinstance(value, (str, bytes)):
                    try:
                        value = value.item()
                    except Exception:
                        value = str(value)
                row_values.append(value)
            rows_to_append.append(row_values)

        if not rows_to_append:
            return True

        return manager.append_rows(actual_title, rows_to_append, sheet_id)

    except Exception as e:
        st.error(f"Failed to sync Time Data to Google Sheets: {e}")
        return False


def _replace_time_data_in_google(updated_df: pd.DataFrame) -> bool:
    """Write the provided DataFrame to the Google Sheets Time Data worksheet"""
    if not (
        HAVE_GOOGLE_SHEETS
        and "google_sheets_id" in st.secrets
        and st.secrets["google_sheets_id"]
    ):
        return True

    try:
        sheet_id = st.secrets["google_sheets_id"]
        manager = get_sheets_manager()
        sheet_candidates = ("Time Data", "TimeData")
        worksheet, actual_title = manager.find_worksheet(sheet_candidates, sheet_id)

        if not worksheet or not actual_title:
            st.warning("Time Data worksheet not found in Google Sheets. Please ensure a tab named 'Time Data' exists.")
            return False

        header_values = worksheet.row_values(1)
        headers = [str(cell).strip() for cell in header_values if str(cell).strip()]

        df_to_write = updated_df.copy()
        df_to_write.columns = [str(col).strip() for col in df_to_write.columns]

        if headers:
            for header in headers:
                if header not in df_to_write.columns:
                    df_to_write[header] = ''
            df_to_write = df_to_write[headers]
        elif not df_to_write.empty:
            headers = list(df_to_write.columns)
        else:
            headers = [
                "Job Number", "Job Area", "Date", "Name", "Trade Class",
                "Employee Number", "RT Hours", "OT Hours", "Description of work",
                "Comments", "Night Shift", "Premium Rate", "Subsistence Rate",
                "Travel Rate", "Indirect", "Cost Code"
            ]
            for header in headers:
                if header not in df_to_write.columns:
                    df_to_write[header] = ''
            df_to_write = df_to_write[headers]

        if not df_to_write.empty:
            df_to_write = df_to_write.applymap(_normalize_sheet_value)
        else:
            df_to_write = df_to_write.astype(str)

        success = manager.write_worksheet(actual_title, df_to_write, sheet_id)
        return success

    except Exception as e:
        st.error(f"Failed to update Time Data in Google Sheets: {e}")
        return False


def save_to_session(new_rows):
    """Save new rows to session state and sync to Google Sheets when configured"""
    try:
        new_data_df = pd.DataFrame(new_rows)

        # Add to session state Time Data
        if not st.session_state.session_time_data.empty:
            st.session_state.session_time_data = pd.concat([st.session_state.session_time_data, new_data_df], ignore_index=True)
        else:
            st.session_state.session_time_data = new_data_df

        synced = _sync_time_data_to_google(new_data_df)
        if not synced:
            st.warning("Added lines locally, but could not update Google Sheets Time Data.")

        return True
    except Exception as e:
        st.error(f"Error saving to session: {e}")
        return False

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### Timesheet Entry")
with col2:
    if st.button("?? Force Reload All Data", help="Completely reload all data", type="secondary"):
        # Clear ALL session state data except authentication
        keys_to_keep = ["user_email", "user_type", "authenticated"]
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]

        # Force fresh data flags
        st.session_state.force_fresh_data = True
        st.session_state.auto_fresh_data = True
        st.session_state.data_refresh_timestamp = time.time()
        st.session_state.xlsx_last_mtime = 0  # Force file time check

        # Clear all caches
        st.session_state['sheet_cache_token'] = st.session_state.get('sheet_cache_token', 0) + 1
        st.success("?? All data cleared - Reloading...")
        st.rerun()


# Force fresh data reload if refresh was requested
if st.session_state.get("force_fresh_data", False):
    st.info(f"🔄 Loading fresh data... (Timestamp: {st.session_state.get('data_refresh_timestamp', 'N/A')})")
    # Reset flag after use
    st.session_state.force_fresh_data = False

# Status indicators removed - Google Sheets working properly

# Add live data verification - now optional since issues are resolved
    st.write("## **DEBUGGING EMPLOYEE LIST**")
    try:
        st.write("**Testing direct Excel read vs safe_read_excel:**")

        # Try direct pandas read
        try:
            direct_read = pd.read_excel(XLSX, sheet_name="Employee List")
            st.write(f"Direct pandas read: {len(direct_read)} rows")
        except Exception as e:
            st.write(f"Direct read failed: {e}")

        # Try our safe read
        emp_debug = smart_read_data("Employee List", force_refresh=True)
        st.write(f"**safe_read_excel: {len(emp_debug)} rows**")
        st.write("**All columns:**", list(emp_debug.columns))

        # Check if there are any NaN values in Employee Name that might cause issues
        if "Employee Name" in emp_debug.columns:
            nan_count = emp_debug["Employee Name"].isna().sum()
            st.write(f"**NaN values in Employee Name column: {nan_count}**")

            # Show any rows with NaN names
            nan_rows = emp_debug[emp_debug["Employee Name"].isna()]
            if not nan_rows.empty:
                st.write("**Rows with NaN Employee Names:**")
                st.dataframe(nan_rows)

        # Show all employee names
        name_col = None
        for col in ["Employee Name", "Name", "Employee", "Full Name"]:
            if col in emp_debug.columns:
                name_col = col
                break

        if name_col:
            st.write(f"**All employees in {name_col} column:**")
            st.write(f"**Expected: 11 employees, Actually loaded: {len(emp_debug)}**")

            # Show all rows with their original Excel row numbers if possible
            for idx, row in emp_debug.iterrows():
                name = str(row[name_col])
                person_num = row.get('Person Number', 'N/A')
                active_val = row.get('Active', 'N/A')
                st.write(f"Row {idx+2}: '{name}' (Person: {person_num}, Active: {active_val})")

            # Check specifically for Graham with various spellings
            graham_variations = ['GRAHAM', 'GRAEME', 'GRAHM', 'ST HILAIRE', 'HILAIRE']
            for variation in graham_variations:
                graham_check = emp_debug[emp_debug[name_col].astype(str).str.contains(variation, case=False, na=False)]
                if not graham_check.empty:
                    st.success(f"✅ Found '{variation}' in: {graham_check[name_col].iloc[0]}")
                else:
                    st.write(f"⚪ No match for '{variation}'")

            # Show the full dataframe for inspection
            st.write("**Full Employee DataFrame:**")
            st.dataframe(emp_debug)

            # Check specifically for Graham
            graham_check = emp_debug[emp_debug[name_col].astype(str).str.contains("GRAHAM", case=False, na=False)]
            if not graham_check.empty:
                st.success(f"✅ GRAHAM FOUND in Excel: {graham_check[name_col].iloc[0]}")
            else:
                st.error("❌ GRAHAM NOT FOUND in Excel Employee List")

        # Check Active column
        if "Active" in emp_debug.columns:
            st.write("**Active column data types and values:**")
            st.write(f"Column data type: {emp_debug['Active'].dtype}")
            st.write("Unique values and their types:")
            for val in emp_debug['Active'].unique():
                st.write(f"  '{val}' (type: {type(val).__name__})")

            # Show filtering results
            bool_filter = (emp_debug["Active"] == True)
            str_filter = emp_debug["Active"].astype(str).str.upper().isin(["TRUE", "YES", "Y", "1"])
            combined_filter = bool_filter | str_filter

            st.write(f"Boolean filter (== True): {bool_filter.sum()} employees")
            st.write(f"String filter (TRUE/YES/Y/1): {str_filter.sum()} employees")
            st.write(f"Combined filter result: {combined_filter.sum()} employees")

            filtered_df = emp_debug[combined_filter]
            if name_col:
                st.write("**Employees after Active filtering:**")
                for name in filtered_df[name_col].astype(str).tolist():
                    st.write(f"  - '{name}'")
        else:
            st.warning("No 'Active' column found")

    except Exception as e:
        st.error(f"Employee debug error: {e}")
        import traceback
        st.code(traceback.format_exc())

    st.write("## **DEBUGGING COST CODES**")
    try:
        cost_debug = smart_read_data("Cost Codes", force_refresh=True)
        st.write(f"**RAW DATA LOADED - Total rows: {len(cost_debug)}**")
        st.write("**All columns:**", list(cost_debug.columns))

        if "Active" in cost_debug.columns:
            st.write("**Active column analysis:**")
            st.write(f"Data type: {cost_debug['Active'].dtype}")
            active_vals = cost_debug['Active'].value_counts()
            st.write("Value counts:", dict(active_vals))

            # Show which items are FALSE
            false_items = cost_debug[cost_debug['Active'] == False]
            if not false_items.empty:
                st.write("**Items marked as FALSE:**")
                for idx, row in false_items.iterrows():
                    code_val = row.get('Cost Code', row.get('Code', 'Unknown'))
                    desc_val = row.get('Description', row.get('DESC', 'No description'))
                    st.write(f"  - {code_val} - {desc_val}")

            # Test filtering
            bool_filter = (cost_debug["Active"] == True)
            str_filter = cost_debug["Active"].astype(str).str.upper().isin(["TRUE", "YES", "Y", "1"])
            combined_filter = bool_filter | str_filter

            st.write(f"Items that should be filtered OUT (Active=False): {len(cost_debug) - combined_filter.sum()}")
            st.write(f"Items that should show in dropdown: {combined_filter.sum()}")

            # Specific debug for the problematic cost code
            st.write("**SPECIFIC DEBUG: 00002-170-53**")
            specific_code = cost_debug[cost_debug['Cost Code'].astype(str).str.contains('00002-170-53', na=False)]
            if not specific_code.empty:
                row = specific_code.iloc[0]
                st.write(f"Found: {row['Cost Code']} - {row['Description']}")
                st.write(f"Active value: {row['Active']} (type: {type(row['Active']).__name__})")
                st.write(f"Passes boolean filter: {row['Active'] == True}")
                st.write(f"Passes string filter: {str(row['Active']).upper() in ['TRUE', 'YES', 'Y', '1']}")
            else:
                st.write("❌ 00002-170-53 NOT FOUND in cost codes data")

    except Exception as e:
        st.error(f"Cost codes debug error: {e}")
        import traceback
        st.code(traceback.format_exc())

# --- Date ---
date_val = st.date_input("Date", value=pd.Timestamp.today().date(), format="YYYY/MM/DD", key="date_val")

# Form reset mechanism
if "form_counter" not in st.session_state:
    st.session_state.form_counter = 0

# Initialize session-based Time Data storage
if "session_time_data" not in st.session_state:
    # Load initial data with Google Sheets support
    try:
        initial_data = smart_read_data("Time Data")
    except Exception as e:
        st.warning(f"Failed to load Time Data from configured sources: {e}")
        initial_data = pd.DataFrame()

    if isinstance(initial_data, pd.DataFrame) and (not initial_data.empty or len(initial_data.columns) > 0):
        st.session_state.session_time_data = initial_data
    else:
        st.session_state.session_time_data = pd.DataFrame(columns=[
            "Job Number", "Job Area", "Date", "Name", "Trade Class",
            "Employee Number", "RT Hours", "OT Hours", "Description of work",
            "Comments", "Night Shift", "Premium Rate", "Subsistence Rate",
            "Travel Rate", "Indirect", "Cost Code"
        ])

# --- Helper functions ---
def _find_col(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def _pad_area(val: object) -> str:
    """Ensure area is 3 digits with zero padding"""
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return "000"
    m = re.search(r"\d+", s)
    if m:
        d = m.group(0)
        return d.zfill(3)
    return s

def _build_job_options_local(df: pd.DataFrame):
    """Build job options with proper 3-digit area padding"""
    if df is None or df.empty:
        return []
    job_c  = _find_col(df, ["Job Number", "JOB #", "Job #"])
    area_c = _find_col(df, ["Area Number", "AREA #", "Area #", "AREA#"])
    desc_c = _find_col(df, ["Description", "DESCRIPTION", "PROJECT NAME", "Project Name"])
    if not job_c:
        return []
    out = []
    for _, row in df.iterrows():
        j = str(row.get(job_c, "") or "").strip()
        a = _pad_area(row.get(area_c, "")) if area_c else "000"
        d = str(row.get(desc_c, "") or "").strip() if desc_c else ""
        if j or a or d:
            out.append(f"{j} - {a} - {d}")
    return sorted(pd.Series(out).dropna().astype(str).unique().tolist())

# --- Jobs (Active) ---
if HAVE_UTILS:
    try:
        jobs_df = load_jobs_active(XLSX)
        job_options = _build_job_options_local(jobs_df)
    except Exception as e:
        st.warning(f"Could not load jobs from utils: {e}")
        jobs_df = safe_read_excel(XLSX, "Job Numbers")
        job_options = _build_job_options_local(jobs_df)
else:
    try:
        _df = smart_read_data("Job Numbers")
        _df.columns = [str(c).strip() for c in _df.columns]
        _actcol = _find_col(_df, ["Active", "ACTIVE"])
        if _actcol:
            _df = _df[_df[_actcol].astype(str).str.upper().isin(["TRUE", "YES", "Y", "1"])]
        job_options = _build_job_options_local(_df)
    except Exception:
        job_options = []

job_choice = st.selectbox(
    "Job Number - Area Number - Description",
    job_options,
    index=None,
    placeholder="Select a job...",
    key=f"job_choice_{st.session_state.form_counter}"
)

# --- Cost Codes ---
if HAVE_UTILS:
    try:
        cost_options = load_cost_options(XLSX)
    except Exception as e:
        st.warning(f"Could not load cost codes from utils: {e}")
        cost_options = []
else:
    try:
        _c = smart_read_data("Cost Codes")
        _c.columns = [str(c).strip() for c in _c.columns]
        code_c = _find_col(_c, ["Cost Code", "Code"])
        desc_c = _find_col(_c, ["Description", "DESC", "Name"])
        active_c = _find_col(_c, ["Active", "ACTIVE"])

        if active_c:
            # Handle both boolean and string values for Active
            _c = _c[(_c[active_c] == True) | (_c[active_c].astype(str).str.upper().isin(["TRUE", "YES", "Y", "1"]))]
        
        if code_c:
            if desc_c:
                cost_options = sorted([f"{str(r[code_c]).strip()} - {str(r[desc_c]).strip()}" 
                                     for _, r in _c.iterrows() if str(r[code_c]).strip()])
            else:
                cost_options = sorted([str(r[code_c]).strip() 
                                     for _, r in _c.iterrows() if str(r[code_c]).strip()])
        else:
            cost_options = []

        # Debug removed - working properly

    except Exception:
        cost_options = []

cost_choice = st.selectbox(
    "Cost Code - Description",
    cost_options,
    index=None,
    placeholder="Select a cost code...",
    key=f"cost_choice_{st.session_state.form_counter}"
)

st.divider()

# --- Employees (simple multiselect dropdown only) ---
try:
    _emp_df = smart_read_data("Employee List")
    _emp_df.columns = [str(c).strip() for c in _emp_df.columns]

    if "Active" in _emp_df.columns:
        # Handle both boolean and string values
        _emp_df = _emp_df[(_emp_df["Active"] == True) | (_emp_df["Active"].astype(str).str.upper().isin(["TRUE", "YES", "Y", "1"]))]

    EMP_NAME_COL = _find_col(_emp_df, ["Employee Name", "Name"])
    if not EMP_NAME_COL:
        EMP_NAME_COL = "Employee Name"
        if EMP_NAME_COL not in _emp_df.columns:
            _emp_df[EMP_NAME_COL] = ""

    _employee_options = sorted(_emp_df[EMP_NAME_COL].dropna().astype(str).unique().tolist())

    # Debug removed - working properly

except Exception:
    _emp_df = pd.DataFrame()
    _employee_options = []
    EMP_NAME_COL = "Employee Name"

selected_employees = st.multiselect(
    "Employees",
    options=_employee_options,
    default=[],
    placeholder="Select one or more employees...",
    key=f"selected_employees_{st.session_state.form_counter}"
)

def night_flag_for(_name: str) -> str:
    """Return 'Y' if employee has night shift flag, otherwise empty string"""
    try:
        if _emp_df.empty or EMP_NAME_COL not in _emp_df.columns:
            return ""
        _row = _emp_df.loc[_emp_df[EMP_NAME_COL].astype(str) == str(_name)]
        if _row.empty:
            return ""
        _v = str(_row.iloc[0].get("Night Shift", "")).strip().upper()
        return "Y" if _v in {"Y", "YES", "TRUE", "1"} else ""
    except Exception:
        return ""

# --- Hours Input ---
cols = st.columns(3)
with cols[0]:
    rt_hours = st.number_input("RT Hours", min_value=0.00, step=0.25, format="%.2f", value=0.00, key=f"rt_hours_{st.session_state.form_counter}")
with cols[1]:
    ot_hours = st.number_input("OT Hours", min_value=0.00, step=0.25, format="%.2f", value=0.00, key=f"ot_hours_{st.session_state.form_counter}")
with cols[2]:
    st.write("")

comments = st.text_input("Comments", value="", key=f"comments_{st.session_state.form_counter}")

def _parse_job(choice: str):
    """Parse job choice into job number, area, and description"""
    if not choice:
        return "", "", ""
    parts = choice.split(" - ", 2)
    parts += [""] * (3 - len(parts))
    return parts[0], parts[1], parts[2]

# --- Add line ---
add_disabled = not (job_choice and cost_choice and selected_employees and (rt_hours > 0 or ot_hours > 0))

if st.button("Add line", type="primary", disabled=add_disabled):
    with st.spinner("Adding entries..."):
        job_num, job_area, job_desc = _parse_job(job_choice)
        
        try:
            employee_lookup = {}
            if not _emp_df.empty and EMP_NAME_COL in _emp_df.columns:
                for _, row in _emp_df.iterrows():
                    name = str(row.get(EMP_NAME_COL, ""))
                    employee_lookup[name] = {
                        'emp_num': str(row.get("Person Number", "") or ""),
                        'trade': str(row.get("Override Trade Class", "") or "") or str(row.get("Trade Class", "") or ""),
                        'premium': str(row.get("Premium Rate", "") or ""),
                        'subsistence': str(row.get("Subsistence Rate", "") or ""),
                        'travel': str(row.get("Travel Rate", "") or ""),
                        'indirect': str(row.get("Indirect / Direct", "")).strip().upper() == "INDIRECT",
                        'night': "Y" if str(row.get("Night Shift", "")).strip().upper() in {"Y", "YES", "TRUE", "1"} else ""
                    }
            
            new_rows = []
            date_str = pd.to_datetime(date_val).strftime("%Y-%m-%d")
            cost_code = cost_choice.split(" - ", 1)[0] if cost_choice else ""
            
            for emp_name in selected_employees:
                emp_data = employee_lookup.get(emp_name, {
                    'emp_num': '', 'trade': '', 'premium': '', 'subsistence': '', 'travel': '', 'indirect': False, 'night': ''
                })

                new_row = {
                    "Job Number": job_num,
                    "Job Area": job_area,
                    "Date": date_str,
                    "Name": emp_name,
                    "Trade Class": emp_data['trade'],
                    "Employee Number": emp_data['emp_num'],
                    "RT Hours": rt_hours,
                    "OT Hours": ot_hours,
                    "Description of work": job_desc,
                    "Comments": comments,
                    "Night Shift": emp_data['night'],
                    "Premium Rate": emp_data['premium'],
                    "Subsistence Rate": emp_data['subsistence'],
                    "Travel Rate": emp_data['travel'],
                    "Indirect": emp_data['indirect'],
                    "Cost Code": cost_code,
                }
                new_rows.append(new_row)
            
            success = save_to_session(new_rows)

            if success:
                st.success(f"Added {len(new_rows)} line(s) to Time Data.")
                # Clear form by incrementing counter (changes all widget keys)
                st.session_state.form_counter += 1
                st.rerun()
            else:
                st.error("Failed to save data. Please try again.")
                
        except Exception as e:
            st.error(f"Could not save to Time Data: {e}")

# --- Display current Time Data with proper date filtering ---
st.divider()
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("Current Time Data")
with col2:
    if st.button("🔄 Refresh Data", help="Clear cache and reload Time Data"):
        st.session_state['sheet_cache_token'] = st.session_state.get('sheet_cache_token', 0) + 1
        st.rerun()

try:
    selected_date_str = pd.to_datetime(date_val).strftime("%Y-%m-%d")
    filtered_data = get_time_data_from_session(selected_date_str)

    total_data = get_time_data_from_session(None)
    total_entries = len(total_data) if not total_data.empty else 0
    filtered_entries = len(filtered_data) if not filtered_data.empty else 0

    # Show helpful message when no data exists
    if total_entries == 0:
        available_sheets = get_available_worksheets(XLSX)
        if available_sheets and 'Time Data' not in available_sheets:
            st.error(f"'Time Data' worksheet not found! Available worksheets: {', '.join(available_sheets)}")
        elif total_entries == 0:
            st.info("Time Data worksheet is empty. Add some entries using the form above.")

    # Show message when no data exists for selected date but keep filtering strict
    if total_entries > 0 and filtered_entries == 0:
        st.info(f"No entries found for {date_val}. Only entries matching this date will be shown.")
        # Keep filtered_data empty - don't show all entries from other dates

    st.caption(f"Showing {filtered_entries} of {total_entries} total entries for {date_val}")

    if not filtered_data.empty:
        st.dataframe(filtered_data, use_container_width=True, hide_index=True)

        # Only show Delete Entries section to Admin users
        if user_type.upper() == "ADMIN":
            st.subheader("Delete Entries")

            delete_tabs = st.tabs(["Delete Multiple", "Delete All"])

            with delete_tabs[0]:
                individual_delete_options = [
                    f"Row {idx+1}: {row['Name']} - {row['Date']} - {row.get('Job Number', '')} ({row.get('RT Hours', 0)}RT/{row.get('OT Hours', 0)}OT)"
                    for idx, row in filtered_data.iterrows()
                ]

                selected_multiple_delete = st.multiselect(
                    f"Select multiple entries to delete (for {date_val}):",
                    individual_delete_options,
                    default=[],
                    placeholder="Choose multiple entries to delete..."
                )

                col1, col2 = st.columns([2, 1])
                with col2:
                    delete_multiple_button = st.button("Delete Selected Entries", type="secondary", key="delete_multiple")

                if delete_multiple_button and selected_multiple_delete:
                    with st.spinner("Deleting selected entries..."):
                        try:
                            indices_to_delete = []
                            for selected_item in selected_multiple_delete:
                                row_text = selected_item.split(":")[0]
                                display_row_number = int(row_text.split(" ")[1]) - 1

                                if 0 <= display_row_number < len(filtered_data):
                                    actual_index = filtered_data.iloc[display_row_number].name
                                    indices_to_delete.append(actual_index)

                            if indices_to_delete:
                                updated_data = total_data.drop(index=indices_to_delete).reset_index(drop=True)
                                synced = _replace_time_data_in_google(updated_data)
                                if not synced:
                                    st.warning("Deleted entries locally, but could not update Google Sheets.")

                                st.session_state.session_time_data = updated_data
                                st.success(f"Deleted {len(indices_to_delete)} selected entries from {date_val}.")
                                st.rerun()
                            else:
                                st.error("No valid entries selected for deletion.")

                        except (IndexError, ValueError) as e:
                            st.error(f"Could not parse row selections: {e}")
                        except Exception as e:
                            st.error(f"Could not delete entries: {e}")

            with delete_tabs[1]:
                st.warning(f"This will delete ALL {filtered_entries} entries for {date_val}")
                col1, col2 = st.columns([2, 1])
                with col2:
                    delete_all_button = st.button("Delete All Entries", type="secondary", key="delete_all")

                if delete_all_button:
                    with st.spinner("Deleting all entries..."):
                        try:
                            remaining_data = total_data[
                                pd.to_datetime(total_data["Date"]).dt.strftime("%Y-%m-%d") != selected_date_str
                            ].reset_index(drop=True) if not total_data.empty else pd.DataFrame()

                            synced = _replace_time_data_in_google(remaining_data)
                            if not synced:
                                st.warning("Deleted entries locally, but could not update Google Sheets.")

                            st.session_state.session_time_data = remaining_data
                            st.success(f"Deleted {filtered_entries} entries from {date_val}.")
                            st.rerun()

                        except Exception as e:
                            st.error(f"Could not delete entries: {e}")
        else:
            st.info("⚠️ Admin access required to delete entries.")
    else:
        st.info(f"No time data entries found for {date_val}")
        
except Exception as e:
    st.info(f"Time Data sheet not found or empty. Error: {e}")

# --- Export functionality - Admin only ---
if user_type.upper() == "ADMIN":
    st.divider()
    st.subheader("Export to Templates")

    try:
        time_data_for_export = smart_read_data("Time Data", force_refresh=True)
        if time_data_for_export.empty:
            time_data_for_export = safe_read_excel(XLSX, "Time Data")
        if not time_data_for_export.empty:

            def _prepare_employee_entries(entries):
                """Prepare employee entries for Daily Time export (don't combine, keep separate)"""
                if not entries:
                    return []

                prepared_entries = []
                for entry in entries:
                    prepared_entry = entry.copy()
                    prepared_entries.append(prepared_entry)

                return prepared_entries

            def _write_employee_to_daily_time(ws, emp_entries, row_num, employee_info, cost_code_descriptions):
                """Write employee data to specific row in Daily Time template"""
                if not emp_entries:
                    return 0

                emp_name = str(emp_entries[0].get('Name', ''))

                # Base employee info (columns A-D)
                emp_info = employee_info.get(emp_name, {})
                trade_class = str(emp_entries[0].get('Trade Class', '') or emp_info.get('override_trade_class', '') or '')
                ws.cell(row=row_num, column=1, value=emp_name)
                ws.cell(row=row_num, column=2, value=trade_class)

                rate_values = [
                    str(emp_info.get('premium_rate', '') or '').strip(),
                    str(emp_info.get('subsistence_rate', '') or '').strip(),
                    str(emp_info.get('travel_rate', '') or '').strip(),
                ]
                rate_value = next((val for val in rate_values if val), '')
                ws.cell(row=row_num, column=4, value=rate_value or None)

                # First entry goes in columns E-I
                if len(emp_entries) >= 1:
                    entry = emp_entries[0]
                    cost_code = str(entry.get('Cost Code', ''))
                    cost_desc = cost_code_descriptions.get(cost_code, '')

                    job_display = f"{entry.get('Job Number', '')} - {str(entry.get('Job Area', '')).zfill(3)} - {entry.get('Description of work', '')}"

                    ws.cell(row=row_num, column=5, value=cost_desc)  # E: Cost code description
                    ws.cell(row=row_num, column=6, value=cost_code)  # F: Cost code
                    ws.cell(row=row_num, column=7, value=job_display)  # G: Job Number - Area - Description
                    ws.cell(row=row_num, column=8, value=float(entry.get('RT Hours', 0) or 0))  # H: RT
                    ws.cell(row=row_num, column=9, value=float(entry.get('OT Hours', 0) or 0))   # I: OT

                # Second entry goes in columns K-O
                if len(emp_entries) >= 2:
                    entry = emp_entries[1]
                    cost_code = str(entry.get('Cost Code', ''))
                    cost_desc = cost_code_descriptions.get(cost_code, '')

                    job_display_2 = f"{entry.get('Job Number', '')} - {str(entry.get('Job Area', '')).zfill(3)} - {entry.get('Description of work', '')}"

                    ws.cell(row=row_num, column=11, value=cost_desc)  # K: Cost code description
                    ws.cell(row=row_num, column=12, value=cost_code)  # L: Cost code
                    ws.cell(row=row_num, column=13, value=job_display_2)  # M: Job Number - Area - Description
                    ws.cell(row=row_num, column=14, value=float(entry.get('RT Hours', 0) or 0))  # N: RT
                    ws.cell(row=row_num, column=15, value=float(entry.get('OT Hours', 0) or 0))   # O: OT

                # Return number of rows used (1 if 1-2 entries, more if 3+ entries)
                rows_used = 1
                if len(emp_entries) > 2:
                    # For 3+ entries, we need additional rows
                    additional_entries = emp_entries[2:]
                    current_extra_row = row_num + 1

                    for i, entry in enumerate(additional_entries):
                        if i % 2 == 0:  # First entry of new row (columns E-I)
                            cost_code = str(entry.get('Cost Code', ''))
                            cost_desc = cost_code_descriptions.get(cost_code, '')
                            job_display = f"{entry.get('Job Number', '')} - {str(entry.get('Job Area', '')).zfill(3)} - {entry.get('Description of work', '')}"

                            ws.cell(row=current_extra_row, column=1, value=emp_name)
                            ws.cell(row=current_extra_row, column=5, value=cost_desc)
                            ws.cell(row=current_extra_row, column=6, value=cost_code)
                            ws.cell(row=current_extra_row, column=7, value=job_display)
                            ws.cell(row=current_extra_row, column=8, value=float(entry.get('RT Hours', 0) or 0))
                            ws.cell(row=current_extra_row, column=9, value=float(entry.get('OT Hours', 0) or 0))

                        else:  # Second entry of row (columns K-O)
                            cost_code = str(entry.get('Cost Code', ''))
                            cost_desc = cost_code_descriptions.get(cost_code, '')
                            job_display = f"{entry.get('Job Number', '')} - {str(entry.get('Job Area', '')).zfill(3)} - {entry.get('Description of work', '')}"

                            ws.cell(row=current_extra_row, column=11, value=cost_desc)
                            ws.cell(row=current_extra_row, column=12, value=cost_code)
                            ws.cell(row=current_extra_row, column=13, value=job_display)
                            ws.cell(row=current_extra_row, column=14, value=float(entry.get('RT Hours', 0) or 0))
                            ws.cell(row=current_extra_row, column=15, value=float(entry.get('OT Hours', 0) or 0))
                            current_extra_row += 1

                        if i % 2 == 0 and i == len(additional_entries) - 1:
                            # If we have an odd number of additional entries, move to next row
                            current_extra_row += 1

                    rows_used = current_extra_row - row_num

                return rows_used

            def create_template_exports(export_date):
                """Create proper template-based exports using Daily Time.xlsx and TimeEntries.xlsx"""
                filtered_data = time_data_for_export[
                    pd.to_datetime(time_data_for_export['Date']).dt.date == export_date
                ].copy()

                if filtered_data.empty:
                    st.warning(f"No data found for {export_date}")
                    return None

                try:
                    zip_buffer = io.BytesIO()

                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    
                        daily_time_template = Path(__file__).resolve().parent.parent / "Daily Time.xlsx"
                        if daily_time_template.exists():
                            tmp_path = None
                            try:
                                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                                    tmp_path = tmp.name
                                    copyfile(daily_time_template, tmp_path)

                                wb = load_workbook(tmp_path)
                                ws = wb.active

                                for row_idx in range(1, 15):
                                    for col_idx in range(1, 15):
                                        cell = ws.cell(row=row_idx, column=col_idx)
                                        if cell.value and 'DATA DATE' in str(cell.value).upper():
                                            ws.cell(row=row_idx, column=col_idx + 1, value=export_date.strftime('%Y-%m-%d'))
                                            break

                                # Load employee data to determine indirect/direct status
                                employee_df = safe_read_excel(XLSX, "Employee List")
                                employee_info = {}
                                if not employee_df.empty:
                                    for _, emp_row in employee_df.iterrows():
                                        name = str(emp_row.get("Employee Name", ""))
                                        employee_info[name] = {
                                            'indirect': str(emp_row.get("Indirect / Direct", "")).strip().upper() == "INDIRECT",
                                            'override_trade_class': str(emp_row.get("Override Trade Class", "") or ""),
                                            'premium_rate': str(emp_row.get("Premium Rate", "") or ""),
                                            'subsistence_rate': str(emp_row.get("Subsistence Rate", "") or ""),
                                            'travel_rate': str(emp_row.get("Travel Rate", "") or "")
                                        }

                                # Load cost codes for descriptions
                                cost_codes_df = safe_read_excel(XLSX, "Cost Codes")
                                cost_code_descriptions = {}
                                if not cost_codes_df.empty:
                                    for _, cc_row in cost_codes_df.iterrows():
                                        code = str(cc_row.get("Cost Code", "") or "").strip()
                                        desc = str(cc_row.get("Description", "") or "").strip()
                                        if code:
                                            cost_code_descriptions[code] = desc

                                # Group data by employee and combine entries for same employee
                                employee_groups = {}
                                for _, row in filtered_data.iterrows():
                                    emp_name = str(row.get('Name', ''))
                                    if emp_name not in employee_groups:
                                        employee_groups[emp_name] = []
                                    employee_groups[emp_name].append(row)

                                # Separate indirect and direct employees
                                indirect_employees = []
                                direct_employees = []

                                for emp_name, entries in employee_groups.items():
                                    is_indirect = employee_info.get(emp_name, {}).get('indirect', False)
                                    prepared_entries = _prepare_employee_entries(entries)

                                    employee_data = {
                                        'name': emp_name,
                                        'entries': prepared_entries,
                                        'is_indirect': is_indirect
                                    }

                                    if is_indirect:
                                        indirect_employees.append(employee_data)
                                    else:
                                        direct_employees.append(employee_data)

                                # Place indirect employees in rows 8-30
                                current_row = 8
                                used_indirect_rows = []
                                for emp_data in indirect_employees:
                                    if current_row > 30:
                                        break
                                    rows_used = _write_employee_to_daily_time(ws, emp_data['entries'], current_row, employee_info, cost_code_descriptions)
                                    for i in range(rows_used):
                                        used_indirect_rows.append(current_row + i)
                                    current_row += rows_used

                                # Place direct employees in rows 32-261
                                current_row = 32
                                used_direct_rows = []
                                for emp_data in direct_employees:
                                    if current_row > 261:
                                        break
                                    rows_used = _write_employee_to_daily_time(ws, emp_data['entries'], current_row, employee_info, cost_code_descriptions)
                                    for i in range(rows_used):
                                        used_direct_rows.append(current_row + i)
                                    current_row += rows_used

                                # Hide unused rows
                                # Hide unused indirect rows (8-30)
                                for row_num in range(8, 31):
                                    if row_num not in used_indirect_rows:
                                        ws.row_dimensions[row_num].hidden = True

                                # Hide unused direct rows (32-261)
                                for row_num in range(32, 262):
                                    if row_num not in used_direct_rows:
                                        ws.row_dimensions[row_num].hidden = True

                                # Add job summaries starting at row 264
                                current_summary_row = 264

                                # Group data by job number, area, and description
                                job_groups = {}
                                for _, row in filtered_data.iterrows():
                                    job_num = str(row.get('Job Number', ''))
                                    job_area = str(row.get('Job Area', '')).zfill(3)
                                    job_desc = str(row.get('Description of work', ''))
                                    job_key = f"{job_num} - {job_area} - {job_desc}"

                                    if job_key not in job_groups:
                                        job_groups[job_key] = set()

                                    comment = str(row.get('Comments', '')).strip()
                                    if comment and comment.lower() not in ['nan', 'none', '']:
                                        job_groups[job_key].add(comment)

                                # Write job summaries (only if there are comments)
                                for job_key, comments in job_groups.items():
                                    if current_summary_row > 500:  # Avoid going too far down
                                        break

                                    # Only write if there are actual comments
                                    if comments:
                                        # Write job header (bold and underlined)
                                        cell = ws.cell(row=current_summary_row, column=1, value=job_key)
                                        cell.font = openpyxl.styles.Font(bold=True, underline='single')
                                        current_summary_row += 1

                                        # Write each unique comment
                                        for comment in sorted(comments):
                                            if current_summary_row > 500:
                                                break
                                            ws.cell(row=current_summary_row, column=1, value=comment)
                                            current_summary_row += 1

                                        # Add blank line between job groups
                                        current_summary_row += 1

                                wb.save(tmp_path)
                                wb.close()

                                with open(tmp_path, 'rb') as f:
                                    zip_file.writestr(f"{export_date.strftime('%m-%d-%Y')} - Daily Time.xlsx", f.read())

                            finally:
                                if tmp_path and os.path.exists(tmp_path):
                                    try:
                                        os.unlink(tmp_path)
                                    except Exception:
                                        pass
                        
                        timeentries_template = Path(__file__).resolve().parent.parent / "TimeEntries.xlsx"
                        if timeentries_template.exists():
                            # Load employee data for rates (if not already loaded)
                            if 'employee_info' not in locals():
                                employee_df = safe_read_excel(XLSX, "Employee List")
                                employee_info = {}
                                if not employee_df.empty:
                                    for _, emp_row in employee_df.iterrows():
                                        name = str(emp_row.get("Employee Name", ""))
                                        employee_info[name] = {
                                            'indirect': str(emp_row.get("Indirect / Direct", "")).strip().upper() == "INDIRECT",
                                            'subsistence': str(emp_row.get("Subsistence Rate", "") or "")
                                        }

                            unique_jobs = filtered_data['Job Number'].dropna().unique()

                            for job in unique_jobs:
                                if pd.isna(job) or str(job).strip() == '':
                                    continue
                                
                                job_data = filtered_data[filtered_data['Job Number'].astype(str).str.strip() == str(job).strip()].copy()
                                if job_data.empty:
                                    continue

                                tmp_path = None
                                try:
                                    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                                        tmp_path = tmp.name
                                        copyfile(timeentries_template, tmp_path)

                                    wb = load_workbook(tmp_path)
                                    ws = wb.active

                                    current_row = 4
                                    for _, row in job_data.iterrows():
                                        # Get employee data for rates
                                        emp_name = str(row.get('Name', ''))
                                        emp_info = employee_info.get(emp_name, {})

                                        # Helper function to clean values
                                        def clean_value(val):
                                            if pd.isna(val) or str(val).lower() in ['nan', 'none', '']:
                                                return ''
                                            return str(val)

                                        premium_rate = clean_value(row.get('Premium Rate', ''))
                                        subsistence_rate = clean_value(row.get('Subsistence Rate', '')) or clean_value(emp_info.get('subsistence', ''))
                                        travel_rate = clean_value(row.get('Travel Rate', ''))
                                        night_shift = clean_value(row.get('Night Shift', ''))

                                        base_data = [
                                            export_date.strftime('%Y-%m-%d'),  # A - Date
                                            '',                                 # B - Empty
                                            clean_value(row.get('Employee Number', '')),  # C - Employee Number
                                            clean_value(row.get('Name', '')),             # D - Name
                                            clean_value(row.get('Trade Class', '')),      # E - Trade Class
                                            'Y',                               # F - Always 'Y'
                                            clean_value(row.get('Cost Code', '')),        # G - Cost Code
                                            str(row.get('Job Area', '')).zfill(3),        # H - Job Area (3 digits)
                                            '',                                # I - Empty
                                            '211',                             # J - Pay Code (will be changed per entry)
                                            0.0,                               # K - Hours (will be set per entry)
                                            night_shift,                       # L - Night Shift
                                            premium_rate,                      # M - Premium Rate
                                            travel_rate,                       # N - Travel Rate
                                            ''                                 # O - Empty (no comments)
                                        ]

                                        rt_hours = float(row.get('RT Hours', 0) or 0)
                                        if rt_hours > 0:
                                            rt_data = base_data.copy()
                                            rt_data[9] = '211'  # Regular time pay code
                                            rt_data[10] = rt_hours

                                            for col, val in enumerate(rt_data, 1):
                                                ws.cell(row=current_row, column=col, value=val)
                                            current_row += 1

                                        ot_hours = float(row.get('OT Hours', 0) or 0)
                                        if ot_hours > 0:
                                            ot_data = base_data.copy()
                                            ot_data[9] = '212'  # Overtime pay code
                                            ot_data[10] = ot_hours

                                            for col, val in enumerate(ot_data, 1):
                                                ws.cell(row=current_row, column=col, value=val)
                                            current_row += 1

                                        # Add subsistence entry if employee has subsistence rate
                                        if subsistence_rate and subsistence_rate != '':
                                            try:
                                                subsistence_amount = float(subsistence_rate)
                                                if subsistence_amount > 0:
                                                    sub_data = base_data.copy()
                                                    sub_data[9] = '261'  # Subsistence pay code
                                                    sub_data[10] = 1.0   # Hours = 1 for subsistence
                                                    sub_data[12] = subsistence_rate  # Put subsistence rate in column M (Premium Rate column)

                                                    for col, val in enumerate(sub_data, 1):
                                                        ws.cell(row=current_row, column=col, value=val)
                                                    current_row += 1
                                            except (ValueError, TypeError):
                                                pass  # Skip if subsistence rate is not a valid number

                                    wb.save(tmp_path)
                                    wb.close()

                                    with open(tmp_path, 'rb') as f:
                                        zip_file.writestr(f"{export_date.strftime('%m-%d-%Y')} - {job} - Daily Import.xlsx", f.read())

                                finally:
                                    if tmp_path and os.path.exists(tmp_path):
                                        try:
                                            os.unlink(tmp_path)
                                        except Exception:
                                            pass
                    
                    zip_buffer.seek(0)
                    return zip_buffer.getvalue()
                    
                except Exception as e:
                    st.error(f"Error creating export: {e}")
                    return None

            if st.button("Create & Download Exports", type="primary"):
                with st.spinner("Creating export package..."):
                    zip_data = create_template_exports(date_val)
                    if zip_data:
                        st.download_button(
                            label="Download Export Package",
                            data=zip_data,
                            file_name=f"Timesheet_Export_{date_val.strftime('%m-%d-%Y')}.zip",
                            mime="application/zip",
                            key="download_exports"
                        )
                        st.success(f"Export package ready for download! Contains Daily Time and Daily Import files for {date_val}")
                    else:
                        st.error("Failed to create export package")

        else:
            st.info("No time data available for export. Add some entries first.")

    except Exception:
        st.info("No time data available for export. Add some entries first.")

else:
    st.divider()
    st.info("⚠️ Admin access required to export templates.")


