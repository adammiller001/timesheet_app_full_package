from pathlib import Path

APP_NAME = "Timesheet Entry - Production"
EXCEL_FILENAME = "Timesheet Apps.xlsx"  # Workbook expected alongside streamlit_app.py

# Candidate sheet/column names when auto-detecting employees
EMPLOYEE_SHEET_CANDIDATES = ["Employees", "Employee List", "Staff", 0]
EMPLOYEE_COL_CANDIDATES = [
    "Employee",
    "Employee Name",
    "Name",
    "Full Name",
    "User's Email Address",
    "Email",
]


def script_dir() -> Path:
    try:
        return Path(__file__).resolve().parent.parent  # app/.. -> project root
    except NameError:
        return Path.cwd()
