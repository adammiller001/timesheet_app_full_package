from app.auth_users import _find_column, _pin_is_valid


def test_find_column_handles_users_pin_header_variants():
    columns = ["User's Name", "Email", "User's Pin", "Type", "Active"]

    assert _find_column(columns, ["Users Pin", "PIN"]) == "User's Pin"
    assert _find_column(columns, ["Email Address", "Email"]) == "Email"


def test_pin_validation_requires_exactly_four_digits():
    assert _pin_is_valid("1234")
    assert not _pin_is_valid("123")
    assert not _pin_is_valid("12345")
    assert not _pin_is_valid("12A4")
