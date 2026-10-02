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


def test_timesheet_entry_uses_project_assignments_for_jobs_employees_and_sign_in_sheets():
    source_path = Path(__file__).resolve().parents[1] / "pages" / "10_Timesheet_Entry.py"
    source = source_path.read_text(encoding="utf-8")

    assert "filter_jobs_for_user(_project_jobs_df, _user_job_assignments_df, user)" in source
    assert '"Jobs to include"' in source
    assert "sign_in_job_options = build_job_number_options(_accessible_jobs_df)" in source
    assert "options=sign_in_job_options" in source
    assert "disabled=not sign_in_job_choices" in source
    assert "resolve_employees_for_jobs(" in source
    assert "resolve_clients_for_jobs(" in source
    assert "emp_info = _employee_info_for_entry(row)" in source
    assert "on_change=_clear_employee_selection_for_job_change" in source


def test_timesheet_entry_logs_selected_job_number_to_time_data():
    source_path = Path(__file__).resolve().parents[1] / "pages" / "10_Timesheet_Entry.py"
    source = source_path.read_text(encoding="utf-8")

    assert '"Job Number": job_num' in source


def test_timesheet_entry_does_not_read_retired_directory_worksheets():
    source_path = Path(__file__).resolve().parents[1] / "pages" / "10_Timesheet_Entry.py"
    source = source_path.read_text(encoding="utf-8")

    assert 'smart_read_data("Users"' not in source
    assert '"Employee List"' not in source
    assert '"Client Names"' not in source
