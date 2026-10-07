from dataclasses import FrozenInstanceError, fields
from datetime import UTC, date, datetime, timedelta

import pytest

from server.calendar.models import CalendarDay, CalendarEvent, CalendarWeek


def test_models_expose_required_contract_fields() -> None:
    assert {field.name for field in fields(CalendarEvent)} == {"title", "start", "end", "all_day"}
    assert {field.name for field in fields(CalendarDay)} == {"date", "is_today", "events"}
    assert {field.name for field in fields(CalendarWeek)} == {
        "start",
        "end",
        "current_day",
        "days",
    }


def test_empty_week_contains_seven_empty_consecutive_days(empty_week: CalendarWeek) -> None:
    assert len(empty_week.days) == 7
    assert empty_week.days[0].date.weekday() == 0
    assert empty_week.days[-1].date.weekday() == 6
    assert all(day.events == () for day in empty_week.days)
    assert [day.date for day in empty_week.days] == [
        empty_week.start + timedelta(days=offset) for offset in range(7)
    ]


def test_typical_week_supports_multiple_timed_and_all_day_events(
    typical_week: CalendarWeek,
) -> None:
    monday_events = typical_week.days[0].events
    wednesday_event = typical_week.days[2].events[0]

    assert len(monday_events) == 2
    assert all(not event.all_day for event in monday_events)
    assert wednesday_event.all_day is True
    assert type(wednesday_event.start) is date
    assert type(wednesday_event.end) is date


def test_long_event_title_is_preserved(typical_week: CalendarWeek) -> None:
    event = typical_week.days[4].events[0]

    assert len(event.title) > 80
    assert event.title.endswith("available space")


def test_only_current_day_is_marked_as_today(typical_week: CalendarWeek) -> None:
    marked_days = [day.date for day in typical_week.days if day.is_today]

    assert marked_days == [typical_week.current_day]


def test_models_are_immutable(typical_week: CalendarWeek) -> None:
    with pytest.raises(FrozenInstanceError):
        typical_week.current_day = date(2026, 10, 8)


@pytest.mark.parametrize(
    "days",
    [
        tuple(
            CalendarDay(date=date(2026, 10, day_number), is_today=day_number == 7)
            for day_number in range(5, 11)
        ),
        tuple(
            CalendarDay(date=date(2026, 10, day_number), is_today=day_number == 7)
            for day_number in range(5, 12)
        )
        + (CalendarDay(date=date(2026, 10, 12), is_today=False),),
    ],
)
def test_week_rejects_day_count_other_than_seven(days: tuple[CalendarDay, ...]) -> None:
    with pytest.raises(ValueError, match="exactly 7 days"):
        _week(days=days)


def test_week_rejects_non_consecutive_days() -> None:
    days = tuple(
        CalendarDay(
            date=date(2026, 10, day_number if day_number < 10 else day_number + 1),
            is_today=day_number == 7,
        )
        for day_number in range(5, 12)
    )

    with pytest.raises(ValueError, match="7 consecutive dates"):
        _week(days=days)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2026, 10, 6), date(2026, 10, 12)),
        (date(2026, 10, 5), date(2026, 10, 10)),
    ],
)
def test_week_rejects_boundaries_other_than_monday_sunday(start: date, end: date) -> None:
    with pytest.raises(ValueError, match="Monday to Sunday"):
        _week(start=start, end=end)


def test_week_rejects_current_day_outside_week() -> None:
    with pytest.raises(ValueError, match="within the week"):
        _week(current_day=date(2026, 10, 12))


def test_week_rejects_incorrect_today_marker() -> None:
    days = tuple(
        CalendarDay(date=date(2026, 10, day_number), is_today=day_number == 8)
        for day_number in range(5, 12)
    )

    with pytest.raises(ValueError, match="exactly current_day"):
        _week(days=days)


@pytest.mark.parametrize(
    "event",
    [
        lambda: CalendarEvent(
            "",
            datetime(2026, 10, 5, 9, tzinfo=UTC),
            datetime(2026, 10, 5, 10, tzinfo=UTC),
            False,
        ),
        lambda: CalendarEvent(
            "Invalid",
            datetime(2026, 10, 5, 10, tzinfo=UTC),
            datetime(2026, 10, 5, 9, tzinfo=UTC),
            False,
        ),
        lambda: CalendarEvent("Invalid", date(2026, 10, 5), date(2026, 10, 6), False),
        lambda: CalendarEvent(
            "Invalid",
            datetime(2026, 10, 5, 9, tzinfo=UTC),
            datetime(2026, 10, 5, 10, tzinfo=UTC),
            True,
        ),
    ],
)
def test_event_rejects_invalid_contract(event: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        event()


def _week(
    *,
    start: date = date(2026, 10, 5),
    end: date = date(2026, 10, 11),
    current_day: date = date(2026, 10, 7),
    days: tuple[CalendarDay, ...] | None = None,
) -> CalendarWeek:
    if days is None:
        days = tuple(
            CalendarDay(date=date(2026, 10, day_number), is_today=day_number == 7)
            for day_number in range(5, 12)
        )
    return CalendarWeek(start=start, end=end, current_day=current_day, days=days)
