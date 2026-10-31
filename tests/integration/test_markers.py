"""Step completion markers written to MinIO (spec §5.1)."""

import json
from datetime import UTC, datetime

from fundlens import markers, paths
from fundlens.r2 import R2

BUILD = "20261102T030000Z"
STARTED = datetime(2026, 11, 2, 3, 0, 0, tzinfo=UTC)
FINISHED = datetime(2026, 11, 2, 3, 12, 30, 500000, tzinfo=UTC)


def test_a_written_marker_exists_and_carries_the_contract_fields(store: R2) -> None:
    assert not markers.exists("transformed", store, cycle=2026, build_id=BUILD)

    markers.write(
        "transformed",
        store,
        cycle=2026,
        build_id=BUILD,
        started_at=STARTED,
        finished_at=FINISHED,
        row_counts={"committee": 17_000, "contribution": 40_000_000},
    )

    assert markers.exists("transformed", store, cycle=2026, build_id=BUILD)
    body = json.loads(store.get(paths.marker(2026, BUILD, "transformed")))
    assert body == {
        "build_id": BUILD,
        "step": "transformed",
        "cycle": 2026,
        "started_at": "2026-11-02T03:00:00Z",
        "finished_at": "2026-11-02T03:12:30.500000Z",
        "row_counts": {"committee": 17_000, "contribution": 40_000_000},
        "duration_s": 750.5,
    }


def test_read_returns_what_write_wrote(store: R2) -> None:
    written = markers.write(
        "loaded",
        store,
        cycle=2024,
        build_id=BUILD,
        started_at=STARTED,
        finished_at=FINISHED,
        row_counts={},
    )

    assert markers.read("loaded", store, cycle=2024, build_id=BUILD) == written


def test_a_step_that_has_not_finished_has_no_marker(store: R2) -> None:
    markers.write(
        "extracted",
        store,
        cycle=2026,
        build_id=BUILD,
        started_at=STARTED,
        finished_at=FINISHED,
        row_counts={},
    )

    assert markers.read("transformed", store, cycle=2026, build_id=BUILD) is None
    assert not markers.exists("extracted", store, cycle=2026, build_id="20261109T030000Z")
