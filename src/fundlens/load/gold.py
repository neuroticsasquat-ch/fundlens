"""`fundlens load`: every cycle's silver partitions into the Postgres schema `gold_build`
(spec §5.5, NEU-2039 §4.1, NEU-2059, ADR-0007).

Gold holds every cycle, so a load of one cycle's build rebuilds all of gold: the loaded cycle
from that build, every other cycle from the build it is live from (`markers/live.json`, which
`publish` rewrites, or, before any publish has written it, the live `gold.meta.cycles`). DuckDB
computes every gold table from those silver partitions (`sql/gold/NN_<table>.sql`, in filename
order, reading the views `silver.<table>`, each over every cycle's partition), runs
`sql/checks/gold_*.sql` (each a query that must return no rows), and writes each table as a CSV
file under `scratch/`. Then, in one Postgres transaction, `gold_build` is dropped and
recreated, each table gets its hand-written DDL (`sql/gold/ddl/`), its CSV streamed in with
`COPY … FROM STDIN`, its indexes
(`sql/gold/index/`) and an `ANALYZE`, `donor_redirect` a copy of `app.donor_redirect`, and `meta`
its one row, with the live model's version, its run's record (`resolve.runner.RunRecord`) and
its DIME figures for the newest cycle validated under it from `app.resolution_quality`, and
`cycles` the build and source download dates of each cycle. A
failed load leaves no `gold_build` at all, never a partial one; a successful one writes the
`loaded` marker.
`fundlens publish` swaps the schema in.
"""

import logging
import shutil
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, get_args

import duckdb
from psycopg import Connection
from psycopg.abc import Query
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from fundlens import markers, paths
from fundlens.fec.files import files_for
from fundlens.paths import SilverTable
from fundlens.r2 import R2
from fundlens.resolve import model
from fundlens.resolve.runner import run_record
from fundlens.transform.runner import CHUNK_BYTES, Limits, check, literal, render

log = logging.getLogger(__name__)

# The gold tables (spec §7.1). `meta` and `donor_redirect` have DDL but no model: Postgres fills
# them (`FROM_POSTGRES`).
GoldTable = Literal[
    "meta",
    "cycle",
    "race",
    "race_candidate",
    "race_top_committee",
    "candidate",
    "candidate_cycle",
    "candidate_redirect",
    "committee",
    "committee_cycle",
    "committee_top_recipient",
    "search_entity",
    "donor",
    "donor_cycle",
    "donor_top_recipient",
    "donor_redirect",
    "race_top_donor",
    "candidate_top_donor",
    "committee_top_donor",
    "committee_top_organization",
]

# `meta`'s one row is inserted from Python; `donor_redirect` is copied from `app`, which only
# Postgres holds.
FROM_POSTGRES: frozenset[GoldTable] = frozenset({"meta", "donor_redirect"})

# The silver tables the gold SQL reads, and the command that writes each one's partition.
# (`candidate_committee_link` is not among them: silver `contribution` already carries the
# candidate each committee raises for.)
INPUTS: dict[SilverTable, str] = {
    "committee": "transform",
    "candidate": "transform",
    "contribution": "transform",
    "committee_transfer": "transform",
    "jfc_attribution": "transform",
    "contributor": "transform",
    "organization_receipt": "transform",
    "independent_expenditure": "transform",
    "race": "seats",
}

# The silver tables `resolve` rewrites with each row's donor_id (spec §6.6). A build loaded before
# `resolve` has none, so its views get a NULL one and the build has no donors.
RESOLVED: frozenset[SilverTable] = frozenset({"contribution", "jfc_attribution"})


@dataclass(frozen=True)
class Quality:
    """The live model, what its run applied and its DIME figures for the cycle, as `meta`
    carries them (NEU-2054 §7, NEU-2056): the run's fields None when it wrote no record, the
    figures None when the cycle has not been validated under the model."""

    model_version: str | None
    resolver_version: str | None = None
    overrides_count: int | None = None
    adjudications_applied: int | None = None
    precision: Decimal | None = None
    recall: Decimal | None = None
    precision_top: Decimal | None = None
    recall_top: Decimal | None = None
    matched_rows: int | None = None
    dime_version: str | None = None

    @property
    def validated(self) -> bool:
        return self.dime_version is not None


@dataclass(frozen=True)
class Loaded:
    """What `load` did: the build loaded, rows per gold table, the resolution figures `meta`
    carries, and how long each half took."""

    build_id: str
    row_counts: dict[str, int]
    quality: Quality
    # DuckDB aggregates and CSV writes, then `COPY` with indexes and `ANALYZE` (spec §8).
    aggregate_s: float
    copy_s: float


def newest_transformed(store: R2, cycle: int) -> str | None:
    """The newest build of `cycle` with a `transformed` marker, or None if there is none."""
    builds = {
        build
        for key in store.list_keys(paths.markers_dir(cycle))
        if key.endswith("/transformed.json") and (build := paths.build_of(key)) is not None
    }
    return max(builds) if builds else None


def _models(sql_dir: Path) -> list[tuple[GoldTable, Path]]:
    """The gold models in run order, each with the table it creates."""
    tables: dict[str, GoldTable] = {table: table for table in get_args(GoldTable)}
    models: list[tuple[GoldTable, Path]] = []
    for path in sorted((sql_dir / "gold").glob("*.sql")):
        table = tables.get(path.stem.partition("_")[2])
        if table is None or table in FROM_POSTGRES:
            raise ValueError(f"{path.name} names no gold table")
        models.append((table, path))
    if not models:
        raise ValueError(f"no gold models under {sql_dir}")
    return models


def _require_inputs(
    store: R2, cycle: int, build_id: str, *, data_dir: Path
) -> dict[SilverTable, Path]:
    """Every silver partition the gold SQL reads, on local disk; its directory per table.

    A partition absent from the local cache is downloaded from R2 first (ADR-0002). Raises
    `FileNotFoundError` naming the table and the command that writes it when R2 lacks one.
    """
    if not markers.exists("transformed", store, cycle=cycle, build_id=build_id):
        raise FileNotFoundError(
            f"no transformed marker for build {build_id} of {cycle}:"
            f" run `fundlens transform --cycle {cycle} --build-id {build_id}`"
        )
    local_dirs: dict[SilverTable, Path] = {}
    for table, command in INPUTS.items():
        prefix = paths.silver_partition(table, cycle, build_id)
        keys = store.list_keys(prefix + "/")
        if not keys:
            raise FileNotFoundError(
                f"no silver {table} partition for build {build_id} of {cycle}:"
                f" run `fundlens {command} --cycle {cycle} --build-id {build_id}`"
            )
        if paths.rewrite_sentinel(cycle, build_id) in keys:
            # Its parts are a mix of two layouts, which would count every row twice.
            raise FileNotFoundError(
                f"the donor_id rewrite of silver {table} for build {build_id} of {cycle} died"
                " part way: run `fundlens resolve --full` again"
            )
        for key in keys:
            local = paths.local_path(data_dir, key)
            if not local.exists():
                store.download_to(key, local)
        local_dirs[table] = paths.local_path(data_dir, prefix)
    return local_dirs


def _register_silver(
    con: duckdb.DuckDBPyConnection, local_dirs: Mapping[SilverTable, list[Path]]
) -> None:
    """The views `silver.<table>` over the Parquet parts of each cycle's partition."""
    con.execute("CREATE SCHEMA silver")
    for table, partitions in local_dirs.items():
        # The file's own columns: DuckDB would otherwise add `cycle` and `build` from the path;
        # every silver row carries its cycle. `**` reaches into a resolved `contribution`'s
        # `bucket=` directories too (spec §3.4). By name, so a cycle built before a column was
        # added reads it as NULL, and a resolved cycle beside an unresolved one gives the
        # unresolved one's rows a NULL donor_id.
        globs = ", ".join(literal(local / "**" / "*.parquet") for local in partitions)
        source = f"read_parquet([{globs}], hive_partitioning = false, union_by_name = true)"
        con.execute(f"CREATE VIEW silver.{table} AS SELECT * FROM {source}")
        if (
            table in RESOLVED
            and not con.execute(
                f"SELECT 1 FROM (DESCRIBE silver.{table}) WHERE column_name = 'donor_id'"
            ).fetchall()
        ):
            con.execute(
                f"CREATE OR REPLACE VIEW silver.{table} AS"
                f" SELECT *, CAST(NULL AS BIGINT) AS donor_id FROM {source}"
            )
    # DuckDB's CSV writer prints a list as `[…]`; Postgres reads an array as `{…}`.
    con.execute("CREATE MACRO pg_array(l) AS '{' || array_to_string(l, ',') || '}'")


def _source_dates(store: R2, cycle: int) -> dict[str, str | None]:
    """The download date of the newest bronze zip of each of the cycle's files."""
    dates: dict[str, str | None] = {}
    for file in files_for(cycle):
        # Keys end in an ISO download date, so key order is download order.
        keys = sorted(store.list_keys(paths.bronze_dir(cycle, file.name)))
        dates[file.name] = keys[-1].rsplit("/", 1)[1].removesuffix(".zip") if keys else None
    return dates


def _live_cycles(conn: Connection[TupleRow]) -> dict[int, dict[str, Any]]:
    """The live `gold.meta.cycles` by cycle: each one's build and source download dates; empty
    before the first publish."""
    [(meta,)] = conn.execute("SELECT to_regclass('gold.meta')").fetchall()
    if meta is None:
        return {}
    row = conn.execute("SELECT cycles FROM gold.meta").fetchone()
    return {} if row is None else {int(cycle): entry for cycle, entry in row[0].items()}


def _sql(path: Path) -> Query:
    # psycopg types a query as a literal string or bytes, so a formatted `str` cannot be sent by
    # accident. The DDL and index files are the repo's own SQL, read whole: bytes is the honest
    # way to pass them.
    return path.read_bytes()


def _copy_in(conn: Connection[TupleRow], table: GoldTable, csv: Path) -> None:
    # `HEADER match`: Postgres checks the CSV's column names against the table's, so a gold model
    # whose columns drift from its DDL fails here instead of loading values into the wrong columns.
    with (
        conn.cursor() as cur,
        cur.copy(f"COPY gold_build.{table} FROM STDIN (FORMAT csv, HEADER match)") as copy,
        csv.open("rb") as src,
    ):
        while chunk := src.read(CHUNK_BYTES):
            copy.write(chunk)


def _quality(
    conn: Connection[TupleRow], store: R2, cycles: Iterable[int], model_version: str | None
) -> Quality:
    """`model_version`'s run record, and its figures from `app.resolution_quality` for the
    newest of `cycles` validated under it: loading an older cycle keeps the figures a newer one
    has."""
    if model_version is None:
        return Quality(None)
    record = run_record(store, model_version)
    run = (
        Quality(model_version)
        if record is None
        else Quality(model_version, record.release, record.overrides, record.adjudications)
    )
    scopes = {
        scope: rest
        for scope, *rest in conn.execute(
            "SELECT scope, precision, recall, matched_rows, dime_version"
            " FROM app.resolution_quality"
            " WHERE model_version = %s AND cycle = ("
            "  SELECT max(cycle) FROM app.resolution_quality"
            "  WHERE model_version = %s AND scope = 'overall' AND cycle = ANY(%s))",
            (model_version, model_version, list(cycles)),
        ).fetchall()
    }
    overall, top = scopes.get("overall"), scopes.get("top")
    if overall is None:
        return run
    precision, recall, matched_rows, dime_version = overall
    precision_top, recall_top = (top[0], top[1]) if top is not None else (None, None)
    return replace(
        run,
        precision=precision,
        recall=recall,
        precision_top=precision_top,
        recall_top=recall_top,
        matched_rows=matched_rows,
        dime_version=dime_version,
    )


def _load_postgres(
    conn: Connection[TupleRow],
    models: list[tuple[GoldTable, Path]],
    *,
    sql_dir: Path,
    work: Path,
    build_id: str,
    cycles: Mapping[str, object],
    quality: Quality,
) -> int:
    """Rebuild `gold_build` from the CSVs under `work`, in one transaction; the rows of
    `donor_redirect`."""
    with conn.transaction():
        # In the default schema, never inside `gold_build`: an extension living there would be
        # renamed with it and dropped by the next publish's `DROP SCHEMA gold_prev CASCADE`.
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        conn.execute("DROP SCHEMA IF EXISTS gold_build CASCADE")
        conn.execute("CREATE SCHEMA gold_build")
        for table, _ in models:
            conn.execute(_sql(sql_dir / "gold" / "ddl" / f"{table}.sql"))
            _copy_in(conn, table, work / f"{table}.csv")
            index = sql_dir / "gold" / "index" / f"{table}.sql"
            if index.exists():
                conn.execute(_sql(index))
            conn.execute(f"ANALYZE gold_build.{table}")
        conn.execute(_sql(sql_dir / "gold" / "ddl" / "donor_redirect.sql"))
        redirects = conn.execute(
            "INSERT INTO gold_build.donor_redirect (old_donor_id, donor_id)"
            " SELECT old_donor_id, donor_id FROM app.donor_redirect"
        ).rowcount
        conn.execute("ANALYZE gold_build.donor_redirect")
        conn.execute(_sql(sql_dir / "gold" / "ddl" / "meta.sql"))
        conn.execute(
            "INSERT INTO gold_build.meta (build_id, published_at, resolver_version,"
            " model_version, overrides_count, adjudications_applied, precision, recall,"
            " precision_top, recall_top, matched_rows, dime_version, cycles)"
            " VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                build_id,
                quality.resolver_version,
                quality.model_version,
                quality.overrides_count,
                quality.adjudications_applied,
                quality.precision,
                quality.recall,
                quality.precision_top,
                quality.recall_top,
                quality.matched_rows,
                quality.dime_version,
                Jsonb(dict(cycles)),
            ),
        )
    return redirects


def load(
    cycle: int,
    store: R2,
    *,
    build_id: str | None,
    data_dir: Path,
    sql_dir: Path,
    limits: Limits,
    conn: Connection[TupleRow],
) -> Loaded:
    """Build `gold_build` from build `build_id` of `cycle` (the newest transformed one when
    None) and every other cycle's live build; write the `loaded` marker for `build_id`.

    Raises `FileNotFoundError` when the build, another cycle's live build, or one of their
    silver partitions is missing; and
    `ChecksFailed` when a gold check returns rows; in both cases Postgres is untouched and no
    marker is written. Re-running for the same build rebuilds `gold_build` from scratch.
    """
    started_at = datetime.now(UTC)
    if build_id is None:
        build_id = newest_transformed(store, cycle)
        if build_id is None:
            raise FileNotFoundError(
                f"no transformed build for {cycle}: run `fundlens transform --cycle {cycle}`"
            )
    models = _models(sql_dir)
    live = _live_cycles(conn)
    # Gold published before the manifest existed has none: its own record of each cycle stands in,
    # so the first load after this change keeps every cycle already live.
    live_builds = markers.read_live(store) or {
        each: entry["build_id"] for each, entry in live.items()
    }
    builds = live_builds | {cycle: build_id}
    local_dirs: dict[SilverTable, list[Path]] = {table: [] for table in INPUTS}
    for each, each_build in sorted(builds.items()):
        for table, local in _require_inputs(store, each, each_build, data_dir=data_dir).items():
            local_dirs[table].append(local)
    scratch = paths.scratch_dir(data_dir)
    work = scratch / f"load-{cycle}-{build_id}"
    work.mkdir(parents=True, exist_ok=True)
    params = {"cycle": cycle, "build_id": build_id}
    row_counts: dict[str, int] = {}
    try:
        aggregate_started = time.monotonic()
        with duckdb.connect(config=limits.duckdb_config(scratch)) as con:
            _register_silver(con, local_dirs)
            for table, path in models:
                log.info("gold %s (%s): %s", table, ", ".join(map(str, sorted(builds))), path.name)
                con.execute(render(path, params))
            check(con, sql_dir, params, tier="gold", consequence="nothing loaded")
            for table, _ in models:
                con.execute(
                    f"COPY {table} TO {literal(work / f'{table}.csv')} (FORMAT csv, HEADER true)"
                )
                [(rows,)] = con.execute(f"SELECT count(*) FROM {table}").fetchall()
                row_counts[table] = rows
        aggregate_s = time.monotonic() - aggregate_started
        # A cycle carried over keeps the download dates its live build was transformed from: a
        # newer zip, downloaded since and not yet transformed, is not what it serves.
        cycles = {
            str(each): {
                "build_id": each_build,
                "source_dates": live[each]["source_dates"]
                if each != cycle and live.get(each, {}).get("build_id") == each_build
                else _source_dates(store, each),
            }
            for each, each_build in sorted(builds.items())
        }
        quality = _quality(conn, store, builds.keys(), model.latest_version(store))
        copy_started = time.monotonic()
        row_counts["donor_redirect"] = _load_postgres(
            conn,
            models,
            sql_dir=sql_dir,
            work=work,
            build_id=build_id,
            cycles=cycles,
            quality=quality,
        )
        copy_s = time.monotonic() - copy_started
    finally:
        shutil.rmtree(work, ignore_errors=True)
    row_counts["meta"] = 1
    markers.write(
        "loaded",
        store,
        cycle=cycle,
        build_id=build_id,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        row_counts=row_counts,
    )
    return Loaded(build_id, row_counts, quality, aggregate_s, copy_s)
