import io

import pandas as pd
from openpyxl import Workbook

from app.exports.google_templates import (
    _sign_in_client_rows,
    _sign_in_employee_rows,
    build_pdf_image_print_html,
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


def test_sign_in_employee_rows_map_active_columns_l_m_n():
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

    rows, active_count, first_hidden_row = _sign_in_employee_rows(employees)

    assert active_count == 2
    assert first_hidden_row == 18
    assert len(rows) == 64
    assert rows[0] == ["PTW", "ADAM MILLER", "Supervisor"]
    assert rows[1] == ["PTW", "TRAVIS TYCHKOWSKY", "Welder"]
    assert rows[2] == ["", "", ""]


def test_sign_in_client_rows_map_active_rows_and_three_blanks():
    clients = pd.DataFrame(
        [
            ["PEMBINA", "MARK SOMERS", "CONSTRUCTION MANAGER", "TRUE"],
            ["PEMBINA", "INACTIVE CLIENT", "VISITOR", "FALSE"],
            ["PEMBINA", "SCOTT RADTKE", "E&I SUPERVISOR", "Y"],
        ],
        columns=["COMPANY", "PERSON NAME", "CERTIFICATION", "Active"],
    )

    rows, active_count, first_hidden_row = _sign_in_client_rows(clients)

    assert active_count == 2
    assert first_hidden_row == 81
    assert len(rows) == 18
    assert rows[0] == ["PEMBINA", "MARK SOMERS", "CONSTRUCTION MANAGER"]
    assert rows[1] == ["PEMBINA", "SCOTT RADTKE", "E&I SUPERVISOR"]
    assert rows[2] == ["", "", ""]


def test_pdf_image_print_html_renders_images_and_calls_print():
    import fitz

    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "Sign In Sheet")
    pdf_bytes = document.tobytes()
    document.close()

    html = build_pdf_image_print_html(pdf_bytes, auto_print=True)

    assert "data:image/png;base64," in html
    assert "window.print()" in html
    assert "application/pdf" not in html
    assert "Open PDF" not in html
