"""The crosswalk's assignment rules (spec §6.6, ADR-0005) on clusters made up here, against a
migrated `app` schema: what each run of `crosswalk.assign` gives every contributor key, and the
redirects it leaves. The fixture cycle's own run is in `test_resolve.py`."""

import random
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import duckdb
import psycopg
import pytest

from fundlens import paths
from fundlens.r2 import R2
from fundlens.resolve import crosswalk

FIRST = "20261031T040000Z"
SECOND = "20261107T040000Z"
THIRD = "20261114T040000Z"

# Each run's clusters: cluster id → {contributor key: its contribution dollars}.
type Clusters = Mapping[str, Mapping[str, float]]


@pytest.fixture
def conn(migrated_db: str) -> Iterator[psycopg.Connection[Any]]:
    # Autocommit, as the CLI's: each `assign` is a transaction of its own.
    with psycopg.connect(migrated_db, autocommit=True) as connection:
        yield connection


def working(clusters: Clusters) -> duckdb.DuckDBPyConnection:
    """A working file's `cluster` and `contributor` tables, as `resolve --full` leaves them."""
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE cluster (cluster_id VARCHAR, contributor_key VARCHAR,"
        " match_probability DOUBLE)"
    )
    con.execute("CREATE TABLE contributor (contributor_key VARCHAR, amount_total DECIMAL(18, 2))")
    for cluster_id, members in clusters.items():
        for key, amount in members.items():
            con.execute("INSERT INTO cluster VALUES (?, ?, NULL)", [cluster_id, key])
            con.execute("INSERT INTO contributor VALUES (?, ?)", [key, amount])
    return con


def assign(
    conn: psycopg.Connection[Any], clusters: Clusters, scratch: Path, build_id: str = FIRST
) -> crosswalk.Assigned:
    with working(clusters) as con:
        return crosswalk.assign(con, conn, build_id=build_id, scratch=scratch)


def donor_ids(conn: psycopg.Connection[Any]) -> dict[str, int]:
    return dict(conn.execute("SELECT contributor_key, donor_id FROM app.crosswalk").fetchall())


def rows(conn: psycopg.Connection[Any]) -> list[tuple[Any, ...]]:
    return conn.execute("SELECT * FROM app.crosswalk ORDER BY contributor_key").fetchall()


def redirects(conn: psycopg.Connection[Any]) -> dict[int, int]:
    return dict(conn.execute("SELECT old_donor_id, donor_id FROM app.donor_redirect").fetchall())


def sequence(conn: psycopg.Connection[Any]) -> tuple[int, bool]:
    row = conn.execute("SELECT last_value, is_called FROM app.donor_id_seq").fetchone()
    assert row is not None
    return row[0], row[1]


def test_each_new_cluster_gets_one_id_of_its_own(
    conn: psycopg.Connection[Any], tmp_path: Path
) -> None:
    result = assign(conn, {"a": {"A1": 100, "A2": 50}, "b": {"B": 10}}, tmp_path)

    ids = donor_ids(conn)
    assert ids["A1"] == ids["A2"] != ids["B"]
    assert result == crosswalk.Assigned(keys=3, new_donors=2, repointed=0, redirects=0)
    assert sequence(conn) == (max(ids.values()), True)
    assert not tmp_path.joinpath(f"crosswalk-{FIRST}").exists()


def test_assigning_the_same_clusters_again_changes_nothing_and_draws_no_id(
    conn: psycopg.Connection[Any], tmp_path: Path
) -> None:
    assign(conn, {"a": {"A1": 100, "A2": 50}, "b": {"B": 10}, "c": {"C": 5}}, tmp_path)
    before, drawn = rows(conn), sequence(conn)

    # Cluster ids are one run's: the same keys under other names are the same clusters.
    again = {"x": {"C": 5}, "y": {"B": 10}, "z": {"A2": 50, "A1": 100}}
    result = assign(conn, again, tmp_path, SECOND)

    assert rows(conn) == before
    assert sequence(conn) == drawn
    assert result == crosswalk.Assigned(keys=4, new_donors=0, repointed=0, redirects=0)


@pytest.mark.parametrize(("a", "b"), [(100, 10), (10, 100)])
def test_a_merge_keeps_the_heavier_id_and_redirects_the_other(
    conn: psycopg.Connection[Any], tmp_path: Path, a: float, b: float
) -> None:
    assign(conn, {"a": {"A": a}, "b": {"B": b}}, tmp_path)
    first = donor_ids(conn)
    heavier, lighter = ("A", "B") if a > b else ("B", "A")

    result = assign(conn, {"ab": {"A": a, "B": b}}, tmp_path, SECOND)

    assert donor_ids(conn) == {"A": first[heavier], "B": first[heavier]}
    assert redirects(conn) == {first[lighter]: first[heavier]}
    assert result == crosswalk.Assigned(keys=2, new_donors=0, repointed=1, redirects=1)


def test_a_key_moving_to_another_cluster_is_repointed_and_both_ids_stay(
    conn: psycopg.Connection[Any], tmp_path: Path
) -> None:
    assign(conn, {"a": {"A1": 100, "A2": 5}, "b": {"B": 50}}, tmp_path)
    first = donor_ids(conn)

    result = assign(conn, {"a": {"A1": 100}, "b": {"B": 50, "A2": 5}}, tmp_path, SECOND)

    assert donor_ids(conn) == {"A1": first["A1"], "A2": first["B"], "B": first["B"]}
    assert redirects(conn) == {}
    assert result.repointed == 1
    assert result.new_donors == 0


def test_a_split_gives_the_lighter_half_exactly_one_new_id(
    conn: psycopg.Connection[Any], tmp_path: Path
) -> None:
    assign(conn, {"a": {"A1": 100, "A2": 30, "A3": 10}}, tmp_path)
    first = donor_ids(conn)
    drawn, _ = sequence(conn)

    result = assign(conn, {"x": {"A1": 100}, "y": {"A2": 30, "A3": 10}}, tmp_path, SECOND)

    ids = donor_ids(conn)
    assert ids["A1"] == first["A1"]
    assert ids["A2"] == ids["A3"] == drawn + 1
    assert sequence(conn) == (drawn + 1, True)
    assert redirects(conn) == {}
    assert result == crosswalk.Assigned(keys=3, new_donors=1, repointed=2, redirects=0)


def test_a_split_and_a_merge_at_once_keep_every_id_with_its_dollars(
    conn: psycopg.Connection[Any], tmp_path: Path
) -> None:
    assign(conn, {"a": {"A1": 100, "A2": 30}, "b": {"B": 60}}, tmp_path)
    first = donor_ids(conn)

    # A2 leaves A for B, which outweighs it: B keeps its id and A keeps A1's.
    assign(conn, {"x": {"A1": 100}, "y": {"A2": 30, "B": 60}}, tmp_path, SECOND)

    assert donor_ids(conn) == {"A1": first["A1"], "A2": first["B"], "B": first["B"]}
    assert redirects(conn) == {}


def test_redirects_resolve_in_one_hop_after_successive_merges(
    conn: psycopg.Connection[Any], tmp_path: Path
) -> None:
    assign(conn, {"a": {"A": 10}, "b": {"B": 20}, "c": {"C": 100}}, tmp_path)
    first = donor_ids(conn)
    assign(conn, {"ab": {"A": 10, "B": 20}, "c": {"C": 100}}, tmp_path, SECOND)
    assert redirects(conn) == {first["A"]: first["B"]}

    assign(conn, {"abc": {"A": 10, "B": 20, "C": 100}}, tmp_path, THIRD)

    live = set(donor_ids(conn).values())
    assert live == {first["C"]}
    assert redirects(conn) == {first["A"]: first["C"], first["B"]: first["C"]}
    assert set(redirects(conn).values()) <= live


def test_a_key_the_run_did_not_cluster_keeps_its_row_and_its_id(
    conn: psycopg.Connection[Any], tmp_path: Path
) -> None:
    assign(conn, {"a": {"A": 10}, "b": {"B": 20}}, tmp_path)
    before = {row[0]: row for row in rows(conn)}

    assign(conn, {"b": {"B": 20}}, tmp_path, SECOND)

    assert {row[0]: row for row in rows(conn)} == before
    assert redirects(conn) == {}


def random_clusters(rng: random.Random, keys: list[str]) -> dict[str, dict[str, float]]:
    """`keys` dealt at random into clusters, each key worth a random amount."""
    clusters: dict[str, dict[str, float]] = {}
    for key in keys:
        group = f"c{rng.randrange(len(keys) // 2)}"
        clusters.setdefault(group, {})[key] = rng.choice([5, 10, 50, 100, 250, 1000])
    return clusters


@pytest.mark.parametrize("seed", range(8))
def test_any_sequence_of_runs_keeps_the_crosswalk_rules(
    conn: psycopg.Connection[Any], tmp_path: Path, seed: int
) -> None:
    rng = random.Random(seed)
    keys = [f"K{n:02d}" for n in range(24)]
    ever: set[int] = set()
    for run, build_id in enumerate((FIRST, SECOND, THIRD)):
        # Each run clusters most keys, and leaves a few out, as a run over fewer cycles would.
        clustered = [key for key in keys if rng.random() < 0.9]
        clusters = random_clusters(rng, clustered)
        before = donor_ids(conn)
        drawn_before, _ = sequence(conn) if run else (0, False)

        result = assign(conn, clusters, tmp_path, build_id)

        ids = donor_ids(conn)
        # Every clustered key has an id; a cluster has one id, and no two clusters share one.
        per_cluster = {group: {ids[key] for key in members} for group, members in clusters.items()}
        assert all(len(group_ids) == 1 for group_ids in per_cluster.values())
        assert len({next(iter(group_ids)) for group_ids in per_cluster.values()}) == len(clusters)
        # A key left out keeps its id, and every id first seen now was drawn from the sequence.
        assert all(ids[key] == before[key] for key in before if key not in clustered)
        new = set(ids.values()) - ever
        assert len(new) == result.new_donors
        assert all(drawn_before < donor_id for donor_id in new)
        # No merged-away id is ever handed out again, and every redirect lands on a live id.
        assert not set(redirects(conn)) & set(ids.values())
        assert set(redirects(conn).values()) <= set(ids.values())
        ever |= set(ids.values())

        again = assign(conn, clusters, tmp_path, build_id)
        assert donor_ids(conn) == ids
        assert again == crosswalk.Assigned(len(clustered), 0, 0, 0)


def test_the_snapshot_is_the_crosswalk_as_parquet(
    conn: psycopg.Connection[Any], store: R2, tmp_path: Path
) -> None:
    assign(conn, {"a": {"A|1|X|": 100, "B, JR|2||": 50}, "b": {"C": 10}}, tmp_path)

    key = crosswalk.snapshot(conn, store, build_id=SECOND, scratch=tmp_path)

    assert key == paths.resolution_snapshot(SECOND, "crosswalk")
    local = tmp_path / "crosswalk.parquet"
    local.write_bytes(store.get(key))
    with duckdb.connect() as con:
        snapped = con.execute(
            "SELECT contributor_key, donor_id, epoch_us(assigned_at), build_id FROM read_parquet(?)"
            " ORDER BY contributor_key",
            [str(local)],
        ).fetchall()
    expected = conn.execute(
        "SELECT contributor_key, donor_id,"
        " (extract(epoch FROM assigned_at) * 1000000)::bigint, build_id"
        " FROM app.crosswalk ORDER BY contributor_key"
    ).fetchall()
    assert snapped == expected
    assert {row[3] for row in snapped} == {FIRST}
    assert not tmp_path.joinpath(f"snapshot-{SECOND}").exists()


def test_the_snapshot_of_an_empty_crosswalk_is_an_empty_file(
    conn: psycopg.Connection[Any], store: R2, tmp_path: Path
) -> None:
    key = crosswalk.snapshot(conn, store, build_id=FIRST, scratch=tmp_path)

    local = tmp_path / "crosswalk.parquet"
    local.write_bytes(store.get(key))
    with duckdb.connect() as con:
        [(count,)] = con.execute("SELECT count(*) FROM read_parquet(?)", [str(local)]).fetchall()
    assert count == 0
