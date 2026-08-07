from app.integrations.google_sheets import GoogleSheetsManager, _values_to_dataframe


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
