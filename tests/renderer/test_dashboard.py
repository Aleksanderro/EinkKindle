from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from io import BytesIO

from PIL import Image

from server.calendar.models import CalendarDay, CalendarEvent, CalendarWeek
from server.renderer.dashboard import DISPLAY_SIZE, render_dashboard
from server.renderer.demo_data import demo_calendar_week, demo_weather


def test_full_dashboard_is_monochrome_600x800_png() -> None:
    image = render_dashboard(demo_weather(), demo_calendar_week())
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    with Image.open(output) as rendered:
        assert rendered.size == DISPLAY_SIZE == (600, 800)
        assert rendered.format == "PNG"
        assert rendered.mode == "1"
        assert rendered.getextrema() == (0, 255)


def test_dashboard_rendering_is_deterministic() -> None:
    first = BytesIO()
    second = BytesIO()
    render_dashboard(demo_weather(), demo_calendar_week()).save(first, format="PNG")
    render_dashboard(demo_weather(), demo_calendar_week()).save(second, format="PNG")

    assert sha256(first.getvalue()).digest() == sha256(second.getvalue()).digest()


def test_supported_weather_icons_are_visually_distinct() -> None:
    weather = demo_weather()
    icon_hashes = set()
    for weather_code in (0, 2, 3, 45, 63, 75, 95):
        current = replace(weather.current, weather_code=weather_code)
        image = render_dashboard(replace(weather, current=current), demo_calendar_week())
        icon_hashes.add(sha256(image.crop((20, 52, 103, 137)).tobytes()).digest())

    assert len(icon_hashes) == 7


def test_polish_diacritics_are_drawn_instead_of_transliterated() -> None:
    weather = demo_weather()
    with_diacritic = render_dashboard(weather, demo_calendar_week())
    transliterated = render_dashboard(
        replace(weather, location_name="Poznan"), demo_calendar_week()
    )

    assert (
        with_diacritic.crop((18, 7, 110, 42)).tobytes()
        != transliterated.crop((18, 7, 110, 42)).tobytes()
    )


def test_empty_calendar_renders_without_error() -> None:
    week = demo_calendar_week()
    empty_days = tuple(replace(day, events=()) for day in week.days)
    empty_week = replace(week, days=empty_days)

    assert render_dashboard(demo_weather(), empty_week).size == DISPLAY_SIZE


def test_many_events_are_rendered_without_reducing_canvas() -> None:
    week = demo_calendar_week()

    assert len(week.days[0].events) > 3
    assert render_dashboard(demo_weather(), week).size == DISPLAY_SIZE


def test_long_title_renders_without_overflow_error() -> None:
    week = demo_calendar_week()
    long_event = CalendarEvent(
        title="Very long " * 100,
        start=week.days[4].events[0].start,
        end=week.days[4].events[0].end,
        all_day=False,
    )
    days = tuple(
        replace(day, events=(long_event,)) if index == 4 else day
        for index, day in enumerate(week.days)
    )

    assert render_dashboard(demo_weather(), replace(week, days=days)).size == DISPLAY_SIZE


def test_current_day_has_inverted_highlight() -> None:
    image = render_dashboard(demo_weather(), demo_calendar_week())
    today_index = 2
    today_top = 160 + today_index * 91
    non_today_top = 160

    assert image.getpixel((4, today_top + 40)) == 0
    assert image.getpixel((4, non_today_top + 40)) == 255


def test_week_contract_still_accepts_seven_days() -> None:
    week = demo_calendar_week()
    days: tuple[CalendarDay, ...] = tuple(week.days)
    rebuilt = CalendarWeek(
        start=week.start,
        end=week.start + timedelta(days=6),
        current_day=week.current_day,
        days=days,
    )

    assert render_dashboard(demo_weather(), rebuilt).size == DISPLAY_SIZE
