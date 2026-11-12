"""`fundlens run`: the current cycle, the build it runs, and the `fundlens/weekly` monitor, pushed
only with `--scheduled` (spec §5.1, §5.6; NEU-2061).

`pipeline.run` is faked here: which steps a build runs is `tests/integration/test_pipeline.py`'s.
"""

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest
from typer.testing import CliRunner, Result

from fundlens import cli, pipeline
from fundlens.cli import step
from fundlens.heartbeat import Heartbeat, JobFamily
from fundlens.r2 import R2
from fundlens.settings import Settings
from tests.fake_bugsink import FakeTransport, fake_bugsink

BUILD = "20261108T030000Z"


@pytest.fixture
def bugsink() -> Iterator[FakeTransport]:
    with fake_bugsink() as transport:
        yield transport


@pytest.fixture
def pushes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[JobFamily, str]]:
    """Every push, as its monitor and status."""
    sent: list[tuple[JobFamily, str]] = []

    def fake_heartbeat_for(family: JobFamily | None, settings: Settings) -> Heartbeat:
        def send(url: str) -> None:
            assert family is not None
            sent.append((family, parse_qs(urlsplit(url).query)["status"][0]))

        return Heartbeat(f"https://kuma.example/api/push/{family}" if family else None, send=send)

    monkeypatch.setattr(cli, "heartbeat_for", fake_heartbeat_for)
    return sent


@pytest.fixture(autouse=True)
def quiet_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep `cli.main` off the root logger and off the test's own Sentry client."""

    def leave_logging_alone(level: str) -> None:
        pass

    def leave_sentry_alone(settings: Settings, integrations: object) -> None:
        pass

    monkeypatch.setattr(cli, "configure_logging", leave_logging_alone)
    monkeypatch.setattr(cli, "init_sentry", leave_sentry_alone)


@step("load")
def crashing_load() -> None:
    raise RuntimeError("COPY failed: disk full")


@dataclass
class FakePipeline:
    """Records what each run was asked for; crashes in `load`'s own `step` when told to."""

    crash: bool = False
    superseded: bool = False
    calls: list[tuple[int, str, pipeline.Stage | None]] = field(
        default_factory=list[tuple[int, str, pipeline.Stage | None]]
    )

    def run(
        self,
        cycle: int,
        store: R2,
        *,
        build_id: str,
        steps: Mapping[pipeline.Stage, Callable[[], None]],
        from_stage: pipeline.Stage | None = None,
    ) -> pipeline.Ran:
        assert list(steps) == list(pipeline.STAGES)
        self.calls.append((cycle, build_id, from_stage))
        if self.superseded:
            raise pipeline.SupersededBuild("a newer build was transformed: start a new build")
        if self.crash:
            crashing_load()
        return pipeline.Ran(ran=pipeline.STAGES, skipped=())


@pytest.fixture
def fake_pipeline(monkeypatch: pytest.MonkeyPatch) -> FakePipeline:
    fake = FakePipeline()
    monkeypatch.setattr(pipeline, "run", fake.run)
    return fake


def invoke(*args: str) -> Result:
    return CliRunner().invoke(cli.app, ["run", *args])


def test_without_a_cycle_a_run_builds_the_current_cycle(
    monkeypatch: pytest.MonkeyPatch, fake_pipeline: FakePipeline
) -> None:
    monkeypatch.setattr(cli, "_today", lambda: date(2027, 3, 1))

    result = invoke()

    assert result.exit_code == 0, result.output
    [(cycle, _, _)] = fake_pipeline.calls
    assert cycle == 2028


def test_a_build_id_resumes_that_build_from_the_step_asked_for(fake_pipeline: FakePipeline) -> None:
    result = invoke("--cycle", "2024", "--build-id", BUILD, "--from", "load")

    assert result.exit_code == 0, result.output
    assert fake_pipeline.calls == [(2024, BUILD, "load")]
    assert f"finished build {BUILD} of 2024" in result.output


@pytest.mark.parametrize(
    "args",
    [("--build-id", "2026-11-08"), ("--cycle", "2023"), ("--dataset",), ("--from", "seats")],
)
def test_a_usage_error_runs_nothing_and_reports_nothing(
    fake_pipeline: FakePipeline,
    pushes: list[tuple[JobFamily, str]],
    bugsink: FakeTransport,
    args: tuple[str, ...],
) -> None:
    result = invoke(*args, "--scheduled")

    assert result.exit_code == 2, result.output
    assert fake_pipeline.calls == []
    # Not a crash: no Bugsink event, and the weekly monitor is not pushed down.
    assert pushes == []
    assert bugsink.events == []


def test_a_superseded_build_exits_1_without_a_crash(
    fake_pipeline: FakePipeline, pushes: list[tuple[JobFamily, str]], bugsink: FakeTransport
) -> None:
    fake_pipeline.superseded = True

    result = invoke("--cycle", "2024", "--build-id", BUILD)

    assert result.exit_code == 1
    assert "start a new build" in result.output
    assert bugsink.events == []


def test_a_scheduled_run_pushes_the_weekly_monitor_up_when_it_finishes(
    fake_pipeline: FakePipeline, pushes: list[tuple[JobFamily, str]], bugsink: FakeTransport
) -> None:
    result = invoke("--cycle", "2024", "--scheduled")

    assert result.exit_code == 0, result.output
    assert pushes == [("weekly", "up")]
    assert bugsink.events == []


def test_a_scheduled_run_that_crashes_pushes_weekly_down_and_reports_the_crash_once(
    fake_pipeline: FakePipeline, pushes: list[tuple[JobFamily, str]], bugsink: FakeTransport
) -> None:
    fake_pipeline.crash = True

    result = invoke("--cycle", "2024", "--scheduled")

    assert result.exit_code == 1
    assert isinstance(result.exception, RuntimeError)
    assert pushes == [("weekly", "down")]
    # Once, tagged with the step that crashed: `run` does not report it again.
    assert len(bugsink.events) == 1
    assert bugsink.events[0]["tags"] == {"pipeline_mode": "load"}


def test_a_run_by_hand_pushes_nothing_to_weekly(
    fake_pipeline: FakePipeline, pushes: list[tuple[JobFamily, str]], bugsink: FakeTransport
) -> None:
    assert invoke("--cycle", "2024").exit_code == 0
    fake_pipeline.crash = True

    result = invoke("--cycle", "2024")

    assert result.exit_code == 1
    assert pushes == []
    # The crash still reaches Bugsink.
    assert len(bugsink.events) == 1
    assert bugsink.events[0]["tags"] == {"pipeline_mode": "load"}
