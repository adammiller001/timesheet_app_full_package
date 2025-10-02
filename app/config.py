import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent

def get_default_xlsx_path() -> str:
    """Retained for backwards compatibility; no local workbook is used."""
    return os.getenv("STREAMLIT_TIMESHEET_XLSX", "")

# Optional SharePoint settings (unused in this local-first build; keep for future cloud use)
SP_SITE = os.getenv("SP_SITE", "")
CLIENT_ID = os.getenv("CLIENT_ID", "")
TENANT_ID = os.getenv("TENANT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
SP_EXPORT_FOLDER = os.getenv("SP_EXPORT_FOLDER", "Exports")
