"""`fundlens health` against the dev compose's Postgres and MinIO (spec §5.1, §10.3)."""

from collections.abc import Iterator

import pytest
from typer.testing import CliRunner

from fundlens import cli
from fundlens.settings import get_settings


@pytest.fixture(autouse=True)
def fresh_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    def leave_logging_alone(level: str) -> None:
        # The callback reconfigures the root logger, which would outlive the test.
        pass

    monkeypatch.setattr(cli, "configure_logging", leave_logging_alone)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_exits_0_when_postgres_and_r2_are_up() -> None:
    result = CliRunner().invoke(cli.app, ["health"])

    assert result.exit_code == 0, result.output
    assert "postgres: ok" in result.output
    assert "r2: ok" in result.output


def test_exits_1_when_postgres_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    # Nothing listens on port 1: as down as a Postgres gets without stopping the shared one.
    monkeypatch.setenv("DATABASE_URL", "postgresql://fundlens:fundlens@postgres:1/fundlens")

    result = CliRunner().invoke(cli.app, ["health"])

    assert result.exit_code == 1
    assert "postgres: unreachable (OperationalError" in result.output
    assert "r2: ok" in result.output


def test_exits_1_when_r2_rejects_the_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "not-the-secret")

    result = CliRunner().invoke(cli.app, ["health"])

    assert result.exit_code == 1
    assert "r2: unreachable (ClientError" in result.output
