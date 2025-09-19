import os
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

def _clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    try:
        df.columns = [str(c).strip() for c in df.columns]
    except Exception:
        pass
    return df

def read_sheet(path: str, sheet: str, empty_cols=None) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name=sheet)
        return _clean_headers(df)
    except Exception:
        return pd.DataFrame(columns=empty_cols or [])

def get_employees(path: str) -> pd.DataFrame:
    df = read_sheet(path, "Employee List", ["Employee Name","Employee Number","Override Trade Class"])
    if not df.empty:
        df = df.rename(columns={
            "Employee Name":"name",
            "Employee Number":"emp_num",
            "Override Trade Class":"trade",
        })
    return df

def get_jobs(path: str) -> pd.DataFrame:
    df = read_sheet(path, "Job Numbers", ["JOB #","AREA #","DESCRIPTION"])
    if not df.empty:
        df = df.rename(columns={
            "JOB #":"job_num",
            "AREA #":"area_code",
            "DESCRIPTION":"area_desc",
        })
        df["area_code"] = df["area_code"].apply(pad_job_area)
    return df

def get_cost_codes(path: str) -> pd.DataFrame:
    df = read_sheet(path, "Cost Codes", ["Cost Code","Cost Code Description","Active"])
    if not df.empty:
        df = df.rename(columns={
            "Cost Code":"cost_code",
            "Cost Code Description":"cost_desc",
        })
    return df

def only_active_cost_codes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    cols = {c.lower(): c for c in df.columns}
    if "active" in cols:
        col = cols["active"]
        def truthy(x):
            if isinstance(x, bool): return x
            s = str(x).strip().lower()
            return s in {"true","t","yes","y","1","active","enabled"}
        return df[df[col].apply(truthy)]
    return df

def pad_job_area(v) -> str:
    s = str(v).strip()
    return f"{int(s):03d}" if s.isdigit() else s

def get_time_data(path: str) -> pd.DataFrame:
    return read_sheet(path, "Time Data", ["Job Number","Job Area","Date","Name","Class Type","Trade Class","Employee Number","RT Hours","OT Hours","Night Shift","Premium Rate / Subsistence Rate / Travel Rate","Comments"])

def _ensure_time_data_headers(xlsx_file: str):
    wb = load_workbook(xlsx_file)
    if "Time Data" not in wb.sheetnames:
        ws = wb.create_sheet("Time Data")
        ws.append(["Job Number","Job Area","Date","Name","Class Type","Trade Class","Employee Number",
                   "RT Hours","OT Hours","Night Shift","Premium Rate / Subsistence Rate / Travel Rate","Comments"])
        wb.save(xlsx_file); return
    ws = wb["Time Data"]
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    headers = [str(h).strip() if h is not None else "" for h in headers]
    needed=["RT Hours","OT Hours","Night Shift","Premium Rate / Subsistence Rate / Travel Rate","Comments"]
    changed=False
    for h in needed:
        if h not in headers:
            ws.cell(row=1, column=len(headers)+1, value=h); headers.append(h); changed=True
    if changed: wb.save(xlsx_file)

def append_time_row(xlsx_file: str, payload: dict) -> bool:
    try:
        _ensure_time_data_headers(xlsx_file)
        wb = load_workbook(xlsx_file)
        if "Time Data" not in wb.sheetnames:
            ws = wb.create_sheet("Time Data")
            ws.append(["Job Number","Job Area","Date","Name","Class Type","Trade Class","Employee Number",
                       "RT Hours","OT Hours","Night Shift","Premium Rate / Subsistence Rate / Travel Rate","Comments"])
        ws = wb["Time Data"]
        headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        headers = [str(h).strip() if h is not None else "" for h in headers]
        if not any(headers):
            headers = ["Job Number","Job Area","Date","Name","Class Type","Trade Class","Employee Number",
                       "RT Hours","OT Hours","Night Shift","Premium Rate / Subsistence Rate / Travel Rate","Comments"]
            for idx, h in enumerate(headers, start=1): ws.cell(row=1, column=idx, value=h)
        row_vals = [payload.get(h, "") for h in headers]
        ws.append(row_vals); wb.save(xlsx_file)
        return True
    except Exception:
        return False
