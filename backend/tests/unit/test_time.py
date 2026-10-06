from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.time import NaiveDatetimeError, to_local, to_utc

BA = timezone(timedelta(hours=-3))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2026, 10, 6, 10, 0, tzinfo=BA), datetime(2026, 10, 6, 13, 0, tzinfo=UTC)),
        (datetime(2026, 10, 6, 13, 0, tzinfo=UTC), datetime(2026, 10, 6, 13, 0, tzinfo=UTC)),
        (datetime(2026, 10, 6, 23, 0, tzinfo=BA), datetime(2026, 10, 7, 2, 0, tzinfo=UTC)),
    ],
)
def test_to_utc_aware_datetime_returns_same_instant_in_utc(
    value: datetime, expected: datetime
) -> None:
    result = to_utc(value)

    assert result == expected
    assert result.utcoffset() == timedelta(0)
    assert result.tzinfo is UTC


@pytest.mark.parametrize(
    ("value", "expected_wall", "expected_offset"),
    [
        (datetime(2026, 10, 6, 13, 0, tzinfo=UTC), datetime(2026, 10, 6, 10, 0), -3),
        (datetime(2026, 10, 7, 1, 30, tzinfo=UTC), datetime(2026, 10, 6, 22, 30), -3),
    ],
)
def test_to_local_utc_datetime_returns_buenos_aires_wall_time(
    value: datetime, expected_wall: datetime, expected_offset: int
) -> None:
    result = to_local(value)

    assert result.replace(tzinfo=None) == expected_wall
    assert result.utcoffset() == timedelta(hours=expected_offset)
    assert result == value


def test_to_local_accepts_explicit_timezone_name() -> None:
    result = to_local(datetime(2026, 10, 6, 13, 0, tzinfo=UTC), "UTC")

    assert result.utcoffset() == timedelta(0)


@pytest.mark.parametrize("func", [to_utc, to_local])
def test_naive_datetime_raises_naive_datetime_error(func) -> None:
    with pytest.raises(NaiveDatetimeError, match="zona horaria"):
        func(datetime(2026, 10, 6, 10, 0))


def test_naive_datetime_error_is_a_value_error() -> None:
    assert issubclass(NaiveDatetimeError, ValueError)
