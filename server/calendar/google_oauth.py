"""Local OAuth lifecycle for read-only Google Calendar access."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

GOOGLE_CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
GOOGLE_CALENDAR_SCOPES = (GOOGLE_CALENDAR_READONLY_SCOPE,)


class GoogleOAuthError(RuntimeError):
    """Raised when local Google OAuth credentials cannot be obtained or refreshed."""


class GoogleOAuthAuthorizationRequired(GoogleOAuthError):
    """Raised when the one-time interactive login must be run."""


@dataclass(frozen=True, slots=True)
class GoogleOAuthConfig:
    """Local paths and calendar selection required by Google OAuth tooling."""

    client_credentials_path: Path
    token_store_path: Path
    calendar_id: str = "primary"

    def __post_init__(self) -> None:
        if not self.calendar_id:
            raise ValueError("calendar_id must not be empty")


@dataclass(frozen=True, slots=True)
class OAuthBackend:
    """Replaceable OAuth side effects, allowing fully offline unit tests."""

    token_exists: Callable[[Path], bool]
    client_credentials_exist: Callable[[Path], bool]
    load_credentials: Callable[[Path, tuple[str, ...]], Any]
    save_credentials: Callable[[Any, Path], None]
    run_installed_app_flow: Callable[[Path, tuple[str, ...]], Any]
    refresh_credentials: Callable[[Any], None]


class GoogleOAuthManager:
    """Load, refresh, and locally persist read-only Google credentials."""

    def __init__(
        self,
        config: GoogleOAuthConfig,
        *,
        backend: OAuthBackend | None = None,
    ) -> None:
        self._config = config
        self._backend = backend or _default_backend()

    def login(self) -> str:
        """Run the one-time browser flow, persist credentials, and return an access token."""
        client_path = self._config.client_credentials_path
        if not self._backend.client_credentials_exist(client_path):
            raise GoogleOAuthError(f"OAuth client credentials not found: {client_path}")
        credentials = self._backend.run_installed_app_flow(client_path, GOOGLE_CALENDAR_SCOPES)
        token = _validated_token(credentials, require_refresh_token=True)
        self._backend.save_credentials(credentials, self._config.token_store_path)
        return token

    def get_access_token(self) -> str:
        """Return a valid token, refreshing and persisting it when necessary."""
        token_path = self._config.token_store_path
        if not self._backend.token_exists(token_path):
            raise GoogleOAuthAuthorizationRequired(
                "OAuth token store not found; run the Google OAuth login command first"
            )

        credentials = self._backend.load_credentials(token_path, GOOGLE_CALENDAR_SCOPES)
        if getattr(credentials, "valid", False):
            return _validated_token(credentials)

        if getattr(credentials, "expired", False) and getattr(credentials, "refresh_token", None):
            self._backend.refresh_credentials(credentials)
            token = _validated_token(credentials)
            self._backend.save_credentials(credentials, token_path)
            return token

        raise GoogleOAuthAuthorizationRequired(
            "Stored OAuth credentials cannot be refreshed; run the login command again"
        )


def load_google_oauth_config(config_path: str | Path) -> GoogleOAuthConfig:
    """Load the minimal Google Calendar OAuth contract from YAML."""
    path = Path(config_path)
    try:
        raw_config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise GoogleOAuthError(f"cannot read OAuth configuration: {path}") from error
    root = _mapping(raw_config, "config")
    calendar = _mapping(root.get("calendar"), "calendar")
    client_path = _non_empty_string(
        calendar.get("oauth_client_credentials_path"),
        "calendar.oauth_client_credentials_path",
    )
    token_path = _non_empty_string(calendar.get("token_store_path"), "calendar.token_store_path")
    calendar_id = calendar.get("calendar_id", "primary")
    if not isinstance(calendar_id, str) or not calendar_id:
        raise GoogleOAuthError("calendar.calendar_id must be a non-empty string")
    return GoogleOAuthConfig(Path(client_path), Path(token_path), calendar_id)


def _validated_token(credentials: Any, *, require_refresh_token: bool = False) -> str:
    token = getattr(credentials, "token", None)
    if not isinstance(token, str) or not token:
        raise GoogleOAuthError("Google OAuth did not return an access token")
    if require_refresh_token and not getattr(credentials, "refresh_token", None):
        raise GoogleOAuthError(
            "Google OAuth did not return a refresh token; revoke the app grant and retry login"
        )
    return token


def _default_backend() -> OAuthBackend:
    return OAuthBackend(
        token_exists=Path.is_file,
        client_credentials_exist=Path.is_file,
        load_credentials=_load_credentials,
        save_credentials=_save_credentials,
        run_installed_app_flow=_run_installed_app_flow,
        refresh_credentials=_refresh_credentials,
    )


def _load_credentials(path: Path, scopes: tuple[str, ...]) -> Any:
    from google.oauth2.credentials import Credentials

    return Credentials.from_authorized_user_file(str(path), scopes)


def _save_credentials(credentials: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(credentials.to_json(), encoding="utf-8")
    temporary_path.chmod(0o600)
    temporary_path.replace(path)


def _run_installed_app_flow(path: Path, scopes: tuple[str, ...]) -> Any:
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(path), scopes)
    return flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
        open_browser=True,
    )


def _refresh_credentials(credentials: Any) -> None:
    from google.auth.transport.requests import Request

    credentials.refresh(Request())


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GoogleOAuthError(f"{path} must be an object")
    return value


def _non_empty_string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise GoogleOAuthError(f"{path} must be a non-empty string")
    return value
