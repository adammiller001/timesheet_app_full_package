import io
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from app.style_utils import apply_watermark

try:
    from app.integrations.google_sheets import get_sheets_manager

    HAVE_GOOGLE_SHEETS = True
except Exception:
    get_sheets_manager = None
    HAVE_GOOGLE_SHEETS = False


st.set_page_config(page_title="Admin", layout="wide")
apply_watermark()

EMAIL_COLUMN_CANDIDATES = [
    "Email",
    "User Email",
    "Email Address",
    "Login Email",
    "User's Email Address",
    "E-mail",
]
ROLE_COLUMN_CANDIDATES = ["User Type", "UserType", "Role", "Access Level", "Type", "Status"]
ACTIVE_COLUMN_CANDIDATES = ["Active", "Is Active", "Enabled"]

CORE_SHEETS = [
    ("Users", ("Users", "User")),
    ("Employee List", ("Employee List", "Employees")),
    ("Job Numbers", ("Job Numbers", "Jobs")),
    ("Cost Codes", ("Cost Codes", "CostCodes")),
    ("Time Data", ("Time Data", "TimeData")),
]

CONSTRUCTION_SHEETS = [
    "Cable",
    "Glands",
    "Terminations",
    "Tray",
    "Equipment",
    "Junction Boxes",
    "Instruments",
    "Tubing",
    "EHT",
    "EHT RTDs",
]


def _find_column(columns, candidates):
    normalized = {str(col).strip().lower(): col for col in columns}
    for candidate in candidates:
        actual = normalized.get(str(candidate).strip().lower())
        if actual:
            return actual
    return None


def _is_truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    if not text:
        return False
    if text in {"true", "yes", "y", "1", "active", "enabled"}:
        return True
    try:
        return float(text) == 1.0
    except Exception:
        return False


def _normalize_for_sheet(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    cleaned = df.copy()
    cleaned.columns = [str(col).strip() for col in cleaned.columns]
    cleaned = cleaned[[col for col in cleaned.columns if col]]
    cleaned = cleaned.where(pd.notnull(cleaned), "")

    for col in cleaned.columns:
        cleaned[col] = cleaned[col].map(_normalize_value)

    if not cleaned.empty:
        non_empty_mask = cleaned.apply(
            lambda row: any(str(value).strip() for value in row.tolist()),
            axis=1,
        )
        cleaned = cleaned[non_empty_mask].reset_index(drop=True)

    return cleaned


def _normalize_value(value):
    if value is None:
        return ""
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return value


def _get_sheet_id() -> str:
    return str(st.secrets.get("google_sheets_id", "")).strip() if "google_sheets_id" in st.secrets else ""


def _get_manager():
    if not HAVE_GOOGLE_SHEETS or get_sheets_manager is None:
        return None
    return get_sheets_manager()


def _find_worksheet(candidates):
    sheet_id = _get_sheet_id()
    manager = _get_manager()
    if not sheet_id or manager is None:
        return None, None
    return manager.find_worksheet(candidates, sheet_id)


def _read_sheet(candidates, force_refresh=False) -> tuple[pd.DataFrame, str, Optional[str]]:
    sheet_id = _get_sheet_id()
    manager = _get_manager()
    if not sheet_id:
        return pd.DataFrame(), "", "Google Sheets ID is not configured."
    if manager is None:
        return pd.DataFrame(), "", "Google Sheets integration is not available."

    try:
        _, actual_title = manager.find_worksheet(candidates, sheet_id)
        if not actual_title:
            return pd.DataFrame(), "", f"Worksheet not found: {', '.join(candidates)}"
        df = manager.read_worksheet(actual_title, sheet_id, force_refresh=force_refresh)
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        df = df.copy()
        df.columns = [str(col).strip() for col in df.columns]
        return df, actual_title, None
    except Exception as exc:
        return pd.DataFrame(), "", f"Failed to read worksheet: {exc}"


def _write_sheet(sheet_name: str, df: pd.DataFrame) -> bool:
    sheet_id = _get_sheet_id()
    manager = _get_manager()
    if not sheet_id:
        st.error("Google Sheets ID is not configured.")
        return False
    if manager is None:
        st.error("Google Sheets integration is not available.")
        return False
    return bool(manager.write_worksheet(sheet_name, _normalize_for_sheet(df), sheet_id))


def _list_worksheet_titles() -> list[str]:
    sheet_id = _get_sheet_id()
    manager = _get_manager()
    if not sheet_id or manager is None:
        return []

    try:
        worksheets = []
        if hasattr(manager, "_list_worksheets_http"):
            worksheets = manager._list_worksheets_http(sheet_id)  # type: ignore[attr-defined]
        if hasattr(manager, "spreadsheet") and manager.spreadsheet:
            worksheets = manager.spreadsheet.worksheets()
        titles = []
        for worksheet in worksheets:
            if isinstance(worksheet, str):
                titles.append(worksheet)
            elif isinstance(worksheet, dict):
                title = worksheet.get("title")
                if title:
                    titles.append(str(title))
            else:
                title = getattr(worksheet, "title", "")
                if title:
                    titles.append(str(title))
        return sorted(set(titles))
    except Exception:
        return []


def _current_user_is_sheet_admin() -> tuple[bool, Optional[str]]:
    email = str(st.session_state.get("user_email", "")).strip().lower()
    if not email:
        return False, "No signed-in user email is available."

    users_df, actual_title, error = _read_sheet(("Users", "User"), force_refresh=True)
    if error:
        return False, error
    if users_df.empty:
        return False, f"Worksheet '{actual_title}' is empty."

    email_col = _find_column(users_df.columns, EMAIL_COLUMN_CANDIDATES)
    if email_col is None and len(users_df.columns) > 0:
        email_col = users_df.columns[0]
    if email_col is None:
        return False, "Could not identify the email column in Users."

    matches = users_df[users_df[email_col].astype(str).str.strip().str.lower() == email]
    if matches.empty:
        return False, "Your email was not found in the Users worksheet."

    active_col = _find_column(users_df.columns, ACTIVE_COLUMN_CANDIDATES)
    if active_col and active_col in users_df.columns:
        if not _is_truthy(matches.iloc[0].get(active_col)):
            return False, "Your user row is not marked active."

    role_col = _find_column(users_df.columns, ROLE_COLUMN_CANDIDATES)
    if role_col is None and len(users_df.columns) >= 4:
        role_col = users_df.columns[3]
    if role_col is None:
        return False, "Could not identify the role column in Users."

    role_value = str(matches.iloc[0].get(role_col, "")).strip()
    if "admin" not in role_value.lower():
        return False, "Your Users row does not have Admin in the role column."
    return True, None


def _csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def _render_sheet_editor(label: str, candidates, key_prefix: str):
    force_key = f"{key_prefix}_force_refresh"
    if st.button("Refresh from Google", key=f"{key_prefix}_refresh"):
        st.session_state[force_key] = True

    force_refresh = bool(st.session_state.pop(force_key, False))
    df, actual_title, error = _read_sheet(candidates, force_refresh=force_refresh)
    if error:
        st.error(error)
        return

    st.caption(f"Editing Google worksheet: {actual_title}")
    st.download_button(
        "Download CSV backup",
        data=_csv_bytes(df),
        file_name=f"{actual_title.replace(' ', '_')}_backup.csv",
        mime="text/csv",
        key=f"{key_prefix}_backup",
    )

    edited_df = st.data_editor(
        df,
        key=f"{key_prefix}_editor",
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        height=560,
    )

    save_col, note_col = st.columns([1, 4])
    with save_col:
        save_clicked = st.button("Save changes", type="primary", key=f"{key_prefix}_save")
    with note_col:
        st.caption("Saving rewrites this worksheet's values in Google Sheets.")

    if save_clicked:
        if _write_sheet(actual_title, edited_df):
            st.success(f"Saved {label} to Google Sheets.")
            manager = _get_manager()
            if manager is not None and hasattr(manager, "_data_cache"):
                manager._data_cache.pop(actual_title, None)  # type: ignore[attr-defined]
            if actual_title.lower() in {"users", "user"}:
                st.session_state["user_type"] = "Admin"
            st.rerun()
        else:
            st.error(f"Could not save {label}.")


if not st.session_state.get("authenticated", False):
    for login_page in ("streamlit_app.py", "Home.py"):
        try:
            st.switch_page(login_page)
        except Exception:
            pass
    st.warning("Please sign in on the Home page first.")
    st.stop()

user = st.session_state.get("user_email")
st.sidebar.info(f"Signed in as: {user}")

is_admin, admin_error = _current_user_is_sheet_admin()
if not is_admin:
    st.error("Access denied: Admin access required for this page.")
    if admin_error:
        st.info(admin_error)
    st.stop()

st.title("Admin")
st.caption("Manage the Google Sheet data through the app. The workbook remains the hidden shared data store.")

if not _get_sheet_id():
    st.error("Google Sheets ID is not configured.")
    st.stop()

core_tab, construction_tab, raw_tab = st.tabs(["Core Data", "Construction Data", "All Worksheets"])

with core_tab:
    selected_label = st.selectbox(
        "Worksheet",
        [label for label, _ in CORE_SHEETS],
        key="admin_core_sheet_select",
    )
    selected_candidates = next(candidates for label, candidates in CORE_SHEETS if label == selected_label)
    _render_sheet_editor(selected_label, selected_candidates, f"core_{selected_label.lower().replace(' ', '_')}")

with construction_tab:
    category = st.selectbox(
        "Construction worksheet",
        CONSTRUCTION_SHEETS,
        key="admin_construction_sheet_select",
    )
    _render_sheet_editor(category, (category,), f"construction_{category.lower().replace(' ', '_')}")

with raw_tab:
    titles = _list_worksheet_titles()
    if not titles:
        st.warning("No worksheet list is available. Use the Core Data or Construction Data tabs instead.")
    else:
        raw_title = st.selectbox("Worksheet", titles, key="admin_raw_sheet_select")
        _render_sheet_editor(raw_title, (raw_title,), f"raw_{raw_title.lower().replace(' ', '_')}")
