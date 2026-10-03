"""Open-Meteo HTTP integration and response mapping."""

from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from server.weather.models import CurrentWeather, DailyForecast, Weather

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoResponseError(ValueError):
    """Raised when Open-Meteo returns a payload that violates the expected contract."""


def map_open_meteo_response(payload: object, *, location_name: str) -> Weather:
    """Map a validated subset of an Open-Meteo response to domain models."""
    root = _mapping(payload, "response")
    current = _mapping(_required(root, "current", "response"), "current")
    hourly = _mapping(_required(root, "hourly", "response"), "hourly")
    daily = _mapping(_required(root, "daily", "response"), "daily")

    utc_offset_seconds = _integer(
        _required(root, "utc_offset_seconds", "response"), "utc_offset_seconds"
    )
    data_time = _datetime(
        _required(current, "time", "current"),
        "current.time",
        utc_offset_seconds=utc_offset_seconds,
    )
    precipitation_probability = _current_precipitation_probability(
        hourly, data_time=data_time, utc_offset_seconds=utc_offset_seconds
    )

    current_weather = CurrentWeather(
        temperature_c=_number(
            _required(current, "temperature_2m", "current"), "current.temperature_2m"
        ),
        apparent_temperature_c=_number(
            _required(current, "apparent_temperature", "current"),
            "current.apparent_temperature",
        ),
        relative_humidity_percent=_percentage(
            _required(current, "relative_humidity_2m", "current"),
            "current.relative_humidity_2m",
        ),
        wind_speed_kmh=_number(
            _required(current, "wind_speed_10m", "current"), "current.wind_speed_10m"
        ),
        precipitation_probability_percent=_percentage(
            precipitation_probability,
            "hourly.precipitation_probability",
        ),
        weather_code=_integer(
            _required(current, "weather_code", "current"), "current.weather_code"
        ),
    )

    dates = _sequence(_required(daily, "time", "daily"), "daily.time")
    minimums = _sequence(
        _required(daily, "temperature_2m_min", "daily"), "daily.temperature_2m_min"
    )
    maximums = _sequence(
        _required(daily, "temperature_2m_max", "daily"), "daily.temperature_2m_max"
    )
    probabilities = _sequence(
        _required(daily, "precipitation_probability_max", "daily"),
        "daily.precipitation_probability_max",
    )
    codes = _sequence(_required(daily, "weather_code", "daily"), "daily.weather_code")

    lengths = {len(dates), len(minimums), len(maximums), len(probabilities), len(codes)}
    if len(lengths) != 1:
        raise OpenMeteoResponseError("daily forecast arrays have different lengths")

    forecasts: list[DailyForecast] = []
    current_date = data_time.date()
    for index, raw_date in enumerate(dates):
        forecast_date = _date(raw_date, f"daily.time[{index}]")
        if forecast_date <= current_date:
            continue
        forecasts.append(
            DailyForecast(
                date=forecast_date,
                temperature_min_c=_number(minimums[index], f"daily.temperature_2m_min[{index}]"),
                temperature_max_c=_number(maximums[index], f"daily.temperature_2m_max[{index}]"),
                precipitation_probability_max_percent=_percentage(
                    probabilities[index], f"daily.precipitation_probability_max[{index}]"
                ),
                weather_code=_integer(codes[index], f"daily.weather_code[{index}]"),
            )
        )
        if len(forecasts) == 3:
            break

    if len(forecasts) != 3:
        raise OpenMeteoResponseError("daily forecast must contain three days after data time")

    return Weather(
        location_name=location_name,
        data_time=data_time,
        current=current_weather,
        daily_forecast=(forecasts[0], forecasts[1], forecasts[2]),
    )


class OpenMeteoClient:
    """Fetch weather from Open-Meteo and expose only domain models."""

    def __init__(
        self,
        *,
        location_name: str,
        latitude: float,
        longitude: float,
        timezone_name: str,
        timeout_seconds: float = 10.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._location_name = location_name
        self._latitude = latitude
        self._longitude = longitude
        self._timezone_name = timezone_name
        self._timeout = httpx.Timeout(timeout_seconds)
        self._http_client = http_client

    def fetch_weather(self) -> Weather:
        """Fetch and map current conditions and the next three daily forecasts."""
        params = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "timezone": self._timezone_name,
            "forecast_days": 4,
            "current": (
                "temperature_2m,apparent_temperature,relative_humidity_2m,"
                "wind_speed_10m,weather_code"
            ),
            "hourly": "precipitation_probability",
            "daily": (
                "temperature_2m_min,temperature_2m_max,precipitation_probability_max,weather_code"
            ),
        }
        if self._http_client is not None:
            response = self._http_client.get(
                OPEN_METEO_FORECAST_URL, params=params, timeout=self._timeout
            )
        else:
            with httpx.Client() as client:
                response = client.get(OPEN_METEO_FORECAST_URL, params=params, timeout=self._timeout)
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as error:
            raise OpenMeteoResponseError("Open-Meteo returned invalid JSON") from error
        return map_open_meteo_response(payload, location_name=self._location_name)


def _required(mapping: Mapping[str, Any], key: str, path: str) -> Any:
    try:
        return mapping[key]
    except KeyError as error:
        raise OpenMeteoResponseError(f"missing required field: {path}.{key}") from error


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OpenMeteoResponseError(f"{path} must be an object")
    return value


def _sequence(value: object, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise OpenMeteoResponseError(f"{path} must be an array")
    return value


def _number(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OpenMeteoResponseError(f"{path} must be a number")
    return float(value)


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OpenMeteoResponseError(f"{path} must be an integer")
    return value


def _percentage(value: object, path: str) -> int:
    percentage = _integer(value, path)
    if not 0 <= percentage <= 100:
        raise OpenMeteoResponseError(f"{path} must be between 0 and 100")
    return percentage


def _current_precipitation_probability(
    hourly: Mapping[str, Any], *, data_time: datetime, utc_offset_seconds: int
) -> object:
    times = _sequence(_required(hourly, "time", "hourly"), "hourly.time")
    probabilities = _sequence(
        _required(hourly, "precipitation_probability", "hourly"),
        "hourly.precipitation_probability",
    )
    if len(times) != len(probabilities):
        raise OpenMeteoResponseError("hourly forecast arrays have different lengths")

    current_hour = data_time.replace(minute=0, second=0, microsecond=0)
    for index, raw_time in enumerate(times):
        forecast_time = _datetime(
            raw_time,
            f"hourly.time[{index}]",
            utc_offset_seconds=utc_offset_seconds,
        )
        if forecast_time == current_hour:
            return probabilities[index]

    raise OpenMeteoResponseError("hourly forecast does not contain the current hour")


def _date(value: object, path: str) -> date:
    if not isinstance(value, str):
        raise OpenMeteoResponseError(f"{path} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise OpenMeteoResponseError(f"{path} must be an ISO date") from error


def _datetime(value: object, path: str, *, utc_offset_seconds: int) -> datetime:
    if not isinstance(value, str):
        raise OpenMeteoResponseError(f"{path} must be an ISO datetime")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise OpenMeteoResponseError(f"{path} must be an ISO datetime") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(seconds=utc_offset_seconds)))
    return parsed
