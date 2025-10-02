import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent

def get_default_xlsx_path() -> str:
    """Locate the legacy Excel workbook path for local fallback workflows."""
    sidecar = APP_DIR.parent / "timesheet_default_path.txt"
    if sidecar.exists():
        try:
            candidate = sidecar.read_text().strip()
            if candidate:
                return candidate
        except Exception:
            pass
    env_path = os.getenv("STREAMLIT_TIMESHEET_XLSX", "")
    if env_path:
        return env_path
    return str(APP_DIR.parent / "TimeSheet Apps.xlsx")

# Optional SharePoint settings (unused in this local-first build; keep for future cloud use)
SP_SITE = os.getenv("SP_SITE", "")
CLIENT_ID = os.getenv("CLIENT_ID", "")
TENANT_ID = os.getenv("TENANT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
SP_EXPORT_FOLDER = os.getenv("SP_EXPORT_FOLDER", "Exports")
