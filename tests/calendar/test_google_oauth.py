from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from server.calendar.google_oauth import (
    GOOGLE_CALENDAR_SCOPES,
    GoogleOAuthAuthorizationRequired,
    GoogleOAuthConfig,
    GoogleOAuthError,
    GoogleOAuthManager,
    OAuthBackend,
    load_google_oauth_config,
)


@dataclass
class FakeCredentials:
    token: str | None
    valid: bool
    expired: bool
    refresh_token: str | None


class FakeOAuthBackend:
    def __init__(self, credentials: FakeCredentials, *, token_exists: bool = True) -> None:
        self.credentials = credentials
        self.has_token = token_exists
        self.saved: list[tuple[FakeCredentials, Path]] = []
        self.flow_calls: list[tuple[Path, tuple[str, ...]]] = []
        self.refresh_calls = 0

    def as_backend(self) -> OAuthBackend:
        return OAuthBackend(
            token_exists=lambda path: self.has_token,
            client_credentials_exist=lambda path: True,
            load_credentials=self.load,
            save_credentials=self.save,
            run_installed_app_flow=self.run_flow,
            refresh_credentials=self.refresh,
        )

    def load(self, path: Path, scopes: tuple[str, ...]) -> FakeCredentials:
        assert path == Path("config/local/token.json")
        assert scopes == GOOGLE_CALENDAR_SCOPES
        return self.credentials

    def save(self, credentials: Any, path: Path) -> None:
        self.saved.append((credentials, path))

    def run_flow(self, path: Path, scopes: tuple[str, ...]) -> FakeCredentials:
        self.flow_calls.append((path, scopes))
        return self.credentials

    def refresh(self, credentials: FakeCredentials) -> None:
        self.refresh_calls += 1
        credentials.token = "refreshed-access-token"
        credentials.valid = True
        credentials.expired = False


def test_returns_still_valid_stored_access_token() -> None:
    fake = FakeOAuthBackend(FakeCredentials("valid-access-token", True, False, "refresh"))

    token = GoogleOAuthManager(_config(), backend=fake.as_backend()).get_access_token()

    assert token == "valid-access-token"
    assert fake.refresh_calls == 0
    assert fake.saved == []


def test_refreshes_expired_token_and_persists_credentials() -> None:
    credentials = FakeCredentials("expired", False, True, "refresh-token")
    fake = FakeOAuthBackend(credentials)

    token = GoogleOAuthManager(_config(), backend=fake.as_backend()).get_access_token()

    assert token == "refreshed-access-token"
    assert fake.refresh_calls == 1
    assert fake.saved == [(credentials, Path("config/local/token.json"))]


def test_missing_token_requires_one_time_login() -> None:
    fake = FakeOAuthBackend(
        FakeCredentials(None, False, False, None),
        token_exists=False,
    )

    with pytest.raises(GoogleOAuthAuthorizationRequired, match="login command"):
        GoogleOAuthManager(_config(), backend=fake.as_backend()).get_access_token()


def test_login_requests_readonly_scope_and_saves_refreshable_credentials() -> None:
    credentials = FakeCredentials("new-access-token", True, False, "refresh-token")
    fake = FakeOAuthBackend(credentials, token_exists=False)

    token = GoogleOAuthManager(_config(), backend=fake.as_backend()).login()

    assert token == "new-access-token"
    assert fake.flow_calls == [(Path("config/local/client.json"), GOOGLE_CALENDAR_SCOPES)]
    assert fake.saved == [(credentials, Path("config/local/token.json"))]


def test_login_rejects_credentials_without_refresh_token() -> None:
    fake = FakeOAuthBackend(FakeCredentials("access-token", True, False, None))

    with pytest.raises(GoogleOAuthError, match="refresh token"):
        GoogleOAuthManager(_config(), backend=fake.as_backend()).login()

    assert fake.saved == []


def test_unrefreshable_stored_credentials_require_login() -> None:
    fake = FakeOAuthBackend(FakeCredentials("expired", False, True, None))

    with pytest.raises(GoogleOAuthAuthorizationRequired, match="login command"):
        GoogleOAuthManager(_config(), backend=fake.as_backend()).get_access_token()


def test_example_config_points_to_ignored_local_oauth_files() -> None:
    config = load_google_oauth_config("config/config.example.yaml")

    assert config.client_credentials_path == Path("config/local/google-oauth-client.json")
    assert config.token_store_path == Path("config/local/google-calendar-token.json")
    assert config.calendar_id == "primary"


def _config() -> GoogleOAuthConfig:
    return GoogleOAuthConfig(
        client_credentials_path=Path("config/local/client.json"),
        token_store_path=Path("config/local/token.json"),
    )
