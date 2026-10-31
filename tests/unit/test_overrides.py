"""`resolution/overrides.yaml`: its schema, the rules it keeps by itself, the keys it names and how
it rewrites a run's clusters (spec §6.5). Checking `from` against the crosswalk, and the fixture
cycle's overrides end to end, are in `tests/integration/test_resolve.py`."""

from datetime import date
from pathlib import Path

import duckdb
import pytest

from fundlens.resolve import overrides
from fundlens.resolve.overrides import Applied, Merge, Overrides, OverridesError, Split, SplitKey

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMITTED = REPO_ROOT / "resolution" / "overrides.yaml"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "resolution" / "overrides.yaml"

MERGE = """
- merge: ["A|1||", "B|1||"]
  reason: one person
  added: 2026-10-31
"""
SPLIT = """
- split: {contributor_key: "C|2||", from: 7}
  reason: not that donor
  added: 2026-10-31
"""


def problems(document: str) -> list[str]:
    with pytest.raises(OverridesError) as raised:
        overrides.parse(document)
    return raised.value.problems


def test_the_committed_file_is_valid() -> None:
    # CI's check of every change to the file: a malformed one fails here, before any run reads it.
    overrides.load(COMMITTED)


def test_the_fixture_file_is_one_merge_and_one_split() -> None:
    loaded = overrides.load(FIXTURE)

    assert len(loaded.merges) == 1
    assert len(loaded.splits) == 1


def test_parses_merges_and_splits_in_file_order() -> None:
    loaded = overrides.parse(MERGE + SPLIT)

    assert loaded == Overrides(
        merges=(Merge(merge=["A|1||", "B|1||"], reason="one person", added=date(2026, 10, 31)),),
        splits=(
            Split(
                split=SplitKey.model_validate({"contributor_key": "C|2||", "from": 7}),
                reason="not that donor",
                added=date(2026, 10, 31),
            ),
        ),
    )
    assert loaded.keys() == {"A|1||", "B|1||", "C|2||"}


@pytest.mark.parametrize("document", ["", "[]", "# nothing yet\n"])
def test_an_empty_file_is_no_overrides(document: str) -> None:
    assert overrides.parse(document) == Overrides()


def test_a_key_in_two_merges_is_rejected() -> None:
    bad = (
        MERGE
        + """
- merge: ["B|1||", "D|1||"]
  reason: also one person
  added: 2026-10-31
"""
    )

    assert problems(bad) == ["'B|1||' is in merge 1 and merge 2"]


def test_the_committed_file_with_a_key_in_two_merges_is_rejected() -> None:
    # A bad copy of the committed file itself: what CI says when a PR lists a key twice.
    bad = COMMITTED.read_text().replace("[]\n", "") + MERGE + MERGE.replace("A|1||", "E|1||")

    assert problems(bad) == ["'B|1||' is in merge 1 and merge 2"]


def test_a_key_twice_in_one_merge_is_rejected() -> None:
    bad = MERGE.replace('"B|1||"', '"A|1||"')

    assert problems(bad) == ["'A|1||' is twice in merge 1"]


def test_a_key_split_twice_or_both_merged_and_split_is_rejected() -> None:
    bad = MERGE + SPLIT + SPLIT + SPLIT.replace("C|2||", "A|1||")

    assert problems(bad) == ["'C|2||' is split twice", "'A|1||' is both split and in merge 1"]


# The fields every entry carries besides its kind.
RA = "reason: r, added: 2026-10-31"


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ("merge: [A]", "the file: Input should be a valid list"),
        ("- [A, B]", "entry 1: an entry is either `merge:` or `split:`"),
        (f"- {{merge: [A|1], {RA}}}", "entry 1 merge: List should have at least 2 items"),
        ("- {merge: [A, B], added: 2026-10-31}", "entry 1 reason: Field required"),
        (
            "- {merge: [A, B], reason: ' ', added: 2026-10-31}",
            "entry 1 reason: String should have at least 1 character",
        ),
        (
            "- {merge: [A, B], reason: r, added: someday}",
            "entry 1 added: Input should be a valid date",
        ),
        (f"- {{merge: [A, B], {RA}, by: me}}", "entry 1 by: Extra inputs are not permitted"),
        (
            f"- {{split: {{contributor_key: A, from: 0}}, {RA}}}",
            "entry 1 split.from: Input should be greater than 0",
        ),
        (f"- {{split: {{contributor_key: A}}, {RA}}}", "entry 1 split.from: Field required"),
        (
            f"- {{merge: [A, B], {RA}}}\n- {{split: A, {RA}}}",
            "entry 2 split: Input should be a valid dictionary",
        ),
        ("- merge: [A, B]\n  reason: [r", "not YAML: "),
    ],
)
def test_a_malformed_entry_is_rejected_by_number_and_field(document: str, expected: str) -> None:
    assert any(problem.startswith(expected) for problem in problems(document)), problems(document)


def contributors(*keys: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("CREATE TABLE contributor (contributor_key VARCHAR)")
    con.executemany("INSERT INTO contributor VALUES (?)", [(key,) for key in keys])
    return con


def test_unknown_keys_are_those_the_run_does_not_hold() -> None:
    con = contributors("A|1||", "B|1||")

    assert overrides.unknown_keys(con, overrides.parse(MERGE + SPLIT)) == ["C|2||"]
    assert overrides.unknown_keys(con, overrides.parse(MERGE)) == []
    assert overrides.unknown_keys(con, Overrides()) == []


def clustered(groups: dict[str, list[str]]) -> duckdb.DuckDBPyConnection:
    """A working file's `cluster` table: each cluster id and its keys, each joined at 0.97."""
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE cluster (cluster_id VARCHAR, contributor_key VARCHAR,"
        " match_probability DOUBLE)"
    )
    con.executemany(
        "INSERT INTO cluster VALUES (?, ?, ?)",
        [
            (cluster_id, key, 0.97 if len(keys) > 1 else None)
            for cluster_id, keys in groups.items()
            for key in keys
        ],
    )
    return con


def partition(con: duckdb.DuckDBPyConnection) -> set[frozenset[str]]:
    rows = con.execute(
        "SELECT list(contributor_key ORDER BY contributor_key) FROM cluster GROUP BY cluster_id"
    ).fetchall()
    return {frozenset(keys) for (keys,) in rows}


def entries(*entries: str) -> Overrides:
    return overrides.parse("\n".join(entries))


def merge(*keys: str) -> str:
    return f"- {{merge: [{', '.join(repr(key) for key in keys)}], reason: r, added: 2026-10-31}}"


def split(key: str) -> str:
    return f"- {{split: {{contributor_key: {key!r}, from: 1}}, reason: r, added: 2026-10-31}}"


def test_a_merge_joins_every_key_of_every_cluster_it_names() -> None:
    con = clustered({"a": ["a1", "a2"], "b": ["b1"], "c": ["c1", "c2"]})

    applied = overrides.rewrite(con, entries(merge("a2", "b1")))

    assert partition(con) == {frozenset({"a1", "a2", "b1"}), frozenset({"c1", "c2"})}
    assert applied == Applied(merges=1, splits=0, clusters_joined=1)


def test_merges_naming_one_cluster_between_them_join_all_their_clusters() -> None:
    con = clustered({"a": ["a1", "a2"], "b": ["b1"], "c": ["c1"], "d": ["d1"]})

    applied = overrides.rewrite(con, entries(merge("c1", "a1"), merge("b1", "a2")))

    assert partition(con) == {frozenset({"a1", "a2", "b1", "c1"}), frozenset({"d1"})}
    assert applied.clusters_joined == 2


def test_a_merge_of_keys_already_clustered_together_changes_nothing() -> None:
    con = clustered({"a": ["a1", "a2"], "b": ["b1"]})

    applied = overrides.rewrite(con, entries(merge("a1", "a2")))

    assert partition(con) == {frozenset({"a1", "a2"}), frozenset({"b1"})}
    assert applied == Applied(merges=1, splits=0, clusters_joined=0)


def test_a_split_moves_its_key_alone_and_after_the_merges() -> None:
    con = clustered({"a": ["a", "a2"], "b": ["b1", "b2"]})

    # The key the cluster is named for leaves it: the others keep the name, the key gets another.
    applied = overrides.rewrite(con, entries(merge("a2", "b1"), split("a"), split("b2")))

    assert partition(con) == {frozenset({"a2", "b1"}), frozenset({"a"}), frozenset({"b2"})}
    assert con.execute(
        "SELECT cluster_id, match_probability FROM cluster WHERE contributor_key IN ('a', 'b2')"
        " ORDER BY 1"
    ).fetchall() == [("split:a", None), ("split:b2", None)]
    assert applied == Applied(merges=1, splits=2, clusters_joined=1)


def test_no_overrides_changes_nothing() -> None:
    con = clustered({"a": ["a1", "a2"]})

    assert overrides.rewrite(con, Overrides()) == Applied(0, 0, 0)
    assert partition(con) == {frozenset({"a1", "a2"})}
