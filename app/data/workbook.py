import pandas as pd
import streamlit as st
from typing import List

from app.integrations.google_sheets import get_sheets_manager

TIME_DATA_HEADERS: List[str] = [
    "Job Number",
    "Job Area",
    "Date",
    "Name",
    "Class Type",
    "Trade Class",
    "Employee Number",
    "RT Hours",
    "OT Hours",
    "Night Shift",
    "Premium Rate / Subsistence Rate / Travel Rate",
    "Comments",
]


def _clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    try:
        df.columns = [str(c).strip() for c in df.columns]
    except Exception:
        pass
    return df


def _read_sheet(possible_names: List[str], force_refresh: bool = False) -> pd.DataFrame:
    sheet_id = st.secrets.get("google_sheets_id", "")
    if not sheet_id:
        st.error("Google Sheets ID is not configured in secrets.")
        return pd.DataFrame()

    manager = get_sheets_manager()
    if force_refresh:
        manager._data_cache.clear()  # type: ignore[attr-defined]

    worksheet, actual_title = manager.find_worksheet(possible_names, sheet_id)
    if not worksheet and not actual_title:
        return pd.DataFrame()

    try:
        df = manager.read_worksheet(actual_title or possible_names[0], sheet_id, force_refresh=force_refresh)
        return _clean_headers(df)
    except Exception:
        return pd.DataFrame()


def get_employees(_: str | None = None, force_refresh: bool = False) -> pd.DataFrame:
    df = _read_sheet(["Employee List", "Employees"], force_refresh=force_refresh)
    if not df.empty:
        df = df.rename(columns={
            "Employee Name": "name",
            "Employee Number": "emp_num",
            "Override Trade Class": "trade",
        })
    return df


def get_jobs(_: str | None = None, force_refresh: bool = False) -> pd.DataFrame:
    df = _read_sheet(["Job Numbers", "Jobs"], force_refresh=force_refresh)
    if not df.empty:
        df = df.rename(columns={
            "JOB #": "job_num",
            "AREA #": "area_code",
            "DESCRIPTION": "area_desc",
        })
        if "area_code" in df.columns:
            df["area_code"] = df["area_code"].apply(pad_job_area)
    return df


def get_cost_codes(_: str | None = None, force_refresh: bool = False) -> pd.DataFrame:
    df = _read_sheet(["Cost Codes", "CostCodes"], force_refresh=force_refresh)
    if not df.empty:
        df = df.rename(columns={
            "Cost Code": "cost_code",
            "Cost Code Description": "cost_desc",
        })
    return df


def only_active_cost_codes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    cols = {c.lower(): c for c in df.columns}
    if "active" in cols:
        col = cols["active"]

        def truthy(value):
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            return s in {"true", "t", "yes", "y", "1", "active", "enabled"}

        return df[df[col].apply(truthy)]
    return df


def pad_job_area(value) -> str:
    s = str(value).strip()
    return f"{int(s):03d}" if s.isdigit() else s


def get_time_data(_: str | None = None, force_refresh: bool = False) -> pd.DataFrame:
    df = _read_sheet(["Time Data", "TimeData"], force_refresh=force_refresh)
    if df.empty:
        return pd.DataFrame(columns=TIME_DATA_HEADERS)
    for missing in TIME_DATA_HEADERS:
        if missing not in df.columns:
            df[missing] = ""
    return df[TIME_DATA_HEADERS + [c for c in df.columns if c not in TIME_DATA_HEADERS]]


def append_time_row(_: str, payload: dict) -> bool:
    sheet_id = st.secrets.get("google_sheets_id", "")
    if not sheet_id:
        st.error("Google Sheets ID is not configured in secrets.")
        return False
    manager = get_sheets_manager()
    row = [payload.get(col, "") for col in TIME_DATA_HEADERS]
    success = manager.append_rows("Time Data", [row], sheet_id)
    if success and hasattr(manager, "_data_cache"):
        manager._data_cache.pop("Time Data", None)  # type: ignore[attr-defined]
    return bool(success)
