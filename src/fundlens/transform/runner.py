"""`fundlens transform`: one cycle's bronze zips into the silver tables (spec §5.3).

Plain SQL over DuckDB, no dbt. The runner gives the SQL these tables and views to read:

- one view per FEC bulk file published for the cycle, named for it (`cm`, `cn`, `ccl`, …): the
  newest bronze zip's text file read with the vendored column names, as VARCHAR and then cast to
  the catalogue's types (`fec.files`). DuckDB cannot read a zip, so the text is unpacked under
  `scratch/` for the run and deleted after it;
- `race`, the cycle's seat calendar (`transform.seats`), which candidates attach to;
- `conduit`, the vendored conduit committees (`fec/conduits.csv`);
- `unmatched_filing`, the cycle's `app.unmatched_filing` rows, written by `fundlens seats
  --report`, which must therefore run first.

It runs `sql/silver/*.sql` in filename order. `NN_<table>.sql` creates the silver table
`<table>`; `{cycle}`, `{build_id}`, `{bronze_dir}` and `{silver_dir}` in it are parameters (so a
literal brace is written twice). Then it runs every `sql/checks/silver_*.sql`, each a query that
must return no rows, and stops with `ChecksFailed` before anything is written if one returns
any. Only then is each table written as one zstd Parquet part to the local silver path,
uploaded to R2, and the `transformed` marker written.
"""

import csv
import io
import logging
import shutil
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files as package_files
from pathlib import Path
from typing import get_args

import duckdb
from psycopg import Connection
from psycopg.rows import TupleRow

from fundlens import markers, paths
from fundlens.fec.files import VARCHAR, BulkFile, files_for
from fundlens.paths import SilverTable
from fundlens.r2 import R2
from fundlens.settings import Settings
from fundlens.transform import seats

log = logging.getLogger(__name__)

# Spec §3.4: no Parquet row group above a million rows. DuckDB rounds the size it is given up to
# a multiple of its 2,048-row vector, so this is the largest such multiple under a million.
ROW_GROUP_ROWS = 488 * 2048
CHUNK_BYTES = 1024 * 1024
# Failing rows quoted per check in the error; the query itself finds the rest.
SHOWN_ROWS = 5


class ChecksFailed(Exception):
    """One or more silver checks returned rows: the build is wrong and nothing was uploaded."""


@dataclass(frozen=True)
class Limits:
    """DuckDB's resource limits; None leaves DuckDB's own default."""

    memory_limit: str | None
    max_temp_directory_size: str
    threads: int | None

    @classmethod
    def from_settings(cls, settings: Settings) -> "Limits":
        return cls(
            settings.duckdb_memory_limit,
            settings.duckdb_max_temp_directory_size,
            settings.duckdb_threads,
        )


@dataclass(frozen=True)
class Transformed:
    """What `transform` wrote: rows per silver table, and the R2 keys of their parts."""

    row_counts: dict[str, int]
    keys: list[str]


def _literal(value: str | Path) -> str:
    """`value` as a SQL string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def _newest_bronze(store: R2, cycle: int, file: BulkFile) -> str:
    # Keys end in an ISO download date, so key order is download order.
    keys = sorted(store.list_keys(paths.bronze_dir(cycle, file.name)))
    if not keys:
        raise FileNotFoundError(f"no {file.name} file in bronze for {cycle}")
    return keys[-1]


def _unzip(store: R2, cycle: int, file: BulkFile, *, data_dir: Path, work: Path) -> Path:
    """The newest bronze zip of `file` unpacked under `work`; the text file's path.

    The current cycle's zip is on local disk already (`fec.extract` keeps it there); any other is
    fetched into `work`, so a historical zip never outlives the run (spec §3.4).
    """
    key = _newest_bronze(store, cycle, file)
    local = paths.local_path(data_dir, key)
    if not local.exists():
        local = store.download_to(key, work / f"{file.name}.zip")
    text = work / f"{file.name}.txt"
    with zipfile.ZipFile(local) as archive:
        with archive.open(file.member) as src, text.open("wb") as out:
            shutil.copyfileobj(src, out, CHUNK_BYTES)
    log.info("%s %d read from %s", file.name, cycle, key)
    return text


def _register_bulk(con: duckdb.DuckDBPyConnection, file: BulkFile, text: Path) -> None:
    """The view `<file>`: the bulk file's rows under the vendored names, cast to their types."""
    names = file.header()
    if names != list(file.columns):
        raise ValueError(f"the vendored {file.header_file} disagrees with the catalogue")
    columns = ", ".join(f"{_literal(name)}: 'VARCHAR'" for name in names)
    selected = ", ".join(
        f'"{name}"' if kind == VARCHAR else f'CAST("{name}" AS {kind}) AS "{name}"'
        for name, kind in file.columns.items()
    )
    # Pipe-delimited and unquoted (a quote in a name is just a character), with no header row.
    # FEC's bulk text is not UTF-8 throughout; latin-1 decodes any byte.
    con.execute(
        f"CREATE VIEW {file.name} AS SELECT {selected} FROM read_csv({_literal(text)},"
        f" delim = '|', quote = '', escape = '', header = false, auto_detect = false,"
        f" columns = {{{columns}}}, encoding = 'latin-1')"
    )


def _register_conduits(con: duckdb.DuckDBPyConnection) -> None:
    text = package_files("fundlens.fec").joinpath("conduits.csv").read_text()
    rows = [(row["committee_id"], row["name"]) for row in csv.DictReader(io.StringIO(text))]
    con.execute("CREATE TABLE conduit (committee_id VARCHAR, name VARCHAR)")
    con.executemany("INSERT INTO conduit VALUES (?, ?)", rows)


def _register_unmatched(
    con: duckdb.DuckDBPyConnection, conn: Connection[TupleRow], cycle: int
) -> None:
    rows = conn.execute(
        "SELECT candidate_id FROM app.unmatched_filing WHERE cycle = %s", (cycle,)
    ).fetchall()
    con.execute("CREATE TABLE unmatched_filing (candidate_id VARCHAR)")
    # DuckDB's executemany refuses an empty list, and most cycles have no unmatched filing.
    if rows:
        con.executemany("INSERT INTO unmatched_filing VALUES (?)", rows)


def _models(sql_dir: Path) -> list[tuple[SilverTable, Path]]:
    """The silver models in run order, each with the table it creates."""
    tables: dict[str, SilverTable] = {table: table for table in get_args(SilverTable)}
    models: list[tuple[SilverTable, Path]] = []
    for path in sorted((sql_dir / "silver").glob("*.sql")):
        table = tables.get(path.stem.partition("_")[2])
        if table is None:
            raise ValueError(f"{path.name} names no silver table")
        models.append((table, path))
    if not models:
        raise ValueError(f"no silver models under {sql_dir}")
    return models


def _render(path: Path, params: Mapping[str, object]) -> str:
    return path.read_text().format_map(params)


def _check(con: duckdb.DuckDBPyConnection, sql_dir: Path, params: Mapping[str, object]) -> None:
    """Run every silver check; raise `ChecksFailed` naming each that returned rows."""
    failures: list[str] = []
    for path in sorted((sql_dir / "checks").glob("silver_*.sql")):
        rows = con.execute(_render(path, params)).fetchmany(SHOWN_ROWS + 1)
        if rows:
            shown = "; ".join(str(row) for row in rows[:SHOWN_ROWS])
            more = ", …" if len(rows) > SHOWN_ROWS else ""
            failures.append(f"{path.name}: {shown}{more}")
    if failures:
        raise ChecksFailed("silver checks failed, nothing uploaded:\n" + "\n".join(failures))


def _write(
    con: duckdb.DuckDBPyConnection, table: SilverTable, *, cycle: int, build_id: str, data_dir: Path
) -> tuple[str, Path, int]:
    """Write `table` as one zstd Parquet part to the local silver path; its key, path and rows."""
    key = f"{paths.silver_partition(table, cycle, build_id)}/{paths.part(0)}"
    local = paths.local_path(data_dir, key)
    local.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"COPY {table} TO {_literal(local)}"
        f" (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE {ROW_GROUP_ROWS})"
    )
    [(rows,)] = con.execute(f"SELECT count(*) FROM {table}").fetchall()
    return key, local, rows


def transform(
    cycle: int,
    store: R2,
    *,
    build_id: str,
    data_dir: Path,
    sql_dir: Path,
    limits: Limits,
    conn: Connection[TupleRow],
) -> Transformed:
    """Build, check and upload `cycle`'s silver tables for `build_id`; write `transformed`.

    Raises `FileNotFoundError` when bronze lacks one of the cycle's files, and `ChecksFailed`
    when a check fails, in both cases before anything is written.
    """
    started_at = datetime.now(UTC)
    models = _models(sql_dir)
    scratch = paths.scratch_dir(data_dir)
    work = scratch / f"transform-{cycle}-{build_id}"
    work.mkdir(parents=True, exist_ok=True)
    config: dict[str, str | bool | int | float | list[str]] = {
        "temp_directory": str(scratch),
        "max_temp_directory_size": limits.max_temp_directory_size,
    }
    if limits.memory_limit is not None:
        config["memory_limit"] = limits.memory_limit
    if limits.threads is not None:
        config["threads"] = limits.threads
    params = {
        "cycle": cycle,
        "build_id": build_id,
        "bronze_dir": paths.local_path(data_dir, f"bronze/cycle={cycle}"),
        "silver_dir": paths.local_path(data_dir, "silver"),
    }
    try:
        with duckdb.connect(config=config) as con:
            for file in files_for(cycle):
                _register_bulk(con, file, _unzip(store, cycle, file, data_dir=data_dir, work=work))
            seats.load_races(con, seats.races_for(cycle))
            _register_conduits(con)
            _register_unmatched(con, conn, cycle)
            for table, path in models:
                log.info("silver %s %d: %s", table, cycle, path.name)
                con.execute(_render(path, params))
            _check(con, sql_dir, params)
            written = [
                _write(con, table, cycle=cycle, build_id=build_id, data_dir=data_dir)
                for table, _ in models
            ]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    for key, local, _ in written:
        store.put(key, local)
    row_counts = {table: rows for (table, _), (_, _, rows) in zip(models, written, strict=True)}
    markers.write(
        "transformed",
        store,
        cycle=cycle,
        build_id=build_id,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        row_counts=row_counts,
    )
    return Transformed(row_counts, [key for key, _, _ in written])
