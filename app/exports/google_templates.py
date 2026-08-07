from __future__ import annotations

import io
from datetime import date, datetime
from typing import Iterable

import pandas as pd
import streamlit as st
from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.integrations.google_sheets import get_sheets_manager


def _normalize_name(value: object) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none"} else text


def _is_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = _clean_text(value).lower()
    if text in {"true", "yes", "y", "1", "active", "enabled"}:
        return True
    try:
        return float(text) == 1.0
    except Exception:
        return False


def _find_column(df: pd.DataFrame, candidates: Iterable[str], fallback_index: int | None = None) -> str | None:
    if df is None or df.empty:
        return None
    columns = [str(col).strip() for col in df.columns]
    exact = {col: col for col in columns}
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]
    normalized = {_normalize_name(col): col for col in columns}
    for candidate in candidates:
        match = normalized.get(_normalize_name(candidate))
        if match:
            return match
    if fallback_index is not None and len(columns) > fallback_index:
        return columns[fallback_index]
    return None


def get_google_template_workbook_bytes(spreadsheet_id: str | None = None) -> bytes:
    """Return an Excel export of the configured Google Sheets workbook."""
    sheet_id = str(spreadsheet_id or st.secrets.get("google_sheets_id", "")).strip()
    if not sheet_id:
        raise RuntimeError("Google Sheets ID is not configured.")
    return get_sheets_manager().export_spreadsheet_xlsx(sheet_id)


def load_template_sheet_workbook(template_bytes: bytes, sheet_candidates: Iterable[str]) -> tuple[Workbook, Worksheet]:
    """Load one worksheet from a Google-exported workbook and remove the other tabs."""
    wb = load_workbook(io.BytesIO(template_bytes))
    candidates = list(sheet_candidates)
    normalized_candidates = {_normalize_name(candidate) for candidate in candidates}

    selected_name = None
    sheet_lookup = {_normalize_name(name): name for name in wb.sheetnames}
    for normalized_candidate in normalized_candidates:
        if normalized_candidate in sheet_lookup:
            selected_name = sheet_lookup[normalized_candidate]
            break

    if selected_name is None:
        for name in wb.sheetnames:
            normalized_sheet = _normalize_name(name)
            if any(candidate and candidate in normalized_sheet for candidate in normalized_candidates):
                selected_name = name
                break

    if selected_name is None:
        wanted = ", ".join(candidates)
        found = ", ".join(wb.sheetnames)
        raise RuntimeError(f"Template worksheet not found. Wanted one of: {wanted}. Found: {found}")

    ws = wb[selected_name]
    wb.active = wb.index(ws)
    for sheet_name in list(wb.sheetnames):
        if sheet_name != selected_name:
            del wb[sheet_name]

    if ws.sheet_view:
        ws.sheet_view.topLeftCell = "A1"
        if ws.sheet_view.selection:
            ws.sheet_view.selection[0].activeCell = "A1"
            ws.sheet_view.selection[0].sqref = "A1"
    return wb, ws


def workbook_to_bytes(wb: Workbook) -> bytes:
    buffer = io.BytesIO()
    wb.save(buffer)
    wb.close()
    buffer.seek(0)
    return buffer.getvalue()


def build_sign_in_sheet_workbook(
    template_bytes: bytes,
    employees_df: pd.DataFrame,
    sign_in_date: date | datetime,
) -> tuple[bytes, int]:
    """Fill the Sign In Sheet tab from active Employee List rows."""
    wb, ws = load_template_sheet_workbook(template_bytes, ("Sign In Sheet", "SignInSheet"))

    if isinstance(sign_in_date, datetime):
        sign_in_value = sign_in_date.date()
    else:
        sign_in_value = sign_in_date
    ws["D6"] = sign_in_value

    if employees_df is None:
        employees_df = pd.DataFrame()
    employees_df = employees_df.copy()
    employees_df.columns = [str(col).strip() for col in employees_df.columns]

    company_col = _find_column(employees_df, ("Company Name", "Company", "Employer"), 11)
    name_col = _find_column(employees_df, ("Employee Name", "Name", "Employee"), 2)
    craft_col = _find_column(employees_df, ("Craft / Certification", "Craft Certification", "Craft", "Certification"), 12)
    active_col = _find_column(employees_df, ("Active", "Is Active", "Enabled"), 13)

    if active_col:
        employees_df = employees_df[employees_df[active_col].apply(_is_truthy)]

    for row_num in range(11, 75):
        ws.row_dimensions[row_num].hidden = False
        for col_num in range(1, 6):
            ws.cell(row=row_num, column=col_num, value=None)

    rows_written = 0
    for _, employee in employees_df.iterrows():
        if rows_written >= 64:
            break
        target_row = 11 + rows_written
        ws.cell(target_row, 1, _clean_text(employee.get(company_col, "")) if company_col else "")
        ws.cell(target_row, 2, _clean_text(employee.get(name_col, "")) if name_col else "")
        ws.cell(target_row, 3, _clean_text(employee.get(craft_col, "")) if craft_col else "")
        rows_written += 1

    first_hidden_row = 11 + rows_written + 5
    for row_num in range(max(first_hidden_row, 11), 75):
        ws.row_dimensions[row_num].hidden = True

    return workbook_to_bytes(wb), rows_written
