"""`fundlens diagnose`: the working file's wrong pairs against DIME, taken apart (NEU-2182).

Validation counts the wrong pairs; it does not say which they are. `diagnose` builds the labelled
records `validate --clusters` scores, through the same function (`validate.label`), so the
matching rules are the same: whole dollars, one `cid` per contribution. It then lists every pair
of labelled keys in one cluster, wrong when DIME gives the two another person, and counts the
wrong and correct pairs by the cluster's size and matched dollars, by how the pair was joined
(the same key, an `edge` between the keys by probability band, or a chain), by the field
agreement of a direct pair, and by how many keys share its name; with a sample of wrong pairs to
classify by hand. It reads the working file and DIME and writes nothing: no Postgres, R2 or
crosswalk.
"""

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import duckdb

from fundlens import paths
from fundlens.r2 import R2
from fundlens.resolve.cluster import CLUSTER_TABLE, EDGE_TABLE
from fundlens.resolve.model import FIRST_NAME_VETO_JW, initial_pair_sql, nickname_pair_sql
from fundlens.resolve.validate import check_clusters, label, newest_resolved
from fundlens.transform.runner import Limits, literal

CONTRIBUTOR_TABLE = "contributor"

# The bands each breakdown reports, in order, every one even when it holds no pair.
SIZE_BANDS = ("1", "2", "3–5", "6–10", "11–25", "26–50", "51–200", "> 200")
DOLLAR_BANDS = ("< $1k", "$1k–10k", "$10k–50k", "≥ $50k")
LINK_BANDS = (
    "same key",
    "direct < 0.95",
    "direct 0.95–0.99",
    "direct 0.99–0.999",
    "direct ≥ 0.999",
    "chained",
)
NAME_BANDS = ("1", "2–10", "11–100", "> 100")

# How many field-agreement patterns of direct wrong pairs are reported, most wrong pairs first.
TOP_PATTERNS = 20
# The sample is drawn from clusters of this many keys or fewer: the wrong pairs a cap cannot cut.
SAMPLE_MAX_KEYS = 50

_SIZE_BAND = """
    CASE
        WHEN keys = 1 THEN '1'
        WHEN keys = 2 THEN '2'
        WHEN keys <= 5 THEN '3–5'
        WHEN keys <= 10 THEN '6–10'
        WHEN keys <= 25 THEN '11–25'
        WHEN keys <= 50 THEN '26–50'
        WHEN keys <= 200 THEN '51–200'
        ELSE '> 200'
    END
"""
_DOLLAR_BAND = """
    CASE
        WHEN dollars < 1000 THEN '< $1k'
        WHEN dollars < 10000 THEN '$1k–10k'
        WHEN dollars < 50000 THEN '$10k–50k'
        ELSE '≥ $50k'
    END
"""
_LINK_BAND = """
    CASE
        WHEN key_a = key_b THEN 'same key'
        WHEN probability IS NULL THEN 'chained'
        WHEN probability < 0.95 THEN 'direct < 0.95'
        WHEN probability < 0.99 THEN 'direct 0.95–0.99'
        WHEN probability < 0.999 THEN 'direct 0.99–0.999'
        ELSE 'direct ≥ 0.999'
    END
"""
_NAME_BAND = """
    CASE
        WHEN name_keys = 1 THEN '1'
        WHEN name_keys <= 10 THEN '2–10'
        WHEN name_keys <= 100 THEN '11–100'
        ELSE '> 100'
    END
"""


def _null_or(field: str, levels: str) -> str:
    return f"CASE WHEN a.{field} IS NULL OR b.{field} IS NULL THEN 'null' {levels} END"


_NICKNAME = nickname_pair_sql(
    "a.first_name", "a.first_name_nicknames", "b.first_name", "b.first_name_nicknames"
)
# The level of each field a direct pair's pattern reports: the model's first-name levels
# (`model._first_name`) in its order, and the others' as NEU-2182 names them.
_LEVELS = {
    "first_name": _null_or(
        "first_name",
        "WHEN a.first_name = b.first_name THEN 'exact'"
        f" WHEN {_NICKNAME} THEN 'nickname'"
        " WHEN jaro_winkler_similarity(a.first_name, b.first_name) >= 0.92 THEN 'jw ≥ 0.92'"
        " WHEN jaro_winkler_similarity(a.first_name, b.first_name) >= $veto THEN 'jw ≥ 0.8'"
        f" WHEN {initial_pair_sql('a.first_name', 'b.first_name')} THEN 'initial only'"
        " ELSE 'other'",
    ),
    "last_name": _null_or("last_name", "WHEN a.last_name = b.last_name THEN 'exact' ELSE 'differ'"),
    "zip5": _null_or("zip5", "WHEN a.zip5 = b.zip5 THEN 'exact' ELSE 'differ'"),
    "employer": _null_or(
        "employer_norm", "WHEN a.employer_norm = b.employer_norm THEN 'exact' ELSE 'differ'"
    ),
    "occupation": _null_or(
        "occupation_norm", "WHEN a.occupation_norm = b.occupation_norm THEN 'same' ELSE 'differ'"
    ),
}
FIELDS = tuple(_LEVELS)

# A sampled key's fields, as `Side.fields` holds them.
SIDE_COLUMNS = (
    "first_name",
    "last_name",
    "zip5",
    "city",
    "state",
    "employer_norm",
    "occupation_norm",
)


@dataclass(frozen=True)
class Band:
    """The wrong and correct pairs in one band of a breakdown."""

    label: str
    wrong: int
    correct: int

    @property
    def precision(self) -> float | None:
        total = self.wrong + self.correct
        return self.correct / total if total else None


@dataclass(frozen=True)
class Pattern:
    """One field-agreement pattern of direct pairs: a level per one of `FIELDS`."""

    levels: tuple[str, ...]
    wrong: int
    correct: int


@dataclass(frozen=True)
class Side:
    """One key of a sampled pair: its `SIDE_COLUMNS` and the person DIME says it is."""

    contributor_key: str
    bonica_cid: str
    fields: tuple[str | None, ...]


@dataclass(frozen=True)
class Sampled:
    """A wrong pair to classify by hand."""

    cluster_id: str
    keys: int
    link: str
    a: Side
    b: Side


@dataclass(frozen=True)
class Breakdown:
    """The wrong and correct pairs of a working file's clusters, taken apart."""

    predicted: int
    correct: int
    by_size: list[Band]
    by_dollars: list[Band]
    by_link: list[Band]
    patterns: list[Pattern]
    by_name: list[Band]
    sample: list[Sampled]

    @property
    def wrong(self) -> int:
        return self.predicted - self.correct


@dataclass(frozen=True)
class Diagnosis:
    """What `diagnose` read, and the breakdown."""

    cycle: int
    build_id: str
    contribution_rows: int
    matched_rows: int
    breakdown: Breakdown


def _bands(con: duckdb.DuckDBPyConnection, column: str, order: Sequence[str]) -> list[Band]:
    counts = {
        band: (wrong, correct)
        for band, wrong, correct in con.execute(
            f"SELECT {column}, count(*) FILTER (NOT correct), count(*) FILTER (correct)"
            f" FROM pair GROUP BY {column}"
        ).fetchall()
    }
    return [Band(band, *counts.get(band, (0, 0))) for band in order]


def breakdown(con: duckdb.DuckDBPyConnection, *, run: str, sample: int = 0) -> Breakdown:
    """Take apart the pairs of the table `labelled(contributor_key, donor_id, bonica_cid, amount)`
    on `con`, whose `donor_id` is the working file's `cluster_id`; `run` is the schema holding the
    working file's `cluster`, `edge` and `contributor` tables. With `sample`, that many wrong
    pairs from clusters of `SAMPLE_MAX_KEYS` keys or fewer, in a fixed order.

    A pair is two labelled keys in one cluster, so the pairs are those `validate.score` counts:
    correct when DIME gives both one `cid`. A key DIME gives two `cid`s is two labelled keys, a
    wrong pair of the same key. A direct pair's keys have an `edge`; a chained pair's have none.
    """
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE pair AS
        WITH
            size AS (
                SELECT cluster_id, count(*) AS keys FROM {run}.{CLUSTER_TABLE} GROUP BY cluster_id
            ),
            dollars AS (
                SELECT donor_id AS cluster_id, sum(amount) AS dollars FROM labelled
                GROUP BY donor_id
            ),
            name AS (
                SELECT first_name, last_name, count(*) AS name_keys
                FROM {run}.{CONTRIBUTOR_TABLE} GROUP BY ALL
            ),
            joined AS (
                SELECT
                    l.donor_id AS cluster_id,
                    l.contributor_key AS key_a,
                    r.contributor_key AS key_b,
                    l.bonica_cid AS cid_a,
                    r.bonica_cid AS cid_b,
                    l.bonica_cid = r.bonica_cid AS correct
                FROM labelled AS l
                JOIN labelled AS r
                    ON r.donor_id = l.donor_id
                    AND (
                        l.contributor_key < r.contributor_key
                        OR (l.contributor_key = r.contributor_key AND l.bonica_cid < r.bonica_cid)
                    )
            ),
            measured AS (
                SELECT
                    j.*,
                    size.keys,
                    dollars.dollars,
                    e.match_probability AS probability,
                    -- The commoner of the two keys' names.
                    greatest(na.name_keys, nb.name_keys) AS name_keys,
                    {", ".join(f"{sql} AS {field}" for field, sql in _LEVELS.items())}
                FROM joined AS j
                JOIN size USING (cluster_id)
                JOIN dollars USING (cluster_id)
                JOIN {run}.{CONTRIBUTOR_TABLE} AS a ON a.contributor_key = j.key_a
                JOIN {run}.{CONTRIBUTOR_TABLE} AS b ON b.contributor_key = j.key_b
                LEFT JOIN {run}.{EDGE_TABLE} AS e
                    ON e.contributor_key_l = j.key_a AND e.contributor_key_r = j.key_b
                LEFT JOIN name AS na
                    ON na.first_name IS NOT DISTINCT FROM a.first_name
                    AND na.last_name IS NOT DISTINCT FROM a.last_name
                LEFT JOIN name AS nb
                    ON nb.first_name IS NOT DISTINCT FROM b.first_name
                    AND nb.last_name IS NOT DISTINCT FROM b.last_name
            )
        SELECT
            *,
            {_SIZE_BAND} AS size_band,
            {_DOLLAR_BAND} AS dollar_band,
            {_LINK_BAND} AS link_band,
            {_NAME_BAND} AS name_band
        FROM measured
        """,
        {"veto": FIRST_NAME_VETO_JW},
    )
    [(predicted, correct)] = con.execute(
        "SELECT count(*), count(*) FILTER (correct) FROM pair"
    ).fetchall()
    fields = ", ".join(FIELDS)
    patterns = [
        Pattern(tuple(row[: len(FIELDS)]), row[-2], row[-1])
        for row in con.execute(
            f"""
            SELECT {fields}, count(*) FILTER (NOT correct) AS wrong,
                count(*) FILTER (correct) AS correct
            FROM pair
            WHERE key_a <> key_b AND probability IS NOT NULL
            GROUP BY {fields}
            HAVING count(*) FILTER (NOT correct) > 0
            ORDER BY wrong DESC, {fields}
            LIMIT {TOP_PATTERNS}
            """
        ).fetchall()
    ]
    sampled: list[Sampled] = []
    if sample:
        sides = ", ".join(
            f"a.{column} AS a_{column}, b.{column} AS b_{column}" for column in SIDE_COLUMNS
        )
        for row in con.execute(
            f"""
            SELECT p.cluster_id, p.keys, p.link_band, p.key_a, p.cid_a, p.key_b, p.cid_b, {sides}
            FROM pair AS p
            JOIN {run}.{CONTRIBUTOR_TABLE} AS a ON a.contributor_key = p.key_a
            JOIN {run}.{CONTRIBUTOR_TABLE} AS b ON b.contributor_key = p.key_b
            WHERE NOT p.correct AND p.keys <= {SAMPLE_MAX_KEYS}
            -- A hash, not random(): the same working file draws the same sample.
            ORDER BY hash(p.key_a, p.cid_a, p.key_b, p.cid_b), p.key_a, p.cid_a, p.key_b, p.cid_b
            LIMIT $n
            """,
            {"n": sample},
        ).fetchall():
            cluster_id, keys, link, key_a, cid_a, key_b, cid_b, *values = row
            sampled.append(
                Sampled(
                    cluster_id,
                    keys,
                    link,
                    Side(key_a, cid_a, tuple(values[0::2])),
                    Side(key_b, cid_b, tuple(values[1::2])),
                )
            )
    result = Breakdown(
        predicted=predicted,
        correct=correct,
        by_size=_bands(con, "size_band", SIZE_BANDS),
        by_dollars=_bands(con, "dollar_band", DOLLAR_BANDS),
        by_link=_bands(con, "link_band", LINK_BANDS),
        patterns=patterns,
        by_name=_bands(con, "name_band", NAME_BANDS),
        sample=sampled,
    )
    con.execute("DROP TABLE pair")
    return result


def diagnose(
    store: R2,
    *,
    cycle: int,
    data_dir: Path,
    limits: Limits,
    working_file: Path,
    sample: int = 0,
) -> Diagnosis:
    """Take apart the wrong pairs of the working file's clusters against DIME for the newest
    resolved build of `cycle` (`breakdown`). Writes nothing.

    Raises `FileNotFoundError` when the cycle has no resolved build, the working file holds no
    `cluster`, `edge` or `contributor` table, or R2 has no DIME file for the cycle, and
    `validate.NotResolved` when a labelled key is in no cluster.
    """
    if sample < 0:
        raise ValueError(f"sample {sample} is not a number of pairs")
    build_id = newest_resolved(store, cycle)
    if build_id is None:
        raise FileNotFoundError(f"no resolved build for {cycle}: run `fundlens resolve --full`")
    check_clusters(working_file, (CLUSTER_TABLE, EDGE_TABLE, CONTRIBUTOR_TABLE))
    scratch = paths.scratch_dir(data_dir)
    work = scratch / f"diagnose-{cycle}-{build_id}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        with duckdb.connect(config=limits.duckdb_config(scratch)) as con:
            contribution_rows, matched_rows = label(
                con,
                store,
                cycle=cycle,
                build_id=build_id,
                data_dir=data_dir,
                work=work,
                clusters=working_file,
            )
            con.execute(f"ATTACH {literal(working_file)} AS run (READ_ONLY)")
            result = breakdown(con, run="run", sample=sample)
            con.execute("DETACH run")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return Diagnosis(cycle, build_id, contribution_rows, matched_rows, result)
