from pathlib import Path

import pytest
from pydantic import ValidationError

from fundlens.settings import Settings

REQUIRED = {
    "DATABASE_URL": "postgresql://u:p@db:5432/fundlens",
    "R2_ENDPOINT": "http://minio:9000",
    "R2_ACCESS_KEY_ID": "key",
    "R2_SECRET_ACCESS_KEY": "hunter2",
}

OPTIONAL = (
    "R2_BUCKET",
    "R2_PUBLIC_BUCKET",
    "DATA_DIR",
    "SQL_DIR",
    "DUCKDB_MEMORY_LIMIT",
    "DUCKDB_MAX_TEMP_DIRECTORY_SIZE",
    "DUCKDB_THREADS",
    "LOG_LEVEL",
    "CLOUDFLARE_ZONE_ID",
    "CLOUDFLARE_API_TOKEN",
    "SENTRY_DSN",
    "OTEL_RESOURCE_ATTRIBUTES",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "KUMA_PUSH_WEEKLY",
    "KUMA_PUSH_PUBLISH",
)


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in (*REQUIRED, *OPTIONAL):
        monkeypatch.delenv(name, raising=False)
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


def test_reads_required_values_and_applies_defaults(env: pytest.MonkeyPatch) -> None:
    settings = Settings()  # pyright: ignore[reportCallIssue]

    assert settings.database_url == REQUIRED["DATABASE_URL"]
    assert settings.r2_endpoint == REQUIRED["R2_ENDPOINT"]
    assert settings.r2_secret_access_key.get_secret_value() == "hunter2"
    assert settings.r2_bucket == "fundlens-data"
    assert settings.r2_public_bucket == "fundlens-public"
    assert settings.data_dir == Path("/data/fundlens")
    assert settings.sql_dir == Path("/app/sql")
    assert settings.duckdb_memory_limit is None
    assert settings.duckdb_max_temp_directory_size == "60GB"
    assert settings.duckdb_threads is None
    assert settings.log_level == "INFO"
    # No zone in dev: publish skips the purge.
    assert settings.cloudflare_zone_id is None
    assert settings.cloudflare_api_token is None
    # Telemetry is off until the deploy sets it.
    assert settings.sentry_dsn is None
    assert settings.otel_resource_attributes == ""
    assert settings.otel_exporter_otlp_endpoint is None
    assert settings.kuma_push_weekly is None
    assert settings.kuma_push_publish is None


def test_secrets_are_not_rendered(env: pytest.MonkeyPatch) -> None:
    env.setenv("KUMA_PUSH_WEEKLY", "https://kuma.example/api/push/s3cr3tTok")
    env.setenv("SENTRY_DSN", "https://dsnK3y@bugsink.example/1")
    env.setenv("CLOUDFLARE_API_TOKEN", "cfPurg3Tok")

    settings = Settings()  # pyright: ignore[reportCallIssue]

    assert "hunter2" not in repr(settings)
    assert "s3cr3tTok" not in repr(settings)
    assert "dsnK3y" not in repr(settings)
    assert "cfPurg3Tok" not in repr(settings)


def test_missing_database_url_fails(env: pytest.MonkeyPatch) -> None:
    env.delenv("DATABASE_URL")

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings()  # pyright: ignore[reportCallIssue]
