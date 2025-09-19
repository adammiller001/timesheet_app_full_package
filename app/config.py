import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent

def get_default_xlsx_path() -> str:
    """Where to find the main workbook. Looks for a sidecar file first, else env var, else local default."""
    sidecar = APP_DIR.parent / "timesheet_default_path.txt"
    if sidecar.exists():
        try:
            p = sidecar.read_text().strip()
            if p:
                return p
        except Exception:
            pass
    return os.getenv("STREAMLIT_TIMESHEET_XLSX", str(APP_DIR.parent / "TimeSheet Apps.xlsx"))

# Optional SharePoint settings (unused in this local-first build; keep for future cloud use)
SP_SITE = os.getenv("SP_SITE", "")
CLIENT_ID = os.getenv("CLIENT_ID", "")
TENANT_ID = os.getenv("TENANT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
SP_EXPORT_FOLDER = os.getenv("SP_EXPORT_FOLDER", "Exports")
