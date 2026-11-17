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

`resolve_incremental` (spec §6.10, NEU-2062) resolves only one cycle's keys the crosswalk has
not seen, against that working file and with the live model, untrained: the weekly run's.
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
from splink import DuckDBAPI, Linker

from fundlens import markers, paths
from fundlens.r2 import R2
from fundlens.resolve import adjudicate, crosswalk, model, nicknames, overrides
from fundlens.resolve.adjudicate import UNADJUDICATED_TABLE
from fundlens.resolve.cluster import (
    CLUSTER_TABLE,
    COMPONENT_TABLE,
    EDGE_TABLE,
    Attached,
    Reclustered,
    attach,
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

    Keyed by the model, so it describes the run that last resolved with the live model: a
    `--full` run, whose record is what makes its saved model live (`model.live_version`), or an
    incremental one (`resolve_incremental`, NEU-2062), which writes its own over it.
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
    _write_contributors(con, CONTRIBUTOR_TABLE, partitions)
    [(rows,)] = con.execute(f"SELECT count(*) FROM {CONTRIBUTOR_TABLE}").fetchall()
    return rows


def _write_contributors(
    con: duckdb.DuckDBPyConnection, table: str, partitions: list[Path], *, only: str | None = None
) -> None:
    """The table `table`, in `contributor`'s columns (`_load_contributors`), of the keys of
    `partitions`, or only those in the table `only`."""
    files = "[" + ", ".join(literal(part / "*.parquet") for part in partitions) + "]"
    keys = "" if only is None else f"WHERE contributor_key IN (SELECT contributor_key FROM {only})"
    linked = sorted(nicknames.pairs())
    con.execute(
        f"""
        CREATE TABLE {table} AS
        WITH reported AS (
            SELECT * FROM read_parquet({files}, hive_partitioning = false) {keys}
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
    em_max_pairs: float,
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
        _stamp(con, build_id)
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
                    linker,
                    db_api,
                    keys=keys,
                    min_training_keys=min_training_keys,
                    em_max_pairs=em_max_pairs,
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


class NoBaseline(Exception):
    """Incremental resolution has nothing to resolve against: no live model, or no working file
    whose clusters are the crosswalk's donors. `resolve --full` makes both."""


# The working file's tables incremental resolution builds on.
_BASELINE_TABLES = frozenset({CONTRIBUTOR_TABLE, EDGE_TABLE, COMPONENT_TABLE, CLUSTER_TABLE})
# The temp tables and tables `resolve_incremental` works in, dropped when it is done.
_NEW_KEYS, _NEW_CONTRIBUTORS, _NEW_EDGES, _KNOWN = "new_key", "new_contributor", "new_edge", "known"
# The model version the working file's clusters were made with (`_stamp`).
_STAMP_TABLE = "resolved_with"


def incremental_ready(store: R2, data_dir: Path) -> bool:
    """Whether there is a live model and a working file holding clusters to resolve against:
    whether `resolve_incremental` can run, short of the check it makes against the crosswalk."""
    database = paths.resolution_database(data_dir)
    if model.live_version(store) is None or not database.exists():
        return False
    with duckdb.connect(database, read_only=True) as con:
        tables = {name for (name,) in con.execute("SHOW TABLES").fetchall()}
    return _BASELINE_TABLES <= tables


@dataclass(frozen=True)
class Linked:
    """What `resolve_incremental` did."""

    model_version: str
    cycle: int
    build: str
    # The cycle's keys, and those of them the crosswalk had not given a donor_id.
    cycle_keys: int
    new_keys: int
    # Pairs at or above the match threshold with a new key at either end.
    edges: int
    attached: Attached
    overridden: overrides.Applied
    adjudicated: adjudicate.Applied
    assigned: crosswalk.Assigned
    memory_limit: str
    phase_s: dict[str, float] = field(default_factory=dict[str, float])


def _stamp(con: duckdb.DuckDBPyConnection, version: str) -> None:
    """Record in the working file the model version its clusters were made with."""
    con.execute(
        f"CREATE OR REPLACE TABLE {_STAMP_TABLE} AS SELECT $version::VARCHAR AS model_version",
        {"version": version},
    )


def _check_stamp(con: duckdb.DuckDBPyConnection, live: str, tables: set[str]) -> None:
    """Raise `NoBaseline` if the working file's clusters were made with a model other than the
    live one: a `--full` run that died after its crosswalk and before its record leaves its
    clusters, and the crosswalk, made with a model that is not live. A working file from before
    the stamp (NEU-2062) is the backfill's, which finished."""
    if _STAMP_TABLE not in tables:
        return
    [(version,)] = con.execute(f"SELECT model_version FROM {_STAMP_TABLE}").fetchall()
    if version != live:
        raise NoBaseline(
            f"the working file was resolved with model {version}, but the live model is {live}:"
            f" finish that run with `fundlens resolve --full --model {version}`"
        )


def _forget_unknown(con: duckdb.DuckDBPyConnection, cycle: int) -> int:
    """Remove from the working file every key the crosswalk (the temp table `known`) does not
    hold, which an incremental run of `cycle` that died before its crosswalk committed left;
    how many. A cluster or component named by such a key is named again by its lowest key, so
    no id names a key the file does not hold.

    Raises `NoBaseline` if one of them was seen in another cycle: no incremental run of `cycle`
    left that, and the crosswalk is not the one the working file was resolved into."""
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE unknown AS SELECT contributor_key, first_cycle"
        f" FROM {CONTRIBUTOR_TABLE} ANTI JOIN {_KNOWN} USING (contributor_key)"
    )
    [(stale, foreign)] = con.execute(
        "SELECT count(*), count(*) FILTER (WHERE first_cycle <> $cycle) FROM unknown",
        {"cycle": cycle},
    ).fetchall()
    if foreign:
        raise NoBaseline(
            f"the working file holds {foreign} keys of other cycles than {cycle} that"
            " app.crosswalk does not: it is not the crosswalk the file was resolved into. Run"
            " `fundlens resolve --full`"
        )
    if stale:
        tables = {name for (name,) in con.execute("SHOW TABLES").fetchall()}
        clustered = [
            table
            for table in (COMPONENT_TABLE, CLUSTER_TABLE, UNADJUDICATED_TABLE)
            if table in tables
        ]
        for table in (CONTRIBUTOR_TABLE, *clustered):
            con.execute(
                f"DELETE FROM {table}"
                " WHERE contributor_key IN (SELECT contributor_key FROM unknown)"
            )
        for table in clustered:
            con.execute(
                f"""
                UPDATE {table} SET cluster_id = renamed.lowest
                FROM (
                    SELECT cluster_id, min(contributor_key) AS lowest FROM {table}
                    WHERE cluster_id IN (SELECT contributor_key FROM unknown)
                    GROUP BY cluster_id
                ) AS renamed
                WHERE {table}.cluster_id = renamed.cluster_id
                """
            )
        con.execute(
            f"DELETE FROM {EDGE_TABLE}"
            " WHERE contributor_key_l IN (SELECT contributor_key FROM unknown)"
            " OR contributor_key_r IN (SELECT contributor_key FROM unknown)"
        )
        log.info("resolve: forgot %d keys an earlier run left without a donor_id", stale)
    con.execute("DROP TABLE unknown")
    return stale


def _extend_unadjudicated(con: duckdb.DuckDBPyConnection) -> None:
    """Add each new key to `unadjudicated` (the clusters after overrides and before
    adjudications), where `attach` put it in `cluster`: in the unadjudicated cluster of the lowest
    key that stood in its cluster, or, in a cluster of new keys alone, in that cluster. So
    `adjudicate` goes on choosing among clusters no verdict has shaped (spec §6.8). A working
    file from before adjudication (NEU-2055) gets its `unadjudicated` from `cluster` first."""
    tables = {name for (name,) in con.execute("SHOW TABLES").fetchall()}
    if UNADJUDICATED_TABLE not in tables:
        con.execute(
            f"CREATE TABLE {UNADJUDICATED_TABLE} AS"
            f" FROM {CLUSTER_TABLE} ANTI JOIN {_NEW_KEYS} USING (contributor_key)"
        )
    con.execute(
        f"""
        INSERT INTO {UNADJUDICATED_TABLE} BY NAME
        WITH
            fresh AS (
                SELECT c.* FROM {CLUSTER_TABLE} AS c JOIN {_NEW_KEYS} USING (contributor_key)
            ),
            stood AS (
                SELECT c.cluster_id, arg_min(u.cluster_id, c.contributor_key) AS unadjudicated
                FROM {CLUSTER_TABLE} AS c
                JOIN {UNADJUDICATED_TABLE} AS u USING (contributor_key)
                WHERE c.cluster_id IN (SELECT cluster_id FROM fresh)
                GROUP BY c.cluster_id
            )
        SELECT
            coalesce(s.unadjudicated, f.cluster_id) AS cluster_id,
            f.contributor_key,
            f.match_probability
        FROM fresh AS f
        LEFT JOIN stood AS s USING (cluster_id)
        """
    )


def _check_baseline(con: duckdb.DuckDBPyConnection) -> None:
    """Raise `NoBaseline` unless the working file's clusters are the crosswalk's donors: each
    cluster's keys carry one donor_id, and each donor_id's keys are in one cluster. Else a run
    that died between clustering and its crosswalk left clusters no donor_id stands for, and new
    keys joining them would re-point the keys around them."""
    [(mixed, spread)] = con.execute(
        f"""
        WITH carried AS (
            SELECT c.cluster_id, k.donor_id
            FROM {CLUSTER_TABLE} AS c JOIN {_KNOWN} AS k USING (contributor_key)
        )
        SELECT
            (SELECT count(*) FROM (SELECT cluster_id FROM carried GROUP BY cluster_id
                HAVING count(DISTINCT donor_id) > 1)),
            (SELECT count(*) FROM (SELECT donor_id FROM carried GROUP BY donor_id
                HAVING count(DISTINCT cluster_id) > 1))
        """
    ).fetchall()
    if mixed or spread:
        raise NoBaseline(
            f"the working file's clusters are not the crosswalk's donors ({mixed} clusters hold"
            f" several donor_ids, {spread} donor_ids span several clusters): run"
            " `fundlens resolve --full`"
        )


def _link(
    linker: Linker, db_api: DuckDBAPI, con: duckdb.DuckDBPyConnection, *, match_threshold: float
) -> int:
    """Score the new keys against every key that stood and against each other with the saved
    model, writing each pair at or above `match_threshold` once (`contributor_key_l` the lower) to
    the table `new_edge`; its row count. The pairs among keys that stood are never scored again."""
    # Splink's stub leaves one of `register`'s input types unknown, as `model.linker` says.
    new = db_api.register(_NEW_CONTRIBUTORS)  # pyright: ignore[reportUnknownMemberType]
    stood = db_api.register(CONTRIBUTOR_TABLE)  # pyright: ignore[reportUnknownMemberType]
    between = linker.inference.predict_between(
        new, stood, threshold_match_probability=match_threshold, warning_mode="never"
    )
    within = linker.inference.predict_within(
        new, threshold_match_probability=match_threshold, warning_mode="never"
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {_NEW_EDGES} AS
        SELECT
            least(contributor_key_l, contributor_key_r) AS contributor_key_l,
            greatest(contributor_key_l, contributor_key_r) AS contributor_key_r,
            max(match_probability) AS match_probability
        FROM (
            SELECT contributor_key_l, contributor_key_r, match_probability
            FROM {between.physical_name}
            UNION ALL
            SELECT contributor_key_l, contributor_key_r, match_probability
            FROM {within.physical_name}
        )
        GROUP BY ALL
        """
    )
    for predictions in (between, within):
        predictions.drop_table_from_database_and_remove_from_cache()
    [(edges,)] = con.execute(f"SELECT count(*) FROM {_NEW_EDGES}").fetchall()
    return edges


def resolve_incremental(
    store: R2,
    *,
    cycle: int,
    data_dir: Path,
    limits: Limits,
    thresholds: Thresholds,
    max_keys: int,
    overrides_path: Path,
    adjudication: adjudicate.Version,
    adjudicate_min_amount: int,
    conn: Connection[TupleRow],
    release: str | None,
) -> Linked:
    """Resolve the keys of `cycle`'s newest transformed build that `app.crosswalk` does not hold
    against everything resolved before, with the live model and no training (spec §6.10).

    The new keys are scored against every key in the working file's `contributor` and against
    each other (`_link`), never the keys already there against each other, and join the working
    file's tables: `contributor`, `edge`, then `cluster` and `component` by `attach`, which
    leaves every cluster standing, so a new key joins a donor or forms a new one. The overrides
    file at `overrides_path` and the confident verdicts of `adjudication` are applied again, as
    `resolve_full` applies them; the crosswalk gives each new key its donor_id, writing only the
    rows that change; and only this cycle's build gets its silver rewritten with donor_ids and
    its `resolved` marker. The run's record, written last under the live model's version, says
    what it applied (`RunRecord`).

    A key that stood keeps the attributes and totals of the run that resolved it: its totals
    weigh only which id a cluster keeps should one hold two (§6.6).

    Raises `NoBaseline` when there is no live model, no working file with clusters, or one
    whose clusters are not the crosswalk's donors; `FileNotFoundError` when `cycle` has no
    transformed build; and `OverridesError` as `resolve_full` does.
    """
    asserted = overrides.load(overrides_path)
    version = model.live_version(store)
    if version is None:
        raise NoBaseline("no live model to resolve with: run `fundlens resolve --full`")
    build = transformed_builds(store).get(cycle)
    if build is None:
        raise FileNotFoundError(
            f"no transformed build of {cycle}: run `fundlens transform --cycle {cycle}`"
        )
    saved = _saved_model(store, version)
    database = paths.resolution_database(data_dir)
    if not database.exists():
        raise NoBaseline("no working file to resolve against: run `fundlens resolve --full`")
    started_at = datetime.now(UTC)
    times: dict[str, float] = {}
    scratch = paths.scratch_dir(data_dir)
    scratch.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(database, config=limits.duckdb_config(scratch)) as con:
        tables = {name for (name,) in con.execute("SHOW TABLES").fetchall()}
        if not _BASELINE_TABLES <= tables:
            raise NoBaseline(
                "the working file holds no clusters to resolve against: run"
                " `fundlens resolve --full`"
            )
        model.register(con)
        _check_stamp(con, version, tables)
        [(memory_limit,)] = con.execute("SELECT current_setting('memory_limit')").fetchall()
        with _phase("load", times):
            partition = _local_partition(store, cycle, build, data_dir=data_dir)
            crosswalk.read_crosswalk(con, conn, table=_KNOWN, work=scratch / f"known-{build}")
            _forget_unknown(con, cycle)
            _check_baseline(con)
            con.execute(
                f"""
                CREATE OR REPLACE TEMP TABLE {_NEW_KEYS} AS
                SELECT DISTINCT contributor_key
                FROM read_parquet({literal(partition / "*.parquet")}, hive_partitioning = false)
                ANTI JOIN {_KNOWN} USING (contributor_key)
                """
            )
            con.execute(f"DROP TABLE IF EXISTS {_NEW_CONTRIBUTORS}")
            _write_contributors(con, _NEW_CONTRIBUTORS, [partition], only=_NEW_KEYS)
            [(new_keys,)] = con.execute(f"SELECT count(*) FROM {_NEW_KEYS}").fetchall()
            cycle_keys = _count(con, partition)
        db_api = DuckDBAPI(con)
        linker = model.linker(db_api, CONTRIBUTOR_TABLE, saved)
        with _phase("link", times):
            # Splink cannot block an empty table.
            if new_keys:
                edges = _link(linker, db_api, con, match_threshold=thresholds.match)
            else:
                con.execute(f"CREATE OR REPLACE TABLE {_NEW_EDGES} AS FROM {EDGE_TABLE} LIMIT 0")
                edges = 0
            con.execute(f"INSERT INTO {CONTRIBUTOR_TABLE} BY NAME FROM {_NEW_CONTRIBUTORS}")
            con.execute(f"INSERT INTO {EDGE_TABLE} BY NAME FROM {_NEW_EDGES}")
            # An override may name a key new this week, so after the new keys are in.
            overrides.check(con, conn, asserted)
        with _phase("attach", times):
            attached = attach(
                con,
                new_keys=_NEW_KEYS,
                new_edges=_NEW_EDGES,
                max_keys=max_keys,
                cluster_threshold=thresholds.cluster,
            )
            _extend_unadjudicated(con)
        with _phase("overrides", times):
            overridden = overrides.rewrite(con, asserted)
            overrides.rewrite(con, asserted, table=UNADJUDICATED_TABLE)
        with _phase("adjudications", times):
            adjudicated = adjudicate.apply(
                con,
                adjudicate.confident(conn, adjudication),
                min_amount=adjudicate_min_amount,
                overrides=asserted,
                snapshot=False,
            )
        with _phase("save", times):
            linker.table_management.delete_tables_created_by_splink_from_db()
            for table in (_NEW_CONTRIBUTORS, _NEW_EDGES, _NEW_KEYS, _KNOWN):
                con.execute(f"DROP TABLE {table}")
            con.execute("CHECKPOINT")
        with _phase("crosswalk", times):
            assigned = crosswalk.assign(con, conn, build_id=build, scratch=scratch)
        with _phase("silver", times):
            contributions = crosswalk.onto_silver(
                con, store, cycle=cycle, build_id=build, data_dir=data_dir
            )
    markers.write(
        "resolved",
        store,
        cycle=cycle,
        build_id=build,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        row_counts={CLUSTER_TABLE: cycle_keys, "contribution": contributions},
    )
    record = RunRecord(
        release=release,
        overrides=overridden.merges + overridden.splits,
        adjudications=adjudicated.merges + adjudicated.splits,
    )
    store.put(paths.resolution_run(version), record.model_dump_json().encode())
    log.info(
        "resolved %d new contributor keys of %d in %d (model %s, %.2f s; DuckDB memory limit %s)",
        new_keys,
        cycle_keys,
        cycle,
        version,
        sum(times.values()),
        memory_limit,
    )
    return Linked(
        version,
        cycle,
        build,
        cycle_keys,
        new_keys,
        edges,
        attached,
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
