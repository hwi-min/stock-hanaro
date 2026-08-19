from datetime import datetime, timezone

from app.repositories.dashboard import current_week_bounds_utc


def test_current_week_bounds_use_korean_monday_to_sunday():
    start, end = current_week_bounds_utc(datetime(2026, 8, 18, 3, 0, tzinfo=timezone.utc))

    assert start == datetime(2026, 8, 16, 15, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 8, 23, 15, 0, tzinfo=timezone.utc)


def test_current_week_bounds_handle_month_boundary():
    start, end = current_week_bounds_utc(datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc))

    assert start == datetime(2026, 8, 30, 15, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 9, 6, 15, 0, tzinfo=timezone.utc)
