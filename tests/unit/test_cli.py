import tomllib
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from fundlens import cli
from fundlens.cli import app

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_version_prints_the_pyproject_version() -> None:
    expected = tomllib.loads(PYPROJECT.read_text())["project"]["version"]

    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == expected


def test_no_arguments_prints_help() -> None:
    result = CliRunner().invoke(app, [])

    assert "--version" in result.output


def test_api_serves_the_app_factory_behind_the_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_run(target: str, **kwargs: Any) -> None:
        calls.append((target, kwargs))

    def leave_logging_alone(level: str) -> None:
        # The callback reconfigures the root logger, which would outlive the test.
        pass

    monkeypatch.setattr(cli.uvicorn, "run", fake_run)
    monkeypatch.setattr(cli, "configure_logging", leave_logging_alone)

    result = CliRunner().invoke(app, ["api", "--port", "8123"])

    assert result.exit_code == 0, result.output
    [(target, kwargs)] = calls
    assert target == "fundlens.api.app:create_app"
    assert kwargs["factory"] is True
    assert kwargs["port"] == 8123
    assert kwargs["proxy_headers"] is True
    assert kwargs["forwarded_allow_ips"] == "*"
