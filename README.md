# EinkKindle Weather + Calendar Dashboard

Bateryjny dashboard pogody i kalendarza dla Kindle 4 Non-Touch.

Urządzeniem docelowym jest Kindle 4 z firmware 4.1.2 i ekranem o rozdzielczości 600 × 800 pikseli.

Backend będzie działał na osobnym komputerze lub serwerze. Kindle będzie pełnił rolę cienkiego klienta, wyświetlającego przygotowany wcześniej obraz.

MVP wyświetla jeden statyczny ekran 600 × 800: kompaktową sekcję aktualnej pogody oraz główną sekcję kalendarza bieżącego tygodnia. Widok obejmuje 7 dni od poniedziałku do niedzieli; każdy dzień pokazuje nazwę dnia tygodnia i datę w formacie `DD.MM`, aktualny dzień jest wyróżniony, a eventy są przypisane do odpowiednich dni.

Serwer pobiera dane z Open-Meteo i Google Calendar, normalizuje je do modeli domenowych `WeatherSnapshot` i `CalendarWeek`, a następnie generuje `output/dashboard.png`. Kindle pobiera przez read-only HTTP wyłącznie gotowy dashboard. MVP nie obsługuje przycisków.
