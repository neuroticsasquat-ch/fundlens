"""What incremental resolution builds on (spec §6.10, NEU-2062): a working file whose clusters are
the crosswalk's donors, made with the live model, and cleared of whatever a run that died before
its crosswalk committed left in it."""

import duckdb
import pytest

from fundlens.resolve import runner

# The private checks `resolve_incremental` makes before it links anything.
forget_unknown = runner._forget_unknown  # pyright: ignore[reportPrivateUsage]
check_baseline = runner._check_baseline  # pyright: ignore[reportPrivateUsage]
check_stamp = runner._check_stamp  # pyright: ignore[reportPrivateUsage]
stamp = runner._stamp  # pyright: ignore[reportPrivateUsage]

CYCLE = 2026


def working_file(
    clusters: dict[str, str], known: dict[str, int], first_cycles: dict[str, int] | None = None
) -> duckdb.DuckDBPyConnection:
    """A working file whose keys are `clusters`' (first seen in `CYCLE` unless `first_cycles`
    says otherwise; components and unadjudicated clusters as the clusters), an edge between each
    key and the next, and the crosswalk `known` as the temp table `known`."""
    con = duckdb.connect()
    keys = sorted(clusters)
    cycles = first_cycles or {}
    con.execute(
        "CREATE TABLE contributor AS SELECT unnest($keys::VARCHAR[]) AS contributor_key,"
        " unnest($cycles::INTEGER[]) AS first_cycle",
        {"keys": keys, "cycles": [cycles.get(key, CYCLE) for key in keys]},
    )
    for table in ("cluster", "component", "unadjudicated"):
        con.execute(
            f"CREATE TABLE {table} AS SELECT unnest($ids::VARCHAR[]) AS cluster_id,"
            " unnest($keys::VARCHAR[]) AS contributor_key",
            {"keys": keys, "ids": [clusters[key] for key in keys]},
        )
    con.execute(
        "CREATE TABLE edge AS SELECT unnest($l::VARCHAR[]) AS contributor_key_l,"
        " unnest($r::VARCHAR[]) AS contributor_key_r, 0.99 AS match_probability",
        {"l": keys[:-1], "r": keys[1:]},
    )
    con.execute(
        "CREATE TEMP TABLE known AS SELECT unnest($keys::VARCHAR[]) AS contributor_key,"
        " unnest($ids::BIGINT[]) AS donor_id",
        {"keys": list(known), "ids": list(known.values())},
    )
    return con


def test_keys_the_crosswalk_never_gave_an_id_are_forgotten_with_their_edges_and_names() -> None:
    # `a` is the key a dead run left; an override in that run named the cluster after it.
    con = working_file({"a": "a", "b": "a", "c": "a"}, {"b": 1, "c": 1})

    assert forget_unknown(con, CYCLE) == 1

    for table in ("cluster", "component", "unadjudicated"):
        rows = con.execute(f"SELECT contributor_key, cluster_id FROM {table} ORDER BY 1").fetchall()
        assert rows == [("b", "b"), ("c", "b")], table
    keys = {key for (key,) in con.execute("SELECT contributor_key FROM contributor").fetchall()}
    assert keys == {"b", "c"}
    assert con.execute("SELECT contributor_key_l, contributor_key_r FROM edge").fetchall() == [
        ("b", "c")
    ]
    check_baseline(con)


def test_a_key_of_another_cycle_the_crosswalk_lacks_is_no_baseline_and_nothing_is_forgotten() -> (
    None
):
    con = working_file({"a": "a", "b": "a"}, {"b": 1}, first_cycles={"a": 2024})

    with pytest.raises(runner.NoBaseline, match="keys of other cycles"):
        forget_unknown(con, CYCLE)

    assert con.execute("SELECT count(*) FROM contributor").fetchall() == [(2,)]


@pytest.mark.parametrize(
    ("clusters", "known"),
    [
        # A cluster joining two donors: a run that died before its crosswalk merged them.
        ({"a": "a", "b": "a"}, {"a": 1, "b": 2}),
        # A donor across two clusters: one that split it.
        ({"a": "a", "b": "b"}, {"a": 1, "b": 1}),
    ],
)
def test_clusters_that_are_not_the_crosswalks_donors_are_no_baseline(
    clusters: dict[str, str], known: dict[str, int]
) -> None:
    con = working_file(clusters, known)

    with pytest.raises(runner.NoBaseline, match="resolve --full"):
        check_baseline(con)


def test_a_working_file_resolved_with_a_model_that_is_not_live_is_no_baseline() -> None:
    con = duckdb.connect()
    stamp(con, "20261115T030000Z")
    tables = {"resolved_with"}

    check_stamp(con, "20261115T030000Z", tables)
    with pytest.raises(runner.NoBaseline, match="--model 20261115T030000Z"):
        check_stamp(con, "20261101T030000Z", tables)
    # A working file from before the stamp: the backfill's, which finished.
    check_stamp(con, "20261101T030000Z", set())
