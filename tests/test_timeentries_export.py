from app.exports.timeentries_export import build_daily_import_rate_cells


def test_subsistence_rate_only_goes_on_subsistence_line():
    regular_rate, subsistence_rate = build_daily_import_rate_cells(
        night_shift="",
        premium_rate="",
        subsistence_rate="225",
        travel_rate="",
    )

    assert regular_rate == ""
    assert subsistence_rate == "225"


def test_regular_rate_uses_premium_or_travel_not_subsistence():
    premium_regular_rate, premium_subsistence_rate = build_daily_import_rate_cells(
        night_shift="",
        premium_rate="PREM",
        subsistence_rate="225",
        travel_rate="TRAVEL",
    )
    travel_regular_rate, travel_subsistence_rate = build_daily_import_rate_cells(
        night_shift="",
        premium_rate="",
        subsistence_rate="225",
        travel_rate="TRAVEL",
    )

    assert premium_regular_rate == "PREM"
    assert premium_subsistence_rate == "225"
    assert travel_regular_rate == "TRAVEL"
    assert travel_subsistence_rate == "225"


def test_night_shift_keeps_ns_rate_indicator():
    regular_rate, subsistence_rate = build_daily_import_rate_cells(
        night_shift="Y",
        premium_rate="PREM",
        subsistence_rate="225",
        travel_rate="TRAVEL",
    )

    assert regular_rate == "NS"
    assert subsistence_rate == "NS"
