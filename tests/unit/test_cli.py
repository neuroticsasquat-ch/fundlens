import tomllib
from pathlib import Path

from typer.testing import CliRunner

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
