from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import streamlit as st

try:
    from app.integrations.google_sheets import get_sheets_manager

    HAVE_GOOGLE_SHEETS = True
except Exception:  # pragma: no cover - optional dependency/runtime config
    get_sheets_manager = None
    HAVE_GOOGLE_SHEETS = False


EMAIL_COLUMN_CANDIDATES = [
    "Email",
    "User Email",
    "Email Address",
    "Login Email",
    "User's Email Address",
    "E-mail",
]
TYPE_COLUMN_CANDIDATES = ["User Type", "UserType", "Role", "Access Level", "Type"]
ACTIVE_COLUMN_CANDIDATES = ["Active", "Is Active", "Enabled", "Status"]
PIN_COLUMN_CANDIDATES = ["User's Pin", "Users Pin", "User Pin", "PIN", "Pin"]
REMEMBER_TOKEN_COLUMN = "Remember Token"
REMEMBER_TOKEN_CANDIDATES = [REMEMBER_TOKEN_COLUMN, "Login Token", "Device Token"]


@dataclass
class AuthResult:
    ok: bool
    user_type: str = "User"
    error: Optional[str] = None
    needs_pin_setup: bool = False


def _norm(value) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _find_column(columns, candidates) -> Optional[str]:
    exact = {str(col).strip().lower(): col for col in columns}
    for candidate in candidates:
        match = exact.get(str(candidate).strip().lower())
        if match:
            return match

    normalized = {_norm(col): col for col in columns}
    for candidate in candidates:
        match = normalized.get(_norm(candidate))
        if match:
            return match
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


def _clean(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none"} else text


def _pin_is_valid(pin: str) -> bool:
    return len(str(pin)) == 4 and str(pin).isdigit()


def _sheet_id() -> str:
    return str(st.secrets.get("google_sheets_id", "")).strip() if "google_sheets_id" in st.secrets else ""


def _get_users_sheet(force_refresh=False) -> tuple[pd.DataFrame, str, Optional[str]]:
    sheet_id = _sheet_id()
    if not (HAVE_GOOGLE_SHEETS and get_sheets_manager and sheet_id):
        return pd.DataFrame(), "", "Google Sheets integration is not configured."

    manager = get_sheets_manager()
    if force_refresh and hasattr(manager, "_data_cache"):
        manager._data_cache.pop("Users", None)  # type: ignore[attr-defined]
        manager._data_cache.pop("User", None)  # type: ignore[attr-defined]

    worksheet, actual_title = manager.find_worksheet(["Users", "User"], sheet_id)
    if not actual_title:
        return pd.DataFrame(), "", "Users worksheet not found in Google Sheets."

    try:
        df = manager.read_worksheet(actual_title, sheet_id, force_refresh=force_refresh)
    except Exception as exc:
        return pd.DataFrame(), actual_title, f"Google Sheets error: {exc}"

    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(), actual_title, f"Google Sheets worksheet '{actual_title}' is empty."

    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df, actual_title, None


def _write_users_sheet(df: pd.DataFrame, actual_title: str) -> bool:
    sheet_id = _sheet_id()
    if not (HAVE_GOOGLE_SHEETS and get_sheets_manager and sheet_id):
        st.error("Google Sheets integration is not configured.")
        return False
    manager = get_sheets_manager()
    ok = bool(manager.write_worksheet(actual_title, df, sheet_id, value_input_option="RAW"))
    if ok and hasattr(manager, "_data_cache"):
        manager._data_cache.pop(actual_title, None)  # type: ignore[attr-defined]
        manager._data_cache.pop("Users", None)  # type: ignore[attr-defined]
        manager._data_cache.pop("User", None)  # type: ignore[attr-defined]
    return ok


def _active_users(df: pd.DataFrame) -> pd.DataFrame:
    active_col = _find_column(df.columns, ACTIVE_COLUMN_CANDIDATES)
    if active_col and active_col in df.columns:
        return df[df[active_col].apply(_is_truthy)].copy()
    return df.copy()


def _find_user_row(df: pd.DataFrame, email: str):
    email_col = _find_column(df.columns, EMAIL_COLUMN_CANDIDATES)
    if not email_col:
        return None, None, f"Email column not found. Available columns: {list(df.columns)}"
    matches = df[df[email_col].astype(str).str.strip().str.lower() == str(email).strip().lower()]
    if matches.empty:
        return None, email_col, "Email not found in users list"
    return matches.index[0], email_col, None


def _get_user_type(df: pd.DataFrame, row_index) -> str:
    role_col = _find_column(df.columns, TYPE_COLUMN_CANDIDATES)
    if role_col is None and len(df.columns) >= 4:
        role_col = df.columns[3]
    raw_user_type = df.at[row_index, role_col] if role_col in df.columns else "User"
    user_type_clean = _clean(raw_user_type)
    user_type_upper = user_type_clean.upper()
    if "ADMIN" in user_type_upper:
        return "Admin"
    if user_type_upper in {"USER", "STANDARD", "EMPLOYEE"}:
        return "User"
    return user_type_clean or "User"


def _validate_user_base(email: str, force_refresh=False) -> tuple[pd.DataFrame, str, object, Optional[str], str]:
    df, actual_title, error = _get_users_sheet(force_refresh=force_refresh)
    if error:
        return df, actual_title, None, error, "User"

    active_df = _active_users(df)
    if active_df.empty:
        return df, actual_title, None, "No active users found in Users worksheet.", "User"

    row_index, _, row_error = _find_user_row(active_df, email)
    if row_error:
        return df, actual_title, None, row_error, "User"

    full_row_index, _, full_row_error = _find_user_row(df, email)
    if full_row_error:
        return df, actual_title, None, full_row_error, "User"

    return df, actual_title, full_row_index, None, _get_user_type(df, full_row_index)


def get_login_status(email: str, force_refresh=False) -> AuthResult:
    if not str(email or "").strip():
        return AuthResult(False, error="Please enter your email address")

    df, _, row_index, error, user_type = _validate_user_base(email, force_refresh=force_refresh)
    if error:
        if "not configured" in error.lower():
            return AuthResult(True, "Admin")
        return AuthResult(False, error=error)

    pin_col = _find_column(df.columns, PIN_COLUMN_CANDIDATES)
    if not pin_col:
        return AuthResult(True, user_type=user_type, needs_pin_setup=True)
    return AuthResult(True, user_type=user_type, needs_pin_setup=not bool(_clean(df.at[row_index, pin_col])))


def authenticate_user(email: str, pin: str, force_refresh=False) -> AuthResult:
    df, _, row_index, error, user_type = _validate_user_base(email, force_refresh=force_refresh)
    if error:
        if "not configured" in error.lower():
            return AuthResult(True, "Admin")
        return AuthResult(False, error=error)

    pin_col = _find_column(df.columns, PIN_COLUMN_CANDIDATES)
    saved_pin = _clean(df.at[row_index, pin_col]) if pin_col else ""
    if not saved_pin:
        return AuthResult(False, user_type=user_type, needs_pin_setup=True)
    if not _pin_is_valid(str(pin)):
        return AuthResult(False, user_type=user_type, error="Enter your 4-digit PIN.")
    if str(pin) != saved_pin:
        return AuthResult(False, user_type=user_type, error="Incorrect PIN.")
    return AuthResult(True, user_type=user_type)


def create_user_pin(email: str, pin: str, confirm_pin: str, force_refresh=True) -> AuthResult:
    if not _pin_is_valid(str(pin)):
        return AuthResult(False, error="PIN must be exactly 4 digits.")
    if str(pin) != str(confirm_pin):
        return AuthResult(False, error="PIN entries do not match.")

    df, actual_title, row_index, error, user_type = _validate_user_base(email, force_refresh=force_refresh)
    if error:
        return AuthResult(False, error=error)

    pin_col = _find_column(df.columns, PIN_COLUMN_CANDIDATES)
    if not pin_col:
        pin_col = "User's Pin"
        df[pin_col] = ""

    if _clean(df.at[row_index, pin_col]):
        return AuthResult(False, user_type=user_type, error="A PIN already exists for this user. Please sign in with that PIN.")

    df.at[row_index, pin_col] = str(pin)
    if not _write_users_sheet(df, actual_title):
        return AuthResult(False, user_type=user_type, error="Could not save PIN to the Users worksheet.")
    return AuthResult(True, user_type=user_type)


def add_remember_token(email: str, force_refresh=True) -> Optional[str]:
    df, actual_title, row_index, error, _ = _validate_user_base(email, force_refresh=force_refresh)
    if error:
        return None

    token_col = _find_column(df.columns, REMEMBER_TOKEN_CANDIDATES)
    if not token_col:
        token_col = REMEMBER_TOKEN_COLUMN
        df[token_col] = ""

    token = secrets.token_urlsafe(24)
    existing = [item for item in _clean(df.at[row_index, token_col]).split("|") if item]
    existing.append(token)
    df.at[row_index, token_col] = "|".join(existing[-5:])
    if not _write_users_sheet(df, actual_title):
        return None
    return token


def authenticate_remembered_device(email: str, token: str, force_refresh=False) -> AuthResult:
    if not _clean(email) or not _clean(token):
        return AuthResult(False)

    df, _, row_index, error, user_type = _validate_user_base(email, force_refresh=force_refresh)
    if error:
        return AuthResult(False, error=error)

    token_col = _find_column(df.columns, REMEMBER_TOKEN_CANDIDATES)
    if not token_col:
        return AuthResult(False)
    tokens = [item for item in _clean(df.at[row_index, token_col]).split("|") if item]
    if token not in tokens:
        return AuthResult(False)
    return AuthResult(True, user_type=user_type)
