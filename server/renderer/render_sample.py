"""Generate a sample Kindle weather image without network access."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from server.renderer.weather import save_weather_png
from server.weather.models import CurrentWeather, DailyForecast, Weather

OUTPUT_PATH = Path("output/weather.png")


def main() -> None:
    """Render representative domain data to the standard output path."""
    weather = Weather(
        location_name="Pozna\u0144",
        data_time=datetime(2026, 10, 3, 12, 15, tzinfo=timezone(timedelta(hours=2))),
        current=CurrentWeather(
            temperature_c=14.2,
            apparent_temperature_c=13.1,
            relative_humidity_percent=72,
            wind_speed_kmh=11.5,
            precipitation_probability_percent=25,
            weather_code=2,
        ),
        daily_forecast=(
            DailyForecast(date(2026, 10, 4), 7.5, 14.0, 40, 61),
            DailyForecast(date(2026, 10, 5), 6.0, 13.5, 60, 63),
            DailyForecast(date(2026, 10, 6), 5.5, 12.0, 10, 1),
        ),
    )
    save_weather_png(weather, OUTPUT_PATH)
    print(f"Generated {OUTPUT_PATH} ({weather.location_name}, 600x800 monochrome PNG)")


if __name__ == "__main__":
    main()
