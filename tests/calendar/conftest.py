from datetime import UTC, date, datetime

import pytest

from server.calendar.models import CalendarDay, CalendarEvent, CalendarWeek


@pytest.fixture
def typical_week() -> CalendarWeek:
    monday = date(2026, 10, 5)
    events_by_day = {
        monday: (
            CalendarEvent(
                title="Team sync",
                start=datetime(2026, 10, 5, 9, 0, tzinfo=UTC),
                end=datetime(2026, 10, 5, 9, 30, tzinfo=UTC),
                all_day=False,
            ),
            CalendarEvent(
                title="Dentist",
                start=datetime(2026, 10, 5, 15, 0, tzinfo=UTC),
                end=datetime(2026, 10, 5, 16, 0, tzinfo=UTC),
                all_day=False,
            ),
        ),
        date(2026, 10, 7): (
            CalendarEvent(
                title="Conference",
                start=date(2026, 10, 7),
                end=date(2026, 10, 8),
                all_day=True,
            ),
        ),
        date(2026, 10, 9): (
            CalendarEvent(
                title=(
                    "A deliberately long event title that the future dashboard renderer "
                    "will need to fit within the available space"
                ),
                start=datetime(2026, 10, 9, 13, 0, tzinfo=UTC),
                end=datetime(2026, 10, 9, 14, 30, tzinfo=UTC),
                all_day=False,
            ),
        ),
    }
    current_day = date(2026, 10, 7)
    days = tuple(
        CalendarDay(
            date=date(2026, 10, day_number),
            is_today=day_number == 7,
            events=events_by_day.get(date(2026, 10, day_number), ()),
        )
        for day_number in range(5, 12)
    )
    return CalendarWeek(
        start=monday,
        end=date(2026, 10, 11),
        current_day=current_day,
        days=days,
    )


@pytest.fixture
def empty_week() -> CalendarWeek:
    monday = date(2026, 10, 5)
    days = tuple(
        CalendarDay(
            date=date(2026, 10, day_number),
            is_today=day_number == 7,
        )
        for day_number in range(5, 12)
    )
    return CalendarWeek(
        start=monday,
        end=date(2026, 10, 11),
        current_day=date(2026, 10, 7),
        days=days,
    )
