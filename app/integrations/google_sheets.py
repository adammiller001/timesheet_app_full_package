"""
Google Sheets integration for PTW Timesheet App
Replaces Excel file dependency with cloud-based Google Sheets
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from typing import Optional, Dict, Any
import time

class GoogleSheetsManager:
    """Manages Google Sheets integration for timesheet data"""

    def __init__(self):
        self.gc = None
        self.spreadsheet = None
        self._last_connection_time = 0

    def connect(self) -> bool:
        """Connect to Google Sheets using service account credentials"""
        try:
            # Check if we have credentials in secrets
            if "google_sheets" not in st.secrets:
                st.error("Google Sheets credentials not found in secrets. Please configure Google Sheets integration.")
                return False

            # Create credentials from secrets
            credentials_info = dict(st.secrets["google_sheets"])
            credentials = Credentials.from_service_account_info(
                credentials_info,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )

            # Connect to Google Sheets
            self.gc = gspread.authorize(credentials)
            self._last_connection_time = time.time()
            return True

        except Exception as e:
            st.error(f"Failed to connect to Google Sheets: {e}")
            return False

    def get_spreadsheet(self, spreadsheet_id: str):
        """Get spreadsheet by ID"""
        try:
            if not self.gc:
                if not self.connect():
                    return None

            self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
            return self.spreadsheet

        except Exception as e:
            st.error(f"❌ Failed to access spreadsheet ID: {spreadsheet_id}")
            st.error(f"Error details: {e}")

            # Check if it's a permissions issue
            if "403" in str(e):
                st.error("🔒 Permission denied - Make sure you shared the spreadsheet with the service account")
            elif "400" in str(e):
                st.error("📄 Document format issue - Make sure the file is converted to Google Sheets format")
            elif "404" in str(e):
                st.error("🔍 Spreadsheet not found - Check the spreadsheet ID")

            return None

    def read_worksheet(self, worksheet_name: str, spreadsheet_id: Optional[str] = None) -> pd.DataFrame:
        """Read data from a worksheet and return as DataFrame"""
        try:
            if spreadsheet_id and not self.spreadsheet:
                if not self.get_spreadsheet(spreadsheet_id):
                    return pd.DataFrame()

            if not self.spreadsheet:
                st.error("No spreadsheet connected")
                return pd.DataFrame()

            # Get the worksheet
            worksheet = self.spreadsheet.worksheet(worksheet_name)

            # Get all values
            data = worksheet.get_all_records()

            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Convert boolean-like strings to actual booleans for Active columns
            if 'Active' in df.columns:
                df['Active'] = df['Active'].astype(str).str.upper().map({
                    'TRUE': True, 'FALSE': False, 'YES': True, 'NO': False,
                    'Y': True, 'N': False, '1': True, '0': False
                }).fillna(df['Active'])

            return df

        except Exception as e:
            st.error(f"Failed to read worksheet '{worksheet_name}': {e}")
            return pd.DataFrame()

    def write_worksheet(self, worksheet_name: str, data: pd.DataFrame, spreadsheet_id: Optional[str] = None) -> bool:
        """Write DataFrame to a worksheet"""
        try:
            if spreadsheet_id and not self.spreadsheet:
                if not self.get_spreadsheet(spreadsheet_id):
                    return False

            if not self.spreadsheet:
                st.error("No spreadsheet connected")
                return False

            # Get the worksheet
            worksheet = self.spreadsheet.worksheet(worksheet_name)

            # Clear existing data
            worksheet.clear()

            # Convert DataFrame to list of lists
            values = [data.columns.tolist()] + data.values.tolist()

            # Update the worksheet
            worksheet.update(values)

            return True

        except Exception as e:
            st.error(f"Failed to write to worksheet '{worksheet_name}': {e}")
            return False

# Global instance
sheets_manager = GoogleSheetsManager()

def get_sheets_manager() -> GoogleSheetsManager:
    """Get the global sheets manager instance"""
    return sheets_manager

def read_timesheet_data(worksheet_name: str) -> pd.DataFrame:
    """
    Convenience function to read timesheet data from Google Sheets
    Falls back to Excel if Google Sheets is not configured
    """
    try:
        # Try Google Sheets first
        if "google_sheets_id" in st.secrets and st.secrets["google_sheets_id"]:
            manager = get_sheets_manager()
            df = manager.read_worksheet(worksheet_name, st.secrets["google_sheets_id"])
            if not df.empty:
                return df

        # Fallback to Excel file
        from pathlib import Path
        excel_path = Path(__file__).parent.parent.parent / "TimeSheet Apps.xlsx"
        if excel_path.exists():
            df = pd.read_excel(excel_path, sheet_name=worksheet_name)
            return df

    except Exception as e:
        st.error(f"Failed to read {worksheet_name}: {e}")

    return pd.DataFrame()