# EinkKindle Weather + Calendar Dashboard

## Local Google Calendar OAuth

Create a Google Cloud OAuth client of type **Desktop app** with the Google Calendar API enabled and
download its client credentials JSON. Copy `config/config.example.yaml` to the ignored
`config/config.yaml`, then place the downloaded file at
`config/local/google-oauth-client.json`. The refreshable token is written to the ignored
`config/local/google-calendar-token.json`.

Run the one-time browser login:

```powershell
python -m server.calendar.google_oauth_login --config config/config.yaml
```

Run the live normalized-calendar smoke test:

```powershell
python -m server.calendar.google_calendar_live_smoke --config config/config.yaml
```

Bateryjny dashboard pogody i kalendarza dla Kindle 4 Non-Touch.

Urządzeniem docelowym jest Kindle 4 z firmware 4.1.2 i ekranem o rozdzielczości 600 × 800 pikseli.

Backend będzie działał na osobnym komputerze lub serwerze. Kindle będzie pełnił rolę cienkiego klienta, wyświetlającego przygotowany wcześniej obraz.

MVP wyświetla jeden statyczny ekran 600 × 800: kompaktową sekcję aktualnej pogody oraz główną sekcję kalendarza bieżącego tygodnia. Widok obejmuje 7 dni od poniedziałku do niedzieli; każdy dzień pokazuje nazwę dnia tygodnia i datę w formacie `DD.MM`, aktualny dzień jest wyróżniony, a eventy są przypisane do odpowiednich dni.

Serwer pobiera dane z Open-Meteo i Google Calendar, normalizuje je do modeli domenowych `WeatherSnapshot` i `CalendarWeek`, a następnie generuje `output/dashboard.png`. Kindle pobiera przez read-only HTTP wyłącznie gotowy dashboard. MVP nie obsługuje przycisków.
