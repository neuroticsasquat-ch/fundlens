"""`fundlens load`: one cycle's silver partitions into the Postgres schema `gold_build`
(spec §5.5, NEU-2039 §4.1, ADR-0007).

DuckDB computes every gold table from the build's silver partitions (`sql/gold/NN_<table>.sql`,
in filename order, reading the views `silver.<table>`), runs `sql/checks/gold_*.sql` (each a
query that must return no rows), and writes each table as a CSV file under `scratch/`. Then, in
one Postgres transaction, `gold_build` is dropped and recreated, each table gets its hand-written
DDL (`sql/gold/ddl/`), its CSV streamed in with `COPY … FROM STDIN`, its indexes
(`sql/gold/index/`) and an `ANALYZE`, and `meta` its one row. A failed load leaves no
`gold_build` at all, never a partial one; a successful one writes the `loaded` marker.
`fundlens publish` swaps the schema in.
"""

import logging
import shutil
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, get_args

import duckdb
from psycopg import Connection
from psycopg.abc import Query
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from fundlens import markers, paths
from fundlens.fec.files import files_for
from fundlens.paths import SilverTable
from fundlens.r2 import R2
from fundlens.transform.runner import CHUNK_BYTES, Limits, check, literal, render

log = logging.getLogger(__name__)

# The M2 gold tables (spec §7.1); the donor tables arrive in M3. `meta` has DDL but no model:
# its one row is inserted from Python.
GoldTable = Literal[
    "meta",
    "cycle",
    "race",
    "race_candidate",
    "race_top_committee",
    "candidate",
    "candidate_cycle",
    "committee",
    "committee_cycle",
    "committee_top_recipient",
    "search_entity",
]

# The silver tables the gold SQL reads, and the command that writes each one's partition.
# (`candidate_committee_link` is not among them: silver `contribution` already carries the
# candidate each committee raises for.)
INPUTS: dict[SilverTable, str] = {
    "committee": "transform",
    "candidate": "transform",
    "contribution": "transform",
    "committee_transfer": "transform",
    "race": "seats",
}


@dataclass(frozen=True)
class Loaded:
    """What `load` did: the build loaded, rows per gold table, and how long each half took."""

    build_id: str
    row_counts: dict[str, int]
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
        if table is None or table == "meta":
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
        for key in keys:
            local = paths.local_path(data_dir, key)
            if not local.exists():
                store.download_to(key, local)
        local_dirs[table] = paths.local_path(data_dir, prefix)
    return local_dirs


def _register_silver(
    con: duckdb.DuckDBPyConnection, local_dirs: Mapping[SilverTable, Path]
) -> None:
    """The views `silver.<table>` over each partition's Parquet parts."""
    con.execute("CREATE SCHEMA silver")
    for table, local in local_dirs.items():
        # The file's own columns: DuckDB would otherwise add `cycle` and `build` from the path.
        con.execute(
            f"CREATE VIEW silver.{table} AS SELECT * FROM"
            f" read_parquet({literal(local / '*.parquet')}, hive_partitioning = false)"
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


def _load_postgres(
    conn: Connection[TupleRow],
    models: list[tuple[GoldTable, Path]],
    *,
    sql_dir: Path,
    work: Path,
    build_id: str,
    cycles: Mapping[str, object],
) -> None:
    """Rebuild `gold_build` from the CSVs under `work`, in one transaction."""
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
        conn.execute(_sql(sql_dir / "gold" / "ddl" / "meta.sql"))
        conn.execute(
            "INSERT INTO gold_build.meta (build_id, published_at, cycles) VALUES (%s, NULL, %s)",
            (build_id, Jsonb(dict(cycles))),
        )


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
    None); write the `loaded` marker.

    Raises `FileNotFoundError` when the build or one of its silver partitions is missing, and
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
    local_dirs = _require_inputs(store, cycle, build_id, data_dir=data_dir)
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
                log.info("gold %s %d: %s", table, cycle, path.name)
                con.execute(render(path, params))
            check(con, sql_dir, params, tier="gold", consequence="nothing loaded")
            for table, _ in models:
                con.execute(
                    f"COPY {table} TO {literal(work / f'{table}.csv')} (FORMAT csv, HEADER true)"
                )
                [(rows,)] = con.execute(f"SELECT count(*) FROM {table}").fetchall()
                row_counts[table] = rows
        aggregate_s = time.monotonic() - aggregate_started
        cycles = {str(cycle): {"build_id": build_id, "source_dates": _source_dates(store, cycle)}}
        copy_started = time.monotonic()
        _load_postgres(conn, models, sql_dir=sql_dir, work=work, build_id=build_id, cycles=cycles)
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
    return Loaded(build_id, row_counts, aggregate_s, copy_s)
