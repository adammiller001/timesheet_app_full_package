import pandas as pd

from app.features.project_assignments import (
    build_job_number_key,
    build_job_number_options,
    build_job_options,
    filter_jobs_for_user,
    job_number_key_from_option,
    resolve_clients_for_jobs,
    resolve_employees_for_jobs,
)


def _jobs():
    return pd.DataFrame(
        [
            ["Project A", "100", "005", "Area A", "TRUE"],
            ["Project B", "100", "008", "Area B", "TRUE"],
            ["Project C", "200", "001", "Area C", "TRUE"],
            ["Inactive", "300", "001", "Closed", "FALSE"],
        ],
        columns=["PROJECT NAME", "JOB #", "AREA #", "DESCRIPTION", "ACTIVE"],
    )


def test_user_assignment_allows_every_active_area_for_the_job_number():
    assignments = pd.DataFrame(
        [
            ["worker@example.com", "100", "TRUE"],
            ["worker@example.com", "200", "FALSE"],
        ],
        columns=["Email", "Job Number", "Active"],
    )

    allowed = filter_jobs_for_user(_jobs(), assignments, "WORKER@example.com")

    assert build_job_options(allowed) == ["100 - 005 - Area A", "100 - 008 - Area B"]
    assert build_job_number_options(allowed) == ["100"]
    assert build_job_number_key("100") == build_job_number_key(100.0)
    assert job_number_key_from_option("100 - 005 - Area A") == build_job_number_key("100")
    assert job_number_key_from_option("100 - 008 - Area B") == build_job_number_key("100")


def test_missing_user_assignment_sheet_exposes_no_jobs():
    allowed = filter_jobs_for_user(_jobs(), pd.DataFrame(), "worker@example.com")

    assert allowed.empty


def test_employee_assignment_is_the_complete_project_record():
    assignments = pd.DataFrame(
        [["SUBS", "10", "ALEX", "100", "EJ3", "", "225", "PARTNER", "Lead", "TRUE"]],
        columns=[
            "Time Record Type", "Person Number", "Employee Name", "Job Number",
            "Override Trade Class", "Night Shift", "Subsistence Rate", "Company",
            "Craft / Certification", "Active",
        ],
    )

    resolved = resolve_employees_for_jobs(
        assignments,
        [build_job_number_key("100")],
        shift="day",
    )

    assert resolved["Employee Name"].tolist() == ["ALEX"]
    assert resolved.loc[0, "Override Trade Class"] == "EJ3"
    assert resolved.loc[0, "Night Shift"] == ""
    assert resolved.loc[0, "Subsistence Rate"] == "225"
    assert resolved.loc[0, "Time Record Type"] == "SUBS"
    assert resolved.loc[0, "Company"] == "PARTNER"
    assert resolved.loc[0, "Craft / Certification"] == "Lead"


def test_employee_sign_in_union_deduplicates_after_shift_filter():
    assignments = pd.DataFrame(
        [
            ["10", "ALEX", "100", "", "TRUE"],
            ["10", "ALEX", "200", "Y", "TRUE"],
            ["20", "BLAIR", "100", "Y", "TRUE"],
        ],
        columns=["Person Number", "Employee Name", "Job Number", "Night Shift", "Active"],
    )
    job_numbers = [build_job_number_key("100"), build_job_number_key("200")]

    day_rows = resolve_employees_for_jobs(assignments, job_numbers, shift="day")
    night_rows = resolve_employees_for_jobs(assignments, job_numbers, shift="night")

    assert day_rows["Employee Name"].tolist() == ["ALEX"]
    assert night_rows["Employee Name"].tolist() == ["ALEX", "BLAIR"]


def test_client_assignment_shift_is_project_specific():
    assignments = pd.DataFrame(
        [["NEW OWNER", "SAM", "100", "Lead", "Night", "TRUE"]],
        columns=["Company", "Person Name", "Job Number", "Certification", "Shift", "Active"],
    )

    resolved = resolve_clients_for_jobs(
        assignments,
        [build_job_number_key("100")],
        shift="night",
    )

    assert resolved["Person Name"].tolist() == ["SAM"]
    assert resolved.loc[0, "Company"] == "NEW OWNER"
    assert resolved.loc[0, "Certification"] == "Lead"
    assert resolved.loc[0, "Shift"] == "Night"
