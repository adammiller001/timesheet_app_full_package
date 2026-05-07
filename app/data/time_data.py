from __future__ import annotations

from datetime import date, datetime
from typing import Optional
import re

import pandas as pd


TIME_DATA_COLUMNS = [
    "Job Number", "Job Area", "Date", "Name", "Trade Class",
    "Employee Number", "RT Hours", "OT Hours", "Description of work",
    "Comments", "Night Shift", "Premium Rate", "Subsistence Rate",
    "Travel Rate", "Indirect", "Cost Code", "Entered By"
]


def normalize_job_area_value(value, blank_value: str = "") -> str:
    if value is None:
        return blank_value
    try:
        if pd.isna(value):
            return blank_value
    except Exception:
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return blank_value
    match = re.search(r"\d+", text)
    if match:
        return match.group(0).zfill(3)
    return text


def normalize_sheet_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return ""
        return ("{0:.15g}".format(float(value))).rstrip(".0") if float(value).is_integer() else "{0:.15g}".format(float(value))
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def prepare_time_data_dataframe(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None or df.empty:
        df = pd.DataFrame(columns=TIME_DATA_COLUMNS)
    else:
        df = df.copy()
    for col in TIME_DATA_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    ordered_cols = TIME_DATA_COLUMNS + [col for col in df.columns if col not in TIME_DATA_COLUMNS]
    df = df[ordered_cols]
    if "Date" in df.columns and not df.empty:
        try:
            df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        except Exception:
            df["Date"] = df["Date"].astype(str)
    df_map = getattr(df, "map", None)
    df = df_map(normalize_sheet_value) if df_map else df.applymap(normalize_sheet_value)
    if "Job Area" in df.columns:
        df["Job Area"] = df["Job Area"].apply(normalize_job_area_value)
    return df


def filter_time_data_by_date(df: pd.DataFrame, date_filter=None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame(columns=TIME_DATA_COLUMNS)
    data = df.copy()
    if date_filter and "Date" in data.columns and not data.empty:
        selected_date = pd.to_datetime(date_filter).strftime("%Y-%m-%d")
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        data = data[data["Date"].dt.strftime("%Y-%m-%d") == selected_date]
    return data


def append_time_rows(existing_df: Optional[pd.DataFrame], new_rows_df: pd.DataFrame) -> pd.DataFrame:
    existing = prepare_time_data_dataframe(existing_df)
    new_rows = prepare_time_data_dataframe(new_rows_df)
    return prepare_time_data_dataframe(pd.concat([existing, new_rows], ignore_index=True))
