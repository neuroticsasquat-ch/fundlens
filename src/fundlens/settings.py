"""Every environment variable fundlens reads, in one place (spec §10.1).

Later tickets add their own settings here (Cloudflare, DeepInfra, telemetry, DuckDB limits)
rather than reading `os.environ` where they are used.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")

    # R2 in prod, MinIO in dev and CI: the same S3 client, pointed at a different endpoint.
    r2_endpoint: str = Field(..., alias="R2_ENDPOINT")
    r2_access_key_id: str = Field(..., alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: SecretStr = Field(..., alias="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field(default="fundlens-data", alias="R2_BUCKET")
    r2_public_bucket: str = Field(default="fundlens-public", alias="R2_PUBLIC_BUCKET")

    # Root of the local cache volumes (bronze/, silver/, scratch/, resolution/; spec §3.4).
    data_dir: Path = Field(default=Path("/data/fundlens"), alias="DATA_DIR")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Origins the API's CORS headers allow (spec §7.2): the SPA in prod, plus its local servers
    # in dev. A JSON list in the environment; the first is the one a request without an
    # `Origin` is answered for (`api.cors`).
    cors_origins: list[str] = Field(default=["https://fundlens.org"], alias="CORS_ORIGINS")

    # Telemetry (spec §10.3). All unset in dev and CI, where Sentry stays off and every Kuma push
    # is a no-op.
    # Secret because its key is what Bugsink accepts events on.
    sentry_dsn: SecretStr | None = Field(default=None, alias="SENTRY_DSN")
    # OTel reads these itself inside `opentelemetry-instrument`; they are read here only so
    # Sentry can report the same release and environment (`telemetry.resolve_telemetry`).
    otel_resource_attributes: str = Field(default="", alias="OTEL_RESOURCE_ATTRIBUTES")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    # One Uptime Kuma push monitor per job family. Secret because the token in the URL is the
    # monitor's only credential (see `logging.redact_push_token`).
    kuma_push_weekly: SecretStr | None = Field(default=None, alias="KUMA_PUSH_WEEKLY")
    kuma_push_publish: SecretStr | None = Field(default=None, alias="KUMA_PUSH_PUBLISH")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
