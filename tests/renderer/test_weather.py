from datetime import UTC, date, datetime
from hashlib import sha256
from io import BytesIO

from PIL import Image

from server.renderer.weather import DISPLAY_SIZE, render_weather, weather_code_info
from server.weather.models import CurrentWeather, DailyForecast, Weather


def test_render_weather_creates_monochrome_600x800_png() -> None:
    image = render_weather(_weather())
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    with Image.open(output) as rendered:
        assert rendered.size == DISPLAY_SIZE == (600, 800)
        assert rendered.format == "PNG"
        assert rendered.mode == "1"
        assert rendered.getextrema() == (0, 255)


def test_rendering_is_deterministic() -> None:
    first = BytesIO()
    second = BytesIO()
    render_weather(_weather()).save(first, format="PNG")
    render_weather(_weather()).save(second, format="PNG")

    assert sha256(first.getvalue()).digest() == sha256(second.getvalue()).digest()


def test_maps_weather_codes_to_descriptions_and_icons() -> None:
    assert weather_code_info(0).description == "Clear sky"
    assert weather_code_info(0).icon == "sun"
    assert weather_code_info(63).icon == "rain"
    assert weather_code_info(75).icon == "snow"
    assert weather_code_info(95).icon == "storm"
    assert weather_code_info(999).description == "Unknown conditions"
    assert weather_code_info(999).icon == "unknown"


def _weather() -> Weather:
    return Weather(
        location_name="Pozna\u0144",
        data_time=datetime(2026, 10, 3, 12, 15, tzinfo=UTC),
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
            DailyForecast(date(2026, 10, 5), 6.0, 13.5, 60, 71),
            DailyForecast(date(2026, 10, 6), 5.5, 12.0, 10, 95),
        ),
    )
