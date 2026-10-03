from copy import deepcopy
from dataclasses import fields
from datetime import date, timedelta

import httpx
import pytest

from server.weather.models import CurrentWeather, DailyForecast, Weather
from server.weather.open_meteo import (
    OPEN_METEO_FORECAST_URL,
    OpenMeteoClient,
    OpenMeteoResponseError,
    map_open_meteo_response,
)


@pytest.fixture
def valid_payload() -> dict[str, object]:
    return {
        "utc_offset_seconds": 7200,
        "current": {
            "time": "2026-10-03T12:15",
            "temperature_2m": 14.2,
            "apparent_temperature": 13.1,
            "relative_humidity_2m": 72,
            "wind_speed_10m": 11.5,
            "weather_code": 3,
        },
        "hourly": {
            "time": ["2026-10-03T11:00", "2026-10-03T12:00", "2026-10-03T13:00"],
            "precipitation_probability": [10, 25, 30],
        },
        "daily": {
            "time": ["2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06"],
            "temperature_2m_min": [8.0, 7.5, 6.0, 5.5],
            "temperature_2m_max": [15.0, 14.0, 13.5, 12.0],
            "precipitation_probability_max": [20, 40, 60, 10],
            "weather_code": [2, 61, 63, 1],
        },
    }


def test_maps_valid_open_meteo_response(valid_payload: dict[str, object]) -> None:
    weather = map_open_meteo_response(valid_payload, location_name="Warsaw")

    assert weather.location_name == "Warsaw"
    assert weather.data_time.isoformat() == "2026-10-03T12:15:00+02:00"
    assert weather.data_time.utcoffset() == timedelta(hours=2)
    assert weather.current == CurrentWeather(
        temperature_c=14.2,
        apparent_temperature_c=13.1,
        relative_humidity_percent=72,
        wind_speed_kmh=11.5,
        precipitation_probability_percent=25,
        weather_code=3,
    )
    assert weather.daily_forecast == (
        DailyForecast(date(2026, 10, 4), 7.5, 14.0, 40, 61),
        DailyForecast(date(2026, 10, 5), 6.0, 13.5, 60, 63),
        DailyForecast(date(2026, 10, 6), 5.5, 12.0, 10, 1),
    )


def test_domain_models_expose_all_required_fields() -> None:
    assert {field.name for field in fields(CurrentWeather)} == {
        "temperature_c",
        "apparent_temperature_c",
        "relative_humidity_percent",
        "wind_speed_kmh",
        "precipitation_probability_percent",
        "weather_code",
    }
    assert {field.name for field in fields(DailyForecast)} == {
        "date",
        "temperature_min_c",
        "temperature_max_c",
        "precipitation_probability_max_percent",
        "weather_code",
    }
    assert {field.name for field in fields(Weather)} == {
        "location_name",
        "data_time",
        "current",
        "daily_forecast",
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload["current"].pop("temperature_2m"), "temperature_2m"),
        (lambda payload: payload["daily"].pop("weather_code"), "weather_code"),
        (lambda payload: payload["hourly"].pop("time"), "hourly.time"),
        (
            lambda payload: payload["daily"]["temperature_2m_min"].pop(),
            "different lengths",
        ),
        (lambda payload: payload["current"].update({"relative_humidity_2m": "72"}), "must be"),
    ],
)
def test_rejects_incomplete_or_invalid_provider_response(
    valid_payload: dict[str, object], mutation: object, message: str
) -> None:
    payload = deepcopy(valid_payload)
    mutation(payload)

    with pytest.raises(OpenMeteoResponseError, match=message):
        map_open_meteo_response(payload, location_name="Warsaw")


def test_client_checks_http_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = _client(http_client)
        with pytest.raises(httpx.HTTPStatusError):
            client.fetch_weather()


def test_client_propagates_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = _client(http_client)
        with pytest.raises(httpx.ReadTimeout):
            client.fetch_weather()


def test_client_sends_location_timezone_and_explicit_timeout(
    valid_payload: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_timeout: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.copy_with(query=None) == httpx.URL(OPEN_METEO_FORECAST_URL)
        assert request.url.params["latitude"] == "52.2297"
        assert request.url.params["longitude"] == "21.0122"
        assert request.url.params["timezone"] == "Europe/Warsaw"
        assert request.url.params["forecast_days"] == "4"
        assert request.url.params["hourly"] == "precipitation_probability"
        return httpx.Response(200, request=request, json=valid_payload)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        original_get = http_client.get

        def recording_get(*args: object, **kwargs: object) -> httpx.Response:
            captured_timeout.append(kwargs["timeout"])
            return original_get(*args, **kwargs)

        monkeypatch.setattr(http_client, "get", recording_get)
        weather = _client(http_client).fetch_weather()

    assert weather.location_name == "Warsaw"
    assert isinstance(captured_timeout[0], httpx.Timeout)


def _client(http_client: httpx.Client) -> OpenMeteoClient:
    return OpenMeteoClient(
        location_name="Warsaw",
        latitude=52.2297,
        longitude=21.0122,
        timezone_name="Europe/Warsaw",
        timeout_seconds=3.0,
        http_client=http_client,
    )
