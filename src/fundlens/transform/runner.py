"""`fundlens transform`: one cycle's bronze files into the silver tables (spec §5.3).

Plain SQL over DuckDB, no dbt. The runner gives the SQL these tables and views to read:

- one view per FEC bulk file published for the cycle, named for it (`cm`, `cn`, `ccl`, …): the
  newest bronze file read with the catalogue's column names, as VARCHAR and then cast to the
  catalogue's types (`fec.files`). A zip's text file, pipe-delimited and named by the vendored
  header, and a CSV, whose header row must be the catalogue's columns, are both copied under
  `scratch/` for the run, rewritten as UTF-8 without NUL bytes on the way (`copy_as_utf8`), and
  deleted after it (`fetch_bulk`). An `indiv` text file that disagrees in size with the same rows
  split under `by_date/` is read from those files instead (`copy_bulk`, NEU-2321). The files
  that carry the itemized files' transaction key, `indiv`, `oth`, `pas2`, `oppexp` and
  `CommunicationCosts`, read each transaction of a filing once: a row FEC's file repeats, the
  same in every column but SUB_ID, is in `<file>_repeat` and not the view, which reads
  `<file>_published` (`_drop_fec_repeats`, NEU-2401);
  A catalogued file FEC does not publish for the cycle (`ccl` before 2000, spec §4) is an empty
  table of the same columns, so the SQL reads it as a file with no rows;
- `race`, the cycle's seat calendar (`transform.seats`), which candidates attach to;
- `house_district`, the cycle's House filings whose `cn` district is not the one they ran in,
  with the one they did (`fec/seats/house_districts.csv`, NEU-2293);
- `special_candidate`, the cycle's filings FEC's results list in a Senate special held beside a
  regular race, and which of the two each stands in (`fec/seats/special_candidates.csv`,
  NEU-2319);
- `conduit`, the vendored conduit committees (`fec/conduits.csv`);
- `handoff`, the vendored handoffs whose date falls in the cycle (`fec/handoffs.csv`): a committee
  handed from one candidate to another, whose money is the first's before the date and the
  second's on and after it (NEU-2126);
- `ie_candidate_correction`, the vendored independent expenditures FEC's `pas2` credits to a
  candidate other than the one the filing names (`fec/ie_candidate_corrections.csv`, NEU-2279);
- `unmatched_filing`, the cycle's `app.unmatched_filing` rows, written by `fundlens seats
  --report`, which must therefore run first;
- the contributor normalizers of `resolve.normalize` as SQL functions (`normalize_name`, `zip5`,
  `normalize_employer`, `normalize_occupation`), from which the contributor key is built, and
  `organization_key`, which groups organization receipts (ADR-0011);
- `fec_line`, the Form 3/3X line FEC files a transaction type on (`fec.lines`, NEU-2193);
- `spending_category`, an operating expenditure's category and its source (`transform.spending`,
  NEU-2153).

It runs `sql/silver/*.sql` in filename order. `NN_<table>.sql` creates the silver table
`<table>`, may leave temporary tables a later file reads, and may fill in a column of an earlier
table that needs its own (03_candidate_committee_link.sql sets `candidate.alias_of`);
`{cycle}`, `{build_id}`, `{bronze_dir}` and `{silver_dir}` in it are parameters (so a literal
brace is written twice).
A model or check puts the larger input on the left of each join: DuckDB builds the join on its
right side as written (`connect`).
Then it runs every `sql/checks/silver_*.sql`, each a query that must return no rows, and stops
with `ChecksFailed` before anything is written if one returns any. Only then is each table
written as one zstd Parquet part to the local silver path and dropped (`WRITTEN_FIRST` first,
then the rest in model order), uploaded to R2 (replacing whatever else the partition held), and
the `transformed` marker written.
A `memory after <step>` line follows the views and each model, check, write and upload: the
process's peak resident memory and its resident memory now (`fundlens.memory`), and DuckDB's own
bytes in memory and spilled (`duckdb_memory()`), which an upload's line, the connection closed,
leaves out (NEU-2408).
"""

import csv
import io
import logging
import shutil
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib.resources import files as package_files
from pathlib import Path
from typing import IO, Literal, get_args

import duckdb
from psycopg import Connection
from psycopg.rows import TupleRow

from fundlens import markers, paths
from fundlens.fec import lines
from fundlens.fec.files import CATALOGUE, VARCHAR, BulkFile, files_for, read_csv_header
from fundlens.memory import resident_and_peak_gib
from fundlens.paths import SilverTable
from fundlens.r2 import R2
from fundlens.resolve import normalize
from fundlens.settings import Settings
from fundlens.transform import seats, spending

log = logging.getLogger(__name__)

# Spec §3.4: no Parquet row group above a million rows. DuckDB rounds the size it is given up to
# a multiple of its 2,048-row vector, so this is the largest such multiple under a million.
ROW_GROUP_ROWS = 488 * 2048
CHUNK_BYTES = 1024 * 1024
# Failing rows quoted per check in the error; the query itself finds the rest.
SHOWN_ROWS = 5
# A transaction's place in FEC's itemized files (`indiv`, `oth`, `pas2`): its filer, filing and
# TRAN_ID there, and FEC's id for the row (NEU-2401).
TRANSACTION_KEY = ("CMTE_ID", "FILE_NUM", "TRAN_ID", "SUB_ID")
# The silver tables written before the rest. Each table is dropped once written, and the
# transform's memory peak is `contribution`'s write, with every table not yet written still held:
# `operating_expenditure` is 0.87 GiB of 2024's, so it goes first (every-FEC-dollar spec §5.1,
# NEU-2152).
WRITTEN_FIRST: tuple[SilverTable, ...] = ("operating_expenditure",)


type DuckDBConfig = dict[str, str | bool | int | float | list[str]]


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

    def duckdb_config(self, temp_directory: Path) -> "DuckDBConfig":
        """The `config` for `duckdb.connect`, spilling under `temp_directory`."""
        config: DuckDBConfig = {
            "temp_directory": str(temp_directory),
            "max_temp_directory_size": self.max_temp_directory_size,
        }
        if self.memory_limit is not None:
            config["memory_limit"] = self.memory_limit
        if self.threads is not None:
            config["threads"] = self.threads
        return config


@dataclass(frozen=True)
class Transformed:
    """What `transform` wrote: rows per silver table, and the R2 keys of their parts."""

    row_counts: dict[str, int]
    keys: list[str]


def literal(value: str | Path) -> str:
    """`value` as a SQL string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def connect(limits: Limits, temp_directory: Path) -> duckdb.DuckDBPyConnection:
    """The transform's DuckDB connection, with `limits` and spilling under `temp_directory`.

    DuckDB has no row count for a `read_csv` view and guesses a few dozen rows, so its build-side
    optimizer turns `indiv LEFT JOIN committee` around and builds the join's hash table on the
    whole bulk file instead of the small table: every row held in memory at once. That ran the
    2024 transform out of memory (NEU-2076). So the optimizer is off and each join builds on its
    right side as written, which the silver SQL keeps the smaller.
    """
    config = limits.duckdb_config(temp_directory)
    config["disabled_optimizers"] = "build_side_probe_side"
    return duckdb.connect(config=config)


def _newest_bronze(store: R2, cycle: int, file: BulkFile) -> str:
    # Keys end in an ISO download date, so key order is download order.
    keys = sorted(store.list_keys(paths.bronze_dir(cycle, file.name)))
    if not keys:
        raise FileNotFoundError(f"no {file.name} file in bronze for {cycle}")
    return keys[-1]


def _decode_line(line: bytes) -> str:
    for encoding in ("utf-8", "cp1252"):
        try:
            return line.decode(encoding)
        except UnicodeDecodeError:
            pass
    # Decodes any byte, the five Windows-1252 leaves undefined among them.
    return line.decode("latin-1")


def _write_utf8(block: bytes, out: IO[bytes]) -> None:
    try:
        block.decode("utf-8")
    except UnicodeDecodeError:
        block = b"".join(
            _decode_line(line).encode("utf-8") for line in block.splitlines(keepends=True)
        )
    # Postgres refuses a NUL in `text`, and a NUL is never data in FEC's pipe-delimited text.
    out.write(block.replace(b"\x00", b""))


def copy_as_utf8(src: IO[bytes], out: IO[bytes], *, chunk_bytes: int = CHUNK_BYTES) -> None:
    """Copy FEC bulk text from `src` to `out` as UTF-8, without its NUL bytes.

    FEC's bulk text is not in one encoding: a newer filing writes UTF-8 and an older or
    Windows-made one latin-1 or Windows-1252, side by side in one file. DuckDB reads one
    encoding, and its latin-1 refuses the bytes 0x80-0x9F, so a single UTF-8 name fails the whole
    file (NEU-2069). Each line is decoded as UTF-8, else Windows-1252, else latin-1, so no line
    can fail and no row is dropped. The copy runs in blocks cut after a newline, so a character
    is never split; a block that is valid UTF-8 already, nearly every one, is written as it is.

    Every NUL byte (0x00) is dropped, from every block. A NUL is never data in FEC's
    pipe-delimited text, and Postgres refuses one in a `text` value, so one that reached silver
    failed gold's `COPY` (1994's `cm`, `C00080291`'s `CONNECTED_ORG_NM`; NEU-2282). Dropping it
    here keeps it out of silver, the published dataset, as well as out of gold.
    """
    tail = b""
    while chunk := src.read(chunk_bytes):
        block = tail + chunk
        cut = block.rfind(b"\n") + 1
        _write_utf8(block[:cut], out)
        tail = block[cut:]
    _write_utf8(tail, out)


def _end_line(out: IO[bytes]) -> None:
    """End the last line written to `out` if it is unended, so the next file starts a row."""
    if out.tell() == 0:
        return
    out.seek(-1, io.SEEK_END)
    if out.read(1) != b"\n":
        out.write(b"\n")


def copy_bulk(
    archive: zipfile.ZipFile, file: BulkFile, out: IO[bytes], *, cycle: int, source: str
) -> None:
    """Copy `file`'s text for `cycle` out of `archive` into `out` as UTF-8 (`copy_as_utf8`);
    `out` must be readable as well as writable.

    The text is `file.member_for(cycle)`, unless the zip also holds its rows split under
    `file.split_dir` and the two disagree in size: then the split files are copied in its place,
    in name order, each ending its last line, with a warning naming `source`. FEC's 2022 `indiv`
    zip holds an `itcont.txt` cut off mid-row at 37% of its `by_date/` files' bytes (NEU-2321).
    When the two agree, as every other cycle's do, the member is read, so a built cycle's rows
    keep their order; reading both would count every row twice.
    """
    member = file.member_for(cycle)
    whole = archive.getinfo(member)
    split = sorted(
        (
            info
            for info in archive.infolist()
            if file.split_dir and info.filename.startswith(file.split_dir) and not info.is_dir()
        ),
        key=lambda info: info.filename,
    )
    split_bytes = sum(info.file_size for info in split)
    if not split or split_bytes == whole.file_size:
        with archive.open(whole) as src:
            copy_as_utf8(src, out)
        return
    # The sizes with thousands separators, as FEC's listings and the backfill runbook write them.
    log.warning(
        "%s: %s holds %s bytes but %s %s; reading %s",
        source,
        member,
        f"{whole.file_size:,}",
        file.split_dir,
        f"{split_bytes:,}",
        file.split_dir,
    )
    for info in split:
        with archive.open(info) as src:
            copy_as_utf8(src, out)
        _end_line(out)


def fetch_bulk(store: R2, cycle: int, file: BulkFile, *, data_dir: Path, work: Path) -> Path:
    """The newest bronze file of `file` copied under `work` as UTF-8; the copy's path.

    The current cycle's file is on local disk already (`fec.extract` keeps it there); any other
    is fetched into `work`, so a historical file never outlives the run (spec §3.4). A zip's text
    is its member, or its split files when the two disagree (`copy_bulk`). A CSV's header row
    must be the catalogue's columns, else `ValueError` naming the bronze key, before any of it is
    read.
    """
    key = _newest_bronze(store, cycle, file)
    local = paths.local_path(data_dir, key)
    if not local.exists():
        local = store.download_to(key, work / f"{file.name}.{file.format}")
    text = work / f"{file.name}.txt"
    if file.format == "csv":
        if read_csv_header(local) != list(file.columns):
            raise ValueError(f"{key}: the header row is not the catalogued {file.name} columns")
        with local.open("rb") as src, text.open("wb") as out:
            copy_as_utf8(src, out)
    else:
        with zipfile.ZipFile(local) as archive, text.open("w+b") as out:
            copy_bulk(archive, file, out, cycle=cycle, source=key)
    log.info("%s %d read from %s", file.name, cycle, key)
    return text


def register_bulk(con: duckdb.DuckDBPyConnection, file: BulkFile, text: Path) -> None:
    """The view `<file>`: the bulk file's rows under the catalogue's names, cast to their types.

    `text` is `fetch_bulk`'s copy, UTF-8 throughout. An itemized file's view reads each
    transaction once, its rows as published being `<file>_published` (`_drop_fec_repeats`).
    """
    # A CSV's header row was checked by `fetch_bulk`; a zip's names are its vendored header.
    if file.format == "zip" and file.header() != list(file.columns):
        raise ValueError(f"the vendored {file.header_file} disagrees with the catalogue")
    columns = ", ".join(f"{literal(name)}: 'VARCHAR'" for name in file.columns)
    selected = ", ".join(
        f'"{name}"' if kind == VARCHAR else f'CAST("{name}" AS {kind}) AS "{name}"'
        for name, kind in file.columns.items()
    )
    if file.format == "csv":
        # RFC 4180 with a header row, which `fetch_bulk` checked. FEC quotes every field and
        # writes a blank one as `""`, which reads as NULL, as a zip's empty field does.
        dialect = (
            "delim = ',', quote = '\"', escape = '\"', header = true, allow_quoted_nulls = true"
        )
    else:
        # Pipe-delimited and unquoted (a quote in a name is just a character), no header row.
        # A `trailing_delimiter` file's lines end in a `|`: DuckDB reads the empty field after the
        # last column as nothing and refuses a non-empty one, which
        # tests/unit/test_transform_trailing_delimiter.py holds it to.
        dialect = "delim = '|', quote = '', escape = '', header = false"
    source = (
        f"SELECT {selected} FROM read_csv({literal(text)},"
        f" {dialect}, auto_detect = false, columns = {{{columns}}}, encoding = 'utf-8')"
    )
    if not set(TRANSACTION_KEY) <= file.columns.keys():
        con.execute(f"CREATE VIEW {file.name} AS {source}")
        return
    con.execute(f"CREATE VIEW {file.name}_published AS {source}")
    _drop_fec_repeats(con, file)


def _drop_fec_repeats(con: duckdb.DuckDBPyConnection, file: BulkFile) -> None:
    """The view `<file>`: `<file>_published` less the rows FEC's file repeats (NEU-2401).

    A filer gives each transaction on a filing its own TRAN_ID, and FEC's file sometimes holds one
    transaction on two, three or four rows: the same in every column but SUB_ID. On 2024 every
    such row checked against its raw filing (`docquery.fec.gov/dcdev/posted/<FILE_NUM>.fec`) is
    one transaction there. `indiv` holds 18,519 rows beyond a transaction's first, $2.5M on 14
    filings at 11 committees, ten of the filings whole: Marianne Williamson's YE 2023 amendment
    counted $1,221,546 of earmarks against the $611,208 it itemized. `oth` holds 227, $11.4M,
    and `pas2` 37, $177,242 (docs/measurements/summary-files-2024.md Q16). So a row is read when it
    is the first, by SUB_ID, of the rows of an electronic filing (FILE_NUM above 0) that share its
    TRAN_ID and every other column; `<file>_repeat` holds the SUB_ID of each other. A copy under
    the first's own SUB_ID is no repeat here: both are read, for the key checks to stop the build
    on (2024's SUB_IDs are unique). Rows sharing a TRAN_ID that differ are all read: nothing says
    which is the transaction (2024: 3 TRAN_IDs in `indiv`, 2 in `oth`, 1 in `pas2`). Nor is a row
    with no TRAN_ID a repeat, as a paper filing's are: one donor's gifts of one size on one day
    are separate gifts (Q13f). Every silver model reads the view, so each rule sees a filing as
    filed. A row with no SUB_ID is read, for the key checks to stop the build on.

    Built in two steps, so the whole file is never held: the transactions on more than one row, by
    a hash of their filing and TRAN_ID, then those rows alone, each against the lowest SUB_ID of
    the rows it equals.
    """
    published = f"{file.name}_published"
    shared = f"hash({', '.join(TRANSACTION_KEY[:3])})"
    columns = ", ".join(f'"{name}"' for name in file.columns if name != "SUB_ID")
    con.execute(f"""
        CREATE TEMP TABLE {file.name}_repeat AS
        WITH shared AS (
            SELECT {shared} AS filed_as
            FROM {published}
            WHERE FILE_NUM > 0 AND nullif(trim(TRAN_ID), '') IS NOT NULL
            GROUP BY 1
            HAVING count(*) > 1
        )
        SELECT SUB_ID
        FROM {published}
        JOIN shared ON shared.filed_as = {shared}
        WHERE FILE_NUM > 0 AND nullif(trim(TRAN_ID), '') IS NOT NULL
        QUALIFY SUB_ID > min(SUB_ID) OVER (PARTITION BY {columns})
    """)
    con.execute(f"""
        CREATE VIEW {file.name} AS
        SELECT *
        FROM {published}
        WHERE SUB_ID IS NULL OR SUB_ID NOT IN (SELECT SUB_ID FROM {file.name}_repeat)
    """)


def register_unpublished(con: duckdb.DuckDBPyConnection, file: BulkFile) -> None:
    """The table `<file>`, empty, with the bulk file's columns and types: a file FEC does not
    publish for the cycle reads as one with no rows (`ccl` before 2000, spec §4). An itemized
    file's `<file>_repeat` is empty too."""
    columns = ", ".join(f'"{name}" {kind}' for name, kind in file.columns.items())
    con.execute(f"CREATE TABLE {file.name} ({columns})")
    if set(TRANSACTION_KEY) <= file.columns.keys():
        con.execute(f"CREATE TEMP TABLE {file.name}_repeat (SUB_ID {file.columns['SUB_ID']})")


def _register_conduits(con: duckdb.DuckDBPyConnection) -> None:
    text = package_files("fundlens.fec").joinpath("conduits.csv").read_text()
    rows = [(row["committee_id"], row["name"]) for row in csv.DictReader(io.StringIO(text))]
    con.execute("CREATE TABLE conduit (committee_id VARCHAR, name VARCHAR)")
    con.executemany("INSERT INTO conduit VALUES (?, ?)", rows)


def handoffs() -> list[tuple[str, str, str, date]]:
    """Every vendored handoff (`fec/handoffs.csv`, NEU-2126): the committee, the candidates it was
    handed from and to, and the date."""
    text = package_files("fundlens.fec").joinpath("handoffs.csv").read_text()
    return [
        (
            row["committee_id"],
            row["from_candidate_id"],
            row["to_candidate_id"],
            date.fromisoformat(row["handoff_date"]),
        )
        for row in csv.DictReader(io.StringIO(text))
    ]


def _register_handoffs(con: duckdb.DuckDBPyConnection, cycle: int) -> None:
    rows = [handoff for handoff in handoffs() if handoff[3].year in (cycle - 1, cycle)]
    con.execute(
        "CREATE TABLE handoff (committee_id VARCHAR, from_candidate_id VARCHAR,"
        " to_candidate_id VARCHAR, handoff_date DATE)"
    )
    # DuckDB's executemany refuses an empty list, and most cycles have no handoff.
    if rows:
        con.executemany("INSERT INTO handoff VALUES (?, ?, ?, ?)", rows)


def _register_house_districts(con: duckdb.DuckDBPyConnection, cycle: int) -> None:
    rows = list(seats.house_districts(cycle).items())
    con.execute("CREATE TABLE house_district (candidate_id VARCHAR, district VARCHAR)")
    # DuckDB's executemany refuses an empty list, and most cycles correct no district.
    if rows:
        con.executemany("INSERT INTO house_district VALUES (?, ?)", rows)


def _register_special_candidates(con: duckdb.DuckDBPyConnection, cycle: int) -> None:
    rows = [(r.candidate_id, r.office, r.state, r.race) for r in seats.special_candidates(cycle)]
    con.execute(
        "CREATE TABLE special_candidate"
        " (candidate_id VARCHAR, office VARCHAR, state VARCHAR, race VARCHAR)"
    )
    # DuckDB's executemany refuses an empty list, and most cycles have no special beside a race.
    if rows:
        con.executemany("INSERT INTO special_candidate VALUES (?, ?, ?, ?)", rows)


def _register_ie_candidate_corrections(con: duckdb.DuckDBPyConnection) -> None:
    # Keyed by SUB_ID, unique across FEC's files, so every cycle can load the whole list: a row of
    # another cycle matches nothing.
    text = package_files("fundlens.fec").joinpath("ie_candidate_corrections.csv").read_text()
    rows = [
        (int(row["sub_id"]), row["pas2_candidate_id"], row["candidate_id"])
        for row in csv.DictReader(io.StringIO(text))
    ]
    con.execute(
        "CREATE TABLE ie_candidate_correction (sub_id UBIGINT, pas2_candidate_id VARCHAR,"
        " candidate_id VARCHAR)"
    )
    con.executemany("INSERT INTO ie_candidate_correction VALUES (?, ?, ?)", rows)


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


def render(path: Path, params: Mapping[str, object]) -> str:
    """The SQL in `path` with its `{name}` parameters filled from `params`."""
    return path.read_text().format_map(params)


def check(
    con: duckdb.DuckDBPyConnection,
    sql_dir: Path,
    params: Mapping[str, object],
    *,
    tier: Literal["silver", "gold"],
    consequence: str,
    after: Callable[[str], None] | None = None,
) -> None:
    """Run every `sql/checks/<tier>_*.sql`; raise `ChecksFailed` naming each that returned rows.

    `consequence` says what the failure spared ("nothing uploaded"); the gold loader reuses this
    with its own. `after`, when given, is called with each check's step name (`<tier> check
    <file>`) once its rows are fetched.
    """
    failures: list[str] = []
    for path in sorted((sql_dir / "checks").glob(f"{tier}_*.sql")):
        log.info("%s check %s", tier, path.name)
        rows = con.execute(render(path, params)).fetchmany(SHOWN_ROWS + 1)
        if after is not None:
            after(f"{tier} check {path.name}")
        if rows:
            shown = "; ".join(str(row) for row in rows[:SHOWN_ROWS])
            more = ", …" if len(rows) > SHOWN_ROWS else ""
            failures.append(f"{path.name}: {shown}{more}")
    if failures:
        raise ChecksFailed(f"{tier} checks failed, {consequence}:\n" + "\n".join(failures))


def write_order(tables: list[SilverTable]) -> list[SilverTable]:
    """`tables` in the order `transform` writes them: `WRITTEN_FIRST`'s, then the rest as given."""
    return sorted(tables, key=lambda table: table not in WRITTEN_FIRST)


def _log_memory(step: str, con: duckdb.DuckDBPyConnection | None = None) -> None:
    """Log `memory after <step>`: the process's peak resident memory and its resident memory now,
    then, given `con`, what DuckDB holds in memory and has spilled, all in GiB (NEU-2408)."""
    resident, peak = resident_and_peak_gib()
    if con is None:
        log.info("memory after %s: peak resident %.2f GiB, resident %.2f GiB", step, peak, resident)
        return
    [(in_memory, spilled)] = con.execute(
        "SELECT coalesce(sum(memory_usage_bytes), 0), coalesce(sum(temporary_storage_bytes), 0)"
        " FROM duckdb_memory()"
    ).fetchall()
    log.info(
        "memory after %s: peak resident %.2f GiB, resident %.2f GiB,"
        " DuckDB %.2f GiB in memory, %.2f GiB spilled",
        step,
        peak,
        resident,
        in_memory / 2**30,
        spilled / 2**30,
    )


def _log_spending(con: duckdb.DuckDBPyConnection, cycle: int) -> None:
    """Log `operating_expenditure`'s rows, its counted rows and dollars, and the counted dollars
    no rule or trusted code classifies, with their share: the figures a cycle's spending is
    checked against (every-FEC-dollar spec §5.1, §5.3; NEU-2152, NEU-2153)."""
    [(rows, counted, dollars, unclassified)] = con.execute(
        "SELECT count(*), count(*) FILTER (WHERE counted),"
        " coalesce(sum(amount) FILTER (WHERE counted), 0),"
        " coalesce(sum(amount) FILTER (WHERE counted AND category_source = 'unclassified'), 0)"
        " FROM operating_expenditure"
    ).fetchall()
    share = f"{unclassified / dollars:.2%}" if dollars else "n/a"
    log.info(
        "operating_expenditure %d: %s rows, %s counted, $%s counted, $%s (%s) unclassified",
        cycle,
        f"{rows:,}",
        f"{counted:,}",
        f"{dollars:,}",
        f"{unclassified:,}",
        share,
    )


def _log_ie_24_48(con: duckdb.DuckDBPyConnection, cycle: int) -> None:
    """Log the 24/48-hour file's rows `independent_expenditure` adds, rows and dollars by each of
    the two rules, and the largest single row with its spender: a hoax filing that passes the
    screen shows here (every-FEC-dollar spec §6.3, NEU-2165). `ie_24_48_added` is the model's."""
    added = dict.fromkeys(("by_spender", "timeliness"), (0, Decimal(0)))
    for rule, rows, dollars in con.execute(
        "SELECT rule, count(*), coalesce(sum(amount), 0) FROM ie_24_48_added GROUP BY rule"
    ).fetchall():
        added[rule] = (rows, dollars)
    largest = con.execute(
        "SELECT amount, committee_id, source_record_id FROM ie_24_48_added"
        " ORDER BY amount DESC NULLS LAST, source_record_id LIMIT 1"
    ).fetchone()
    log.info(
        "independent_expenditure %d: 24/48-hour rows added: by spender %s rows, $%s;"
        " timeliness %s rows, $%s; largest %s",
        cycle,
        *(f"{figure:,}" for rows, dollars in added.values() for figure in (rows, dollars)),
        "none" if largest is None else f"${largest[0]:,} by {largest[1]} ({largest[2]})",
    )


def _log_pas2_kinds(con: duckdb.DuckDBPyConnection, cycle: int) -> None:
    """Log `independent_expenditure`'s communication costs and party coordinated expenditures, rows
    and dollars of each, and the communication costs `CommunicationCosts` gives a type: the
    figures a cycle's two kinds are checked against (every-FEC-dollar spec §6.2, NEU-2167)."""
    [(costs, cost_dollars, typed, coordinated, coordinated_dollars)] = con.execute(
        "SELECT"
        " count(*) FILTER (WHERE kind = 'communication_cost'),"
        " coalesce(sum(amount) FILTER (WHERE kind = 'communication_cost'), 0),"
        " count(*) FILTER (WHERE kind = 'communication_cost' AND communication_type IS NOT NULL),"
        " count(*) FILTER (WHERE kind = 'coordinated'),"
        " coalesce(sum(amount) FILTER (WHERE kind = 'coordinated'), 0)"
        " FROM independent_expenditure"
    ).fetchall()
    log.info(
        "independent_expenditure %d: communication costs %s rows, $%s, %s with a type;"
        " party coordinated %s rows, $%s",
        cycle,
        f"{costs:,}",
        f"{cost_dollars:,}",
        f"{typed:,}",
        f"{coordinated:,}",
        f"{coordinated_dollars:,}",
    )


def _log_electioneering(con: duckdb.DuckDBPyConnection, cycle: int) -> None:
    """Log `electioneering_communication`'s rows and dollars, the dollars reaching a race, and the
    disbursements' copies dropped: the figures a cycle's electioneering communications are checked
    against (every-FEC-dollar spec §6.4, NEU-2166). A copy is a row of a spender of the cycle the
    table does not hold."""
    [(rows, dollars, in_races, filed)] = con.execute(
        "SELECT count(*), coalesce(sum(amount), 0),"
        " coalesce(sum(amount) FILTER (WHERE race_id IS NOT NULL), 0),"
        " (SELECT count(*) FROM ElectioneeringComm"
        "  WHERE COMMITTEE_ID IN (SELECT committee_id FROM committee))"
        " FROM electioneering_communication"
    ).fetchall()
    log.info(
        "electioneering_communication %d: %s rows, $%s; $%s reaching a race;"
        " disbursements' copies dropped: %s",
        cycle,
        f"{rows:,}",
        f"{dollars:,}",
        f"{in_races:,}",
        f"{filed - rows:,}",
    )


def _write(
    con: duckdb.DuckDBPyConnection, table: SilverTable, *, cycle: int, build_id: str, data_dir: Path
) -> tuple[str, Path, int]:
    """Write `table` as one zstd Parquet part to the local silver path, then drop it, so memory
    holds only the tables still to write; its key, path and rows.

    The local partition is replaced whole, so a build transformed again holds none of the parts
    a donor_id rewrite (`resolve.crosswalk`) put there.
    """
    log.info("write %s %d", table, cycle)
    key = f"{paths.silver_partition(table, cycle, build_id)}/{paths.part(0)}"
    local = paths.local_path(data_dir, key)
    shutil.rmtree(local.parent, ignore_errors=True)
    local.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"COPY {table} TO {literal(local)}"
        f" (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE {ROW_GROUP_ROWS})"
    )
    [(rows,)] = con.execute(f"SELECT count(*) FROM {table}").fetchall()
    con.execute(f"DROP TABLE {table}")
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
    params = {
        "cycle": cycle,
        "build_id": build_id,
        "bronze_dir": paths.local_path(data_dir, f"bronze/cycle={cycle}"),
        "silver_dir": paths.local_path(data_dir, "silver"),
    }
    try:
        with connect(limits, scratch) as con:
            published = files_for(cycle)
            for file in published:
                register_bulk(
                    con, file, fetch_bulk(store, cycle, file, data_dir=data_dir, work=work)
                )
            for file in CATALOGUE.values():
                if file not in published:
                    register_unpublished(con, file)
            seats.load_races(con, seats.races_for(cycle))
            _register_conduits(con)
            _register_handoffs(con, cycle)
            _register_house_districts(con, cycle)
            _register_special_candidates(con, cycle)
            _register_ie_candidate_corrections(con)
            _register_unmatched(con, conn, cycle)
            normalize.register(con)
            lines.register(con)
            spending.register(con)
            _log_memory(f"views {cycle}", con)
            for table, path in models:
                log.info("silver %s %d: %s", table, cycle, path.name)
                con.execute(render(path, params))
                _log_memory(f"silver {table} {cycle}", con)
            check(
                con,
                sql_dir,
                params,
                tier="silver",
                consequence="nothing uploaded",
                after=lambda step: _log_memory(step, con),
            )
            _log_spending(con, cycle)
            _log_ie_24_48(con, cycle)
            _log_pas2_kinds(con, cycle)
            _log_electioneering(con, cycle)
            written: dict[SilverTable, tuple[str, Path, int]] = {}
            for table in write_order([table for table, _ in models]):
                written[table] = _write(
                    con, table, cycle=cycle, build_id=build_id, data_dir=data_dir
                )
                _log_memory(f"write {table} {cycle}", con)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    for key, local, _ in written.values():
        log.info("upload %s", key)
        prefix = key.rsplit("/", 1)[0] + "/"
        stale = set(store.list_keys(prefix)) - {key}
        store.put(key, local)
        # A build transformed again: whatever else its partition held is gone, the rewrite
        # sentinel of a donor_id rewrite that died among it.
        store.delete_keys(sorted(stale))
        _log_memory(f"upload {key}")
    row_counts = {table: rows for table, (_, _, rows) in written.items()}
    markers.write(
        "transformed",
        store,
        cycle=cycle,
        build_id=build_id,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        row_counts=row_counts,
    )
    return Transformed(row_counts, [key for key, _, _ in written.values()])
