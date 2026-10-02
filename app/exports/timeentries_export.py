import io
import pandas as pd
from datetime import date
from copy import copy
from app.data.workbook import get_employees, get_time_data, pad_job_area
from app.exports.google_templates import get_google_template_workbook_bytes, load_template_sheet_workbook
from app.features.project_assignments import build_job_number_key
from app.utils.excel_style import clone_row_styles

EXPECTED_HEADERS = ['Date','Time Record Type','Person Number','Employee Name','Override Trade Class','Post To Payroll','Cost Code / Phase','JobArea','Scope Change','Pay Code','Hours','Night Shift','Premium Rate / Subsistence Rate / Travel Rate','Comments']
PAYCODE_MAP = {"REG":"211","OT":"212","SUBSISTENCE":"261"}


def _normalize_employee_key(name) -> str:
    return ''.join(ch for ch in str(name or '').upper() if ch.isalnum())


def _is_truthy_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().upper()
    if text in {"TRUE", "YES", "Y", "1", "ON"}:
        return True
    try:
        return float(text) == 1.0
    except Exception:
        return False


def _find_column(df: pd.DataFrame, candidates: tuple[str, ...] | list[str]):
    normalized_cols = {
        ''.join(ch for ch in str(col).strip().lower() if ch.isalnum()): col
        for col in df.columns
    }
    for candidate in candidates:
        match = normalized_cols.get(''.join(ch for ch in str(candidate).strip().lower() if ch.isalnum()))
        if match:
            return match
    return None


def filter_daily_import_rows(day_df: pd.DataFrame, employees_df: pd.DataFrame) -> pd.DataFrame:
    """Apply Daily Import preferences without dropping inactive historical entries."""
    if day_df is None or day_df.empty or employees_df is None or employees_df.empty:
        return day_df

    employees = employees_df.copy()
    employees.columns = [str(c).strip() for c in employees.columns]
    daily_import_col = _find_column(
        employees,
        ("Daily Import", "DailyImport", "Include Daily Import", "Include in Daily Import"),
    )
    if not daily_import_col:
        return day_df

    name_col = _find_column(employees, ("Employee Name", "Name", "Employee")) or (
        employees.columns[2] if len(employees.columns) > 2 else None
    )
    if not name_col:
        return day_df.iloc[0:0].copy()

    job_col = _find_column(employees, ("Job Number", "JOB #", "Job #", "Job"))
    number_col = _find_column(employees, ("Person Number", "Employee Number", "emp_num"))
    if "Name" not in day_df.columns:
        return day_df.iloc[0:0].copy()

    preferences = {}
    match_jobs = job_col is not None and "Job Number" in day_df.columns
    for _, row in employees.iterrows():
        job_key = build_job_number_key(row.get(job_col, "")) if match_jobs else ""
        included = _is_truthy_flag(row.get(daily_import_col, ""))
        name_key = _normalize_employee_key(row.get(name_col, ""))
        if name_key:
            preferences[("name", name_key, job_key)] = included
        number_key = build_job_number_key(row.get(number_col, "")) if number_col else ""
        if number_key:
            preferences[("number", number_key, job_key)] = included

    def include_entry(row):
        job_key = build_job_number_key(row.get("Job Number", "")) if match_jobs else ""
        number_key = build_job_number_key(row.get("Employee Number", ""))
        number_match = ("number", number_key, job_key)
        if number_key and number_match in preferences:
            return preferences[number_match]
        name_key = _normalize_employee_key(row.get("Name", ""))
        # A removed assignment must not silently erase saved time from an export.
        return preferences.get(("name", name_key, job_key), True)

    mask = day_df.apply(include_entry, axis=1)
    return day_df[mask].copy()


def _clean_rate_value(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none"} else text


def build_daily_import_rate_cells(
    night_shift,
    premium_rate="",
    subsistence_rate="",
    travel_rate="",
) -> tuple[str, str]:
    """Return column M values for RT/OT rows and the subsistence 261 row."""
    subsistence_rate_cell = _clean_rate_value(subsistence_rate)
    if _clean_rate_value(night_shift):
        return "NS", subsistence_rate_cell
    regular_rate_cell = _clean_rate_value(premium_rate) or _clean_rate_value(travel_rate)
    return regular_rate_cell, subsistence_rate_cell


def apply_daily_import_data_row_style(ws, row_num: int, template_row: int = 4, max_col: int = 15) -> None:
    """Apply the normal Daily Import data row style to a generated row."""
    if template_row in ws.row_dimensions:
        ws.row_dimensions[row_num].height = ws.row_dimensions[template_row].height

    for col_idx in range(1, max_col + 1):
        source = ws.cell(row=template_row, column=col_idx)
        target = ws.cell(row=row_num, column=col_idx)
        if source.has_style:
            target.font = copy(source.font)
            target.fill = copy(source.fill)
            target.border = copy(source.border)
            target.alignment = copy(source.alignment)
            target.protection = copy(source.protection)
            target.number_format = source.number_format


def _build_rows(sub: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in sub.iterrows():
        reg_h = float(r.get("RT Hours",0) or 0.0)
        ot_h  = float(r.get("OT Hours",0) or 0.0)
        base = {
            "Date": pd.to_datetime(r.get("Date","")).strftime("%Y-%m-%d"),
            "Time Record Type": "",
            "Person Number": r.get("Employee Number",""),
            "Employee Name": r.get("Name",""),
            "Override Trade Class": r.get("Trade Class",""),
            "Post To Payroll": "Y",
            "Cost Code / Phase": r.get("Class Type",""),
            "JobArea": pad_job_area(r.get("Job Area","")),
            "Scope Change": "",
            "Pay Code": "",
            "Hours": 0.0,
            "Night Shift": "",
            "Premium Rate / Subsistence Rate / Travel Rate": r.get("Premium Rate / Subsistence Rate / Travel Rate",""),
            "Comments": "",
        }
        if reg_h>0:
            t=base.copy(); t["Pay Code"]=PAYCODE_MAP.get("REG","211"); t["Hours"]=reg_h; rows.append(t)
        if ot_h>0:
            t=base.copy(); t["Pay Code"]=PAYCODE_MAP.get("OT","212");  t["Hours"]=ot_h; rows.append(t)
    return pd.DataFrame(rows, columns=EXPECTED_HEADERS)

def _find_template_sheet(wb):
    if "TimeEntries" in wb.sheetnames:
        return wb["TimeEntries"]
    for name in wb.sheetnames:
        if "timeentries" in name.lower():
            return wb[name]
    for name in wb.sheetnames:
        ws = wb[name]
        headers = [str(c.value).strip() if c.value is not None else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
        if headers[:len(EXPECTED_HEADERS)] == EXPECTED_HEADERS:
            return ws
    raise RuntimeError(f"Template workbook does not contain a compatible sheet. Found sheets: {wb.sheetnames}")

def _render_job(day_df: pd.DataFrame, job: str, template_bytes: bytes) -> bytes:
    subset = day_df[day_df["Job Number"].astype(str).str.strip() == str(job)].copy()
    out_df = _build_rows(subset)
    wb, _ = load_template_sheet_workbook(
        template_bytes,
        ("TimeEntries", "Time Entries"),
    )
    ws = _find_template_sheet(wb)
    headers = [str(c.value).strip() if c.value is not None else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
    max_col = len(headers)
    data_start = 2
    has_template_data_row = ws.max_row >= 2
    for ridx, row in enumerate(out_df.itertuples(index=False), start=data_start):
        if has_template_data_row and ridx != 2:
            clone_row_styles(ws, ws, 2, ridx, max_col)
        for c_idx, val in enumerate(row, start=1):
            ws.cell(row=ridx, column=c_idx, value=val)
    last_written = data_start + len(out_df) - 1
    if has_template_data_row and ws.max_row > last_written:
        for r in range(last_written+1, ws.max_row+1):
            for c in range(1, max_col+1):
                ws.cell(row=r, column=c, value=None)
    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    return buf.getvalue()

def per_job_exports(xlsx_path: str, export_date: date):
    td = get_time_data(xlsx_path)
    if td.empty or "Date" not in td.columns:
        return []
    dmask = td["Date"].astype(str).str[:10] == export_date.strftime("%Y-%m-%d")
    day_df = td[dmask].copy()
    if day_df.empty:
        return []
    day_df = filter_daily_import_rows(day_df, get_employees(xlsx_path))
    if day_df.empty:
        return []
    template_bytes = get_google_template_workbook_bytes()
    jobs_for_day = sorted(day_df["Job Number"].astype(str).str.strip().unique().tolist())
    for job in jobs_for_day:
        content = _render_job(day_df, job, template_bytes)
        file_name = f"{export_date.strftime('%m-%d-%Y')} - {job} - Daily Time Import.xlsx"
        yield file_name, content
