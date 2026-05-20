from app.integrations.google_sheets import _values_to_dataframe


def test_values_to_dataframe_preserves_formatted_job_area_text():
    values = [
        ["Job Number", "Job Area", "Name"],
        ["2624138043", "900", "ADAM MILLER"],
        ["2624138043", "003", "TRAVIS TYCHKOWSKY"],
    ]

    df = _values_to_dataframe(values)

    assert df.loc[0, "Job Area"] == "900"
    assert df.loc[1, "Job Area"] == "003"
