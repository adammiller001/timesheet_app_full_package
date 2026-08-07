import datetime as dt
import io

import pandas as pd
from openpyxl import Workbook

from app.exports.google_templates import (
    build_sign_in_print_html,
    get_google_template_workbook_bytes,
    load_template_sheet_workbook,
)


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


def test_google_template_export_falls_back_to_existing_session(monkeypatch):
    class FakeResponse:
        content = b"xlsx-bytes"

        def raise_for_status(self):
            return None

    class FakeSession:
        def get(self, url, params):
            assert url == "https://www.googleapis.com/drive/v3/files/sheet-id/export"
            assert params["mimeType"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return FakeResponse()

    class FakeManager:
        def _ensure_session(self):
            return FakeSession()

    monkeypatch.setattr("app.exports.google_templates.get_sheets_manager", lambda: FakeManager())

    assert get_google_template_workbook_bytes("sheet-id") == b"xlsx-bytes"


def test_sign_in_print_html_creates_one_print_page_per_date():
    employees = pd.DataFrame(
        [
            ["EMPL", "S-MIL10", "ADAM MILLER", "", "", "", "", "", "", "", "", "PTW", "Supervisor", "TRUE"],
            ["EMPL", "72454", "ANDY LYNDS", "", "", "", "", "", "", "", "", "PTW", "Electrician", "FALSE"],
            ["EMPL", "17446", "TRAVIS TYCHKOWSKY", "", "", "", "", "", "", "", "", "PTW", "Welder", "Y"],
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

    html, active_count, sheet_count = build_sign_in_print_html(
        employees,
        [dt.date(2026, 8, 1), dt.date(2026, 8, 2)],
    )

    assert active_count == 2
    assert sheet_count == 2
    assert html.count("class='sign-page'") == 2
    assert "2026/08/01" in html
    assert "2026/08/02" in html
    assert "ADAM MILLER" in html
    assert "TRAVIS TYCHKOWSKY" in html
    assert "ANDY LYNDS" not in html
    assert "Supervisor" in html
    assert "Welder" in html
    assert "window.print()" in html
