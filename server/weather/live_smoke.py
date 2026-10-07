"""Manual live smoke test for the Open-Meteo integration.

Run from the repository root with:
    python -m server.weather.live_smoke
"""

from server.weather.models import Weather
from server.weather.open_meteo import OpenMeteoClient


def format_weather(weather: Weather) -> str:
    """Format normalized domain data without exposing the provider payload."""
    current = weather.current
    lines = [
        f"Location: {weather.location_name}",
        f"Data time: {weather.data_time.isoformat()}",
        "Current weather:",
        f"  Temperature: {current.temperature_c:.1f} deg C",
        f"  Feels like: {current.apparent_temperature_c:.1f} deg C",
        f"  Humidity: {current.relative_humidity_percent}%",
        f"  Wind speed: {current.wind_speed_kmh:.1f} km/h",
        f"  Precipitation probability: {current.precipitation_probability_percent}%",
        f"  Weather code: {current.weather_code}",
        "Next 3 days:",
    ]
    for day in weather.daily_forecast:
        lines.append(
            f"  {day.date.isoformat()}: "
            f"min {day.temperature_min_c:.1f} deg C, "
            f"max {day.temperature_max_c:.1f} deg C, "
            f"precipitation {day.precipitation_probability_max_percent}%, "
            f"code {day.weather_code}"
        )
    return "\n".join(lines)


def main() -> None:
    """Fetch and print one live weather snapshot for Poznan."""
    client = OpenMeteoClient(
        location_name="Pozna\u0144",
        latitude=52.4064,
        longitude=16.9252,
        timezone_name="Europe/Warsaw",
    )
    print(format_weather(client.fetch_weather()))


if __name__ == "__main__":
    main()
