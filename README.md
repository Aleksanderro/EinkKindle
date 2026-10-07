# EinkKindle Weather + Calendar Dashboard

## Local Google Calendar OAuth

1. Copy `config/config.example.yaml` to the ignored `config/config.yaml`.
2. In Google Cloud, enable Google Calendar API, create an OAuth client of type **Desktop app**, and
   download its client credentials JSON to a location outside this repository and workspace.
3. Choose a second JSON path outside the repository and workspace for the generated token store. Set
   both external paths in the local `config/config.yaml` under `calendar.oauth_client_file` and
   `calendar.token_file`. The application never copies either file into the project.
4. Run the one-time browser login shown below. It creates the token store at the configured external
   path and stores the refresh token there.
5. Run the live normalized-calendar smoke test shown below.

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
