"""The R2 and local path layout of spec §3.4."""

from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from fundlens import paths

BUILD = "20261102T030000Z"


@pytest.mark.parametrize(
    ("built", "expected"),
    [
        (
            paths.bronze_zip(2026, "indiv", date(2026, 11, 2)),
            "bronze/cycle=2026/indiv/2026-11-02.zip",
        ),
        (paths.bronze_dir(2024, "cm"), "bronze/cycle=2024/cm/"),
        (
            f"{paths.silver_partition('committee', 2024, BUILD)}/{paths.part(0)}",
            f"silver/committee/cycle=2024/build={BUILD}/part-0000.parquet",
        ),
        (
            f"{paths.silver_bucket(2024, BUILD, 0)}/{paths.part(12)}",
            f"silver/contribution/cycle=2024/build={BUILD}/bucket=00/part-0012.parquet",
        ),
        (
            f"{paths.silver_bucket(2024, BUILD, 255)}/{paths.part(0)}",
            f"silver/contribution/cycle=2024/build={BUILD}/bucket=ff/part-0000.parquet",
        ),
        (
            paths.resolution_snapshot(BUILD, "crosswalk"),
            f"resolution/build={BUILD}/crosswalk.parquet",
        ),
        (
            paths.resolution_snapshot(BUILD, "adjudication"),
            f"resolution/build={BUILD}/adjudication.parquet",
        ),
        *[
            (paths.marker(2026, BUILD, step), f"markers/cycle=2026/build={BUILD}/{step}.json")
            for step in ("extracted", "transformed", "resolved", "loaded", "published")
        ],
    ],
)
def test_builds_every_example_path_in_the_spec(built: str, expected: str) -> None:
    assert built == expected


@pytest.mark.parametrize(
    "started_at",
    [
        datetime(2026, 11, 2, 3, 0, 0, tzinfo=UTC),
        datetime(1980, 1, 1, 0, 0, 0, tzinfo=UTC),
        datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC),
    ],
)
def test_build_id_round_trips(started_at: datetime) -> None:
    build_id = paths.format_build_id(started_at)

    assert paths.parse_build_id(build_id) == started_at


def test_build_id_is_the_utc_time_of_run_start() -> None:
    # 03:00 box time in Berlin summer is 01:00 UTC; microseconds don't survive.
    started_at = datetime(2026, 7, 5, 3, 0, 0, 999, tzinfo=timezone(timedelta(hours=2)))

    assert paths.format_build_id(started_at) == "20260705T010000Z"


def test_build_id_needs_an_aware_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        paths.format_build_id(datetime(2026, 11, 2, 3, 0, 0))


@pytest.mark.parametrize("build_id", ["2026-11-02T03:00:00Z", "20261102T030000", "latest", ""])
def test_rejects_a_malformed_build_id(build_id: str) -> None:
    with pytest.raises(ValueError, match="YYYYMMDDTHHMMSSZ"):
        paths.marker(2026, build_id, "transformed")


@pytest.mark.parametrize("cycle", [2025, 0, -2])
def test_rejects_a_cycle_that_is_not_an_even_year(cycle: int) -> None:
    with pytest.raises(ValueError, match="even year"):
        paths.silver_partition("committee", cycle, BUILD)


@pytest.mark.parametrize("bucket", [-1, 256])
def test_rejects_a_bucket_outside_256(bucket: int) -> None:
    with pytest.raises(ValueError, match="outside 0..255"):
        paths.silver_bucket(2024, BUILD, bucket)


def test_the_local_cache_mirrors_the_r2_key() -> None:
    data_dir = Path("/data/fundlens")
    key = paths.bronze_zip(2026, "indiv", date(2026, 11, 2))

    assert paths.local_path(data_dir, key) == Path(
        "/data/fundlens/bronze/cycle=2026/indiv/2026-11-02.zip"
    )
    assert paths.scratch_dir(data_dir) == Path("/data/fundlens/scratch")
    assert paths.resolution_dir(data_dir) == Path("/data/fundlens/resolution")
