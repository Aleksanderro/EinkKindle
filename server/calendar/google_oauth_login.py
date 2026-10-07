"""Run the one-time local Google Calendar OAuth login."""

import argparse
from collections.abc import Sequence

from server.calendar.google_oauth import GoogleOAuthManager, load_google_oauth_config


def main(argv: Sequence[str] | None = None) -> None:
    """Authorize in a browser and save refreshable credentials locally."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/config.yaml", help="Path to local YAML config")
    args = parser.parse_args(argv)
    config = load_google_oauth_config(args.config)
    GoogleOAuthManager(config).login()
    print(f"OAuth login complete. Token stored at {config.token_file}")


if __name__ == "__main__":
    main()
