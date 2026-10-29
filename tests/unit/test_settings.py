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


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in (*REQUIRED, "R2_BUCKET", "R2_PUBLIC_BUCKET", "DATA_DIR", "LOG_LEVEL"):
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
    assert settings.log_level == "INFO"


def test_secret_is_not_rendered(env: pytest.MonkeyPatch) -> None:
    settings = Settings()  # pyright: ignore[reportCallIssue]

    assert "hunter2" not in repr(settings)


def test_missing_database_url_fails(env: pytest.MonkeyPatch) -> None:
    env.delenv("DATABASE_URL")

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings()  # pyright: ignore[reportCallIssue]
