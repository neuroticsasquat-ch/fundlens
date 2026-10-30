"""`cli.step`: a pipeline command reports its crash, and only its crash (spec §5.1, ADR-0025).

Kuma has no `/fail` path: the step's `fail` push is `status=down` (see `fundlens.heartbeat`).
"""

from collections.abc import Iterator
from typing import Annotated
from urllib.parse import parse_qs, urlsplit

import pytest
import sentry_sdk
import typer
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport
from typer.testing import CliRunner

from fundlens import cli
from fundlens.cli import step
from fundlens.heartbeat import Heartbeat, JobFamily
from fundlens.settings import Settings
from fundlens.telemetry import pipeline_integrations

PUSH = "https://kuma.example/api/push/weekly"


class FakeTransport(Transport):
    """Keeps every event the SDK would have sent to Bugsink."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, object]] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        event = envelope.get_event()
        if event is not None:
            self.events.append(dict(event))


@pytest.fixture
def bugsink() -> Iterator[FakeTransport]:
    """A live SDK with the pipeline's own integrations, delivering to a fake transport."""
    transport = FakeTransport()
    sentry_sdk.init(
        dsn="https://key@bugsink.example/1",
        transport=transport,
        integrations=pipeline_integrations(),
    )
    yield transport
    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(None)


@pytest.fixture
def pushes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    sent: list[str] = []

    def fake_heartbeat_for(family: JobFamily | None, settings: Settings) -> Heartbeat:
        return Heartbeat(PUSH if family else None, send=sent.append)

    monkeypatch.setattr(cli, "heartbeat_for", fake_heartbeat_for)
    return sent


def params(url: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}


def test_a_step_that_raises_pushes_fail_reports_once_and_reraises(
    bugsink: FakeTransport, pushes: list[str]
) -> None:
    @step("transform", family="weekly")
    def transform() -> None:
        raise RuntimeError("check failed: orphan contributions\nfirst orphan: SA17.123")

    with pytest.raises(RuntimeError, match="orphan contributions"):
        transform()

    assert [params(url) for url in pushes] == [
        {"status": "down", "msg": "transform: RuntimeError: check failed: orphan contributions"}
    ]
    # Once, although the step also logs the exception: logging is breadcrumbs only.
    assert len(bugsink.events) == 1
    assert bugsink.events[0]["tags"] == {"pipeline_mode": "transform"}


def test_a_step_that_returns_pushes_ok_and_reports_nothing(
    bugsink: FakeTransport, pushes: list[str]
) -> None:
    @step("load", family="weekly")
    def load(cycle: int) -> int:
        return cycle

    assert load(2024) == 2024
    assert [params(url)["status"] for url in pushes] == ["up"]
    assert params(pushes[0])["msg"] == "load: ok"
    assert bugsink.events == []


def test_a_step_without_a_family_pushes_nothing_but_still_reports(
    bugsink: FakeTransport, pushes: list[str]
) -> None:
    @step("seats")
    def seats() -> None:
        raise ValueError("no apportionment for 2032")

    with pytest.raises(ValueError):
        seats()

    assert pushes == []
    assert len(bugsink.events) == 1


@pytest.mark.parametrize(
    ("code", "status", "msg"), [(0, "up", "load: ok"), (3, "down", "load: exited 3")]
)
def test_a_deliberate_exit_pushes_by_its_code_and_is_not_a_crash(
    bugsink: FakeTransport, pushes: list[str], code: int, status: str, msg: str
) -> None:
    @step("load", family="weekly")
    def load() -> None:
        raise typer.Exit(code)

    with pytest.raises(typer.Exit):
        load()

    assert [(params(url)["status"], params(url)["msg"]) for url in pushes] == [(status, msg)]
    assert bugsink.events == []


def test_typer_reads_the_wrapped_signature_and_the_crash_fails_the_command(
    bugsink: FakeTransport, pushes: list[str]
) -> None:
    demo = typer.Typer()
    seen: list[int] = []

    @demo.command()
    @step("extract", family="weekly")
    def extract(cycle: Annotated[int, typer.Option()]) -> None:
        seen.append(cycle)
        if cycle == 1999:
            raise RuntimeError("not a cycle")

    assert CliRunner().invoke(demo, ["--cycle", "2024"]).exit_code == 0
    assert seen == [2024]

    result = CliRunner().invoke(demo, ["--cycle", "1999"])
    assert result.exit_code == 1
    assert isinstance(result.exception, RuntimeError)
    assert [params(url)["status"] for url in pushes] == ["up", "down"]
