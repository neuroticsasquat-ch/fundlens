"""`pipeline.run` against markers in MinIO: a build skips the steps it finished, so a crashed run
resumes where it stopped (spec §5.1; NEU-2061). The steps are fakes that log their calls and write
their markers, as the real ones do.
"""

import functools
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from fundlens import markers, pipeline
from fundlens.pipeline import Stage
from fundlens.r2 import R2

CYCLE = 2024
BUILD = "20261108T030000Z"
AT = datetime(2026, 11, 8, 3, 0, 0, tzinfo=UTC)


@dataclass
class FakeSteps:
    """Each stage logs its call and writes its marker, unless told to crash or to skip it."""

    store: R2
    crash_in: Stage | None = None
    no_marker_from: Stage | None = None
    calls: list[Stage] = field(default_factory=list[Stage])

    def step(self, stage: Stage) -> None:
        self.calls.append(stage)
        if stage == self.crash_in:
            raise RuntimeError(f"{stage} crashed")
        if stage == self.no_marker_from:
            return
        markers.write(
            pipeline.MARKERS[stage],
            self.store,
            cycle=CYCLE,
            build_id=BUILD,
            started_at=AT,
            finished_at=AT,
            row_counts={},
        )

    def run(self, from_stage: Stage | None = None) -> pipeline.Ran:
        steps: dict[Stage, Callable[[], None]] = {
            stage: functools.partial(self.step, stage) for stage in pipeline.STAGES
        }
        return pipeline.run(CYCLE, self.store, build_id=BUILD, steps=steps, from_stage=from_stage)


def written(store: R2) -> list[Stage]:
    return [
        stage
        for stage in pipeline.STAGES
        if markers.exists(pipeline.MARKERS[stage], store, cycle=CYCLE, build_id=BUILD)
    ]


def test_a_run_crashed_in_load_resumes_with_only_load_and_publish(store: R2) -> None:
    crashed = FakeSteps(store, crash_in="load")
    with pytest.raises(RuntimeError, match="load crashed"):
        crashed.run()
    assert crashed.calls == ["extract", "transform", "resolve", "load"]

    resumed = FakeSteps(store)
    ran = resumed.run()

    assert resumed.calls == ["load", "publish"]
    assert ran == pipeline.Ran(ran=("load", "publish"), skipped=("extract", "transform", "resolve"))
    assert written(store) == list(pipeline.STAGES)


def test_a_finished_build_runs_nothing_again(store: R2) -> None:
    FakeSteps(store).run()

    again = FakeSteps(store)
    ran = again.run()

    assert again.calls == []
    assert ran.skipped == pipeline.STAGES


def test_from_reruns_that_step_and_every_one_after_it(store: R2) -> None:
    FakeSteps(store).run()

    forced = FakeSteps(store)
    forced.run(from_stage="resolve")

    assert forced.calls == ["resolve", "load", "publish"]


def test_a_step_that_writes_no_marker_stops_the_run(store: R2) -> None:
    steps = FakeSteps(store, no_marker_from="resolve")

    with pytest.raises(pipeline.StepWroteNoMarker, match="no `resolved` marker"):
        steps.run()

    assert steps.calls == ["extract", "transform", "resolve"]


def test_a_build_a_newer_one_has_superseded_runs_nothing(store: R2) -> None:
    newer = "20261115T030000Z"
    markers.write(
        "transformed",
        store,
        cycle=CYCLE,
        build_id=newer,
        started_at=AT,
        finished_at=AT,
        row_counts={},
    )
    steps = FakeSteps(store)

    with pytest.raises(pipeline.SupersededBuild, match=f"resume {newer}"):
        steps.run()

    assert steps.calls == []
