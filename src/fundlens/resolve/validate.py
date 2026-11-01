"""`fundlens dime` and `fundlens validate`: resolution scored against DIME (spec §6.9, ADR-0009).

Adam Bonica's DIME labels every FEC contribution with a resolved contributor id, `bonica.cid`.
`import_dime` takes one cycle's downloaded DIME contribution file, archives it in R2 and writes
the slim Parquet of its FEC individual rows (`paths.reference_dime`), the only part of DIME the
validator reads. `validate` joins that file to the cycle's bronze `indiv` rows by the filer's
committee and transaction ids, then by `SUB_ID` to the resolved silver `contribution`, and
scores fundlens's `donor_id` against `bonica.cid` over the labelled contributor keys: pairwise
precision and recall, overall and over the `cid`s with the most matched dollars. The figures
go to `app.resolution_quality`, from which `load` copies the live model's into `gold.meta`.
"""

import csv
import gzip
import logging
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from psycopg import Connection
from psycopg.rows import TupleRow

from fundlens import paths
from fundlens.fec.files import CATALOGUE
from fundlens.r2 import R2
from fundlens.resolve import crosswalk, model
from fundlens.transform.runner import ROW_GROUP_ROWS, Limits, literal, register_bulk, unzip_bulk

log = logging.getLogger(__name__)

DIME_VERSION = "4.0"
DIME_SOURCE = "https://data.stanford.edu/dime"
DIME_CITATION = (
    "Bonica, Adam. 2024. Database on Ideology, Money in Politics, and Elections: "
    "Public version 4.0 [Computer file]. Stanford, CA: Stanford University Libraries. "
    "https://data.stanford.edu/dime"
)
DIME_LICENSE = "ODC-BY 1.0"

RUNBOOK = "docs/runbooks/refreshing-dime.md"

# The `cid`s with the most matched dollars that the `top` scope scores.
DEFAULT_TOP = 10_000

# The slim Parquet's columns, each from its DIME column (NEU-2054 §3.3). `contributor.type` is
# read too, by the truth filter, and not kept.
SLIM_COLUMNS = {
    "transaction_id": "transaction.id",
    "cmte_id": "efec.comid.orig",
    "tran_id": "efec.transaction.id.orig",
    "amount": "amount",
    "date": "date",
    "bonica_cid": "bonica.cid",
    "transaction_type": "transaction.type",
    "contributor_name": "contributor.name",
}
CONTRIBUTOR_TYPE = "contributor.type"


@dataclass(frozen=True)
class Imported:
    """What `import_dime` read, kept and wrote."""

    rows_read: int
    rows_kept: int
    # Truth rows dropped for an amount or date that would not cast, or no `bonica.cid`.
    rows_dropped: int
    cids: int
    raw_key: str
    parquet_key: str


@dataclass(frozen=True)
class Score:
    """Pairwise precision and recall over a set of labelled keys (ADR-0009)."""

    labelled_keys: int
    correct_pairs: int
    predicted_pairs: int
    true_pairs: int

    @property
    def precision(self) -> float | None:
        return self.correct_pairs / self.predicted_pairs if self.predicted_pairs else None

    @property
    def recall(self) -> float | None:
        return self.correct_pairs / self.true_pairs if self.true_pairs else None


@dataclass(frozen=True)
class Validated:
    """What `validate` scored and wrote: one `Score` per scope."""

    cycle: int
    build_id: str
    model_version: str
    contribution_rows: int
    matched_rows: int
    top_limit: int
    overall: Score
    top: Score


class NotResolved(Exception):
    """The build's silver `contribution` carries a NULL `donor_id`: there is nothing to score."""


def _q(name: str) -> str:
    # DIME's column names are dotted, so every one is quoted.
    return '"' + name.replace('"', '""') + '"'


def _header(path: Path) -> list[str]:
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", newline="") as f:
        empty: list[str] = []
        return next(csv.reader(f), empty)


def _check_source(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"no DIME file at {path}")
    if not path.name.endswith((".csv", ".csv.gz")):
        raise ValueError(f"{path.name} is not a .csv or .csv.gz")
    header = {name.strip() for name in _header(path)}
    for column in (*SLIM_COLUMNS.values(), CONTRIBUTOR_TYPE):
        if column not in header:
            # A renamed column in a new DIME release fails here, not later with zero rows.
            raise ValueError(f"{path.name} has no {column} column")


def import_dime(store: R2, *, cycle: int, path: Path, data_dir: Path, limits: Limits) -> Imported:
    """Archive the DIME contribution file at `path` for `cycle` in R2 and write the slim Parquet
    of its FEC individual rows, locally and in R2 (NEU-2054 §4).

    A row is kept when DIME marks it an individual's (`contributor.type = 'I'`), it carries an
    FEC committee id and transaction id and a `bonica.cid`, and its amount and date cast. The
    file is read once: every row goes to a staging Parquet under `scratch/`, with the columns of
    any but the truth rows nulled out, so the rows read are counted without decompressing it
    twice.
    """
    _check_source(path)
    raw_key = paths.reference_dime_raw(DIME_VERSION, cycle)
    parquet_key = paths.reference_dime(DIME_VERSION, cycle)
    parquet = paths.local_path(data_dir, parquet_key)
    parquet.parent.mkdir(parents=True, exist_ok=True)
    scratch = paths.scratch_dir(data_dir)
    work = scratch / f"dime-{cycle}"
    work.mkdir(parents=True, exist_ok=True)
    staged = work / "staged.parquet"
    truth = (
        f"{_q(CONTRIBUTOR_TYPE)} = 'I'"
        f" AND regexp_full_match(coalesce({_q('efec.comid.orig')}, ''), 'C\\d{{8}}')"
        f" AND coalesce({_q('efec.transaction.id.orig')}, '') <> ''"
    )
    kept = ", ".join(
        f"CASE WHEN is_truth THEN {_q(source)} END AS {column}"
        for column, source in SLIM_COLUMNS.items()
    )
    try:
        with duckdb.connect(config=limits.duckdb_config(scratch)) as con:
            con.execute(
                f"COPY (SELECT is_truth, {kept} FROM ("
                f" SELECT *, coalesce({truth}, false) AS is_truth FROM read_csv({literal(path)},"
                " header = true, all_varchar = true, quote = '\"', escape = '\"',"
                " nullstr = ['', '\\N'])"
                f")) TO {literal(staged)} (FORMAT parquet, COMPRESSION zstd)"
            )
            [(rows_read, truth_rows)] = con.execute(
                f"SELECT count(*), count(*) FILTER (is_truth) FROM read_parquet({literal(staged)})"
            ).fetchall()
            con.execute(
                f"""
                COPY (
                    SELECT * FROM (
                        SELECT
                            transaction_id,
                            cmte_id,
                            tran_id,
                            try_cast(amount AS DECIMAL(14,2)) AS amount,
                            try_cast(date AS DATE) AS date,
                            bonica_cid,
                            transaction_type,
                            contributor_name
                        FROM read_parquet({literal(staged)})
                        WHERE is_truth
                    )
                    WHERE amount IS NOT NULL AND date IS NOT NULL AND bonica_cid IS NOT NULL
                ) TO {literal(parquet)}
                (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE {ROW_GROUP_ROWS})
                """
            )
            [(rows_kept, cids)] = con.execute(
                f"SELECT count(*), count(DISTINCT bonica_cid) FROM read_parquet({literal(parquet)})"
            ).fetchall()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    # The Parquet first, so a bad file fails before the long upload of the raw one.
    store.put(parquet_key, parquet)
    store.put(raw_key, path)
    log.info("dime %d: %d rows read, %d kept", cycle, rows_read, rows_kept)
    return Imported(rows_read, rows_kept, truth_rows - rows_kept, cids, raw_key, parquet_key)


def newest_resolved(store: R2, cycle: int) -> str | None:
    """The newest build of `cycle` with a `resolved` marker, or None if there is none."""
    builds = {
        build
        for key in store.list_keys(paths.markers_dir(cycle))
        if key.endswith("/resolved.json") and (build := paths.build_of(key)) is not None
    }
    return max(builds) if builds else None


def score(con: duckdb.DuckDBPyConnection, records: str) -> Score:
    """The pairwise counts over the table `records`, one row per labelled key in the columns
    `donor_id` and `bonica_cid` (ADR-0009).

    From the contingency table n(donor_id, cid): correct pairs are Σ C(n(d,c), 2), predicted
    pairs Σ_d C(n(d,·), 2) and true pairs Σ_c C(n(·,c), 2).
    """
    [(keys, correct, predicted, true)] = con.execute(
        f"""
        WITH
            cell AS (SELECT count(*) AS n FROM {records} GROUP BY donor_id, bonica_cid),
            predicted AS (SELECT count(*) AS n FROM {records} GROUP BY donor_id),
            truth AS (SELECT count(*) AS n FROM {records} GROUP BY bonica_cid)
        SELECT
            (SELECT count(*) FROM {records}),
            (SELECT coalesce(sum(n * (n - 1) // 2), 0) FROM cell),
            (SELECT coalesce(sum(n * (n - 1) // 2), 0) FROM predicted),
            (SELECT coalesce(sum(n * (n - 1) // 2), 0) FROM truth)
        """
    ).fetchall()
    return Score(int(keys), int(correct), int(predicted), int(true))


def _local_dime(store: R2, cycle: int, *, data_dir: Path) -> Path:
    key = paths.reference_dime(DIME_VERSION, cycle)
    local = paths.local_path(data_dir, key)
    if local.exists():
        return local
    try:
        return store.download_to(key, local)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"no DIME v{DIME_VERSION} file for {cycle} in R2 ({key}): import it as {RUNBOOK} says"
        ) from exc


def _write(conn: Connection[TupleRow], result: Validated, validated_at: datetime) -> None:
    with conn.transaction():
        for scope, scored, top_limit in (
            ("overall", result.overall, None),
            ("top", result.top, result.top_limit),
        ):
            conn.execute(
                """
                INSERT INTO app.resolution_quality (
                    model_version, cycle, scope, dime_version, top_limit, contribution_rows,
                    matched_rows, labelled_keys, correct_pairs, predicted_pairs, true_pairs,
                    precision, recall, validated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (model_version, cycle, scope) DO UPDATE SET
                    dime_version = EXCLUDED.dime_version,
                    top_limit = EXCLUDED.top_limit,
                    contribution_rows = EXCLUDED.contribution_rows,
                    matched_rows = EXCLUDED.matched_rows,
                    labelled_keys = EXCLUDED.labelled_keys,
                    correct_pairs = EXCLUDED.correct_pairs,
                    predicted_pairs = EXCLUDED.predicted_pairs,
                    true_pairs = EXCLUDED.true_pairs,
                    precision = EXCLUDED.precision,
                    recall = EXCLUDED.recall,
                    validated_at = EXCLUDED.validated_at
                """,
                (
                    result.model_version,
                    result.cycle,
                    scope,
                    DIME_VERSION,
                    top_limit,
                    result.contribution_rows,
                    result.matched_rows,
                    scored.labelled_keys,
                    scored.correct_pairs,
                    scored.predicted_pairs,
                    scored.true_pairs,
                    scored.precision,
                    scored.recall,
                    validated_at,
                ),
            )


def validate(
    store: R2,
    *,
    cycle: int,
    model_version: str | None,
    top: int,
    data_dir: Path,
    limits: Limits,
    conn: Connection[TupleRow],
) -> Validated:
    """Score the newest resolved build of `cycle` against DIME and write the overall and top
    scopes to `app.resolution_quality` under `model_version` (the newest saved model when None)
    (NEU-2054 §5).

    Raises `FileNotFoundError` when the cycle has no resolved build, no model is saved, or R2
    has no DIME file for the cycle, and `NotResolved` when the build's contributions are not all
    resolved; in every case before anything is written. Re-running overwrites the same two rows.
    """
    if top < 1:
        raise ValueError(f"top {top} is not a positive number of donors")
    build_id = newest_resolved(store, cycle)
    if build_id is None:
        raise FileNotFoundError(f"no resolved build for {cycle}: run `fundlens resolve --full`")
    version = model_version or model.latest_version(store)
    if version is None:
        raise FileNotFoundError("no saved resolution model: run `fundlens resolve --full`")
    if not store.exists(paths.resolution_model(version)):
        # Figures under a model nobody saved are rows `load` never reads.
        raise FileNotFoundError(f"no saved resolution model {version}: see `resolution/model/`")
    dime = _local_dime(store, cycle, data_dir=data_dir)
    # A cached partition is read as it stands, as the crosswalk reads it: R2's may be a rewrite
    # that died part way.
    contributions = crosswalk.local_partition(
        store,
        paths.silver_partition("contribution", cycle, build_id),
        cycle=cycle,
        build_id=build_id,
        data_dir=data_dir,
    )
    scratch = paths.scratch_dir(data_dir)
    work = scratch / f"validate-{cycle}-{build_id}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        with duckdb.connect(config=limits.duckdb_config(scratch)) as con:
            indiv = CATALOGUE["indiv"]
            register_bulk(con, indiv, unzip_bulk(store, cycle, indiv, data_dir=data_dir, work=work))
            silver = (
                f"read_parquet({literal(contributions / '**' / '*.parquet')},"
                " hive_partitioning = false)"
            )
            con.execute(
                "CREATE TABLE silver AS SELECT source_record_id, contributor_key, donor_id,"
                f" amount, date FROM {silver}"
            )
            [(contribution_rows, unresolved)] = con.execute(
                "SELECT count(*), count(*) FILTER (donor_id IS NULL) FROM silver"
            ).fetchall()
            if unresolved:
                raise NotResolved(
                    f"build {build_id} of {cycle} is not resolved: {unresolved} contributions"
                    " have no donor_id; run `fundlens resolve --full`"
                )
            # Tables, not views, so the joins below are planned on real row counts.
            con.execute(
                "CREATE TABLE bronze AS SELECT SUB_ID AS sub_id, CMTE_ID AS cmte_id,"
                " TRAN_ID AS tran_id, abs(TRANSACTION_AMT) AS amount FROM indiv"
                " WHERE CMTE_ID IS NOT NULL AND TRAN_ID IS NOT NULL"
            )
            # Amounts meet by magnitude: a refund's sign is the filer's choice in FEC's bulk
            # file, and the committee and transaction ids already pin the row.
            con.execute(
                "CREATE TABLE dime AS SELECT DISTINCT cmte_id, tran_id, abs(amount) AS amount,"
                f" date, bonica_cid FROM read_parquet({literal(dime)})"
            )
            # The counted contributions with their FEC ids; `amount` is the dollars as counted.
            con.execute(
                """
                CREATE TABLE fec AS
                SELECT
                    s.source_record_id AS sub_id, b.cmte_id, b.tran_id, b.amount AS magnitude,
                    s.date, s.amount, s.contributor_key, s.donor_id
                FROM silver AS s
                JOIN bronze AS b ON b.sub_id = s.source_record_id
                """
            )
            # One cid per contribution, or nothing: a row DIME labels twice is ambiguous.
            con.execute(
                """
                CREATE TABLE matched AS
                SELECT f.sub_id, f.contributor_key, f.donor_id, f.amount,
                    any_value(d.bonica_cid) AS bonica_cid
                FROM fec AS f
                JOIN dime AS d
                    ON d.cmte_id = f.cmte_id AND d.tran_id = f.tran_id
                    AND d.amount = f.magnitude AND d.date = f.date
                GROUP BY f.sub_id, f.contributor_key, f.donor_id, f.amount
                HAVING count(DISTINCT d.bonica_cid) = 1
                """
            )
            [(matched_rows,)] = con.execute("SELECT count(*) FROM matched").fetchall()
            # The records scored: one per contributor key and the person DIME says it is.
            con.execute(
                "CREATE TABLE labelled AS SELECT contributor_key, donor_id, bonica_cid,"
                " sum(amount) AS amount FROM matched GROUP BY ALL"
            )
            con.execute(
                """
                CREATE TABLE labelled_top AS
                SELECT * FROM labelled
                WHERE bonica_cid IN (
                    SELECT bonica_cid FROM labelled GROUP BY bonica_cid
                    ORDER BY sum(amount) DESC, bonica_cid LIMIT ?
                )
                """,
                [top],
            )
            overall = score(con, "labelled")
            top_scored = score(con, "labelled_top")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    result = Validated(
        cycle,
        build_id,
        version,
        contribution_rows,
        matched_rows,
        top,
        overall,
        top_scored,
    )
    _write(conn, result, datetime.now(UTC))
    log.info(
        "validated %d build %s under model %s: %d of %d contributions matched",
        cycle,
        build_id,
        version,
        matched_rows,
        contribution_rows,
    )
    return result
