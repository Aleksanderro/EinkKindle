"""Provider-independent calendar domain models."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """An event displayed on the dashboard.

    All-day events use dates; timed events use datetimes.
    """

    title: str
    start: date | datetime
    end: date | datetime
    all_day: bool

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("event title must be a non-empty string")
        if not isinstance(self.all_day, bool):
            raise TypeError("event all_day must be a bool")

        if self.all_day:
            if type(self.start) is not date or type(self.end) is not date:
                raise TypeError("all-day event start and end must be dates")
        elif not isinstance(self.start, datetime) or not isinstance(self.end, datetime):
            raise TypeError("timed event start and end must be datetimes")

        if self.end <= self.start:
            raise ValueError("event end must be after start")


@dataclass(frozen=True, slots=True)
class CalendarDay:
    """One day and its events in a calendar week."""

    date: date
    is_today: bool
    events: tuple[CalendarEvent, ...] = ()

    def __post_init__(self) -> None:
        if type(self.date) is not date:
            raise TypeError("calendar day date must be a date")
        if not isinstance(self.is_today, bool):
            raise TypeError("calendar day is_today must be a bool")
        if not isinstance(self.events, tuple) or not all(
            isinstance(event, CalendarEvent) for event in self.events
        ):
            raise TypeError("calendar day events must be a tuple of CalendarEvent instances")


@dataclass(frozen=True, slots=True)
class CalendarWeek:
    """A complete Monday-Sunday week consumed by the dashboard renderer."""

    start: date
    end: date
    current_day: date
    days: tuple[
        CalendarDay,
        CalendarDay,
        CalendarDay,
        CalendarDay,
        CalendarDay,
        CalendarDay,
        CalendarDay,
    ]

    def __post_init__(self) -> None:
        if any(type(value) is not date for value in (self.start, self.end, self.current_day)):
            raise TypeError("calendar week start, end, and current_day must be dates")
        if not isinstance(self.days, tuple) or not all(
            isinstance(day, CalendarDay) for day in self.days
        ):
            raise TypeError("calendar week days must be a tuple of CalendarDay instances")
        if len(self.days) != 7:
            raise ValueError("calendar week must contain exactly 7 days")
        if self.start.weekday() != 0 or self.end.weekday() != 6:
            raise ValueError("calendar week must run from Monday to Sunday")
        if self.end != self.start + timedelta(days=6):
            raise ValueError("calendar week end must be 6 days after start")

        expected_dates = tuple(self.start + timedelta(days=offset) for offset in range(7))
        if tuple(day.date for day in self.days) != expected_dates:
            raise ValueError("calendar week days must be 7 consecutive dates from start to end")
        if self.current_day not in expected_dates:
            raise ValueError("calendar week current_day must be within the week")
        if any(day.is_today != (day.date == self.current_day) for day in self.days):
            raise ValueError("exactly current_day must be marked as today")
