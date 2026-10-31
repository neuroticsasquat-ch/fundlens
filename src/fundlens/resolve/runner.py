"""`fundlens resolve --full`: every cycle's contributor keys linked into clusters (spec §6).

Resolution reads the newest transformed `contributor` partition of every cycle into its DuckDB
working file (`paths.resolution_database`) as one table, `contributor`: a key reported in several
cycles is one row, its attributes the variant of the cycle with the most contributions, its
counts and totals summed. It trains the Splink model on that table (`resolve.model`), saves the
model as JSON locally and in R2 under this run's `build_id`, writes the `cluster` table beside
`contributor` (`resolve.cluster`), gives every key its persistent donor_id in `app.crosswalk`
(`resolve.crosswalk`), rewrites each cycle's `contribution` and `contributor` partitions with it,
and writes a `resolved` marker for each cycle's transformed build. DuckDB runs under the
pipeline's memory limit and spills under `scratch/`, and each phase's wall time is logged.
"""

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from psycopg import Connection
from psycopg.rows import TupleRow
from splink import DuckDBAPI

from fundlens import markers, paths
from fundlens.r2 import R2
from fundlens.resolve import crosswalk, model
from fundlens.resolve.cluster import CLUSTER_TABLE, cluster
from fundlens.transform.runner import Limits, literal

log = logging.getLogger(__name__)

CONTRIBUTOR_TABLE = "contributor"


@dataclass(frozen=True)
class Thresholds:
    """Where a predicted pair is kept, and where it joins two keys (spec §6.4)."""

    match: float
    cluster: float


@dataclass(frozen=True)
class Resolved:
    """What `resolve_full` did."""

    model_version: str
    model_key: str
    # Whether u and m were estimated, rather than left at their priors (`model.train`).
    trained: bool
    contributor_keys: int
    clusters: int
    # Each cycle resolved, and the transformed build its contributors came from.
    builds: dict[int, str]
    assigned: crosswalk.Assigned
    # DuckDB's memory limit as the run's connection had it.
    memory_limit: str
    # Wall time of each phase, in run order.
    phase_s: dict[str, float] = field(default_factory=dict[str, float])


def transformed_builds(store: R2) -> dict[int, str]:
    """Every cycle with a transformed build, and its newest one, in cycle order."""
    builds: dict[int, str] = {}
    for key in store.list_keys(paths.MARKERS_PREFIX):
        if not key.endswith("/transformed.json"):
            continue
        cycle, build = paths.cycle_of(key), paths.build_of(key)
        if cycle is not None and build is not None:
            builds[cycle] = max(builds.get(cycle, build), build)
    return dict(sorted(builds.items()))


def _local_partition(store: R2, cycle: int, build_id: str, *, data_dir: Path) -> Path:
    """The cycle's `contributor` partition on local disk, downloaded first if not cached."""
    prefix = paths.silver_partition("contributor", cycle, build_id)
    keys = store.list_keys(prefix + "/")
    if not keys:
        raise FileNotFoundError(
            f"no silver contributor partition for build {build_id} of {cycle}:"
            f" run `fundlens transform --cycle {cycle} --build-id {build_id}`"
        )
    for key in keys:
        local = paths.local_path(data_dir, key)
        if not local.exists():
            store.download_to(key, local)
    return paths.local_path(data_dir, prefix)


def _count(con: duckdb.DuckDBPyConnection, partition: Path) -> int:
    [(rows,)] = con.execute(
        f"SELECT count(*) FROM read_parquet({literal(partition / '*.parquet')},"
        " hive_partitioning = false)"
    ).fetchall()
    return rows


def _load_contributors(con: duckdb.DuckDBPyConnection, partitions: list[Path]) -> int:
    """The table `contributor`: one row per key across `partitions`, in the columns the model
    reads (`model.settings`), with its counts and totals across cycles; its row count."""
    files = "[" + ", ".join(literal(part / "*.parquet") for part in partitions) + "]"
    con.execute(
        f"""
        CREATE TABLE {CONTRIBUTOR_TABLE} AS
        WITH reported AS (
            SELECT * FROM read_parquet({files}, hive_partitioning = false)
        ),
        chosen AS (
            SELECT
                *,
                sum(contribution_count) OVER by_key AS contributions,
                sum(amount_total) OVER by_key AS amount,
                min(first_cycle) OVER by_key AS first_seen,
                max(last_cycle) OVER by_key AS last_seen
            FROM reported
            WINDOW by_key AS (PARTITION BY contributor_key)
            QUALIFY row_number() OVER (
                PARTITION BY contributor_key
                ORDER BY contribution_count DESC, amount_total DESC, last_cycle DESC
            ) = 1
        ),
        surname AS (
            SELECT name_last, soundex(name_last) AS last_name_soundex
            FROM (SELECT DISTINCT name_last FROM chosen)
        )
        SELECT
            chosen.contributor_key,
            chosen.name_first AS first_name,
            chosen.name_last AS last_name,
            left(chosen.name_first, 1) AS first_initial,
            surname.last_name_soundex,
            chosen.zip5,
            left(chosen.zip5, 3) AS zip3,
            chosen.city,
            chosen.state,
            chosen.employer_norm,
            chosen.occupation_norm,
            chosen.contributions AS contribution_count,
            chosen.amount AS amount_total,
            chosen.first_seen AS first_cycle,
            chosen.last_seen AS last_cycle
        FROM chosen
        LEFT JOIN surname ON surname.name_last = chosen.name_last
        """
    )
    [(rows,)] = con.execute(f"SELECT count(*) FROM {CONTRIBUTOR_TABLE}").fetchall()
    return rows


@contextmanager
def _phase(name: str, times: dict[str, float]) -> Generator[None]:
    started = time.perf_counter()
    yield
    times[name] = time.perf_counter() - started
    log.info("resolve %s: %.2f s", name, times[name])


def _fresh_database(data_dir: Path) -> Path:
    """The working file, with any earlier run's removed: `--full` rebuilds it whole."""
    database = paths.resolution_database(data_dir)
    database.parent.mkdir(parents=True, exist_ok=True)
    for stale in (database, database.with_name(database.name + ".wal")):
        stale.unlink(missing_ok=True)
    return database


def resolve_full(
    store: R2,
    *,
    build_id: str,
    data_dir: Path,
    limits: Limits,
    thresholds: Thresholds,
    min_training_keys: int,
    conn: Connection[TupleRow],
) -> Resolved:
    """Train the model on every cycle's contributors and cluster them; write the model, the
    `cluster` table, the crosswalk, each cycle's silver with its donor_ids and each cycle's
    `resolved` marker (spec §6.3–§6.6, §5.1).

    Raises `FileNotFoundError` when no cycle has been transformed.
    """
    started_at = datetime.now(UTC)
    builds = transformed_builds(store)
    if not builds:
        raise FileNotFoundError("no transformed build of any cycle: run `fundlens transform`")
    times: dict[str, float] = {}
    scratch = paths.scratch_dir(data_dir)
    scratch.mkdir(parents=True, exist_ok=True)
    database = _fresh_database(data_dir)
    model_key = paths.resolution_model(build_id)
    model_path = paths.local_path(data_dir, model_key)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(database, config=limits.duckdb_config(scratch)) as con:
        model.register(con)
        [(memory_limit,)] = con.execute("SELECT current_setting('memory_limit')").fetchall()
        with _phase("load", times):
            partitions = {
                cycle: _local_partition(store, cycle, build, data_dir=data_dir)
                for cycle, build in builds.items()
            }
            keys = _load_contributors(con, list(partitions.values()))
            cycle_keys = {cycle: _count(con, part) for cycle, part in partitions.items()}
        linker = model.linker(DuckDBAPI(con), CONTRIBUTOR_TABLE, model.settings())
        with _phase("train", times):
            trained = model.train(linker, keys=keys, min_training_keys=min_training_keys)
        with _phase("cluster", times):
            cluster(
                linker, con, match_threshold=thresholds.match, cluster_threshold=thresholds.cluster
            )
            [(clusters,)] = con.execute(
                f"SELECT count(DISTINCT cluster_id) FROM {CLUSTER_TABLE}"
            ).fetchall()
        with _phase("save", times):
            linker.misc.save_model_to_json(str(model_path), overwrite=True)
            # Splink's working tables are a run's scratch; the file keeps the input and clusters.
            linker.table_management.delete_tables_created_by_splink_from_db()
        store.put(model_key, model_path)
        with _phase("crosswalk", times):
            assigned = crosswalk.assign(con, conn, build_id=build_id, scratch=scratch)
        with _phase("silver", times):
            contributions = {
                cycle: crosswalk.onto_silver(
                    con, store, cycle=cycle, build_id=build, data_dir=data_dir
                )
                for cycle, build in builds.items()
            }
    finished_at = datetime.now(UTC)
    for cycle, build in builds.items():
        markers.write(
            "resolved",
            store,
            cycle=cycle,
            build_id=build,
            started_at=started_at,
            finished_at=finished_at,
            # The cycle's own keys, each in `cluster` (a key of several cycles counts in each).
            row_counts={CLUSTER_TABLE: cycle_keys[cycle], "contribution": contributions[cycle]},
        )
    log.info(
        "resolved %d contributor keys into %d clusters across %d cycles (model %s, %s;"
        " DuckDB memory limit %s)",
        keys,
        clusters,
        len(builds),
        build_id,
        "trained" if trained else "priors",
        memory_limit,
    )
    return Resolved(
        build_id, model_key, trained, keys, clusters, builds, assigned, memory_limit, times
    )
