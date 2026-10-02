from pathlib import Path
import ast
from typing import Optional

import pandas as pd


def test_assignment_blank_fields_do_not_read_adjacent_columns():
    source_path = Path(__file__).resolve().parents[1] / "pages" / "10_Timesheet_Entry.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    names = {
        "_clean_text_value", "_get_employee_list_value", "_get_employee_truck",
        "_get_employee_post_to_payroll", "_get_employee_night_shift",
    }
    definitions = [node for node in ast.walk(tree)
                   if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"pd": pd, "Optional": Optional}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(source_path), "exec"), namespace)
    employee = pd.Series({
        "Person Number": "70299I", "Employee Name": "ELBERT WIEBE",
        "Job Number": "2624138043", "Time Record Type": "EMPL",
        "Indirect / Direct": "Direct", "Override Trade Class": "EJ2",
        "Truck": "", "Post To Payroll": "Y", "Night Shift": "",
        "Premium Rate": "", "Subsistence Rate": "", "Travel Rate": "",
    })
    assert namespace["_get_employee_night_shift"](employee) == ""
    assert namespace["_get_employee_truck"](employee) == ""
    assert namespace["_get_employee_post_to_payroll"](employee) == "Y"
    for header, old_position in (("Premium Rate", 8), ("Subsistence Rate", 9), ("Travel Rate", 10)):
        assert namespace["_get_employee_list_value"](employee, [header], old_position) == ""
    employee["Night Shift"] = "Y"
    assert namespace["_get_employee_night_shift"](employee) == "Y"
    employee["Post To Payroll"] = ""
    employee["Truck"] = "12345"
    assert namespace["_get_employee_post_to_payroll"](employee) == ""
    assert namespace["_get_employee_truck"](employee) == "12345"


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
