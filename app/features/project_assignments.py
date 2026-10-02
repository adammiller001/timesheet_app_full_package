from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

from app.data.time_data import normalize_sheet_value


JOB_NUMBER_COLUMNS = ("Job Number", "JOB #", "Job #", "Job", "JobNumber")
JOB_AREA_COLUMNS = ("Job Area", "JobArea", "Area Number", "AREA #", "Area #", "Area")
ACTIVE_COLUMNS = ("Active", "Is Active", "Enabled")


def _clean_value(value) -> str:
    return normalize_sheet_value(value)


def _normalized_column_name(value) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())


def find_column(df: pd.DataFrame, candidates: Iterable[str], fallback_index: int | None = None):
    if not isinstance(df, pd.DataFrame):
        return None
    normalized = {_normalized_column_name(column): column for column in df.columns}
    for candidate in candidates:
        match = normalized.get(_normalized_column_name(candidate))
        if match is not None:
            return match
    if fallback_index is not None and len(df.columns) > fallback_index:
        return df.columns[fallback_index]
    return None


def is_truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    text = _clean_value(value).strip().upper()
    if text in {"TRUE", "YES", "Y", "1", "ON", "ACTIVE", "ENABLED"}:
        return True
    try:
        return float(text) == 1.0
    except (TypeError, ValueError):
        return False


def _canonical_identifier(value) -> str:
    text = _clean_value(value).strip()
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]
    return text.upper()


def build_job_number_key(job_number) -> str:
    """Return the canonical project key used by assignment worksheets."""
    return _canonical_identifier(job_number)


def parse_job_option(option: str) -> tuple[str, str, str]:
    parts = str(option or "").split(" - ", 2)
    parts.extend([""] * (3 - len(parts)))
    return parts[0].strip(), parts[1].strip(), parts[2].strip()


def job_number_key_from_option(option: str) -> str:
    job_number, _, _ = parse_job_option(option)
    return build_job_number_key(job_number)


def _active_rows(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    rows = df.copy()
    active_column = find_column(rows, ACTIVE_COLUMNS)
    if active_column is not None:
        rows = rows[rows[active_column].apply(is_truthy)]
    return rows


def _rows_with_job_numbers(df: pd.DataFrame) -> pd.DataFrame:
    rows = df.copy()
    job_column = find_column(rows, JOB_NUMBER_COLUMNS)
    if job_column is None:
        return pd.DataFrame()
    rows["_project_job_number_key"] = rows[job_column].apply(build_job_number_key)
    return rows[rows["_project_job_number_key"] != ""]


def filter_jobs_for_user(
    jobs_df: pd.DataFrame,
    user_assignments_df: pd.DataFrame,
    user_email: str,
) -> pd.DataFrame:
    """Return globally active jobs assigned to the signed-in user."""
    active_jobs = _rows_with_job_numbers(_active_rows(jobs_df))
    if active_jobs.empty:
        return active_jobs

    email_column = find_column(user_assignments_df, ("Email", "User Email", "Email Address", "E-mail"))
    job_column = find_column(user_assignments_df, JOB_NUMBER_COLUMNS)
    if email_column is None or job_column is None:
        return active_jobs.iloc[0:0].drop(columns=["_project_job_number_key"], errors="ignore")

    assignments = _rows_with_job_numbers(_active_rows(user_assignments_df))
    normalized_email = str(user_email or "").strip().lower()
    assignments = assignments[
        assignments[email_column].astype(str).str.strip().str.lower() == normalized_email
    ]
    allowed_keys = set(assignments["_project_job_number_key"].tolist())
    return active_jobs[active_jobs["_project_job_number_key"].isin(allowed_keys)].drop(
        columns=["_project_job_number_key"],
        errors="ignore",
    )


def build_job_options(jobs_df: pd.DataFrame) -> list[str]:
    if not isinstance(jobs_df, pd.DataFrame) or jobs_df.empty:
        return []
    job_column = find_column(jobs_df, JOB_NUMBER_COLUMNS, 2)
    area_column = find_column(jobs_df, JOB_AREA_COLUMNS, 3)
    description_column = find_column(
        jobs_df,
        ("Description", "DESCRIPTION", "Job Description", "Description of Work"),
        5,
    )
    if job_column is None or area_column is None:
        return []

    options: list[str] = []
    for _, row in jobs_df.iterrows():
        job = _clean_value(row.get(job_column, ""))
        area = _clean_value(row.get(area_column, ""))
        description = _clean_value(row.get(description_column, "")) if description_column else ""
        if not job and not area:
            continue
        label = f"{job} - {area}"
        if description:
            label += f" - {description}"
        options.append(label)
    return sorted(dict.fromkeys(options))


def build_job_number_options(jobs_df: pd.DataFrame) -> list[str]:
    """Return unique Job Numbers for project-level actions such as sign-in sheets."""
    if not isinstance(jobs_df, pd.DataFrame) or jobs_df.empty:
        return []
    job_column = find_column(jobs_df, JOB_NUMBER_COLUMNS, 2)
    if job_column is None:
        return []
    options = [
        _clean_value(value)
        for value in jobs_df[job_column].tolist()
        if _clean_value(value)
    ]
    return sorted(dict.fromkeys(options))


def _base_row_indexes(
    base_df: pd.DataFrame,
    id_candidates: Iterable[str],
    name_candidates: Iterable[str],
) -> tuple[dict[str, dict], dict[str, dict]]:
    id_column = find_column(base_df, id_candidates)
    name_column = find_column(base_df, name_candidates)
    by_id: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for _, row in _active_rows(base_df).iterrows():
        row_dict = row.to_dict()
        identifier = _canonical_identifier(row.get(id_column, "")) if id_column else ""
        name = _canonical_identifier(row.get(name_column, "")) if name_column else ""
        if identifier:
            by_id[identifier] = row_dict
        if name:
            by_name[name] = row_dict
    return by_id, by_name


def _set_from_assignment(
    resolved: dict,
    base_df: pd.DataFrame,
    assignment_row: pd.Series,
    assignment_df: pd.DataFrame,
    target_candidates: Iterable[str],
    source_candidates: Iterable[str] | None = None,
) -> None:
    source_column = find_column(assignment_df, source_candidates or target_candidates)
    if source_column is None:
        return
    target_column = find_column(base_df, target_candidates) or next(iter(target_candidates))
    resolved[target_column] = assignment_row.get(source_column, "")


def resolve_employees_for_jobs(
    employees_df: pd.DataFrame,
    assignments_df: pd.DataFrame,
    job_numbers: Iterable[str],
    shift: str | None = None,
) -> pd.DataFrame:
    """Resolve active employee rows with project-specific assignment values."""
    active_employees = _active_rows(employees_df)
    assignment_id_column = find_column(assignments_df, ("Person Number", "Employee Number"))
    assignment_name_column = find_column(assignments_df, ("Employee Name", "Name", "Employee"))
    assignment_job_column = find_column(assignments_df, JOB_NUMBER_COLUMNS)

    if assignment_job_column is None:
        return active_employees.iloc[0:0].copy()

    selected_keys = {build_job_number_key(job_number) for job_number in job_numbers if job_number}
    if not selected_keys:
        return active_employees.iloc[0:0].copy()

    assignments = _rows_with_job_numbers(_active_rows(assignments_df))
    assignments = assignments[assignments["_project_job_number_key"].isin(selected_keys)]
    by_id, by_name = _base_row_indexes(
        employees_df,
        ("Person Number", "Employee Number"),
        ("Employee Name", "Name", "Employee"),
    )

    resolved_rows: list[dict] = []
    for _, assignment in assignments.iterrows():
        identifier = _canonical_identifier(assignment.get(assignment_id_column, "")) if assignment_id_column else ""
        name = _canonical_identifier(assignment.get(assignment_name_column, "")) if assignment_name_column else ""
        base_row = by_id.get(identifier) if identifier else None
        if base_row is None and name:
            base_row = by_name.get(name)
        if base_row is None:
            continue

        resolved = dict(base_row)
        for candidates in (
            ("Time Record Type", "Record Type"),
            ("Indirect / Direct", "Indirect Direct"),
            ("Override Trade Class", "Trade Class"),
            ("Truck", "Truck Number", "Unit"),
            ("Post To Payroll", "Post to Payroll"),
            ("Night Shift", "NightShift", "Night"),
            ("Premium Rate", "Premium"),
            ("Subsistence Rate", "Subsistence"),
            ("Travel Rate", "Travel"),
            ("Company", "Company Name", "Employer"),
            ("Craft / Certification", "Craft Certification", "Craft", "Certification"),
            ("Daily Import", "Include Daily Import"),
        ):
            _set_from_assignment(resolved, employees_df, assignment, assignments_df, candidates)
        resolved_rows.append(resolved)

    if not resolved_rows:
        return active_employees.iloc[0:0].copy()
    resolved_df = pd.DataFrame(resolved_rows)
    return _filter_employee_shift(resolved_df, shift)


def _filter_employee_shift(employees_df: pd.DataFrame, shift: str | None) -> pd.DataFrame:
    if not isinstance(employees_df, pd.DataFrame) or employees_df.empty:
        return employees_df.copy() if isinstance(employees_df, pd.DataFrame) else pd.DataFrame()
    rows = employees_df.copy()
    night_column = find_column(rows, ("Night Shift", "NightShift", "Night"))
    normalized_shift = str(shift or "").strip().lower()
    if normalized_shift in {"day", "night"}:
        if night_column is None:
            rows = rows.iloc[0:0] if normalized_shift == "night" else rows
        else:
            night_flags = rows[night_column].apply(is_truthy)
            rows = rows[night_flags] if normalized_shift == "night" else rows[~night_flags]

    id_column = find_column(rows, ("Person Number", "Employee Number"))
    name_column = find_column(rows, ("Employee Name", "Name", "Employee"))
    seen: set[str] = set()
    keep_indexes = []
    for index, row in rows.iterrows():
        identity = _canonical_identifier(row.get(id_column, "")) if id_column else ""
        if not identity and name_column:
            identity = _canonical_identifier(row.get(name_column, ""))
        if not identity or identity in seen:
            continue
        seen.add(identity)
        keep_indexes.append(index)
    return rows.loc[keep_indexes].reset_index(drop=True)


def resolve_clients_for_jobs(
    clients_df: pd.DataFrame,
    assignments_df: pd.DataFrame,
    job_numbers: Iterable[str],
    shift: str | None = None,
) -> pd.DataFrame:
    """Resolve active client rows with project-specific certification and shift."""
    active_clients = _active_rows(clients_df)
    company_candidates = ("COMPANY", "Company", "Company Name", "Client Company")
    name_candidates = ("PERSON NAME", "Person Name", "Client Name", "Name")
    assignment_company_column = find_column(assignments_df, company_candidates)
    assignment_name_column = find_column(assignments_df, name_candidates)
    assignment_job_column = find_column(assignments_df, JOB_NUMBER_COLUMNS)
    if assignment_job_column is None:
        return active_clients.iloc[0:0].copy()

    selected_keys = {build_job_number_key(job_number) for job_number in job_numbers if job_number}
    if not selected_keys:
        return active_clients.iloc[0:0].copy()

    assignments = _rows_with_job_numbers(_active_rows(assignments_df))
    assignments = assignments[assignments["_project_job_number_key"].isin(selected_keys)]
    base_company_column = find_column(active_clients, company_candidates)
    base_name_column = find_column(active_clients, name_candidates)
    base_rows = {}
    base_rows_by_name: dict[str, list[dict]] = {}
    for _, row in active_clients.iterrows():
        normalized_name = (
            _canonical_identifier(row.get(base_name_column, "")) if base_name_column else ""
        )
        key = (
            _canonical_identifier(row.get(base_company_column, "")) if base_company_column else "",
            normalized_name,
        )
        if any(key):
            row_dict = row.to_dict()
            base_rows[key] = row_dict
            if normalized_name:
                base_rows_by_name.setdefault(normalized_name, []).append(row_dict)

    resolved_rows: list[dict] = []
    for _, assignment in assignments.iterrows():
        key = (
            _canonical_identifier(assignment.get(assignment_company_column, "")) if assignment_company_column else "",
            _canonical_identifier(assignment.get(assignment_name_column, "")) if assignment_name_column else "",
        )
        base_row = base_rows.get(key)
        if base_row is None and key[1] and len(base_rows_by_name.get(key[1], [])) == 1:
            base_row = base_rows_by_name[key[1]][0]
        if base_row is None:
            continue
        resolved = dict(base_row)
        _set_from_assignment(
            resolved,
            clients_df,
            assignment,
            assignments_df,
            company_candidates,
        )
        _set_from_assignment(
            resolved,
            clients_df,
            assignment,
            assignments_df,
            ("CERTIFICATION", "Certification", "Craft / Certification"),
        )
        _set_from_assignment(
            resolved,
            clients_df,
            assignment,
            assignments_df,
            ("SHIFT", "Shift", "Day / Night"),
        )
        resolved_rows.append(resolved)

    if not resolved_rows:
        return active_clients.iloc[0:0].copy()
    resolved_df = pd.DataFrame(resolved_rows)
    return _filter_client_shift(resolved_df, shift)


def _filter_client_shift(clients_df: pd.DataFrame, shift: str | None) -> pd.DataFrame:
    if not isinstance(clients_df, pd.DataFrame) or clients_df.empty:
        return clients_df.copy() if isinstance(clients_df, pd.DataFrame) else pd.DataFrame()
    rows = clients_df.copy()
    shift_column = find_column(rows, ("SHIFT", "Shift", "Day / Night"))
    normalized_shift = str(shift or "").strip().lower()
    if normalized_shift in {"day", "night"}:
        if shift_column is None:
            rows = rows.iloc[0:0] if normalized_shift == "night" else rows
        else:
            shifts = rows[shift_column].astype(str).str.strip().str.lower()
            night_flags = shifts.eq("night") | shifts.eq("nights") | shifts.eq("n")
            rows = rows[night_flags] if normalized_shift == "night" else rows[~night_flags]

    company_column = find_column(rows, ("COMPANY", "Company", "Company Name", "Client Company"))
    name_column = find_column(rows, ("PERSON NAME", "Person Name", "Client Name", "Name"))
    seen: set[tuple[str, str]] = set()
    keep_indexes = []
    for index, row in rows.iterrows():
        identity = (
            _canonical_identifier(row.get(company_column, "")) if company_column else "",
            _canonical_identifier(row.get(name_column, "")) if name_column else "",
        )
        if not any(identity) or identity in seen:
            continue
        seen.add(identity)
        keep_indexes.append(index)
    return rows.loc[keep_indexes].reset_index(drop=True)
