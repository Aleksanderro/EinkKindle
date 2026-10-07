# Architecture

The server-side data flow is:

```text
Open-Meteo -> WeatherSnapshot ─┐
                               ├-> DashboardRenderer -> dashboard.png
Google Calendar -> CalendarWeek┘
    -> read-only HTTP
    -> Kindle
```

The weather and calendar layers independently own their provider integrations and convert provider
data into the normalized domain models `WeatherSnapshot` and `CalendarWeek`. Provider-specific
responses must not leak into the domain models or renderer.

`DashboardRenderer` consumes both normalized models and produces one static 600x800 display image
at `output/dashboard.png`. It contains a compact current-weather section and a primary current-week
calendar section covering Monday through Sunday. Each day shows its weekday and date in `DD.MM`
format, the current day is visually highlighted, and events are assigned to their respective days.

The HTTP layer exposes the generated dashboard as a minimal, read-only runtime surface. The Kindle
only downloads and displays that prepared image; it never contacts Open-Meteo or Google Calendar
directly. The MVP has no button handling.
