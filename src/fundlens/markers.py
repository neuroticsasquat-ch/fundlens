"""Per-step completion markers in R2 (spec §5.1).

A marker says one step finished for one build of one cycle; `run` skips a step whose marker
exists, which is what lets a crashed run resume with `--build-id`. Its JSON is the M1 shared
contract: `{build_id, step, cycle, started_at, finished_at, row_counts, duration_s}`.
"""

from datetime import datetime

from pydantic import AwareDatetime, BaseModel

from fundlens import paths
from fundlens.paths import Step
from fundlens.r2 import R2


class Marker(BaseModel):
    build_id: str
    step: Step
    cycle: int
    started_at: AwareDatetime
    finished_at: AwareDatetime
    # Rows written, per table the step wrote.
    row_counts: dict[str, int]
    duration_s: float


def write(
    step: Step,
    store: R2,
    *,
    cycle: int,
    build_id: str,
    started_at: datetime,
    finished_at: datetime,
    row_counts: dict[str, int],
) -> Marker:
    """Record that `step` finished; the marker written."""
    marker = Marker(
        build_id=build_id,
        step=step,
        cycle=cycle,
        started_at=started_at,
        finished_at=finished_at,
        row_counts=row_counts,
        duration_s=(finished_at - started_at).total_seconds(),
    )
    store.put(paths.marker(cycle, build_id, step), marker.model_dump_json().encode())
    return marker


def read(step: Step, store: R2, *, cycle: int, build_id: str) -> Marker | None:
    """The marker `step` wrote for this build, or None if it has not finished."""
    try:
        raw = store.get(paths.marker(cycle, build_id, step))
    except FileNotFoundError:
        return None
    return Marker.model_validate_json(raw)


def exists(step: Step, store: R2, *, cycle: int, build_id: str) -> bool:
    return store.exists(paths.marker(cycle, build_id, step))
