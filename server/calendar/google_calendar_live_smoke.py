"""Fetch and print the normalized current Google Calendar week."""

import argparse
from collections.abc import Sequence
from datetime import datetime

from server.calendar.google_calendar import GoogleCalendarClient
from server.calendar.google_oauth import GoogleOAuthManager, load_google_oauth_config


def main(argv: Sequence[str] | None = None) -> None:
    """Run one live calendar fetch without exposing OAuth credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/config.yaml", help="Path to local YAML config")
    args = parser.parse_args(argv)
    config = load_google_oauth_config(args.config)
    access_token = GoogleOAuthManager(config).get_access_token()
    week = GoogleCalendarClient(
        access_token=access_token,
        calendar_id=config.calendar_id,
    ).fetch_current_week()

    print(f"Week: {week.start.isoformat()} - {week.end.isoformat()}")
    for day in week.days:
        marker = " (today)" if day.is_today else ""
        print(f"{day.date:%A %d.%m}{marker}")
        if not day.events:
            print("  No events")
            continue
        for event in day.events:
            if event.all_day:
                when = "ALL DAY"
            else:
                assert isinstance(event.start, datetime)
                when = event.start.strftime("%H:%M")
            print(f"  {when}  {event.title}")


if __name__ == "__main__":
    main()
