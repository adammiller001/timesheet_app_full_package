import pandas as pd

from app.auth_users import (
    _find_column,
    _find_user_rows,
    _first_nonblank,
    _get_user_type_for_rows,
    _pin_is_valid,
)


def test_find_column_handles_users_pin_header_variants():
    columns = ["User's Name", "Email", "User's Pin", "Type", "Active"]

    assert _find_column(columns, ["Users Pin", "PIN"]) == "User's Pin"
    assert _find_column(columns, ["Email Address", "Email"]) == "Email"


def test_pin_validation_requires_exactly_four_digits():
    assert _pin_is_valid("1234")
    assert not _pin_is_valid("123")
    assert not _pin_is_valid("12345")
    assert not _pin_is_valid("12A4")


def test_duplicate_user_assignments_share_authentication_values():
    assignments = pd.DataFrame(
        [
            ["worker@example.com", "Worker", "", "User", "", "100", "TRUE"],
            ["worker@example.com", "Worker", "1234", "Admin", "token", "200", "TRUE"],
            ["worker@example.com", "Worker", "9999", "User", "old", "300", "FALSE"],
        ],
        columns=[
            "Email",
            "User Name",
            "User's Pin",
            "Type",
            "Remember Token",
            "Job Number",
            "Active",
        ],
    )

    indexes, _, error = _find_user_rows(assignments, "WORKER@example.com", active_only=True)

    assert error is None
    assert indexes == [0, 1]
    assert _first_nonblank(assignments, indexes, "User's Pin") == "1234"
    assert _get_user_type_for_rows(assignments, indexes) == "Admin"
