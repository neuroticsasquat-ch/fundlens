"""`fundlens resolve --full`: every cycle's contributor keys linked into clusters (spec §6).

Resolution reads the newest transformed `contributor` partition of every cycle into its DuckDB
working file (`paths.resolution_database`) as one table, `contributor`: a key reported in several
cycles is one row, its attributes the variant of the cycle with the most contributions (for a key
with none, the most JFC attributions), its counts and totals summed. It trains the Splink model
on that table (`resolve.model`) and saves it as JSON, locally and in R2 under this run's
`build_id`, straight away, so a run that fails later keeps its training; or, with `reuse`, reads
a saved model back and trains nothing (NEU-2325). It writes the `edge`, `component` and
re-clustered `cluster` tables beside `contributor` (`resolve.cluster`), merges and
splits it as `resolution/overrides.yaml` asserts (`resolve.overrides`) and then as the confident
verdicts of `fundlens adjudicate` say (`resolve.adjudicate`), gives every key its
persistent donor_id in `app.crosswalk` (`resolve.crosswalk`), rewrites each cycle's
`contribution`, `jfc_attribution` and `contributor` partitions with it, and writes a `resolved`
marker for each cycle's transformed build and, last, the run's record (`RunRecord`) beside its
model, which makes that model the live model (`model.live_version`).
Splink's scratch tables are dropped as soon as the run has used them (`model.drop_scratch`).
DuckDB runs under the pipeline's memory limit and
spills under `scratch/`, and each phase's wall time is logged.
"""

import json
import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

import duckdb
from psycopg import Connection
from psycopg.rows import TupleRow
from pydantic import BaseModel
from splink import DuckDBAPI

from fundlens import markers, paths
from fundlens.r2 import R2
from fundlens.resolve import adjudicate, crosswalk, model, nicknames, overrides
from fundlens.resolve.cluster import (
    CLUSTER_TABLE,
    COMPONENT_TABLE,
    EDGE_TABLE,
    Reclustered,
    cluster,
    components_at,
    recluster,
)
from fundlens.transform.runner import Limits, literal

log = logging.getLogger(__name__)

CONTRIBUTOR_TABLE = "contributor"


@dataclass(frozen=True)
class Thresholds:
    """Where a predicted pair is kept, and where it joins two keys (spec §6.4)."""

    match: float
    cluster: float


class Parameters(StrEnum):
    """Where a run's model parameters came from, as the CLI prints it."""

    # u and m estimated from the contributors (`model.train`).
    TRAINED = "trained"
    # Too few keys to estimate u and m: the model keeps its priors.
    PRIORS = "priors (too few keys to train on)"
    # A saved model read back (`resolve --full --model`): nothing trained.
    REUSED = "reused (saved model)"


@dataclass(frozen=True)
class Resolved:
    """What `resolve_full` did."""

    model_version: str
    model_key: str
    parameters: Parameters
    contributor_keys: int
    clusters: int
    reclustered: Reclustered
    # Each cycle resolved, and the transformed build its contributors came from.
    builds: dict[int, str]
    overridden: overrides.Applied
    adjudicated: adjudicate.Applied
    assigned: crosswalk.Assigned
    # DuckDB's memory limit as the run's connection had it.
    memory_limit: str
    # Wall time of each phase, in run order.
    phase_s: dict[str, float] = field(default_factory=dict[str, float])


class RunRecord(BaseModel):
    """What a `resolve --full` run applied, saved under its model version
    (`paths.resolution_run`) for `load` to carry into `gold.meta` (NEU-2056).

    Keyed by the model, so it describes the `--full` run that last resolved with the live
    model; it is what makes a saved model live (`model.live_version`). An incremental run
    (NEU-2062) that applies overrides without training must write its own.
    """

    # The deployed release (commit) that resolved; None where none is known (dev, CI).
    release: str | None
    # Override entries applied: merges and splits.
    overrides: int
    # Adjudication verdicts that merged or split clusters.
    adjudications: int


def run_record(store: R2, version: str) -> RunRecord | None:
    """The record of the run that resolved with model `version`, or None if it wrote none (a
    run before NEU-2056, or one that stopped part way). The live model always has one."""
    try:
        raw = store.get(paths.resolution_run(version))
    except FileNotFoundError:
        return None
    return RunRecord.model_validate_json(raw)


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
    """The cycle's `contributor` partition on local disk, downloaded first if not cached.

    Raises `FileNotFoundError` when the build has no `contributor` partition, or no
    `jfc_attribution` one: a build transformed before JFC attributions (NEU-2078) has neither
    that table nor `contributor.attribution_count`, and must be transformed again.
    """
    prefix = paths.silver_partition("contributor", cycle, build_id)
    keys = store.list_keys(prefix + "/")
    attributions = store.list_keys(paths.silver_partition("jfc_attribution", cycle, build_id) + "/")
    for table, present in (("contributor", keys), ("jfc_attribution", attributions)):
        if not present:
            raise FileNotFoundError(
                f"no silver {table} partition for build {build_id} of {cycle}:"
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
    reads (`model.settings`, the first name's `first_name_nicknames` from `nicknames.pairs`), with
    its counts and totals across cycles; its row count."""
    files = "[" + ", ".join(literal(part / "*.parquet") for part in partitions) + "]"
    linked = sorted(nicknames.pairs())
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
                sum(attribution_count) OVER by_key AS attributions,
                min(first_cycle) OVER by_key AS first_seen,
                max(last_cycle) OVER by_key AS last_seen
            FROM reported
            WINDOW by_key AS (PARTITION BY contributor_key)
            QUALIFY row_number() OVER (
                PARTITION BY contributor_key
                ORDER BY
                    contribution_count DESC,
                    amount_total DESC,
                    attribution_count DESC,
                    last_cycle DESC
            ) = 1
        ),
        surname AS (
            SELECT name_last, soundex(name_last) AS last_name_soundex
            FROM (SELECT DISTINCT name_last FROM chosen)
        ),
        -- Each first name the nickname table names, and the names it links to that one.
        nickname AS (
            SELECT name, list(DISTINCT other ORDER BY other) AS first_name_nicknames
            FROM (SELECT unnest($names::VARCHAR[]) AS name, unnest($others::VARCHAR[]) AS other)
            GROUP BY name
        )
        SELECT
            chosen.contributor_key,
            chosen.name_first AS first_name,
            coalesce(nickname.first_name_nicknames, []::VARCHAR[]) AS first_name_nicknames,
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
            chosen.attributions AS attribution_count,
            chosen.first_seen AS first_cycle,
            chosen.last_seen AS last_cycle
        FROM chosen
        LEFT JOIN surname ON surname.name_last = chosen.name_last
        LEFT JOIN nickname ON nickname.name = chosen.name_first
        """,
        {"names": [name for name, _ in linked], "others": [other for _, other in linked]},
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


def _saved_model(store: R2, version: str) -> dict[str, Any]:
    """Model `version` as `resolve --full` saved it; `FileNotFoundError` naming its key if it
    was never saved."""
    key = paths.resolution_model(version)
    try:
        raw = store.get(key)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"no saved model at {key}: see `{paths.MODEL_PREFIX}`") from exc
    return cast(dict[str, Any], json.loads(raw))


def resolve_full(
    store: R2,
    *,
    build_id: str,
    reuse: bool = False,
    data_dir: Path,
    limits: Limits,
    thresholds: Thresholds,
    max_keys: int,
    min_training_keys: int,
    overrides_path: Path,
    adjudication: adjudicate.Version,
    adjudicate_min_amount: int,
    conn: Connection[TupleRow],
    release: str | None,
) -> Resolved:
    """Train the model on every cycle's contributors, cluster them and re-cluster under the
    cluster cap `max_keys`, then apply the overrides file at `overrides_path` and the confident
    verdicts of `adjudication` (`adjudicate.apply`); write the model as version `build_id` right
    after training, then the `edge`, `component` and `cluster` tables, the crosswalk, each
    cycle's silver with its donor_ids, each cycle's `resolved` marker and, last, the run's record
    naming `release`, which makes the model live (spec §6.3–§6.6, §5.1, NEU-2122, NEU-2056,
    NEU-2325).

    With `reuse`, the model saved as version `build_id` is read back from R2 instead: nothing is
    trained or saved, and the rest of the run is the same, under that version.

    Raises `FileNotFoundError` when no cycle has been transformed, or `reuse` names a model never
    saved, and `OverridesError` when the overrides file is malformed or names a key or donor_id
    the run does not know, before the run trains anything.
    """
    # Read first, so a malformed file stops the run before it trains anything.
    asserted = overrides.load(overrides_path)
    model_key = paths.resolution_model(build_id)
    # Before the contributors load, so a mistyped version costs seconds.
    saved = _saved_model(store, build_id) if reuse else None
    started_at = datetime.now(UTC)
    builds = transformed_builds(store)
    if not builds:
        raise FileNotFoundError("no transformed build of any cycle: run `fundlens transform`")
    times: dict[str, float] = {}
    scratch = paths.scratch_dir(data_dir)
    scratch.mkdir(parents=True, exist_ok=True)
    database = _fresh_database(data_dir)
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
            # Before training, so an entry naming a key or donor_id the run does not know costs
            # minutes, not a full training run.
            overrides.check(con, conn, asserted)
        db_api = DuckDBAPI(con)
        if saved is not None:
            linker = model.linker(db_api, CONTRIBUTOR_TABLE, saved)
            parameters = Parameters.REUSED
        else:
            linker = model.linker(db_api, CONTRIBUTOR_TABLE, model.settings())
            with _phase("train", times):
                trained = model.train(
                    linker, db_api, keys=keys, min_training_keys=min_training_keys
                )
            parameters = Parameters.TRAINED if trained else Parameters.PRIORS
            # Now, not after the run: a run that fails later keeps hours of training, and
            # `--model` resolves with it (NEU-2325). It is not live until the run's record is.
            with _phase("model", times):
                linker.misc.save_model_to_json(str(model_path), overwrite=True)
                store.put(model_key, model_path)
        with _phase("cluster", times):
            cluster(
                linker, con, match_threshold=thresholds.match, cluster_threshold=thresholds.cluster
            )
            # `edge` and `component` hold what these did.
            model.drop_scratch(db_api, model.PREDICTION_SCRATCH)
        with _phase("recluster", times):
            reclustered = recluster(con, max_keys=max_keys, cluster_threshold=thresholds.cluster)
        with _phase("overrides", times):
            overridden = overrides.rewrite(con, asserted)
        with _phase("adjudications", times):
            adjudicated = adjudicate.apply(
                con,
                adjudicate.confident(conn, adjudication),
                min_amount=adjudicate_min_amount,
                overrides=asserted,
            )
        [(clusters,)] = con.execute(
            f"SELECT count(DISTINCT cluster_id) FROM {CLUSTER_TABLE}"
        ).fetchall()
        with _phase("save", times):
            # Splink's working tables are a run's scratch; the file keeps the input, the edges,
            # the components and the clusters.
            linker.table_management.delete_tables_created_by_splink_from_db()
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
    record = RunRecord(
        release=release,
        overrides=overridden.merges + overridden.splits,
        adjudications=adjudicated.merges + adjudicated.splits,
    )
    store.put(paths.resolution_run(build_id), record.model_dump_json().encode())
    log.info(
        "resolved %d contributor keys into %d clusters across %d cycles (model %s, %s;"
        " DuckDB memory limit %s)",
        keys,
        clusters,
        len(builds),
        build_id,
        parameters.name.lower(),
        memory_limit,
    )
    return Resolved(
        build_id,
        model_key,
        parameters,
        keys,
        clusters,
        reclustered,
        builds,
        overridden,
        adjudicated,
        assigned,
        memory_limit,
        times,
    )


@dataclass(frozen=True)
class Rewritten:
    """What `recluster_working_file` did."""

    reclustered: Reclustered
    overridden: overrides.Applied
    adjudicated: adjudicate.Applied
    clusters: int


def recluster_working_file(
    *,
    data_dir: Path,
    limits: Limits,
    max_keys: int,
    cluster_threshold: float,
    overrides_path: Path,
    adjudication: adjudicate.Version,
    adjudicate_min_amount: int,
    conn: Connection[TupleRow],
    rebuild: bool = False,
) -> Rewritten:
    """Rewrite the working file's `cluster` table as `resolve_full` would under the cluster cap
    `max_keys`: its components re-clustered, then the overrides file at `overrides_path` and the
    confident verdicts of `adjudication` applied (NEU-2122 §5.1, spec §6.8). Nothing else
    changes: no crosswalk, silver, marker or R2.

    With `rebuild`, the components are first rebuilt from `edge` at `cluster_threshold`
    (`components_at`) into a temp table, `component` left as linkage wrote it: the threshold
    sweep (NEU-2182). Without it, `component` is re-clustered as it stands.

    Raises `FileNotFoundError` when there is no working file or it holds no `component`, `edge`
    or `contributor` table, and `OverridesError` as `resolve_full` does; in every case, and on
    any failure part way, the previous `cluster` table stands.
    """
    asserted = overrides.load(overrides_path)
    database = paths.resolution_database(data_dir)
    missing = FileNotFoundError("no components in the working file: run `fundlens resolve --full`")
    if not database.exists():
        raise missing
    scratch = paths.scratch_dir(data_dir)
    scratch.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(database, config=limits.duckdb_config(scratch)) as con:
        tables = {name for (name,) in con.execute("SHOW TABLES").fetchall()}
        if not {COMPONENT_TABLE, EDGE_TABLE, CONTRIBUTOR_TABLE} <= tables:
            raise missing
        overrides.check(con, conn, asserted)
        # One transaction, so a failure part way leaves the previous clusters in place.
        con.begin()
        try:
            components = (
                components_at(con, cluster_threshold=cluster_threshold)
                if rebuild
                else COMPONENT_TABLE
            )
            reclustered = recluster(
                con, max_keys=max_keys, cluster_threshold=cluster_threshold, components=components
            )
            overridden = overrides.rewrite(con, asserted)
            adjudicated = adjudicate.apply(
                con,
                adjudicate.confident(conn, adjudication),
                min_amount=adjudicate_min_amount,
                overrides=asserted,
            )
            [(clusters,)] = con.execute(
                f"SELECT count(DISTINCT cluster_id) FROM {CLUSTER_TABLE}"
            ).fetchall()
        except BaseException:
            con.rollback()
            raise
        con.commit()
    return Rewritten(reclustered, overridden, adjudicated, clusters)
