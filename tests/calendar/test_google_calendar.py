from copy import deepcopy
from datetime import date, datetime

import httpx
import pytest

from server.calendar.google_calendar import (
    GoogleCalendarClient,
    GoogleCalendarResponseError,
    map_google_calendar_response,
)


@pytest.fixture
def typical_payload() -> dict[str, object]:
    return {
        "items": [
            {
                "summary": "Later meeting",
                "start": {"dateTime": "2026-10-05T15:00:00+02:00"},
                "end": {"dateTime": "2026-10-05T16:00:00+02:00"},
            },
            {
                "summary": "Conference",
                "start": {"date": "2026-10-07"},
                "end": {"date": "2026-10-08"},
            },
            {
                "summary": "Morning meeting",
                "start": {"dateTime": "2026-10-05T09:00:00+02:00"},
                "end": {"dateTime": "2026-10-05T09:30:00+02:00"},
            },
            {
                "summary": "Recurring stand-up",
                "start": {"dateTime": "2026-10-06T10:00:00+02:00"},
                "end": {"dateTime": "2026-10-06T10:15:00+02:00"},
            },
            {
                "summary": "Recurring stand-up",
                "start": {"dateTime": "2026-10-08T10:00:00+02:00"},
                "end": {"dateTime": "2026-10-08T10:15:00+02:00"},
            },
        ]
    }


def test_maps_typical_week_and_sorts_events(typical_payload: dict[str, object]) -> None:
    week = _map(typical_payload)

    assert week.start == date(2026, 10, 5)
    assert week.end == date(2026, 10, 11)
    assert len(week.days) == 7
    assert [event.title for event in week.days[0].events] == [
        "Morning meeting",
        "Later meeting",
    ]


def test_maps_all_day_event(typical_payload: dict[str, object]) -> None:
    event = _map(typical_payload).days[2].events[0]

    assert event.title == "Conference"
    assert event.all_day is True
    assert event.start == date(2026, 10, 7)
    assert event.end == date(2026, 10, 8)


def test_maps_timed_event_to_warsaw(typical_payload: dict[str, object]) -> None:
    event = _map(typical_payload).days[0].events[0]

    assert event.all_day is False
    assert isinstance(event.start, datetime)
    assert event.start.isoformat() == "2026-10-05T09:00:00+02:00"


def test_recurring_instances_are_preserved(typical_payload: dict[str, object]) -> None:
    week = _map(typical_payload)

    assert week.days[1].events[0].title == "Recurring stand-up"
    assert week.days[3].events[0].title == "Recurring stand-up"


def test_maps_empty_week() -> None:
    week = _map({"items": []})

    assert all(day.events == () for day in week.days)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.pop("items"),
        lambda payload: payload["items"][0].pop("summary"),
        lambda payload: payload["items"][0]["start"].pop("dateTime"),
        lambda payload: payload["items"][0].update({"end": {"date": "2026-10-06"}}),
    ],
)
def test_rejects_incomplete_provider_response(
    typical_payload: dict[str, object], mutation: object
) -> None:
    payload = deepcopy(typical_payload)
    mutation(payload)

    with pytest.raises(GoogleCalendarResponseError):
        _map(payload)


def test_client_requests_only_current_week_and_expands_recurring_events(
    typical_payload: dict[str, object],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["timeMin"] == "2026-10-05T00:00:00+02:00"
        assert request.url.params["timeMax"] == "2026-10-12T00:00:00+02:00"
        assert request.url.params["timeZone"] == "Europe/Warsaw"
        assert request.url.params["singleEvents"] == "true"
        assert request.url.params["orderBy"] == "startTime"
        assert "attendees" not in request.url.params["fields"]
        assert request.headers["Authorization"] == "Bearer test-token"
        return httpx.Response(200, request=request, json=typical_payload)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        week = GoogleCalendarClient(
            access_token="test-token", http_client=http_client
        ).fetch_current_week(current_day=date(2026, 10, 7))

    assert week.current_day == date(2026, 10, 7)
    assert sum(len(day.events) for day in week.days) == 5


def test_client_checks_http_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, request=request, json={"error": {"message": "Forbidden"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = GoogleCalendarClient(access_token="test-token", http_client=http_client)
        with pytest.raises(httpx.HTTPStatusError):
            client.fetch_current_week(current_day=date(2026, 10, 7))


def test_client_reads_all_pages() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                200,
                request=request,
                json={
                    "items": [],
                    "nextPageToken": "next-page",
                },
            )
        assert request.url.params["pageToken"] == "next-page"
        return httpx.Response(200, request=request, json={"items": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        GoogleCalendarClient(access_token="test-token", http_client=http_client).fetch_current_week(
            current_day=date(2026, 10, 7)
        )

    assert len(requests) == 2


def test_multiday_all_day_event_is_assigned_to_each_covered_day() -> None:
    payload = {
        "items": [
            {
                "summary": "Trip",
                "start": {"date": "2026-10-06"},
                "end": {"date": "2026-10-09"},
            }
        ]
    }

    week = _map(payload)

    assert [len(day.events) for day in week.days] == [0, 1, 1, 1, 0, 0, 0]


def _map(payload: object):
    return map_google_calendar_response(
        payload,
        week_start=date(2026, 10, 5),
        current_day=date(2026, 10, 7),
    )
