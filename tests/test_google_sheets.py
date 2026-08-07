from app.integrations.google_sheets import GoogleSheetsManager, _values_to_dataframe
from requests.exceptions import HTTPError


def test_values_to_dataframe_preserves_formatted_job_area_text():
    values = [
        ["Job Number", "Job Area", "Name"],
        ["2624138043", "900", "ADAM MILLER"],
        ["2624138043", "003", "TRAVIS TYCHKOWSKY"],
    ]

    df = _values_to_dataframe(values)

    assert df.loc[0, "Job Area"] == "900"
    assert df.loc[1, "Job Area"] == "003"


def test_batch_update_values_uses_google_values_batch_endpoint(monkeypatch):
    posted = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"totalUpdatedRanges": 2}

    class FakeSession:
        def post(self, url, json):
            posted["url"] = url
            posted["json"] = json
            return FakeResponse()

    manager = GoogleSheetsManager()
    monkeypatch.setattr(manager, "_ensure_session", lambda: FakeSession())

    response = manager.batch_update_values(
        "sheet-id",
        [
            {"range": "'Print 1'!D6", "values": [["2026/08/01"]]},
            {"range": "'Print 1'!A76:C93", "values": [["PEMBINA", "MARK SOMERS", "SAFETY"]]},
        ],
    )

    assert response == {"totalUpdatedRanges": 2}
    assert posted["url"] == "https://sheets.googleapis.com/v4/spreadsheets/sheet-id/values:batchUpdate"
    assert posted["json"]["valueInputOption"] == "USER_ENTERED"
    assert len(posted["json"]["data"]) == 2


def test_export_sheet_pdf_can_repeat_frozen_rows(monkeypatch):
    captured = {}

    class FakeResponse:
        content = b"pdf"

        def raise_for_status(self):
            return None

    class FakeSession:
        def get(self, url, params):
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

    manager = GoogleSheetsManager()
    monkeypatch.setattr(manager, "_ensure_session", lambda: FakeSession())

    assert manager.export_sheet_pdf("sheet-id", 123, repeat_frozen_rows=True) == b"pdf"
    assert captured["url"] == "https://docs.google.com/spreadsheets/d/sheet-id/export"
    assert captured["params"]["gid"] == "123"
    assert captured["params"]["fzr"] == "true"


def test_export_sheet_pdf_retries_google_rate_limit(monkeypatch):
    attempts = []
    sleep_delays = []

    class FakeResponse:
        def __init__(self, status_code, content=b""):
            self.status_code = status_code
            self.content = content
            self.headers = {"Retry-After": "0.1"} if status_code == 429 else {}

        def raise_for_status(self):
            if self.status_code >= 400:
                error = HTTPError(f"{self.status_code} Error")
                error.response = self
                raise error

    class FakeSession:
        def get(self, url, params):
            attempts.append((url, params))
            if len(attempts) == 1:
                return FakeResponse(429)
            return FakeResponse(200, b"pdf")

    manager = GoogleSheetsManager()
    monkeypatch.setattr(manager, "_ensure_session", lambda: FakeSession())
    monkeypatch.setattr("app.integrations.google_sheets.time.sleep", lambda delay: sleep_delays.append(delay))

    assert manager.export_sheet_pdf("sheet-id", 123, repeat_frozen_rows=True) == b"pdf"
    assert len(attempts) == 2
    assert sleep_delays == [0.1]
