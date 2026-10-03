"""Provider-independent weather domain models."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class CurrentWeather:
    """Weather conditions observed for a location at a point in time."""

    temperature_c: float
    apparent_temperature_c: float
    relative_humidity_percent: int
    wind_speed_kmh: float
    precipitation_probability_percent: int
    weather_code: int


@dataclass(frozen=True, slots=True)
class DailyForecast:
    """Weather forecast aggregated for one day."""

    date: date
    temperature_min_c: float
    temperature_max_c: float
    precipitation_probability_max_percent: int
    weather_code: int


@dataclass(frozen=True, slots=True)
class Weather:
    """Complete weather data consumed by the renderer."""

    location_name: str
    data_time: datetime
    current: CurrentWeather
    daily_forecast: tuple[DailyForecast, DailyForecast, DailyForecast]
