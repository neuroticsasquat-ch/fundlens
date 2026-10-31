"""Every R2 key and local cache path the pipeline uses (spec §3.4), as pure functions.

R2 keys are relative to the bucket. The local cache mirrors them under `DATA_DIR`
(`local_path`), so a step that downloads an object finds it where the key says it lives, and the
disk can be dropped at any time without losing anything R2 does not hold (ADR-0002).
"""

import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

# The silver tables of the canonical schema (spec §4).
SilverTable = Literal[
    "committee",
    "candidate",
    "candidate_committee_link",
    "race",
    "contributor",
    "contribution",
    "committee_transfer",
    "independent_expenditure",
]

# One completion marker per pipeline step (spec §5.1), named for the state it records.
Step = Literal["extracted", "transformed", "resolved", "loaded", "published"]

# The resolution tables snapshotted to R2 at publish (spec §5.5).
ResolutionTable = Literal["crosswalk", "adjudication"]

BUILD_ID_FORMAT = "%Y%m%dT%H%M%SZ"
_BUILD_ID = re.compile(r"\d{8}T\d{6}Z")
_BUILD_IN_KEY = re.compile(r"/build=(\d{8}T\d{6}Z)(?:/|$)")
_CYCLE_IN_KEY = re.compile(r"/cycle=(\d+)/")

# Every completion marker of every cycle lives under here (`markers_dir`).
MARKERS_PREFIX = "markers/"

# `silver/contribution` is split into donor_id % 256 buckets (spec §3.4).
BUCKETS = 256


def format_build_id(started_at: datetime) -> str:
    """The `build_id` for a run that started at `started_at`: `YYYYMMDDTHHMMSSZ`, in UTC."""
    if started_at.tzinfo is None:
        raise ValueError("started_at must be timezone-aware")
    return started_at.astimezone(UTC).strftime(BUILD_ID_FORMAT)


def parse_build_id(build_id: str) -> datetime:
    """The run start a `build_id` encodes, as an aware UTC datetime."""
    _check_build_id(build_id)
    return datetime.strptime(build_id, BUILD_ID_FORMAT).replace(tzinfo=UTC)


def _check_build_id(build_id: str) -> None:
    # A `build_id` reaches these functions from `--build-id` on the command line; a malformed one
    # would otherwise write a build directory no reader ever resolves.
    if not _BUILD_ID.fullmatch(build_id):
        raise ValueError(f"build_id {build_id!r} is not YYYYMMDDTHHMMSSZ")


def _check_cycle(cycle: int) -> None:
    # FEC two-year cycles are named for their even closing year.
    if cycle < 1 or cycle % 2:
        raise ValueError(f"cycle {cycle} is not an even year")


def bronze_dir(cycle: int, file: str) -> str:
    """Every download of one FEC bulk file for one cycle: `bronze/cycle=<c>/<file>/`."""
    _check_cycle(cycle)
    return f"bronze/cycle={cycle}/{file}/"


def bronze_zip(cycle: int, file: str, download_date: date) -> str:
    """One FEC bulk zip, as downloaded on `download_date`: `bronze/cycle=<c>/<file>/<date>.zip`."""
    return f"{bronze_dir(cycle, file)}{download_date.isoformat()}.zip"


def silver_cycle_dir(table: SilverTable, cycle: int) -> str:
    """Every build of one cycle of a silver table: `silver/<table>/cycle=<c>/`."""
    _check_cycle(cycle)
    return f"silver/{table}/cycle={cycle}/"


def silver_partition(table: SilverTable, cycle: int, build_id: str) -> str:
    """The directory holding one build of one cycle of a silver table."""
    _check_build_id(build_id)
    return f"{silver_cycle_dir(table, cycle)}build={build_id}"


def silver_bucket(cycle: int, build_id: str, bucket: int) -> str:
    """One `donor_id % 256` bucket of a `silver/contribution` build, named in two-digit hex."""
    if not 0 <= bucket < BUCKETS:
        raise ValueError(f"bucket {bucket} is outside 0..{BUCKETS - 1}")
    return f"{silver_partition('contribution', cycle, build_id)}/bucket={bucket:02x}"


def rewrite_sentinel(cycle: int, build_id: str) -> str:
    """The object a donor_id rewrite of a `silver/contribution` build holds while it replaces the
    build's parts in R2 (`resolve.crosswalk`): while it exists, the parts are not to be read."""
    return f"{silver_partition('contribution', cycle, build_id)}/_rewriting"


def part(index: int) -> str:
    """The file name of the `index`th Parquet part in a partition or bucket."""
    return f"part-{index:04d}.parquet"


def resolution_snapshot(build_id: str, table: ResolutionTable) -> str:
    """The snapshot of a resolution table taken when `build_id` was published."""
    _check_build_id(build_id)
    return f"resolution/build={build_id}/{table}.parquet"


def markers_dir(cycle: int) -> str:
    """Every marker of every build of one cycle: `markers/cycle=<c>/`."""
    _check_cycle(cycle)
    return f"{MARKERS_PREFIX}cycle={cycle}/"


def marker(cycle: int, build_id: str, step: Step) -> str:
    """The completion marker `step` writes for one build of one cycle (spec §5.1)."""
    _check_build_id(build_id)
    return f"{markers_dir(cycle)}build={build_id}/{step}.json"


def build_of(key: str) -> str | None:
    """The `build_id` in a silver or marker key's `build=` segment, or None if it has none.

    How a step lists the builds under a cycle prefix: `build_id`s are `YYYYMMDDTHHMMSSZ`, so
    sorting the results sorts them by run start.
    """
    match = _BUILD_IN_KEY.search(key)
    return match.group(1) if match else None


def cycle_of(key: str) -> int | None:
    """The cycle in a silver or marker key's `cycle=` segment, or None if it has none."""
    match = _CYCLE_IN_KEY.search(key)
    return int(match.group(1)) if match else None


def resolution_model(version: str) -> str:
    """The trained Splink model `version`, as JSON: `resolution/model/<version>.json`.

    A model's version is the `build_id` of the `resolve --full` run that trained it, so key
    order is training order.
    """
    _check_build_id(version)
    return f"resolution/model/{version}.json"


def local_path(data_dir: Path, key: str) -> Path:
    """Where the local cache keeps the object at `key`."""
    return data_dir / key


def scratch_dir(data_dir: Path) -> Path:
    """DuckDB's `temp_directory`. Local only: nothing in it outlives a run."""
    return data_dir / "scratch"


def resolution_dir(data_dir: Path) -> Path:
    """The Splink model and DuckDB working file. Local only: R2 keeps the snapshots."""
    return data_dir / "resolution"


def resolution_database(data_dir: Path) -> Path:
    """Resolution's DuckDB working file: the `contributor` keys it linked and their `cluster`s,
    which the crosswalk reads. Local only, rebuilt by every `resolve --full`."""
    return resolution_dir(data_dir) / "resolve.duckdb"
