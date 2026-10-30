"""Itemized contributions, read from silver Parquet by in-process DuckDB (ADR-0006, spec §7.2).

Postgres holds only aggregates; "what did this committee or candidate actually receive" is a row
list scanned out of one silver partition, `silver/contribution/cycle=<c>/build=<b>/`, where
`<b>` is the cycle's live build in `gold.meta.cycles`. Every request is a filtered, ordered,
limited scan: never an aggregate.

Rows come newest first, ties broken by `source_record_id`, and are paged by an opaque cursor
holding the last row's `(date, source_record_id)` and the build it was read from. A cursor keeps
reading its own build after a publish swaps a newer one in, so a walk through the pages neither
skips nor repeats a row; once that build is pruned the cursor is gone (`BuildGone`) and the walk
must start again from the first page.

The partitions are read from `DATA_DIR/silver`, the silver volume the `api` service mounts
read-only. Reading R2 over httpfs instead, for a runner with no volume, is a change to where
`partition` points, not to the query.
"""

import base64
import binascii
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

import duckdb

from fundlens import paths
from fundlens.load.db import Pool

PAGE_SIZE = 100

# Small, because one request reads one partition and returns at most a page of it; the pipeline's
# DuckDB limits are its own (settings.py) and never reach the API.
MEMORY_LIMIT = "512MB"
THREADS = 2

# What a page filters on: a candidate's contributions, or a committee's receipts.
type Recipient = Literal["candidate_id", "recipient_committee_id"]

COLUMNS: tuple[str, ...] = (
    "source_record_id",
    "date",
    "amount",
    "recipient_committee_id",
    "candidate_id",
    "contributor_name",
    "contributor_city",
    "contributor_state",
    "contributor_zip",
    "contributor_employer",
    "contributor_occupation",
    "entity_type",
    "transaction_type",
    "report_type",
    "memo_text",
    "conduit_committee_id",
    "is_self_funding",
    "image_num",
)


class CycleNotLive(Exception):
    """No published build covers the cycle."""


class BadCursor(Exception):
    """The cursor is not one this API issued."""


class BuildGone(Exception):
    """The cursor's build has been pruned since its first page was read."""


@dataclass(frozen=True)
class Cursor:
    """Where a page ends: the build it was read from and its last row's sort key."""

    build_id: str
    date: date | None
    source_record_id: int

    def encode(self) -> str:
        raw = json.dumps(
            [self.build_id, self.date and self.date.isoformat(), str(self.source_record_id)],
            separators=(",", ":"),
        )
        return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, token: str) -> "Cursor":
        try:
            raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
            build_id, day, record = json.loads(raw)
            paths.parse_build_id(build_id)
            return cls(build_id, None if day is None else date.fromisoformat(day), int(record))
        except (binascii.Error, UnicodeDecodeError, TypeError, ValueError) as exc:
            # json.JSONDecodeError is a ValueError, as is a malformed build id or date.
            raise BadCursor(token) from exc


@dataclass(frozen=True)
class Page:
    rows: list[dict[str, Any]]
    next_cursor: str | None


def read_live_builds(pool: Pool) -> dict[int, str]:
    """Each cycle's live silver build, from `gold.meta.cycles`.

    An `UndefinedTable` before the first publish propagates, and the API answers it with a 503.
    """
    with pool.connection() as conn:
        row = conn.execute("SELECT cycles FROM gold.meta").fetchone()
    if row is None:
        return {}
    cycles: Mapping[str, Mapping[str, str]] = row[0]
    return {int(cycle): entry["build_id"] for cycle, entry in cycles.items()}


class ItemizedReader:
    """One DuckDB database per process; each read takes a cursor of its own, since the routes
    run in a thread pool and a DuckDB connection is not safe to share between threads."""

    def __init__(self, data_dir: Path, live_builds: Callable[[], Mapping[int, str]]) -> None:
        self._data_dir = data_dir
        self._live_builds = live_builds
        self._db = duckdb.connect(
            config={
                "memory_limit": MEMORY_LIMIT,
                "threads": THREADS,
                # Never fetch an extension from the network in a request.
                "autoinstall_known_extensions": False,
                "autoload_known_extensions": False,
            }
        )

    def close(self) -> None:
        self._db.close()

    def partition(self, cycle: int, build_id: str) -> Path:
        return paths.local_path(
            self._data_dir, paths.silver_partition("contribution", cycle, build_id)
        )

    def contributions(
        self,
        cycle: int,
        recipient: Recipient,
        recipient_id: str,
        *,
        cursor: str | None,
        limit: int = PAGE_SIZE,
    ) -> Page:
        """One page of `recipient_id`'s contributions in `cycle`, after `cursor` if given.

        Raises `CycleNotLive`, `BadCursor`, or `BuildGone` for a cursor whose build is pruned.
        """
        after = None if cursor is None else Cursor.decode(cursor)
        if after is None:
            build_id = self._live_builds().get(cycle)
            if build_id is None:
                raise CycleNotLive(cycle)
        else:
            build_id = after.build_id
        partition = self.partition(cycle, build_id)
        if not partition.is_dir():
            if after is not None:
                raise BuildGone(build_id)
            # gold.meta names a build the volume does not hold: not the caller's doing.
            raise FileNotFoundError(f"live silver partition missing: {partition}")
        # `date DESC` puts nulls last; the keyset predicate below follows the same order.
        where = [f"{recipient} = $recipient_id"]
        params: dict[str, object] = {
            "files": str(partition / "**" / "*.parquet"),
            "recipient_id": recipient_id,
            "limit": limit + 1,
        }
        if after is not None:
            params["after_id"] = after.source_record_id
            if after.date is None:
                where.append("date IS NULL AND source_record_id > $after_id")
            else:
                params["after_date"] = after.date
                where.append(
                    "(date < $after_date OR date IS NULL"
                    " OR (date = $after_date AND source_record_id > $after_id))"
                )
        query = (
            f"SELECT {', '.join(COLUMNS)}"
            " FROM read_parquet($files, hive_partitioning = false)"
            f" WHERE {' AND '.join(where)}"
            " ORDER BY date DESC NULLS LAST, source_record_id"
            " LIMIT $limit"
        )
        try:
            with self._db.cursor() as con:
                result = con.execute(query, params)
                rows = [dict(zip(COLUMNS, row, strict=True)) for row in result.fetchall()]
        except duckdb.IOException:
            # Pruned between the check above and the read.
            if after is not None and not partition.is_dir():
                raise BuildGone(build_id) from None
            raise
        more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = None
        if more:
            last = rows[-1]
            next_cursor = Cursor(build_id, last["date"], last["source_record_id"]).encode()
        return Page(rows, next_cursor)
