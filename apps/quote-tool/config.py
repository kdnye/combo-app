"""Central configuration for the Quote Tool Flask application.

The module resolves the application's base directory, ensures the default
SQLite instance folder exists, and exposes the :class:`Config` settings class.

Key settings exposed by :class:`Config`:

* ``SECRET_KEY``: Secures Flask sessions and form submissions. Generated at
  startup when the ``SECRET_KEY`` environment variable is missing so each
  deployment receives a unique value.
* ``SQLALCHEMY_DATABASE_URI`` and ``SQLALCHEMY_ENGINE_OPTIONS``: Provide the
  SQLAlchemy connection string and optional connection pooling behaviour.
* ``GOOGLE_MAPS_API_KEY``: Supplies credentials for distance calculations and
  address lookups.
* ``CACHE_TYPE`` and ``CACHE_REDIS_URL``: Configure the caching backend.
* ``MAIL_*`` fields: Enable optional outbound mail integration for password
  resets and notifications.
* ``RATELIMIT_*`` and ``AUTH_*_RATE_LIMIT``: Configure global and endpoint
  rate limiting enforced by :mod:`flask_limiter`.
* ``WTF_CSRF_ENABLED``: Toggles CSRF protection across forms.

All values default to development-friendly settings and can be overridden via
environment variables so each deployment can customize behaviour without
modifying code.
"""

# config.py
import logging
import os
from pathlib import Path
from secrets import token_urlsafe
from typing import Iterable, Optional, Set, Tuple
from urllib.parse import parse_qsl, quote_plus, urlencode

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "instance" / "app.db"
# Ensure the default database directory exists so all tools share the same DB.
DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _resolve_secret_key() -> str:
    """Return a cryptographically strong secret key for Flask sessions."""

    configured = os.getenv("SECRET_KEY")
    if configured:
        return configured

    generated = token_urlsafe(32)
    logging.getLogger("quote_tool.config").warning(
        "SECRET_KEY environment variable is not set; generated a one-time key."
    )
    return generated


def _build_bigquery_database_uri() -> Optional[str]:
    """Assemble a SQLAlchemy BigQuery connection string from environment variables.

    The helper inspects ``BIGQUERY_PROJECT`` and ``BIGQUERY_DATASET`` to
    construct a ``bigquery://`` connection URI understood by the
    ``pybigquery`` SQLAlchemy dialect. When ``BIGQUERY_LOCATION`` is set the
    value is appended as a query parameter so BigQuery executes queries in the
    desired region. The function returns ``None`` when the required
    environment variables are missing, allowing the caller to fall back to the
    default SQLite database or a user supplied ``DATABASE_URL``.

    Returns:
        Optional[str]: The completed BigQuery connection string or ``None`` if
        a project or dataset was not provided.
    """

    project = os.getenv("BIGQUERY_PROJECT")
    dataset = os.getenv("BIGQUERY_DATASET")
    if not project or not dataset:
        return None

    location = os.getenv("BIGQUERY_LOCATION")
    uri = f"bigquery://{project}/{dataset}"
    if location:
        uri = f"{uri}?location={location}"
    return uri


def _parse_postgres_options(raw_options: str) -> Iterable[Tuple[str, str]]:
    """Return key/value pairs parsed from ``POSTGRES_OPTIONS``.

    ``POSTGRES_OPTIONS`` accepts a query-string-style value such as
    ``"sslmode=require&application_name=quote-tool"``. The helper uses
    :func:`urllib.parse.parse_qsl` to decode the pairs while preserving order so
    callers can feed the result directly into :func:`urllib.parse.urlencode`.

    Args:
        raw_options: Raw string supplied via ``POSTGRES_OPTIONS``.

    Returns:
        Iterable[Tuple[str, str]]: Key/value pairs suitable for constructing a
        SQLAlchemy query string.
    """

    return parse_qsl(raw_options, keep_blank_values=True)


def build_postgres_database_uri_from_env(
    *, driver: str = "postgresql+psycopg2"
) -> Optional[str]:
    """Assemble a PostgreSQL SQLAlchemy URI based on Compose-style environment variables.

    The helper mirrors the connection string injected by ``docker compose`` in
    ``docker-compose.yml`` so that local scripts and Flask share the same
    overrides. It inspects ``POSTGRES_USER``, ``POSTGRES_PASSWORD``,
    ``POSTGRES_DB``, ``POSTGRES_HOST`` (defaulting to ``"postgres"`` for the
    Compose network), ``POSTGRES_PORT``, and optional ``POSTGRES_OPTIONS`` to
    build a connection string. When ``POSTGRES_PASSWORD`` is unset the function
    returns ``None`` so callers can fall back to
    :func:`_build_bigquery_database_uri` or the SQLite default provided by
    :class:`Config`.

    Args:
        driver: SQLAlchemy driver prefix used when constructing the URI. The
            default matches the ``psycopg2`` driver required by
            :mod:`sqlalchemy` for PostgreSQL connections.

    Returns:
        Optional[str]: Fully assembled SQLAlchemy connection string or ``None``
        when the Compose variables were incomplete.

    External Dependencies:
        Calls :func:`os.getenv` to read environment variables exported by
        Docker Compose or the current shell. Uses
        :func:`urllib.parse.quote_plus` and :func:`urllib.parse.urlencode` to
        safely encode credentials and query options for SQLAlchemy.
    """

    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        return None

    user = os.getenv("POSTGRES_USER", "quote_tool")
    db_name = os.getenv("POSTGRES_DB", "quote_tool")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    options = os.getenv("POSTGRES_OPTIONS", "")
    query_pairs: Iterable[Tuple[str, str]] = []
    if options:
        query_pairs = _parse_postgres_options(options)

    query = f"?{urlencode(list(query_pairs))}" if options else ""
    return (
        f"{driver}://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/"
        f"{quote_plus(db_name)}{query}"
    )


def _read_compose_profiles() -> Set[str]:
    """Return active Docker Compose profiles extracted from ``COMPOSE_PROFILES``.

    The helper consults :func:`os.getenv` so it mirrors the environment exposed
    to the running application container. When the variable is unset the
    function returns an empty set, signalling that only the default profile is
    active. Profiles are split on commas to match the behaviour of
    ``docker compose`` documented at https://docs.docker.com/compose/profiles/.

    Returns:
        Set[str]: Normalised profile names enabled for this deployment.
    """

    raw_profiles = os.getenv("COMPOSE_PROFILES", "")
    return {profile.strip() for profile in raw_profiles.split(",") if profile.strip()}


def _resolve_cache_type() -> str:
    """Select the Flask-Caching backend configured for this deployment.

    The function respects an explicit ``CACHE_TYPE`` override provided via
    :func:`os.getenv`. When the variable is unset and the Compose ``cache``
    profile is active (managed by :func:`_read_compose_profiles`), the helper
    defaults to ``redis`` so the application uses the bundled Redis service. In
    all other scenarios the function returns ``null`` to keep caching disabled.

    Returns:
        str: The cache backend identifier understood by
        :class:`flask_caching.Cache`.
    """

    configured = os.getenv("CACHE_TYPE")
    if configured:
        return configured

    if "cache" in _read_compose_profiles():
        return "redis"

    return "null"


def _resolve_cache_redis_url() -> Optional[str]:
    """Return the Redis connection URI used by Flask-Caching.

    Deployments can override ``CACHE_REDIS_URL`` via :func:`os.getenv`. When it
    is missing and the ``cache`` profile is active, the helper points Flask at
    ``redis://redis:6379/0`` to match the hostname and port declared in
    ``docker-compose.yml``. Otherwise ``None`` is returned so Flask-Caching can
    fall back to its in-memory store.

    Returns:
        Optional[str]: The Redis URI for Flask-Caching or ``None`` when Redis is
        not configured.
    """

    configured = os.getenv("CACHE_REDIS_URL")
    if configured:
        return configured

    if "cache" in _read_compose_profiles():
        return "redis://redis:6379/0"

    return None


def _resolve_ratelimit_storage_uri() -> str:
    """Determine where :mod:`flask_limiter` persists rate-limit counters.

    The function prioritises the ``RATELIMIT_STORAGE_URI`` environment variable
    retrieved via :func:`os.getenv`. When absent and the Compose ``cache``
    profile is enabled, a Redis URI targeting database ``1`` is returned so the
    limiter keeps counters separate from the application cache. Otherwise the
    function falls back to ``memory://`` which scopes counters to each Gunicorn
    worker.

    Returns:
        str: The storage URI consumed by :class:`flask_limiter.Limiter`.
    """

    configured = os.getenv("RATELIMIT_STORAGE_URI")
    if configured:
        return configured

    if "cache" in _read_compose_profiles():
        return "redis://redis:6379/1"

    return "memory://"


def _resolve_mail_allowed_sender_domain(default_sender: str) -> str:
    """Return the domain enforced for :data:`MAIL_DEFAULT_SENDER`.

    Args:
        default_sender: Email address configured as the default sender.

    Returns:
        str: Lowercase domain enforced by :func:`services.mail.validate_sender_domain`,
        defaulting to the domain portion of ``default_sender`` when no explicit
        override is provided.

    External Dependencies:
        Calls :func:`os.getenv` to honour the ``MAIL_ALLOWED_SENDER_DOMAIN``
        override supplied via environment variables.
    """

    override = os.getenv("MAIL_ALLOWED_SENDER_DOMAIN")
    if override is not None:
        return override.strip().lower()

    if "@" not in default_sender:
        return ""

    return default_sender.split("@", 1)[1].strip().lower()


class Config:
    SECRET_KEY = _resolve_secret_key()
    SQLALCHEMY_DATABASE_URI = (
        os.getenv("DATABASE_URL")
        or build_postgres_database_uri_from_env()
        or _build_bigquery_database_uri()
        or f"sqlite:///{DEFAULT_DB_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    WORKSPACE_APPS = [
        {
            "slug": "quote-tool",
            "name": "Hotshot Quote Workspace",
            "description": (
                "Create, revise, and email time-sensitive hotshot quotes with "
                "built-in compliance and margin checks."
            ),
            "endpoint": "quotes.new_quote",
            "primary": True,
            "cta_label": "Open quote builder",
        },
        {
            "slug": "expenses",
            "name": "Expense Reports",
            "description": (
                "Prepare reimbursable expense reports, attach receipts, and "
                "route them for approval."
            ),
            "url": os.getenv("EXPENSES_APP_URL", "http://localhost:8080/"),
            "external": True,
            "cta_label": "Launch expenses portal",
        },
    ]
    DB_POOL_SIZE = os.getenv("DB_POOL_SIZE")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    if DB_POOL_SIZE:
        SQLALCHEMY_ENGINE_OPTIONS["pool_size"] = int(DB_POOL_SIZE)
    CACHE_TYPE = _resolve_cache_type()
    CACHE_REDIS_URL = _resolve_cache_redis_url()
    # Mail/reset settings (optional):
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "quote@freightservices.net")
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.office365.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in {
        "true",
        "1",
        "yes",
        "y",
    }
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in {
        "true",
        "1",
        "yes",
        "y",
    }
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_ALLOWED_SENDER_DOMAIN = _resolve_mail_allowed_sender_domain(
        MAIL_DEFAULT_SENDER
    )
    MAIL_PRIVILEGED_DOMAIN = os.getenv("MAIL_PRIVILEGED_DOMAIN", "freightservices.net")
    MAIL_RATE_LIMIT_PER_USER_PER_HOUR = int(
        os.getenv("MAIL_RATE_LIMIT_PER_USER_PER_HOUR", 10)
    )
    MAIL_RATE_LIMIT_PER_USER_PER_DAY = int(
        os.getenv("MAIL_RATE_LIMIT_PER_USER_PER_DAY", 50)
    )
    MAIL_RATE_LIMIT_PER_FEATURE_PER_HOUR = int(
        os.getenv("MAIL_RATE_LIMIT_PER_FEATURE_PER_HOUR", 200)
    )
    MAIL_RATE_LIMIT_PER_RECIPIENT_PER_DAY = int(
        os.getenv("MAIL_RATE_LIMIT_PER_RECIPIENT_PER_DAY", 25)
    )
    WTF_CSRF_ENABLED = True
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per day;50 per hour")
    RATELIMIT_STORAGE_URI = _resolve_ratelimit_storage_uri()
    RATELIMIT_HEADERS_ENABLED = os.getenv(
        "RATELIMIT_HEADERS_ENABLED", "true"
    ).lower() in {
        "true",
        "1",
        "yes",
        "y",
    }
    AUTH_LOGIN_RATE_LIMIT = os.getenv("AUTH_LOGIN_RATE_LIMIT", "5 per minute")
    AUTH_REGISTER_RATE_LIMIT = os.getenv("AUTH_REGISTER_RATE_LIMIT", "5 per minute")
    AUTH_RESET_RATE_LIMIT = os.getenv("AUTH_RESET_RATE_LIMIT", "5 per minute")
    AUTH_RESET_TOKEN_RATE_LIMIT = os.getenv(
        "AUTH_RESET_TOKEN_RATE_LIMIT", "1 per 15 minutes"
    )
