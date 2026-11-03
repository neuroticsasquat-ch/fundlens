"""`diagnose`'s breakdown of wrong pairs (NEU-2182), on a working file and labelled keys made up
here, with the wrong pairs planted where each breakdown should find them."""

import duckdb
import pytest

from fundlens.resolve.diagnose import Band, Pattern, breakdown
from fundlens.resolve.validate import score

CONTRIBUTOR_COLUMNS = (
    "contributor_key",
    "first_name",
    "last_name",
    "first_initial",
    "zip5",
    "city",
    "state",
    "employer_norm",
    "occupation_norm",
)

# A key's first and last name, employer and the cluster it is in.
type Key = tuple[str | None, str, str | None, str]

# Every key gives from 21201, BALTIMORE MD, as an ENGINEER.
KEYS: dict[str, Key] = {
    # A direct wrong pair: two keys, $500, an edge at 0.97.
    "a1": ("JOHN", "SMITH", "ACME", "a1"),
    "a2": ("JOHN", "SMITH", None, "a1"),
    # A chained wrong pair: three keys, $60,000, joined only through the unlabelled b2.
    "b1": ("BEATRICE", "QUINLAN", "ACME", "b1"),
    "b2": (None, "QUINLAN", "ACME", "b1"),
    "b3": ("DESMOND", "QUINLAN", "ACME", "b1"),
    # A key DIME gives two people: one key, $3,000.
    "c1": ("MARY", "JONES", "ACME", "c1"),
    # A correct direct pair with the direct wrong pair's pattern: two keys, $15,000.
    "d1": ("JOHN", "SMITH", "ACME", "d1"),
    "d2": ("JOHN", "SMITH", None, "d1"),
    # A chained wrong pair in a cluster over the sample's 50 keys: $200.
    **{f"e{n:02d}": (f"NAME{n:02d}", "LEE", "ACME", "e00") for n in range(51)},
}
EDGES = [
    ("a1", "a2", 0.97),
    ("b1", "b2", 0.9995),
    ("b2", "b3", 0.96),
    ("d1", "d2", 0.9999),
    *((f"e{n:02d}", f"e{n + 1:02d}", 0.99) for n in range(2, 50)),
]
# Each labelled key: the key, the person DIME says it is, and its matched dollars.
LABELLED = [
    ("a1", "X", 200),
    ("a2", "Y", 300),
    ("b1", "P", 40_000),
    ("b3", "Q", 20_000),
    ("c1", "R", 1_000),
    ("c1", "S", 2_000),
    ("d1", "T", 7_000),
    ("d2", "T", 8_000),
    ("e00", "U", 100),
    ("e01", "V", 100),
]


def working_file(
    con: duckdb.DuckDBPyConnection,
    keys: dict[str, Key],
    edges: list[tuple[str, str, float]],
    labelled: list[tuple[str, str, int]],
) -> None:
    """The working file's tables under `run`, and `labelled` as `validate.label` writes it."""
    con.execute("ATTACH ':memory:' AS run")
    con.execute(
        "CREATE TABLE run.contributor ("
        + ", ".join(f"{column} VARCHAR" for column in CONTRIBUTOR_COLUMNS)
        + ")"
    )
    con.executemany(
        "INSERT INTO run.contributor"
        " VALUES (?, ?, ?, ?, '21201', 'BALTIMORE', 'MD', ?, 'ENGINEER')",
        [
            [key, first, last, first[0] if first else None, employer]
            for key, (first, last, employer, _) in keys.items()
        ],
    )
    con.execute(
        "CREATE TABLE run.cluster (cluster_id VARCHAR, contributor_key VARCHAR,"
        " match_probability DOUBLE)"
    )
    con.executemany(
        "INSERT INTO run.cluster VALUES (?, ?, NULL)",
        [[cluster_id, key] for key, (*_, cluster_id) in keys.items()],
    )
    con.execute(
        "CREATE TABLE run.edge (contributor_key_l VARCHAR, contributor_key_r VARCHAR,"
        " match_probability DOUBLE)"
    )
    con.executemany("INSERT INTO run.edge VALUES (?, ?, ?)", [list(edge) for edge in edges])
    con.execute(
        "CREATE TABLE labelled (contributor_key VARCHAR, donor_id VARCHAR, bonica_cid VARCHAR,"
        " amount DECIMAL(14,2))"
    )
    con.executemany(
        "INSERT INTO labelled VALUES (?, ?, ?, ?)",
        [[key, keys[key][3], cid, amount] for key, cid, amount in labelled],
    )


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    working_file(con, KEYS, EDGES, LABELLED)
    return con


def bands(found: list[Band]) -> dict[str, tuple[int, int]]:
    """Each band holding a pair, and its wrong and correct pairs."""
    return {band.label: (band.wrong, band.correct) for band in found if band.wrong or band.correct}


def test_each_planted_pair_is_in_its_size_dollar_link_and_name_band(
    con: duckdb.DuckDBPyConnection,
) -> None:
    found = breakdown(con, run="run")

    assert (found.predicted, found.correct, found.wrong) == (5, 1, 4)
    assert bands(found.by_size) == {"1": (1, 0), "2": (1, 1), "3–5": (1, 0), "51–200": (1, 0)}
    assert bands(found.by_dollars) == {
        "< $1k": (2, 0),
        "$1k–10k": (1, 0),
        "$10k–50k": (0, 1),
        "≥ $50k": (1, 0),
    }
    assert bands(found.by_link) == {
        "same key": (1, 0),
        "direct 0.95–0.99": (1, 0),
        "direct ≥ 0.999": (0, 1),
        "chained": (2, 0),
    }
    # JOHN SMITH is four keys; every other name is one.
    assert bands(found.by_name) == {"1": (3, 0), "2–10": (1, 1)}
    # Every band is listed, in order, even those holding no pair.
    assert [band.label for band in found.by_size][-2:] == ["51–200", "> 200"]


def test_the_breakdown_counts_the_pairs_validate_scores(con: duckdb.DuckDBPyConnection) -> None:
    scored = score(con, "labelled")

    found = breakdown(con, run="run")

    assert (found.predicted, found.correct) == (scored.predicted_pairs, scored.correct_pairs)


def test_a_direct_wrong_pair_is_counted_by_its_pattern_beside_the_correct_pairs_sharing_it(
    con: duckdb.DuckDBPyConnection,
) -> None:
    found = breakdown(con, run="run")

    assert found.patterns == [Pattern(("exact", "exact", "exact", "null", "same"), 1, 1)]


def test_the_sample_is_the_wrong_pairs_of_clusters_of_fifty_keys_or_fewer_in_a_fixed_order(
    con: duckdb.DuckDBPyConnection,
) -> None:
    found = breakdown(con, run="run", sample=10)
    again = breakdown(con, run="run", sample=10)

    assert {
        (pair.a.contributor_key, pair.b.contributor_key, pair.link) for pair in found.sample
    } == {
        ("a1", "a2", "direct 0.95–0.99"),
        ("b1", "b3", "chained"),
        ("c1", "c1", "same key"),
    }
    assert found.sample == again.sample
    [chained] = [pair for pair in found.sample if pair.link == "chained"]
    assert (chained.cluster_id, chained.keys) == ("b1", 3)
    assert (chained.a.bonica_cid, chained.b.bonica_cid) == ("P", "Q")
    assert chained.a.fields == (
        "BEATRICE",
        "QUINLAN",
        "21201",
        "BALTIMORE",
        "MD",
        "ACME",
        "ENGINEER",
    )
    assert len(breakdown(con, run="run", sample=2).sample) == 2
    assert breakdown(con, run="run").sample == []


@pytest.mark.parametrize(
    ("left", "right", "level"),
    [
        ("JOHN", "JOHN", "exact"),
        ("ELIZABETH", "ELISABETH", "jw ≥ 0.92"),
        ("CARL", "KARL", "jw ≥ 0.8"),
        ("E", "EDWARD", "initial only"),
        (None, "KIRSTEN", "null"),
        ("BEATRICE", "DESMOND", "other"),
    ],
)
def test_a_first_name_level_is_the_models(left: str | None, right: str, level: str) -> None:
    con = duckdb.connect()
    keys: dict[str, Key] = {
        "l": (left, "QUINLAN", "ACME", "l"),
        "r": (right, "QUINLAN", "ACME", "l"),
    }
    working_file(con, keys, [("l", "r", 0.99)], [("l", "X", 100), ("r", "Y", 100)])

    [pattern] = breakdown(con, run="run").patterns

    assert pattern.levels[0] == level
