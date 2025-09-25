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

XLSX = Path(__file__).resolve().parent.parent / "TimeSheet Apps.xlsx"

@st.cache_data(ttl=10, show_spinner=False)
def safe_read_excel_cached(file_path, sheet_name, _file_mtime=None):
    """Cached version of safe_read_excel with shorter TTL for performance"""
    return _safe_read_excel_internal(file_path, sheet_name)

def _safe_read_excel_internal(file_path, sheet_name):
    """Internal function that does the actual Excel reading"""
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
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

def safe_read_excel(file_path, sheet_name):
    """Safely read Excel file with caching based on file modification time"""
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return pd.DataFrame()
        mtime = file_path.stat().st_mtime
        return safe_read_excel_cached(str(file_path), sheet_name, _file_mtime=mtime)
    except Exception as e:
        st.error(f"Error accessing Excel file: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=10, show_spinner=False)
def get_time_data_cached(_file_path, _date_filter=None):
    """Cached time data retrieval with optional date filtering"""
    try:
        data = pd.read_excel(_file_path, sheet_name="Time Data")
        if _date_filter and "Date" in data.columns:
            data["Date"] = pd.to_datetime(data["Date"])
            data = data[data["Date"].dt.strftime("%Y-%m-%d") == _date_filter]
        return data
    except Exception:
        return pd.DataFrame()

def save_to_excel_optimized(new_rows):
    """Optimized Excel saving with better error handling and performance"""
    try:
        existing_data = pd.DataFrame()
        try:
            existing_data = pd.read_excel(XLSX, sheet_name="Time Data")
        except Exception:
            pass
        
        new_data_df = pd.DataFrame(new_rows)
        if not existing_data.empty:
            final_data = pd.concat([existing_data, new_data_df], ignore_index=True)
        else:
            final_data = new_data_df
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                with pd.ExcelWriter(XLSX, mode='a', if_sheet_exists='replace', engine='openpyxl') as writer:
                    final_data.to_excel(writer, sheet_name='Time Data', index=False)
                return True
            except PermissionError:
                if attempt < max_attempts - 1:
                    st.warning(f"Excel file is locked. Retrying... (attempt {attempt + 1})")
                    sleep(1)
                    continue
                else:
                    try:
                        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                            final_data.to_excel(tmp.name, sheet_name='Time Data', index=False)
                        sleep(0.5)
                        import shutil
                        shutil.move(tmp.name, XLSX)
                        return True
                    except Exception as e:
                        st.error(f"Could not save even with temp file method: {e}")
                        return False
            except Exception as e:
                st.error(f"Unexpected error saving to Excel: {e}")
                return False
    except Exception as e:
        st.error(f"Error in save_to_excel_optimized: {e}")
        return False

st.markdown("### Timesheet Entry")

# --- Date ---
date_val = st.date_input("Date", value=pd.Timestamp.today().date(), format="YYYY/MM/DD", key="date_val")

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
        _df = safe_read_excel(XLSX, "Job Numbers")
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
    key="job_choice"
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
        _c = safe_read_excel(XLSX, "Cost Codes")
        _c.columns = [str(c).strip() for c in _c.columns]
        code_c = _find_col(_c, ["Cost Code", "Code"])
        desc_c = _find_col(_c, ["Description", "DESC", "Name"])
        active_c = _find_col(_c, ["Active", "ACTIVE"])
        
        if active_c:
            _c = _c[_c[active_c].astype(str).str.upper().isin(["TRUE", "YES", "Y", "1"])]
        
        if code_c:
            if desc_c:
                cost_options = sorted([f"{str(r[code_c]).strip()} - {str(r[desc_c]).strip()}" 
                                     for _, r in _c.iterrows() if str(r[code_c]).strip()])
            else:
                cost_options = sorted([str(r[code_c]).strip() 
                                     for _, r in _c.iterrows() if str(r[code_c]).strip()])
        else:
            cost_options = []
    except Exception:
        cost_options = []

cost_choice = st.selectbox(
    "Cost Code - Description",
    cost_options,
    index=None,
    placeholder="Select a cost code...",
    key="cost_choice"
)

st.divider()

# --- Employees (simple multiselect dropdown only) ---
try:
    _emp_df = safe_read_excel(XLSX, "Employee List")
    _emp_df.columns = [str(c).strip() for c in _emp_df.columns]

    if "Active" in _emp_df.columns:
        _emp_df = _emp_df[_emp_df["Active"].astype(str).str.upper().isin(["TRUE", "YES", "Y", "1"])]

    EMP_NAME_COL = _find_col(_emp_df, ["Employee Name", "Name"])
    if not EMP_NAME_COL:
        EMP_NAME_COL = "Employee Name"
        if EMP_NAME_COL not in _emp_df.columns:
            _emp_df[EMP_NAME_COL] = ""

    _employee_options = sorted(_emp_df[EMP_NAME_COL].dropna().astype(str).unique().tolist())
except Exception:
    _emp_df = pd.DataFrame()
    _employee_options = []
    EMP_NAME_COL = "Employee Name"

selected_employees = st.multiselect(
    "Employees",
    options=_employee_options,
    default=[],
    placeholder="Select one or more employees...",
    key="selected_employees"
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
    rt_hours = st.number_input("RT Hours", min_value=0.00, step=0.25, format="%.2f", value=0.00, key="rt_hours")
with cols[1]:
    ot_hours = st.number_input("OT Hours", min_value=0.00, step=0.25, format="%.2f", value=0.00, key="ot_hours")
with cols[2]:
    st.write("")

comments = st.text_input("Comments", value="", key="comments")

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
            
            success = save_to_excel_optimized(new_rows)
            
            if success:
                st.success(f"Added {len(new_rows)} line(s) to Time Data sheet.")
                safe_read_excel_cached.clear()
                get_time_data_cached.clear()

                # Clear form fields after successful submission
                st.session_state.selected_employees = []
                st.session_state.job_choice = None
                st.session_state.cost_choice = None
                st.session_state.rt_hours = 0.0
                st.session_state.ot_hours = 0.0
                st.session_state.comments = ""

                st.rerun()
            else:
                st.error("Failed to save data. Please try again.")
                
        except Exception as e:
            st.error(f"Could not save to Time Data: {e}")

# --- Display current Time Data with proper date filtering ---
st.divider()
st.subheader("Current Time Data")

try:
    selected_date_str = pd.to_datetime(date_val).strftime("%Y-%m-%d")
    filtered_data = get_time_data_cached(str(XLSX), selected_date_str)
    
    total_data = get_time_data_cached(str(XLSX), None)
    total_entries = len(total_data) if not total_data.empty else 0
    filtered_entries = len(filtered_data) if not filtered_data.empty else 0
    
    st.caption(f"Showing {filtered_entries} of {total_entries} total entries for {date_val}")
    
    if not filtered_data.empty:
        st.dataframe(filtered_data, use_container_width=True, hide_index=True)
        
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

                            try:
                                with pd.ExcelWriter(XLSX, mode='a', if_sheet_exists='replace', engine='openpyxl') as writer:
                                    updated_data.to_excel(writer, sheet_name='Time Data', index=False)

                                safe_read_excel_cached.clear()
                                get_time_data_cached.clear()
                                st.success(f"Deleted {len(indices_to_delete)} selected entries from {date_val}.")
                                st.rerun()

                            except Exception as e:
                                st.error(f"Could not delete entries: {e}")
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

                        try:
                            with pd.ExcelWriter(XLSX, mode='a', if_sheet_exists='replace', engine='openpyxl') as writer:
                                if not remaining_data.empty:
                                    remaining_data.to_excel(writer, sheet_name='Time Data', index=False)
                                else:
                                    headers = [
                                        "Job Number", "Job Area", "Date", "Name", "Trade Class",
                                        "Employee Number", "RT Hours", "OT Hours", "Description of work",
                                        "Comments", "Night Shift", "Premium Rate", "Subsistence Rate",
                                        "Travel Rate", "Indirect", "Cost Code"
                                    ]
                                    empty_df = pd.DataFrame(columns=headers)
                                    empty_df.to_excel(writer, sheet_name='Time Data', index=False)

                            safe_read_excel_cached.clear()
                            get_time_data_cached.clear()
                            st.success(f"Deleted {filtered_entries} entries from {date_val}.")
                            st.rerun()

                        except Exception as e:
                            st.error(f"Could not delete entries: {e}")

                    except Exception as e:
                        st.error(f"Could not delete entries: {e}")
    else:
        st.info(f"No time data entries found for {date_val}")
        
except Exception as e:
    st.info(f"Time Data sheet not found or empty. Error: {e}")

# --- Export functionality ---
st.divider()
st.subheader("Export to Templates")

try:
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
            ws.cell(row=row_num, column=1, value=emp_name)
            ws.cell(row=row_num, column=2, value=str(emp_entries[0].get('Trade Class', '')))

            # Column D: Employee rates indicator (if employee has any rates)
            emp_info = employee_info.get(emp_name, {})
            if emp_info.get('has_rates', False):
                ws.cell(row=row_num, column=4, value='*')

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
                                    # Check if employee has any rates (G, H, I columns)
                                    has_rates = any([
                                        str(emp_row.get("Premium Rate", "") or "").strip(),
                                        str(emp_row.get("Subsistence Rate", "") or "").strip(),
                                        str(emp_row.get("Travel Rate", "") or "").strip()
                                    ])
                                    employee_info[name] = {
                                        'indirect': str(emp_row.get("Indirect / Direct", "")).strip().upper() == "INDIRECT",
                                        'subsistence': str(emp_row.get("Subsistence Rate", "") or ""),
                                        'has_rates': has_rates
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