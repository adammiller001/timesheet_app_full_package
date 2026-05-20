import pandas as pd

from app.data.time_data import (
    normalize_job_area_value,
    normalize_sheet_value,
    prepare_time_data_dataframe,
)


def test_numeric_sheet_values_keep_trailing_zero_digits():
    assert normalize_sheet_value(900) == "900"
    assert normalize_sheet_value(900.0) == "900"
    assert normalize_sheet_value(100.0) == "100"
    assert normalize_sheet_value(2624138040.0) == "2624138040"


def test_job_area_values_are_preserved_as_entered():
    assert normalize_job_area_value("002") == "002"
    assert normalize_job_area_value("100") == "100"
    assert normalize_job_area_value("900") == "900"
    assert normalize_job_area_value("9") == "9"


def test_prepare_time_data_keeps_job_area_text_exact():
    df = pd.DataFrame(
        {
            "Job Number": [2624138043],
            "Job Area": ["002"],
            "Date": ["2026-05-19"],
            "Name": ["ADAM MILLER"],
        }
    )

    prepared = prepare_time_data_dataframe(df)

    assert prepared.loc[0, "Job Area"] == "002"
