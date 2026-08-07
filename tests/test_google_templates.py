import datetime as dt
import io

import pandas as pd
from openpyxl import Workbook, load_workbook

from app.exports.google_templates import build_sign_in_sheet_workbook, load_template_sheet_workbook


def _template_bytes() -> bytes:
    wb = Workbook()
    wb.active.title = "Daily Time"
    wb.create_sheet("TimeEntries")
    sign_in = wb.create_sheet("Sign In Sheet")
    sign_in["D6"] = ""
    buffer = io.BytesIO()
    wb.save(buffer)
    wb.close()
    buffer.seek(0)
    return buffer.getvalue()


def test_load_template_sheet_workbook_keeps_requested_google_tab_only():
    wb, ws = load_template_sheet_workbook(_template_bytes(), ("TimeEntries", "Time Entries"))

    assert ws.title == "TimeEntries"
    assert wb.sheetnames == ["TimeEntries"]


def test_sign_in_sheet_maps_active_employee_columns_l_m_n():
    employees = pd.DataFrame(
        [
            ["EMPL", "S-MIL10", "ADAM MILLER", "Indirect", "CONM", "TM0122", "Y", "", "", "", "", "PTW", "Supervisor", "TRUE"],
            ["EMPL", "72454", "ANDY LYNDS", "Direct", "EA2", "", "Y", "", "", "", "", "PTW", "Electrician", "FALSE"],
            ["EMPL", "17446", "TRAVIS TYCHKOWSKY", "Direct", "SUP", "76025", "Y", "", "", "", "", "PTW", "Welder", "Y"],
        ],
        columns=[
            "Time Record Type",
            "Person Number",
            "Employee Name",
            "Indirect / Direct",
            "Override Trade Class",
            "Truck",
            "Post To Payroll",
            "Night Shift",
            "Premium Rate",
            "Subsistence Rate",
            "Travel Rate",
            "Company Name",
            "Craft / Certification",
            "Active",
        ],
    )

    output_bytes, rows_written = build_sign_in_sheet_workbook(
        _template_bytes(),
        employees,
        dt.date(2026, 5, 20),
    )

    wb = load_workbook(io.BytesIO(output_bytes))
    ws = wb["Sign In Sheet"]

    assert rows_written == 2
    assert ws["D6"].value == dt.datetime(2026, 5, 20)
    assert ws["A11"].value == "PTW"
    assert ws["B11"].value == "ADAM MILLER"
    assert ws["C11"].value == "Supervisor"
    assert ws["A12"].value == "PTW"
    assert ws["B12"].value == "TRAVIS TYCHKOWSKY"
    assert ws["C12"].value == "Welder"
    assert ws["A13"].value is None
    assert ws.row_dimensions[17].hidden is False
    assert ws.row_dimensions[18].hidden is True
    assert ws.row_dimensions[74].hidden is True
