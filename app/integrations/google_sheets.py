"""
Google Sheets integration for PTW Timesheet App
Supports both gspread and direct Sheets API access.
"""

from __future__ import annotations

import json
import time
from typing import Optional, Dict, Any, Tuple, List
from urllib.parse import quote

import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession
from requests.exceptions import HTTPError

try:  # gspread is optional; fall back to raw API calls when unavailable
    import gspread
    from gspread.exceptions import APIError
    GSPREAD_AVAILABLE = True
except ImportError:  # pragma: no cover - environment without gspread
    gspread = None

    class APIError(Exception):
        """Placeholder used when gspread is not installed."""

    GSPREAD_AVAILABLE = False


SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


def _normalize_title(name: str) -> str:
    """Normalize worksheet titles for comparison"""
    if not name:
        return ""
    return ''.join(ch for ch in str(name).strip().lower() if ch.isalnum())


class GoogleSheetsManager:
    """Manages Google Sheets integration for timesheet data"""

    def __init__(self):
        self.gc = None
        self.spreadsheet = None
        self._session: Optional[AuthorizedSession] = None
        self._credentials_info: Optional[Dict[str, Any]] = None
        self._last_connection_time = 0.0
        self._worksheet_cache: Dict[str, Any] = {
            'timestamp': 0.0,
            'worksheets': []
        }
        self._data_cache: Dict[str, Tuple[float, pd.DataFrame]] = {}

    # ------------------------------------------------------------------
    # Credential / client helpers
    # ------------------------------------------------------------------
    def _load_credentials(self) -> Optional[Credentials]:
        if self._credentials_info is None:
            if "google_sheets" not in st.secrets:
                st.error("Google Sheets credentials not found in secrets. Please configure Google Sheets integration.")
                return None
            # Convert secrets object to plain dict
            self._credentials_info = json.loads(json.dumps(dict(st.secrets["google_sheets"])))
        try:
            return Credentials.from_service_account_info(self._credentials_info, scopes=SCOPES)
        except Exception as exc:  # pragma: no cover - misconfigured secrets
            st.error(f"Failed to load Google credentials: {exc}")
            return None

    def _ensure_gspread_client(self) -> bool:
        if not GSPREAD_AVAILABLE:
            return False
        if self.gc and (time.time() - self._last_connection_time) < 300:
            return True
        creds = self._load_credentials()
        if creds is None:
            return False
        try:
            self.gc = gspread.authorize(creds)
            self._last_connection_time = time.time()
            self._worksheet_cache = {'timestamp': 0.0, 'worksheets': []}
            self._data_cache.clear()
            return True
        except Exception as exc:  # pragma: no cover - gspread auth failure
            st.error(f"Failed to connect to Google Sheets via gspread: {exc}")
            self.gc = None
            return False

    def _ensure_session(self) -> Optional[AuthorizedSession]:
        if self._session is not None:
            return self._session
        creds = self._load_credentials()
        if creds is None:
            return None
        try:
            self._session = AuthorizedSession(creds)
            self._last_connection_time = time.time()
            self._worksheet_cache = {'timestamp': 0.0, 'worksheets': []}
            self._data_cache.clear()
            return self._session
        except Exception as exc:  # pragma: no cover - transport failure
            st.error(f"Failed to establish Google Sheets session: {exc}")
            self._session = None
            return None

    # ------------------------------------------------------------------
    # Worksheet helpers
    # ------------------------------------------------------------------
    def _list_worksheets_http(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        session = self._ensure_session()
        if session is None:
            return []
        cache_ttl = 30
        now = time.time()
        if self._worksheet_cache['worksheets'] and (now - self._worksheet_cache['timestamp']) <= cache_ttl:
            return self._worksheet_cache['worksheets']
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
        params = {"fields": "sheets(properties(title,sheetId))"}
        try:
            response = session.get(url, params=params)
            response.raise_for_status()
            sheets = response.json().get('sheets', [])
            worksheets = [sheet['properties'] for sheet in sheets]
            self._worksheet_cache = {'timestamp': now, 'worksheets': worksheets}
            return worksheets
        except HTTPError as exc:
            st.error(f"Failed to list worksheets via Google API: {exc}")
        except Exception as exc:
            st.error(f"Failed to list worksheets: {exc}")
        return []

    def find_worksheet(self, possible_names, spreadsheet_id: Optional[str] = None):
        """Locate a worksheet by trying multiple candidate names. Returns (worksheet, actual_title)."""
        # Prefer gspread if available
        if spreadsheet_id and self._ensure_gspread_client():
            try:
                if not self.spreadsheet:
                    self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
                cache_ttl = 30
                now = time.time()
                if (not self._worksheet_cache['worksheets'] or
                        (now - self._worksheet_cache['timestamp']) > cache_ttl):
                    self._worksheet_cache['worksheets'] = self.spreadsheet.worksheets()
                    self._worksheet_cache['timestamp'] = now
                worksheets = self._worksheet_cache['worksheets']
                # Ensure cached worksheets are gspread objects; fallback cache may store dicts
                if worksheets and not all(hasattr(ws, 'title') for ws in worksheets):
                    worksheets = self.spreadsheet.worksheets()
                    self._worksheet_cache['worksheets'] = worksheets
                    self._worksheet_cache['timestamp'] = now
                normalized_map = {_normalize_title(ws.title): ws for ws in worksheets}
                for name in possible_names:
                    key = _normalize_title(name)
                    if key in normalized_map:
                        ws = normalized_map[key]
                        return ws, ws.title
                for name in possible_names:
                    key = _normalize_title(name)
                    for ws in worksheets:
                        if key and key in _normalize_title(ws.title):
                            return ws, ws.title
            except APIError as exc:
                if exc.response.status_code == 429:
                    st.warning("Google Sheets rate limit reached while listing worksheets. Please wait a few seconds and try again.")
                else:
                    st.error(f"Failed to inspect worksheets: {exc}")
            except Exception as exc:
                st.error(f"Failed to inspect worksheets: {exc}")
            # fall back to HTTP path if gspread failed

        if not spreadsheet_id:
            st.error("No spreadsheet connected")
            return None, None

        worksheets = self._list_worksheets_http(spreadsheet_id)
        if not worksheets:
            return None, None
        normalized_map = {_normalize_title(ws['title']): ws['title'] for ws in worksheets}
        for name in possible_names:
            key = _normalize_title(name)
            if key in normalized_map:
                title = normalized_map[key]
                return title, title
        for name in possible_names:
            key = _normalize_title(name)
            for ws in worksheets:
                if key and key in _normalize_title(ws['title']):
                    title = ws['title']
                    return title, title
        return None, None

    # ------------------------------------------------------------------
    # Data operations
    # ------------------------------------------------------------------
    def read_worksheet(self, worksheet_name: str, spreadsheet_id: Optional[str] = None, force_refresh: bool = False) -> pd.DataFrame:
        """Read data from a worksheet and return as DataFrame"""
        cache_key = worksheet_name
        if not force_refresh:
            cache_entry = self._data_cache.get(cache_key)
            if cache_entry and (time.time() - cache_entry[0]) < 60:
                return cache_entry[1].copy()

        worksheet, actual_name = self.find_worksheet([worksheet_name], spreadsheet_id)
        if not worksheet:
            st.error(f"Worksheet '{worksheet_name}' not found")
            return pd.DataFrame()

        # gspread path --------------------------------------------------
        if gspread is not None and hasattr(worksheet, "get_all_records"):
            try:
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)
            except APIError as exc:
                if exc.response.status_code == 429:
                    cache_entry = self._data_cache.get(cache_key)
                    if cache_entry:
                        st.info("Using cached Google Sheets data while rate limit resets.")
                        return cache_entry[1].copy()
                    st.warning("Google Sheets rate limit reached while reading data. Please wait a few seconds and try again.")
                    return pd.DataFrame()
                st.error(f"Failed to read worksheet '{worksheet_name}': {exc}")
                return pd.DataFrame()
            except Exception as exc:
                st.error(f"Failed to read worksheet '{worksheet_name}': {exc}")
                return pd.DataFrame()
        else:  # HTTP path ---------------------------------------------
            session = self._ensure_session()
            if session is None or spreadsheet_id is None:
                return pd.DataFrame()
            range_name = quote(actual_name)
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"
            params = {
                "valueRenderOption": "UNFORMATTED_VALUE",
                "dateTimeRenderOption": "FORMATTED_STRING",
            }
            try:
                response = session.get(url, params=params)
                response.raise_for_status()
                values = response.json().get("values", [])
                if not values:
                    return pd.DataFrame()
                headers = [str(col).strip() for col in values[0]]
                rows = values[1:]
                normalized_rows = [row + ["" for _ in range(len(headers) - len(row))] for row in rows]
                df = pd.DataFrame(normalized_rows, columns=headers)
            except HTTPError as exc:
                st.error(f"Failed to read worksheet '{worksheet_name}': {exc}")
                return pd.DataFrame()
            except Exception as exc:
                st.error(f"Failed to read worksheet '{worksheet_name}': {exc}")
                return pd.DataFrame()

        if not df.empty:
            df.columns = [str(col).strip() for col in df.columns]
            df = df[[col for col in df.columns if col and col.strip()]]
            if 'Active' in df.columns:
                df['Active'] = df['Active'].astype(str).str.upper().map({
                    'TRUE': True, 'FALSE': False, 'YES': True, 'NO': False,
                    'Y': True, 'N': False, '1': True, '0': False
                }).fillna(df['Active'])

        self._data_cache[cache_key] = (time.time(), df.copy())
        return df

    def append_rows(self, worksheet_name: str, rows: List[List[Any]], spreadsheet_id: Optional[str] = None, value_input_option: str = "USER_ENTERED") -> bool:
        """Append rows to a worksheet without overwriting existing data"""
        if not rows:
            return True

        worksheet, actual_name = self.find_worksheet([worksheet_name], spreadsheet_id)
        if not worksheet:
            st.error(f"Worksheet '{worksheet_name}' not found when attempting to append rows")
            return False

        cleaned_rows = []
        for row in rows:
            normalized = []
            for val in row:
                if isinstance(val, (float, int)):
                    normalized.append("" if pd.isna(val) else val)
                elif val is None:
                    normalized.append("")
                else:
                    normalized.append(val)
            cleaned_rows.append(normalized)

        if gspread is not None and hasattr(worksheet, "append_rows"):
            try:
                worksheet.append_rows(cleaned_rows, value_input_option=value_input_option)
                self._data_cache.pop(actual_name or worksheet_name, None)
                return True
            except APIError as exc:
                if exc.response.status_code == 429:
                    st.warning("Google Sheets rate limit reached while writing data. Please wait a few seconds and try again.")
                    return False
                st.error(f"Failed to append to worksheet '{worksheet_name}': {exc}")
                return False
            except Exception as exc:
                st.error(f"Failed to append to worksheet '{worksheet_name}': {exc}")
                return False

        session = self._ensure_session()
        if session is None or spreadsheet_id is None:
            return False
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{quote(actual_name)}!A1:append"
        params = {
            "valueInputOption": value_input_option,
            "insertDataOption": "INSERT_ROWS",
        }
        payload = {"values": cleaned_rows}
        try:
            response = session.post(url, params=params, json=payload)
            response.raise_for_status()
            self._data_cache.pop(actual_name or worksheet_name, None)
            return True
        except HTTPError as exc:
            st.error(f"Failed to append to worksheet '{worksheet_name}': {exc}")
            return False
        except Exception as exc:
            st.error(f"Failed to append to worksheet '{worksheet_name}': {exc}")
            return False

    def write_worksheet(self, worksheet_name: str, data: pd.DataFrame, spreadsheet_id: Optional[str] = None) -> bool:
        """Write DataFrame to a worksheet"""
        worksheet, actual_name = self.find_worksheet([worksheet_name], spreadsheet_id)
        if not worksheet:
            st.error(f"Worksheet '{worksheet_name}' not found")
            return False
        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)

        header_row = [str(col) for col in data.columns.tolist()]
        value_rows = []
        for _, row in data.iterrows():
            normalized = []
            for val in row.tolist():
                if pd.isna(val):
                    normalized.append("")
                else:
                    normalized.append(val)
            value_rows.append(normalized)
        values = [header_row] + value_rows

        if gspread is not None and hasattr(worksheet, "clear"):
            try:
                worksheet.clear()
                worksheet.update(values)
                cache_key = actual_name or worksheet_name
                self._data_cache[cache_key] = (time.time(), data.copy())
                return True
            except APIError as exc:
                if exc.response.status_code == 429:
                    st.warning("Google Sheets rate limit reached while writing data. Please wait a few seconds and try again.")
                    return False
                st.error(f"Failed to write to worksheet '{worksheet_name}': {exc}")
                return False
            except Exception as exc:
                st.error(f"Failed to write to worksheet '{worksheet_name}': {exc}")
                return False

        session = self._ensure_session()
        if session is None or spreadsheet_id is None:
            return False
        base = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{quote(actual_name)}"
        try:
            clear_resp = session.post(f"{base}!A1:clear")
            clear_resp.raise_for_status()
            update_params = {"valueInputOption": "USER_ENTERED"}
            update_resp = session.put(f"{base}!A1", params=update_params, json={"values": values})
            update_resp.raise_for_status()
            cache_key = actual_name or worksheet_name
            self._data_cache[cache_key] = (time.time(), data.copy())
            return True
        except HTTPError as exc:
            st.error(f"Failed to write to worksheet '{worksheet_name}': {exc}")
            return False
        except Exception as exc:
            st.error(f"Failed to write to worksheet '{worksheet_name}': {exc}")
            return False


# Global instance
sheets_manager = GoogleSheetsManager()


def get_sheets_manager() -> GoogleSheetsManager:
    """Get the global sheets manager instance"""
    return sheets_manager


def read_timesheet_data(worksheet_name: str, force_refresh: bool = False) -> pd.DataFrame:
    """
    Convenience function to read timesheet data from Google Sheets
    Falls back to Excel if Google Sheets is not configured
    """
    try:
        sheet_id = st.secrets.get("google_sheets_id", "")
        if sheet_id:
            manager = get_sheets_manager()
            df = manager.read_worksheet(worksheet_name, sheet_id, force_refresh=force_refresh)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
    except Exception as exc:
        st.error(f"Failed to read {worksheet_name}: {exc}")

    return pd.DataFrame()
