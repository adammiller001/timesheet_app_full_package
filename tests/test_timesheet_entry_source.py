from pathlib import Path


def test_subsistence_daily_import_rows_use_subs_time_record_type():
    source_path = Path(__file__).resolve().parents[1] / "pages" / "10_Timesheet_Entry.py"
    source = source_path.read_text(encoding="utf-8")

    assert "sub_data[1] = 'SUBS'" in source


def test_night_shift_daily_import_rows_add_total_hours_line():
    source_path = Path(__file__).resolve().parents[1] / "pages" / "10_Timesheet_Entry.py"
    source = source_path.read_text(encoding="utf-8")

    assert "night_shift_total_hours = rt_hours + ot_hours" in source
    assert "return 'NS'" in source
    assert "night_data[4] = _daily_import_night_trade_class(night_data[4])" in source
    assert "night_data[5] = ''" in source
    assert "night_data[9] = '211'" in source
    assert "night_data[10] = night_shift_total_hours" in source
