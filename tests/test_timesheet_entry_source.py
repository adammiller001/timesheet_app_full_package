from pathlib import Path


def test_subsistence_daily_import_rows_use_subs_time_record_type():
    source_path = Path(__file__).resolve().parents[1] / "pages" / "10_Timesheet_Entry.py"
    source = source_path.read_text(encoding="utf-8")

    assert "sub_data[1] = 'SUBS'" in source
