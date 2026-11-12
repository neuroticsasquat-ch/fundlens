"""`fundlens run`: every step of one build of one cycle, in order (spec §5.1).

A step whose marker exists for the build is skipped, so a run that crashed is resumed by running
it again with its `--build-id`: the steps that finished are not repeated. `--from` forces a step,
and every step after it, to run again whatever its marker says. The steps themselves are handed
in, which is how the CLI gives it the real commands and the tests give it fakes.
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, get_args

from fundlens import markers
from fundlens.load.gold import newest_transformed
from fundlens.paths import Step
from fundlens.r2 import R2

log = logging.getLogger(__name__)

Stage = Literal["extract", "transform", "resolve", "load", "publish"]
STAGES: tuple[Stage, ...] = get_args(Stage)
# The marker that says a stage finished for the build.
MARKERS: dict[Stage, Step] = {
    "extract": "extracted",
    "transform": "transformed",
    "resolve": "resolved",
    "load": "loaded",
    "publish": "published",
}


class StepWroteNoMarker(RuntimeError):
    """A step returned without writing its marker for the run's build."""


class SupersededBuild(Exception):
    """The build is older than its cycle's newest transformed build, so cannot be run on."""


@dataclass(frozen=True)
class Ran:
    ran: tuple[Stage, ...]
    # Skipped because their marker for the build already existed.
    skipped: tuple[Stage, ...]


def run(
    cycle: int,
    store: R2,
    *,
    build_id: str,
    steps: Mapping[Stage, Callable[[], None]],
    from_stage: Stage | None = None,
) -> Ran:
    """Run each stage of `build_id` of `cycle` in order, skipping one whose marker exists unless
    it is `from_stage` or after it; which stages ran and which were skipped.

    Raises `SupersededBuild`, before running anything, when a newer build of `cycle` has been
    transformed: `resolve --full` marks each cycle's newest transformed build, and `publish`
    swaps in whatever `load` last staged, so going on with an older build would resolve onto
    and publish the newer one's work. Raises `StepWroteNoMarker` when a step returns without its
    marker for `build_id`: the next step would otherwise read another build's output, or none,
    and say nothing.
    """
    newest = newest_transformed(store, cycle)
    if newest is not None and newest > build_id:
        raise SupersededBuild(
            f"build {build_id} of {cycle} is older than its newest transformed build, {newest}:"
            f" resume {newest} with `--build-id {newest}`, or start a new build"
        )
    forced = set(STAGES[STAGES.index(from_stage) :]) if from_stage else set[Stage]()
    ran: list[Stage] = []
    skipped: list[Stage] = []
    for stage in STAGES:
        marker = MARKERS[stage]
        if stage not in forced and markers.exists(marker, store, cycle=cycle, build_id=build_id):
            log.info("%s of build %s of %d: done already, skipped", stage, build_id, cycle)
            skipped.append(stage)
            continue
        log.info("%s of build %s of %d", stage, build_id, cycle)
        steps[stage]()
        if not markers.exists(marker, store, cycle=cycle, build_id=build_id):
            raise StepWroteNoMarker(
                f"{stage} finished but wrote no `{marker}` marker for build {build_id} of {cycle}"
            )
        ran.append(stage)
    return Ran(tuple(ran), tuple(skipped))
