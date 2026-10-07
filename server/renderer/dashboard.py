"""Monochrome weather and calendar dashboard renderer."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from server.calendar.models import CalendarDay, CalendarEvent, CalendarWeek
from server.weather.models import WeatherSnapshot

DISPLAY_SIZE = (600, 800)
WEATHER_HEIGHT = 160
CALENDAR_ROW_HEIGHT = 91
DAY_COLUMN_WIDTH = 118
MAX_VISIBLE_EVENTS = 3

_WEEKDAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")
_POLISH_GLYPHS = {
    "ą": ("a", "ogonek"),
    "ć": ("c", "acute"),
    "ę": ("e", "ogonek"),
    "ł": ("l", "stroke"),
    "ń": ("n", "acute"),
    "ó": ("o", "acute"),
    "ś": ("s", "acute"),
    "ź": ("z", "acute"),
    "ż": ("z", "dot"),
    "Ą": ("A", "ogonek"),
    "Ć": ("C", "acute"),
    "Ę": ("E", "ogonek"),
    "Ł": ("L", "stroke"),
    "Ń": ("N", "acute"),
    "Ó": ("O", "acute"),
    "Ś": ("S", "acute"),
    "Ź": ("Z", "acute"),
    "Ż": ("Z", "dot"),
}


@dataclass(frozen=True, slots=True)
class WeatherCodeInfo:
    """Provider-independent presentation for a WMO weather code."""

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
    96: WeatherCodeInfo("Storm with hail", "storm"),
    99: WeatherCodeInfo("Storm with hail", "storm"),
}


def weather_code_info(code: int) -> WeatherCodeInfo:
    """Map a WMO weather code to dashboard presentation data."""
    return _WEATHER_CODES.get(code, WeatherCodeInfo("Unknown conditions", "unknown"))


def render_dashboard(weather: WeatherSnapshot, calendar: CalendarWeek) -> Image.Image:
    """Render a complete 600x800 one-bit weather and calendar dashboard."""
    image = Image.new("L", DISPLAY_SIZE, 255)
    draw = ImageDraw.Draw(image)
    _draw_weather(draw, weather)
    _draw_calendar(draw, calendar)
    return image.convert("1", dither=Image.Dither.NONE)


def save_dashboard_png(
    weather: WeatherSnapshot, calendar: CalendarWeek, output_path: str | Path
) -> None:
    """Render and save a dashboard as a PNG file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    render_dashboard(weather, calendar).save(path, format="PNG", optimize=True)


def _draw_weather(draw: ImageDraw.ImageDraw, weather: WeatherSnapshot) -> None:
    current = weather.current
    info = weather_code_info(current.weather_code)
    _draw_localized_text(draw, (18, 12), weather.location_name, font=_font(25), fill=0)
    draw.text(
        (582, 14),
        f"Updated {weather.data_time:%d.%m %H:%M}",
        font=_font(15),
        fill=0,
        anchor="ra",
    )
    _draw_weather_icon(draw, info.icon, (20, 52, 102, 136))
    draw.text((118, 48), f"{current.temperature_c:.0f} C", font=_font(54), fill=0)
    draw.text((280, 49), info.description, font=_font(22), fill=0)
    draw.text(
        (280, 80),
        f"Feels {current.apparent_temperature_c:.0f} C  |  Rain {current.precipitation_probability_percent}%",
        font=_font(17),
        fill=0,
    )
    draw.text(
        (280, 108),
        f"Wind {current.wind_speed_kmh:.1f} km/h  |  Humidity {current.relative_humidity_percent}%",
        font=_font(17),
        fill=0,
    )
    draw.line((0, WEATHER_HEIGHT - 2, 599, WEATHER_HEIGHT - 2), fill=0, width=4)


def _draw_calendar(draw: ImageDraw.ImageDraw, calendar: CalendarWeek) -> None:
    for index, day in enumerate(calendar.days):
        top = WEATHER_HEIGHT + index * CALENDAR_ROW_HEIGHT
        bottom = min(top + CALENDAR_ROW_HEIGHT, DISPLAY_SIZE[1] - 1)
        _draw_day_label(draw, day, top, bottom)
        _draw_events(draw, day, top)
        draw.line((0, bottom, 599, bottom), fill=0, width=2)


def _draw_day_label(draw: ImageDraw.ImageDraw, day: CalendarDay, top: int, bottom: int) -> None:
    if day.is_today:
        draw.rectangle((0, top, DAY_COLUMN_WIDTH, bottom), fill=0)
        fill = 255
        draw.text((10, top + 7), "TODAY", font=_font(13), fill=fill)
        name_y = top + 27
    else:
        fill = 0
        name_y = top + 13

    draw.text((10, name_y), _WEEKDAYS[day.date.weekday()], font=_font(17), fill=fill)
    draw.text((10, name_y + 28), day.date.strftime("%d.%m"), font=_font(23), fill=fill)
    draw.line((DAY_COLUMN_WIDTH, top, DAY_COLUMN_WIDTH, bottom), fill=0, width=3)


def _draw_events(draw: ImageDraw.ImageDraw, day: CalendarDay, top: int) -> None:
    events = day.events
    if not events:
        draw.text((134, top + 32), "No events", font=_font(17), fill=0)
        return

    visible_count = min(len(events), MAX_VISIBLE_EVENTS)
    if len(events) > MAX_VISIBLE_EVENTS:
        visible_count = MAX_VISIBLE_EVENTS - 1

    for index, event in enumerate(events[:visible_count]):
        y = top + 8 + index * 27
        _draw_event(draw, event, y)

    hidden_count = len(events) - visible_count
    if hidden_count:
        y = top + 8 + visible_count * 27
        draw.text((134, y), f"+{hidden_count}", font=_font(18), fill=0)


def _draw_event(draw: ImageDraw.ImageDraw, event: CalendarEvent, y: int) -> None:
    font = _font(17)
    if event.all_day:
        label = "ALL DAY"
        label_width = int(draw.textlength(label, font=font)) + 12
        draw.rounded_rectangle((132, y - 1, 132 + label_width, y + 22), radius=3, fill=0)
        draw.text((138, y + 1), label, font=font, fill=255)
        title_x = 142 + label_width
    else:
        assert isinstance(event.start, datetime)
        draw.text((132, y), event.start.strftime("%H:%M"), font=font, fill=0)
        title_x = 190

    available_width = 586 - title_x
    title = _fit_text(draw, event.title, font, available_width)
    _draw_localized_text(draw, (title_x, y), title, font=font, fill=0)


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> str:
    if _localized_text_length(draw, text, font) <= max_width:
        return text
    suffix = "..."
    low = 0
    high = len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if _localized_text_length(draw, text[:middle] + suffix, font) <= max_width:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip() + suffix


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _localized_text_length(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> float:
    return draw.textlength(
        "".join(_POLISH_GLYPHS.get(char, (char, ""))[0] for char in text), font=font
    )


def _draw_localized_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    *,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: int,
) -> None:
    """Draw Polish glyphs using the compact built-in font plus local diacritics."""
    cursor_x, y = position
    mark_width = max(1, round(getattr(font, "size", 16) / 12))
    for char in text:
        base, mark = _POLISH_GLYPHS.get(char, (char, ""))
        draw.text((cursor_x, y), base, font=font, fill=fill)
        if mark:
            bounds = draw.textbbox((cursor_x, y), base, font=font)
            _draw_diacritic(draw, bounds, mark, fill=fill, width=mark_width)
        cursor_x += draw.textlength(base, font=font)


def _draw_diacritic(
    draw: ImageDraw.ImageDraw,
    bounds: tuple[int, int, int, int],
    mark: str,
    *,
    fill: int,
    width: int,
) -> None:
    left, top, right, bottom = bounds
    center_x = (left + right) // 2
    if mark == "acute":
        draw.line((center_x, top - 1, center_x + 4, top - 5), fill=fill, width=width)
    elif mark == "dot":
        draw.ellipse((center_x - 1, top - 4, center_x + 1, top - 2), fill=fill)
    elif mark == "stroke":
        center_y = (top + bottom) // 2
        draw.line((left, center_y + 2, right, center_y - 2), fill=fill, width=width)
    elif mark == "ogonek":
        draw.line(
            (right - 3, bottom - 1, right - 1, bottom + 3, right - 4, bottom + 5),
            fill=fill,
            width=width,
        )


def _draw_weather_icon(
    draw: ImageDraw.ImageDraw, icon: str, bounds: tuple[int, int, int, int]
) -> None:
    left, top, right, bottom = bounds
    size = min(right - left, bottom - top)
    width = 4

    if icon == "sun":
        _draw_sun(draw, (left + right) // 2, (top + bottom) // 2, size - 8, width)
        return
    if icon == "partly_cloudy":
        _draw_sun(draw, left + 28, top + 27, size // 2, width)
        _draw_cloud(draw, left + 22, top + 31, right, bottom - 3)
        return
    if icon == "cloud":
        _draw_cloud(draw, left + 3, top + 17, right - 2, bottom - 8)
        return
    if icon == "fog":
        for index, inset in enumerate((5, 15, 7, 17)):
            y = top + 20 + index * 16
            draw.line((left + inset, y, right - inset, y), fill=0, width=5)
        return
    if icon in {"rain", "snow", "storm"}:
        center_x = (left + right) // 2
        _draw_cloud(draw, left + 3, top + 3, right - 2, bottom - 30)
        if icon == "rain":
            for x in (center_x - 22, center_x, center_x + 22):
                draw.line((x + 4, bottom - 23, x - 3, bottom - 4), fill=0, width=5)
        elif icon == "snow":
            for x in (center_x - 22, center_x, center_x + 22):
                _draw_snowflake(draw, x, bottom - 13, radius=7)
        else:
            draw.polygon(
                (
                    (center_x + 5, bottom - 30),
                    (center_x - 10, bottom - 11),
                    (center_x, bottom - 11),
                    (center_x - 6, bottom + 1),
                    (center_x + 16, bottom - 19),
                    (center_x + 5, bottom - 19),
                ),
                fill=0,
            )
        return

    draw.ellipse(bounds, outline=0, width=width)
    draw.text(((left + right) // 2, (top + bottom) // 2), "?", font=_font(30), fill=0, anchor="mm")


def _draw_sun(
    draw: ImageDraw.ImageDraw, center_x: int, center_y: int, size: int, width: int
) -> None:
    radius = size // 5
    ray = size // 2
    draw.ellipse(
        (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
        outline=0,
        width=width,
    )
    for delta_x, delta_y in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        draw.line(
            (
                center_x + delta_x * (radius + 3),
                center_y + delta_y * (radius + 3),
                center_x + delta_x * ray,
                center_y + delta_y * ray,
            ),
            fill=0,
            width=width,
        )


def _draw_cloud(draw: ImageDraw.ImageDraw, left: int, top: int, right: int, bottom: int) -> None:
    """Draw a bold, classic cloud silhouette suitable for one-bit displays."""
    cloud_width = right - left
    height = bottom - top
    draw.ellipse(
        (left, top + height // 3, left + cloud_width // 2, bottom),
        fill=0,
    )
    draw.ellipse(
        (left + cloud_width // 4, top, left + cloud_width * 3 // 4, bottom),
        fill=0,
    )
    draw.ellipse(
        (left + cloud_width // 2, top + height // 3, right, bottom),
        fill=0,
    )
    draw.rectangle((left + cloud_width // 5, top + height // 2, right - 3, bottom), fill=0)


def _draw_snowflake(draw: ImageDraw.ImageDraw, center_x: int, center_y: int, radius: int) -> None:
    for delta_x, delta_y in ((radius, 0), (0, radius), (radius - 2, radius - 2)):
        draw.line(
            (
                center_x - delta_x,
                center_y - delta_y,
                center_x + delta_x,
                center_y + delta_y,
            ),
            fill=0,
            width=2,
        )
        if delta_x and delta_y:
            draw.line(
                (
                    center_x - delta_x,
                    center_y + delta_y,
                    center_x + delta_x,
                    center_y - delta_y,
                ),
                fill=0,
                width=2,
            )
