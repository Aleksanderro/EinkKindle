"""Google Calendar HTTP integration and domain mapping."""

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time, timedelta, timezone, tzinfo
from typing import Any
from urllib.parse import quote

import httpx

from server.calendar.models import CalendarDay, CalendarEvent, CalendarWeek

GOOGLE_CALENDAR_API_URL = "https://www.googleapis.com/calendar/v3/calendars"
WARSAW_TIMEZONE = "Europe/Warsaw"


class GoogleCalendarResponseError(ValueError):
    """Raised when Google Calendar returns an invalid or incomplete payload."""


def map_google_calendar_response(
    payload: object, *, week_start: date, current_day: date
) -> CalendarWeek:
    """Map one normalized Google events-list payload to a calendar week."""
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")
    week_end = week_start + timedelta(days=6)
    if not week_start <= current_day <= week_end:
        raise ValueError("current_day must be within the requested week")

    root = _mapping(payload, "response")
    raw_items = _sequence(_required(root, "items", "response"), "response.items")
    events = tuple(_map_event(item, index) for index, item in enumerate(raw_items))

    days = []
    for offset in range(7):
        day_date = week_start + timedelta(days=offset)
        day_events = tuple(
            sorted(
                (event for event in events if _event_occurs_on(event, day_date)),
                key=_event_sort_key,
            )
        )
        days.append(
            CalendarDay(
                date=day_date,
                is_today=day_date == current_day,
                events=day_events,
            )
        )

    return CalendarWeek(
        start=week_start,
        end=week_end,
        current_day=current_day,
        days=tuple(days),  # type: ignore[arg-type]
    )


class GoogleCalendarClient:
    """Fetch the current Warsaw week and return only domain models."""

    def __init__(
        self,
        *,
        access_token: str,
        calendar_id: str = "primary",
        timeout_seconds: float = 10.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not access_token:
            raise ValueError("access_token must not be empty")
        if not calendar_id:
            raise ValueError("calendar_id must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._access_token = access_token
        self._calendar_id = calendar_id
        self._timeout = httpx.Timeout(timeout_seconds)
        self._http_client = http_client

    def fetch_current_week(self, *, current_day: date | None = None) -> CalendarWeek:
        """Fetch Monday-Sunday events, expanding recurring event instances."""
        if current_day is None:
            current_day = _today_in_warsaw()
        week_start = current_day - timedelta(days=current_day.weekday())
        week_end_exclusive = week_start + timedelta(days=7)
        params = {
            "timeMin": _week_boundary(week_start).isoformat(),
            "timeMax": _week_boundary(week_end_exclusive).isoformat(),
            "timeZone": WARSAW_TIMEZONE,
            "singleEvents": "true",
            "orderBy": "startTime",
            "showDeleted": "false",
            "fields": "nextPageToken,items(summary,start(date,dateTime,timeZone),end(date,dateTime,timeZone))",
        }
        url = f"{GOOGLE_CALENDAR_API_URL}/{quote(self._calendar_id, safe='')}/events"

        if self._http_client is not None:
            items = self._fetch_all_items(self._http_client, url, params)
        else:
            with httpx.Client() as client:
                items = self._fetch_all_items(client, url, params)

        return map_google_calendar_response(
            {"items": items}, week_start=week_start, current_day=current_day
        )

    def _fetch_all_items(
        self, client: httpx.Client, url: str, base_params: Mapping[str, str]
    ) -> list[object]:
        items: list[object] = []
        page_token: str | None = None
        while True:
            params = dict(base_params)
            if page_token is not None:
                params["pageToken"] = page_token
            response = client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as error:
                raise GoogleCalendarResponseError(
                    "Google Calendar returned invalid JSON"
                ) from error

            root = _mapping(payload, "response")
            page_items = _sequence(_required(root, "items", "response"), "response.items")
            items.extend(page_items)
            raw_page_token = root.get("nextPageToken")
            if raw_page_token is None:
                return items
            if not isinstance(raw_page_token, str) or not raw_page_token:
                raise GoogleCalendarResponseError("response.nextPageToken must be a string")
            page_token = raw_page_token


def _map_event(value: object, index: int) -> CalendarEvent:
    path = f"response.items[{index}]"
    item = _mapping(value, path)
    title = _required(item, "summary", path)
    if not isinstance(title, str) or not title.strip():
        raise GoogleCalendarResponseError(f"{path}.summary must be a non-empty string")
    start = _mapping(_required(item, "start", path), f"{path}.start")
    end = _mapping(_required(item, "end", path), f"{path}.end")

    start_is_date = "date" in start
    end_is_date = "date" in end
    start_is_datetime = "dateTime" in start
    end_is_datetime = "dateTime" in end
    if start_is_date and end_is_date and not start_is_datetime and not end_is_datetime:
        return CalendarEvent(
            title=title,
            start=_parse_date(start["date"], f"{path}.start.date"),
            end=_parse_date(end["date"], f"{path}.end.date"),
            all_day=True,
        )
    if start_is_datetime and end_is_datetime and not start_is_date and not end_is_date:
        return CalendarEvent(
            title=title,
            start=_parse_datetime(start, f"{path}.start"),
            end=_parse_datetime(end, f"{path}.end"),
            all_day=False,
        )
    raise GoogleCalendarResponseError(
        f"{path} start and end must both contain date or both contain dateTime"
    )


def _parse_date(value: object, path: str) -> date:
    if not isinstance(value, str):
        raise GoogleCalendarResponseError(f"{path} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise GoogleCalendarResponseError(f"{path} must be an ISO date") from error


def _parse_datetime(value: Mapping[str, Any], path: str) -> datetime:
    raw_datetime = _required(value, "dateTime", path)
    if not isinstance(raw_datetime, str):
        raise GoogleCalendarResponseError(f"{path}.dateTime must be an ISO datetime")
    try:
        parsed = datetime.fromisoformat(raw_datetime)
    except ValueError as error:
        raise GoogleCalendarResponseError(f"{path}.dateTime must be an ISO datetime") from error
    if parsed.tzinfo is None:
        if value.get("timeZone") != WARSAW_TIMEZONE:
            raise GoogleCalendarResponseError(
                f"{path}.dateTime must include an offset or Europe/Warsaw timeZone"
            )
        parsed = parsed.replace(tzinfo=_warsaw_timezone_for_local_datetime(parsed))
    return _to_warsaw(parsed)


def _event_occurs_on(event: CalendarEvent, day: date) -> bool:
    if event.all_day:
        assert type(event.start) is date and type(event.end) is date
        return event.start <= day < event.end
    assert isinstance(event.start, datetime) and isinstance(event.end, datetime)
    event_start = _to_warsaw(event.start)
    event_end = _to_warsaw(event.end)
    final_day = (event_end - timedelta(microseconds=1)).date()
    return event_start.date() <= day <= final_day


def _event_sort_key(event: CalendarEvent) -> tuple[int, datetime]:
    if event.all_day:
        assert type(event.start) is date
        return (
            0,
            datetime.combine(event.start, time.min, _warsaw_timezone_for_local_date(event.start)),
        )
    assert isinstance(event.start, datetime)
    return (1, _to_warsaw(event.start))


def _week_boundary(value: date) -> datetime:
    return datetime.combine(value, time.min, _warsaw_timezone_for_local_date(value))


def _today_in_warsaw() -> date:
    now_utc = datetime.now(UTC)
    return _to_warsaw(now_utc).date()


def _to_warsaw(value: datetime) -> datetime:
    value_utc = value.astimezone(UTC)
    return value_utc.astimezone(_warsaw_timezone_for_utc(value_utc))


def _warsaw_timezone_for_local_date(value: date) -> tzinfo:
    return _warsaw_timezone_for_local_datetime(datetime.combine(value, time(12)))


def _warsaw_timezone_for_local_datetime(value: datetime) -> tzinfo:
    dst_start = datetime.combine(_last_sunday(value.year, 3), time(3))
    dst_end = datetime.combine(_last_sunday(value.year, 10), time(3))
    offset_hours = 2 if dst_start <= value < dst_end else 1
    return timezone(timedelta(hours=offset_hours), WARSAW_TIMEZONE)


def _warsaw_timezone_for_utc(value: datetime) -> tzinfo:
    dst_start = datetime.combine(_last_sunday(value.year, 3), time(1), UTC)
    dst_end = datetime.combine(_last_sunday(value.year, 10), time(1), UTC)
    offset_hours = 2 if dst_start <= value < dst_end else 1
    return timezone(timedelta(hours=offset_hours), WARSAW_TIMEZONE)


def _last_sunday(year: int, month: int) -> date:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    return last_day - timedelta(days=(last_day.weekday() + 1) % 7)


def _required(mapping: Mapping[str, Any], key: str, path: str) -> Any:
    try:
        return mapping[key]
    except KeyError as error:
        raise GoogleCalendarResponseError(f"missing required field: {path}.{key}") from error


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GoogleCalendarResponseError(f"{path} must be an object")
    return value


def _sequence(value: object, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise GoogleCalendarResponseError(f"{path} must be an array")
    return value
