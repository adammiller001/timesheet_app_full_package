import pandas as pd

from app.features.project_assignments import (
    build_job_key,
    build_job_options,
    filter_jobs_for_user,
    resolve_clients_for_jobs,
    resolve_employees_for_jobs,
)


def _jobs():
    return pd.DataFrame(
        [
            ["Project A", "100", "005", "Area A", "TRUE"],
            ["Project B", "100", "008", "Area B", "TRUE"],
            ["Inactive", "200", "001", "Closed", "FALSE"],
        ],
        columns=["PROJECT NAME", "JOB #", "AREA #", "DESCRIPTION", "ACTIVE"],
    )


def test_user_assignments_limit_active_job_options_and_normalize_area():
    assignments = pd.DataFrame(
        [
            ["worker@example.com", "100", "5", "TRUE"],
            ["worker@example.com", "100", "008", "FALSE"],
        ],
        columns=["Email", "Job Number", "Job Area", "Active"],
    )

    allowed = filter_jobs_for_user(_jobs(), assignments, "WORKER@example.com")

    assert build_job_options(allowed) == ["100 - 005 - Area A"]
    assert build_job_key("100", "005") == build_job_key(100.0, 5)


def test_missing_user_assignment_sheet_exposes_no_jobs():
    allowed = filter_jobs_for_user(_jobs(), pd.DataFrame(), "worker@example.com")

    assert allowed.empty


def test_employee_assignment_values_override_global_values_including_blanks():
    employees = pd.DataFrame(
        [["EMPL", "10", "ALEX", "EA2", "Y", "99", "PTW", "Electrician", "TRUE"]],
        columns=[
            "Time Record Type", "Person Number", "Employee Name", "Override Trade Class",
            "Night Shift", "Subsistence Rate", "Company", "Craft / Certification", "Active",
        ],
    )
    assignments = pd.DataFrame(
        [["SUBS", "10", "ALEX", "100", "005", "EJ3", "", "225", "PARTNER", "Lead", "TRUE"]],
        columns=[
            "Time Record Type", "Person Number", "Employee Name", "Job Number", "Job Area",
            "Override Trade Class", "Night Shift", "Subsistence Rate", "Company",
            "Craft / Certification", "Active",
        ],
    )

    resolved = resolve_employees_for_jobs(
        employees,
        assignments,
        [build_job_key("100", "005")],
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
    employees = pd.DataFrame(
        [["10", "ALEX", "TRUE"], ["20", "BLAIR", "TRUE"]],
        columns=["Person Number", "Employee Name", "Active"],
    )
    assignments = pd.DataFrame(
        [
            ["10", "ALEX", "100", "005", "", "TRUE"],
            ["10", "ALEX", "100", "008", "Y", "TRUE"],
            ["20", "BLAIR", "100", "005", "Y", "TRUE"],
        ],
        columns=["Person Number", "Employee Name", "Job Number", "Job Area", "Night Shift", "Active"],
    )
    keys = [build_job_key("100", "005"), build_job_key("100", "008")]

    day_rows = resolve_employees_for_jobs(employees, assignments, keys, shift="day")
    night_rows = resolve_employees_for_jobs(employees, assignments, keys, shift="night")

    assert day_rows["Employee Name"].tolist() == ["ALEX"]
    assert night_rows["Employee Name"].tolist() == ["ALEX", "BLAIR"]


def test_client_assignment_shift_is_project_specific():
    clients = pd.DataFrame(
        [["OWNER", "SAM", "Inspector", "Day", "TRUE"]],
        columns=["COMPANY", "PERSON NAME", "CERTIFICATION", "SHIFT", "Active"],
    )
    assignments = pd.DataFrame(
        [["NEW OWNER", "SAM", "100", "008", "Lead", "Night", "TRUE"]],
        columns=["Company", "Person Name", "Job Number", "Job Area", "Certification", "Shift", "Active"],
    )

    resolved = resolve_clients_for_jobs(
        clients,
        assignments,
        [build_job_key("100", "008")],
        shift="night",
    )

    assert resolved["PERSON NAME"].tolist() == ["SAM"]
    assert resolved.loc[0, "COMPANY"] == "NEW OWNER"
    assert resolved.loc[0, "CERTIFICATION"] == "Lead"
    assert resolved.loc[0, "SHIFT"] == "Night"
