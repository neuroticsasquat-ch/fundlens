"""`fundlens publish`: make a loaded gold build live (spec §5.5, NEU-2039 §4.2–§4.6).

One transaction renames `gold_build` to `gold` and the old `gold` to `gold_prev`, so a reader
sees the old build or the new one and never a half-loaded state. Then, once the API's build-id
cache has surely expired, the Cloudflare zone is purged, `app.crosswalk` snapshotted to R2, the
`published` marker written and silver builds older than the previous live one pruned.
`--rollback` swaps `gold_prev` back.

Every Postgres statement here is DDL or a fixed `UPDATE` with nothing to parameterise; the
connection is autocommit so that `conn.transaction()` is one real transaction, not a savepoint
inside an implicit one.
"""

import logging
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import psycopg
from psycopg import Connection, sql
from psycopg.rows import TupleRow

from fundlens import markers, paths
from fundlens.api.cache import BUILD_ID_TTL_SECONDS
from fundlens.paths import SilverTable
from fundlens.publish.cloudflare import Purge
from fundlens.r2 import R2
from fundlens.resolve import crosswalk

log = logging.getLogger(__name__)

# The API re-reads the live build id for its `ETag` at most once a minute (`api.cache`); a purge
# inside that window would let the edge keep a new body under the old `ETag` for a week.
PURGE_DELAY_SECONDS = BUILD_ID_TTL_SECONDS + 15
# A waiting `AccessExclusiveLock` queues ahead of new readers, so a stuck session on a `gold_prev`
# table would stall every API request: the swap gives up instead, and tries again.
LOCK_TIMEOUT = "10s"
SWAP_ATTEMPTS = 3
SWAP_RETRY_SECONDS = 5.0

Sleep = Callable[[float], None]


class NothingToPublish(Exception):
    """No `gold_build` holds this cycle and there is no interrupted publish to finish."""


class NothingToRollBack(Exception):
    """No `gold_prev` build to swap back in."""


@dataclass(frozen=True)
class Pruned:
    builds: int
    objects: int


@dataclass(frozen=True)
class Published:
    """What `publish` did."""

    build_id: str
    # The build now in `gold_prev`, or None on the first publish ever.
    previous_build_id: str | None
    # False when an interrupted publish was resumed: the swap had already happened.
    swapped: bool
    purged: bool
    # The R2 key of the crosswalk as of this publish (spec §5.5).
    crosswalk_key: str
    marker: markers.Marker
    pruned: Pruned


@dataclass(frozen=True)
class RolledBack:
    """What `rollback` did: the build now live, and the one it put in `gold_prev`."""

    build_id: str
    previous_build_id: str


def _schema_exists(conn: Connection[TupleRow], schema: str) -> bool:
    row = conn.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,)).fetchone()
    return row is not None


def _meta(conn: Connection[TupleRow], schema: str) -> tuple[str, dict[str, dict[str, str]]] | None:
    """`(build_id, cycles)` from `<schema>.meta`, or None when there is no such row."""
    if not _schema_exists(conn, schema):
        return None
    try:
        row = conn.execute(
            sql.SQL("SELECT build_id, cycles FROM {}.meta").format(sql.Identifier(schema))
        ).fetchone()
    except psycopg.errors.UndefinedTable:
        return None
    if row is None:
        return None
    build_id, cycles = row
    return str(build_id), cycles


def _live_build(conn: Connection[TupleRow], schema: str, cycle: int) -> str | None:
    """The build `<schema>.meta.cycles` names for `cycle`, or None."""
    meta = _meta(conn, schema)
    if meta is None:
        return None
    entry = meta[1].get(str(cycle))
    return entry["build_id"] if entry else None


def _with_lock_timeout(conn: Connection[TupleRow], statements: list[str], *, sleep: Sleep) -> None:
    """Run `statements` in one transaction under `LOCK_TIMEOUT`, retrying a lock timeout."""
    for attempt in range(1, SWAP_ATTEMPTS + 1):
        try:
            with conn.transaction():
                conn.execute(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'")
                for statement in statements:
                    # The statements are the fixed DDL below, never built from input.
                    conn.execute(statement.encode())
            return
        except psycopg.errors.LockNotAvailable:
            if attempt == SWAP_ATTEMPTS:
                raise
            log.warning(
                "schema swap waited %s for a lock (attempt %d), retrying", LOCK_TIMEOUT, attempt
            )
            sleep(SWAP_RETRY_SECONDS)


def swap(conn: Connection[TupleRow], *, sleep: Sleep = time.sleep) -> None:
    """`gold_build` becomes `gold`, `gold` becomes `gold_prev`, the old `gold_prev` is dropped.

    The drop comes first: `gold_prev` holds a build no API query names, so its exclusive locks
    never wait on a reader, while a rename locks only the schema's catalog row. A first-ever
    publish creates an empty `gold` so the renames are uniform.
    """
    _with_lock_timeout(
        conn,
        [
            "UPDATE gold_build.meta SET published_at = now()",
            "CREATE SCHEMA IF NOT EXISTS gold",
            "DROP SCHEMA IF EXISTS gold_prev CASCADE",
            "ALTER SCHEMA gold RENAME TO gold_prev",
            "ALTER SCHEMA gold_build RENAME TO gold",
        ],
        sleep=sleep,
    )


def _purge(purge: Purge | None, *, sleep: Sleep) -> bool:
    """Wait out the API's build-id cache, then purge; False when no zone is configured."""
    if purge is None:
        log.info("cloudflare purge skipped: not configured")
        return False
    sleep(PURGE_DELAY_SECONDS)
    purge()
    return True


def prune(store: R2, *, data_dir: Path, cycle: int, live: str, prev: str | None) -> Pruned:
    """Delete, in R2 and locally, every silver build of `cycle` older than the previous live one.

    Builds newer than the live one are left alone: someone may have transformed the next build
    and not loaded it yet. Markers are never pruned.
    """
    cutoff = min(live, prev) if prev else live
    builds: set[str] = set()
    objects = 0
    for table in get_args(SilverTable):
        prefix = paths.silver_cycle_dir(table, cycle)
        stale = {
            build
            for key in store.list_keys(prefix)
            if (build := paths.build_of(key)) is not None and build < cutoff
        }
        for build in sorted(stale):
            partition = paths.silver_partition(table, cycle, build)
            objects += store.delete_prefix(partition + "/")
            shutil.rmtree(paths.local_path(data_dir, partition), ignore_errors=True)
            builds.add(build)
    if builds:
        log.info("pruned %d silver builds of %d (%d objects)", len(builds), cycle, objects)
    return Pruned(len(builds), objects)


def publish(
    cycle: int,
    store: R2,
    *,
    conn: Connection[TupleRow],
    data_dir: Path,
    purge: Purge | None,
    sleep: Sleep = time.sleep,
) -> Published:
    """Swap the loaded build of `cycle` in, purge the edge, snapshot the crosswalk, write
    `published`, prune silver.

    Resumes a publish that swapped but did not finish (a `PurgeFailed`, a crash): with no
    `gold_build`, `gold` naming a build for `cycle` and no `published` marker for it, only the
    purge, the marker and the prune are done. Raises `NothingToPublish` when neither applies,
    and `PurgeFailed` after the swap, in which case re-running finishes the publish.
    """
    started_at = datetime.now(UTC)
    staged = _live_build(conn, "gold_build", cycle)
    if staged is not None:
        previous = _live_build(conn, "gold", cycle)
        swap(conn, sleep=sleep)
        build_id, swapped = staged, True
        log.info("published build %s of %d (previous: %s)", build_id, cycle, previous or "none")
    else:
        live = _live_build(conn, "gold", cycle)
        if live is None or markers.exists("published", store, cycle=cycle, build_id=live):
            raise NothingToPublish(
                f"no loaded build for {cycle}: run `fundlens load --cycle {cycle}`"
            )
        previous = _live_build(conn, "gold_prev", cycle)
        build_id, swapped = live, False
        log.info("resuming the publish of build %s of %d after its swap", build_id, cycle)
    purged = _purge(purge, sleep=sleep)
    # Before the marker: a publish resumed after a failed snapshot must take it again.
    crosswalk_key = crosswalk.snapshot(
        conn, store, build_id=build_id, scratch=paths.scratch_dir(data_dir)
    )
    loaded = markers.read("loaded", store, cycle=cycle, build_id=build_id)
    marker = markers.write(
        "published",
        store,
        cycle=cycle,
        build_id=build_id,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        row_counts=loaded.row_counts if loaded else {},
    )
    pruned = prune(store, data_dir=data_dir, cycle=cycle, live=build_id, prev=previous)
    return Published(build_id, previous, swapped, purged, crosswalk_key, marker, pruned)


def rollback(
    conn: Connection[TupleRow], *, purge: Purge | None, sleep: Sleep = time.sleep
) -> RolledBack:
    """Swap `gold_prev` back in as `gold` and purge again; a second rollback swaps forward.

    No marker and no prune: the build was published, and its marker stands. Raises
    `NothingToRollBack` when `gold_prev` holds no build.
    """
    previous = _meta(conn, "gold_prev")
    if previous is None:
        raise NothingToRollBack("nothing to roll back to: gold_prev holds no build")
    live = _meta(conn, "gold")
    if live is None:
        raise NothingToRollBack("nothing to roll back from: gold holds no build")
    _with_lock_timeout(
        conn,
        [
            "ALTER SCHEMA gold RENAME TO gold_rollback",
            "ALTER SCHEMA gold_prev RENAME TO gold",
            "ALTER SCHEMA gold_rollback RENAME TO gold_prev",
        ],
        sleep=sleep,
    )
    log.info("rolled back to build %s; build %s is now gold_prev", previous[0], live[0])
    _purge(purge, sleep=sleep)
    return RolledBack(previous[0], live[0])
