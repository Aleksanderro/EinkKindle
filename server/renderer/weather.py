"""Render normalized weather domain data for the Kindle display."""

from dataclasses import dataclass
from pathlib import Path
from unicodedata import normalize

from PIL import Image, ImageDraw, ImageFont

from server.weather.models import Weather

DISPLAY_SIZE = (600, 800)


@dataclass(frozen=True, slots=True)
class WeatherCodeInfo:
    """Presentation details associated with a WMO weather code."""

    description: str
    icon: str


_WEATHER_CODES: dict[int, WeatherCodeInfo] = {
    0: WeatherCodeInfo("Clear sky", "sun"),
    1: WeatherCodeInfo("Mostly clear", "partly_cloudy"),
    2: WeatherCodeInfo("Partly cloudy", "partly_cloudy"),
    3: WeatherCodeInfo("Overcast", "cloud"),
    45: WeatherCodeInfo("Fog", "fog"),
    48: WeatherCodeInfo("Rime fog", "fog"),
    51: WeatherCodeInfo("Light drizzle", "rain"),
    53: WeatherCodeInfo("Drizzle", "rain"),
    55: WeatherCodeInfo("Heavy drizzle", "rain"),
    56: WeatherCodeInfo("Freezing drizzle", "rain"),
    57: WeatherCodeInfo("Freezing drizzle", "rain"),
    61: WeatherCodeInfo("Light rain", "rain"),
    63: WeatherCodeInfo("Rain", "rain"),
    65: WeatherCodeInfo("Heavy rain", "rain"),
    66: WeatherCodeInfo("Freezing rain", "rain"),
    67: WeatherCodeInfo("Freezing rain", "rain"),
    71: WeatherCodeInfo("Light snow", "snow"),
    73: WeatherCodeInfo("Snow", "snow"),
    75: WeatherCodeInfo("Heavy snow", "snow"),
    77: WeatherCodeInfo("Snow grains", "snow"),
    80: WeatherCodeInfo("Rain showers", "rain"),
    81: WeatherCodeInfo("Rain showers", "rain"),
    82: WeatherCodeInfo("Heavy showers", "rain"),
    85: WeatherCodeInfo("Snow showers", "snow"),
    86: WeatherCodeInfo("Heavy snow showers", "snow"),
    95: WeatherCodeInfo("Thunderstorm", "storm"),
    96: WeatherCodeInfo("Thunderstorm with hail", "storm"),
    99: WeatherCodeInfo("Thunderstorm with hail", "storm"),
}

_WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def weather_code_info(code: int) -> WeatherCodeInfo:
    """Return a stable description and icon category for a WMO code."""
    return _WEATHER_CODES.get(code, WeatherCodeInfo("Unknown conditions", "unknown"))


def render_weather(weather: Weather) -> Image.Image:
    """Render weather data as a monochrome 600x800 image."""
    canvas = Image.new("L", DISPLAY_SIZE, color=255)
    draw = ImageDraw.Draw(canvas)
    font = _font(24)
    small = _font(18)
    medium = _font(30)
    large = _font(78)
    forecast_temperature = _font(25)

    draw.text((24, 18), _display_text(weather.location_name), fill=0, font=medium)
    draw.text(
        (24, 59),
        f"Updated {weather.data_time:%Y-%m-%d %H:%M}",
        fill=0,
        font=small,
    )
    draw.line((20, 91, 580, 91), fill=0, width=3)

    current_info = weather_code_info(weather.current.weather_code)
    _draw_weather_icon(draw, current_info.icon, (36, 116, 246, 326), width=6)
    draw.text(
        (410, 174),
        f"{weather.current.temperature_c:.0f} C",
        fill=0,
        font=large,
        anchor="mm",
    )
    draw.text((410, 249), current_info.description, fill=0, font=font, anchor="mm")
    draw.text(
        (410, 288),
        f"Feels like {weather.current.apparent_temperature_c:.0f} C",
        fill=0,
        font=small,
        anchor="mm",
    )

    draw.rounded_rectangle((20, 347, 580, 468), radius=12, outline=0, width=3)
    details = (
        ("HUMIDITY", f"{weather.current.relative_humidity_percent}%"),
        ("WIND", f"{weather.current.wind_speed_kmh:.1f} km/h"),
        ("PRECIPITATION", f"{weather.current.precipitation_probability_percent}%"),
    )
    for index, (label, value) in enumerate(details):
        center_x = 113 + index * 187
        if index:
            divider_x = 20 + index * 187
            draw.line((divider_x, 363, divider_x, 452), fill=0, width=2)
        draw.text((center_x, 372), label, fill=0, font=small, anchor="ma")
        draw.text((center_x, 417), value, fill=0, font=font, anchor="ma")

    draw.text((24, 489), "NEXT 3 DAYS", fill=0, font=font)
    card_width = 180
    for index, day in enumerate(weather.daily_forecast):
        left = 20 + index * 190
        right = left + card_width
        info = weather_code_info(day.weather_code)
        draw.rounded_rectangle((left, 529, right, 780), radius=12, outline=0, width=3)
        draw.text(
            ((left + right) // 2, 548),
            f"{_WEEKDAYS[day.date.weekday()]} {day.date:%d.%m}",
            fill=0,
            font=small,
            anchor="ma",
        )
        _draw_weather_icon(draw, info.icon, (left + 49, 590, right - 49, 678), width=4)
        draw.text(
            ((left + right) // 2, 696),
            f"{day.temperature_max_c:.0f} / {day.temperature_min_c:.0f} C",
            fill=0,
            font=forecast_temperature,
            anchor="ma",
        )
        draw.text(
            ((left + right) // 2, 742),
            f"Rain {day.precipitation_probability_max_percent}%",
            fill=0,
            font=small,
            anchor="ma",
        )

    return canvas.convert("1", dither=Image.Dither.NONE)


def save_weather_png(weather: Weather, output_path: str | Path) -> None:
    """Render weather and save it as a monochrome PNG."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    render_weather(weather).save(path, format="PNG", optimize=True)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _display_text(value: str) -> str:
    """Transliterate text unsupported by Pillow's compact built-in font."""
    return normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def _draw_weather_icon(
    draw: ImageDraw.ImageDraw,
    icon: str,
    bounds: tuple[int, int, int, int],
    *,
    width: int,
) -> None:
    left, top, right, bottom = bounds
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    size = min(right - left, bottom - top)

    if icon == "sun":
        _draw_sun(draw, center_x, center_y, size, width)
    elif icon == "partly_cloudy":
        _draw_sun(draw, center_x - size // 5, center_y - size // 5, size * 2 // 3, width)
        _draw_cloud(draw, left + size // 7, top + size // 3, right, bottom, width)
    elif icon == "cloud":
        _draw_cloud(draw, left, top, right, bottom, width)
    elif icon == "fog":
        _draw_cloud(draw, left, top, right, bottom - size // 4, width)
        for offset in (0, size // 6, size // 3):
            y = bottom - size // 3 + offset
            draw.line((left + size // 8, y, right - size // 8, y), fill=0, width=width)
    elif icon in {"rain", "snow", "storm"}:
        _draw_cloud(draw, left, top, right, bottom - size // 4, width)
        if icon == "rain":
            for offset in (-size // 4, 0, size // 4):
                x = center_x + offset
                draw.line((x, bottom - size // 4, x - size // 12, bottom), fill=0, width=width)
        elif icon == "snow":
            for offset in (-size // 4, 0, size // 4):
                _draw_snowflake(draw, center_x + offset, bottom - size // 8, size // 8, width)
        else:
            points = (
                (center_x + size // 12, bottom - size // 3),
                (center_x - size // 12, bottom - size // 12),
                (center_x + size // 18, bottom - size // 12),
                (center_x - size // 10, bottom + size // 5),
            )
            draw.line(points, fill=0, width=width, joint="curve")
    else:
        draw.ellipse(bounds, outline=0, width=width)
        draw.text((center_x, center_y), "?", fill=0, font=_font(size // 2), anchor="mm")


def _draw_sun(
    draw: ImageDraw.ImageDraw, center_x: int, center_y: int, size: int, width: int
) -> None:
    radius = size // 4
    ray = size // 2
    draw.ellipse(
        (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
        outline=0,
        width=width,
    )
    for delta_x, delta_y in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        inner_x = center_x + delta_x * (radius + width)
        inner_y = center_y + delta_y * (radius + width)
        outer_x = center_x + delta_x * ray
        outer_y = center_y + delta_y * ray
        draw.line((inner_x, inner_y, outer_x, outer_y), fill=0, width=width)


def _draw_cloud(
    draw: ImageDraw.ImageDraw, left: int, top: int, right: int, bottom: int, width: int
) -> None:
    cloud_width = right - left
    cloud_height = bottom - top
    base_top = top + cloud_height // 2
    draw.rounded_rectangle(
        (left + cloud_width // 10, base_top, right - cloud_width // 10, bottom),
        radius=cloud_height // 4,
        fill=255,
        outline=0,
        width=width,
    )
    draw.ellipse(
        (
            left + cloud_width // 5,
            top + cloud_height // 4,
            left + cloud_width * 3 // 5,
            top + cloud_height * 3 // 4,
        ),
        fill=255,
        outline=0,
        width=width,
    )
    draw.ellipse(
        (
            left + cloud_width * 2 // 5,
            top,
            right - cloud_width // 8,
            top + cloud_height * 3 // 4,
        ),
        fill=255,
        outline=0,
        width=width,
    )
    draw.line(
        (left + cloud_width // 5, bottom, right - cloud_width // 5, bottom),
        fill=0,
        width=width,
    )


def _draw_snowflake(
    draw: ImageDraw.ImageDraw, center_x: int, center_y: int, radius: int, width: int
) -> None:
    draw.line((center_x - radius, center_y, center_x + radius, center_y), fill=0, width=width)
    draw.line((center_x, center_y - radius, center_x, center_y + radius), fill=0, width=width)
    draw.line(
        (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
        fill=0,
        width=width,
    )
    draw.line(
        (center_x - radius, center_y + radius, center_x + radius, center_y - radius),
        fill=0,
        width=width,
    )
