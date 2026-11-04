"""Re-clustering of spec §6.4 (NEU-2122 §3, ADR-0010): components rebuilt so that no cluster holds
a vetoed pair of first names or more keys than the cluster cap, on components made up here; and
the components rebuilt from the kept edges at another cluster threshold (NEU-2182)."""

from itertools import combinations

import duckdb
import pytest

from fundlens.resolve.cluster import components_at, recluster, recluster_component
from tests.unit.test_resolve_model import NamePair, first_name_levels, nicknames_of

VETOED = {frozenset(("ELIZABETH", "KIRSTEN"))}


def pieces(clusters: dict[str, str]) -> set[frozenset[str]]:
    members: dict[str, set[str]] = {}
    for key, cluster_id in clusters.items():
        members.setdefault(cluster_id, set()).add(key)
    return {frozenset(keys) for keys in members.values()}


def test_a_chain_through_a_nameless_key_is_cut_and_the_bridge_takes_its_stronger_edge() -> None:
    members = {"a": "BEATRICE", "b": None, "c": "DESMOND"}
    vetoed = {frozenset(("BEATRICE", "DESMOND"))}

    stronger_to_a = recluster_component(
        members, [("a", "b", 0.999), ("b", "c", 0.97)], vetoed, max_keys=200
    )
    stronger_to_c = recluster_component(
        members, [("a", "b", 0.97), ("b", "c", 0.999)], vetoed, max_keys=200
    )

    assert stronger_to_a == {"a": "a", "b": "a", "c": "c"}
    assert stronger_to_c == {"a": "a", "b": "b", "c": "b"}


def test_a_vetoed_pair_reached_through_two_keys_with_no_first_name_is_cut_apart() -> None:
    members = {"e": "ELIZABETH", "n1": None, "n2": None, "k": "KIRSTEN"}
    # ELIZABETH – n1 – n2 – KIRSTEN: n1 is closer to ELIZABETH, n2 to KIRSTEN.
    edges = [("e", "n1", 0.99), ("n1", "n2", 0.96), ("k", "n2", 0.98)]

    assert pieces(recluster_component(members, edges, VETOED, max_keys=200)) == {
        frozenset({"e", "n1"}),
        frozenset({"k", "n2"}),
    }


def test_the_cap_cuts_a_clique_of_equal_edges_in_key_order() -> None:
    members = dict.fromkeys("abcde", "JOHN")
    edges = [(left, right, 0.99) for left, right in combinations("abcde", 2)]

    found = recluster_component(members, edges, set(), max_keys=3)

    assert found == {"a": "a", "b": "a", "c": "a", "d": "d", "e": "d"}


def test_one_person_twice_the_cap_is_cut_into_few_pieces_and_no_key_alone() -> None:
    cap = 5
    keys = [f"k{n:02d}" for n in range(2 * cap)]
    members = dict.fromkeys(keys, "JOHN")
    # Every key linked to every other, at varied strengths.
    edges = [
        (left, right, 0.95 + 0.001 * ((7 * a + 3 * b) % 49))
        for (a, left), (b, right) in combinations(enumerate(keys), 2)
    ]

    found = pieces(recluster_component(members, edges, set(), max_keys=cap))

    # Where the cut falls is the cap's, not the person's: the pieces left are those no two of
    # which fit under it together, so twice the cap makes two or three of them, never a key
    # alone (it would fit beside any piece but a full one).
    assert len(found) in (2, 3)
    assert all(1 < len(piece) <= cap for piece in found)


def test_a_consistent_component_under_the_cap_comes_back_whole() -> None:
    members = {"a": "ELIZABETH", "b": "ELISABETH", "c": None, "d": "E"}
    edges = [("a", "b", 0.96), ("b", "c", 0.99), ("c", "d", 0.95)]

    assert recluster_component(members, edges, VETOED, max_keys=4) == dict.fromkeys(members, "a")


def test_no_piece_exceeds_the_cap_or_holds_a_vetoed_pair() -> None:
    names = ["ELIZABETH", "KIRSTEN", None, "E", "K", "ELISABETH"]
    members = {f"k{n:02d}": names[n % len(names)] for n in range(30)}
    edges = [
        (left, right, 0.95 + 0.001 * ((11 * a + 5 * b) % 50))
        for (a, left), (b, right) in combinations(enumerate(sorted(members)), 2)
    ]
    vetoed = VETOED | {frozenset(("E", "KIRSTEN")), frozenset(("ELISABETH", "KIRSTEN"))}
    vetoed |= {frozenset(("ELIZABETH", "K")), frozenset(("ELISABETH", "K")), frozenset(("E", "K"))}

    found = pieces(recluster_component(members, edges, vetoed, max_keys=7))

    assert all(len(piece) <= 7 for piece in found)
    for piece in found:
        held = {members[key] for key in piece} - {None}
        assert not any(frozenset(pair) in vetoed for pair in combinations(held, 2)), piece
    assert set().union(*found) == set(members)


# Each pair of first names, and the level of the model's first-name comparison it lands in.
NAME_PAIRS: list[NamePair] = [
    ("JOHN", "JOHN"),  # exact
    ("ELIZABETH", "ELISABETH"),  # Jaro-Winkler ≥ 0.92
    ("CARL", "KARL"),  # Jaro-Winkler ≥ 0.8, different initials
    ("EDWARD", "ELIZABETH"),  # one initial, two full names: vetoed
    ("MARGO", "MICHAEL"),  # one initial, two full names: vetoed
    ("E", "EDWARD"),  # an initial pair
    ("C", "CRAIG"),  # an initial pair
    ("E", "KIRSTEN"),  # a single letter, another initial: vetoed
    ("LOU", "LOUIS"),  # a nickname pair by prefix
    ("BILL", "WILLIAM"),  # a nickname pair by the table, different initials
    (None, "KIRSTEN"),  # no first name
    ("BEATRICE", "DESMOND"),  # vetoed
]


def contributors(con: duckdb.DuckDBPyConnection, names: dict[str, str | None]) -> None:
    """The table `contributor` re-clustering reads: each key, its first name and the
    `first_name_nicknames` `_load_contributors` gives it."""
    con.execute(
        "CREATE TABLE contributor (contributor_key VARCHAR, first_name VARCHAR,"
        " first_name_nicknames VARCHAR[])"
    )
    con.executemany(
        "INSERT INTO contributor VALUES (?, ?, ?)",
        [[key, name, nicknames_of(name)] for key, name in names.items()],
    )


@pytest.fixture
def model_vetoes() -> dict[NamePair, bool]:
    """Whether the model's first-name comparison puts each of `NAME_PAIRS` at its else level."""
    return {pair: level == "else" for pair, level in first_name_levels(NAME_PAIRS).items()}


def pair_components(con: duckdb.DuckDBPyConnection, pairs: list[NamePair]) -> None:
    """Each pair of first names a component of two keys, `{n}l` and `{n}r`, joined by one strong
    edge."""
    contributors(
        con,
        {
            key: name
            for n, (left, right) in enumerate(pairs)
            for key, name in ((f"{n}l", left), (f"{n}r", right))
        },
    )
    con.execute("CREATE TABLE component (cluster_id VARCHAR, contributor_key VARCHAR)")
    con.execute(
        "CREATE TABLE edge (contributor_key_l VARCHAR, contributor_key_r VARCHAR,"
        " match_probability DOUBLE)"
    )
    for n in range(len(pairs)):
        lo, hi = f"{n}l", f"{n}r"
        con.execute("INSERT INTO component VALUES (?, ?), (?, ?)", [lo, lo, lo, hi])
        con.execute("INSERT INTO edge VALUES (?, ?, 0.99)", [lo, hi])


def apart(con: duckdb.DuckDBPyConnection, pairs: list[NamePair]) -> dict[NamePair, bool]:
    clusters = dict(con.execute("SELECT contributor_key, cluster_id FROM cluster").fetchall())
    return {pair: clusters[f"{n}l"] != clusters[f"{n}r"] for n, pair in enumerate(pairs)}


def test_the_vetoed_pairs_recluster_finds_are_the_models_else_level(
    model_vetoes: dict[NamePair, bool],
) -> None:
    con = duckdb.connect()
    pair_components(con, NAME_PAIRS)

    result = recluster(con, max_keys=200, cluster_threshold=0.95)

    assert apart(con, NAME_PAIRS) == model_vetoes
    assert sum(model_vetoes.values()) == 4
    assert result.inconsistent == result.components == 4
    assert result.oversized == 0


def test_two_full_names_sharing_a_first_letter_are_cut_apart_and_a_nickname_is_left_whole() -> None:
    pairs: list[NamePair] = [("MARGO", "MICHAEL"), ("BILL", "WILLIAM")]
    con = duckdb.connect()
    pair_components(con, pairs)

    recluster(con, max_keys=200, cluster_threshold=0.95)

    assert apart(con, pairs) == {("MARGO", "MICHAEL"): True, ("BILL", "WILLIAM"): False}


def test_recluster_leaves_a_consistent_component_as_it_was_and_names_pieces_by_lowest_key() -> None:
    con = duckdb.connect()
    contributors(con, {"a": "JOHN", "b": "JOHN", "c": "JOHN", "x": "MARY", "y": None, "z": "PETER"})
    con.execute(
        "CREATE TABLE component AS SELECT * FROM (VALUES ('a', 'a'), ('a', 'b'), ('a', 'c'),"
        " ('x', 'x'), ('x', 'y'), ('x', 'z')) AS t(cluster_id, contributor_key)"
    )
    # x – y – z chains MARY to PETER; y's edge to z is the stronger. b–c is below the cluster
    # threshold, so it never joins and never sets a probability.
    con.execute(
        "CREATE TABLE edge (contributor_key_l VARCHAR, contributor_key_r VARCHAR,"
        " match_probability DOUBLE)"
    )
    con.execute(
        "INSERT INTO edge VALUES ('a', 'b', 0.97), ('a', 'c', 0.99), ('b', 'c', 0.92),"
        " ('x', 'y', 0.96), ('y', 'z', 0.98)"
    )

    result = recluster(con, max_keys=200, cluster_threshold=0.95)

    rows = con.execute(
        "SELECT contributor_key, cluster_id, match_probability FROM cluster ORDER BY 1"
    ).fetchall()
    assert rows == [
        ("a", "a", 0.99),
        ("b", "a", 0.97),
        ("c", "a", 0.99),
        ("x", "x", None),
        ("y", "y", 0.98),
        ("z", "y", 0.98),
    ]
    assert result.keys_moved == 2
    assert (result.pieces, result.largest_before, result.largest_after) == (2, 3, 3)


def edges_table(
    con: duckdb.DuckDBPyConnection, keys: list[str], edges: list[tuple[str, str, float]]
) -> None:
    contributors(con, dict.fromkeys(keys, "JOHN"))
    con.execute(
        "CREATE TABLE edge (contributor_key_l VARCHAR, contributor_key_r VARCHAR,"
        " match_probability DOUBLE)"
    )
    con.executemany("INSERT INTO edge VALUES (?, ?, ?)", [list(edge) for edge in edges])


def test_components_at_a_threshold_are_the_connected_components_of_the_edges_above_it() -> None:
    con = duckdb.connect()
    # A path from the highest key to the lowest, so the lowest label has the whole way to travel,
    # and a pair below the threshold that would join it to a third component.
    path = [f"p{n:02d}" for n in range(12)]
    keys = [*path, "q1", "q2", "r1", "s1"]
    edges = [(path[n], path[n + 1], 0.999) for n in range(len(path) - 1)]
    edges += [("q1", "q2", 0.97), ("p11", "q1", 0.96), ("r1", "s1", 0.92)]
    edges_table(con, keys, edges)

    table = components_at(con, cluster_threshold=0.965)

    found = dict(con.execute(f"SELECT contributor_key, cluster_id FROM {table}").fetchall())
    assert found == {**dict.fromkeys(path, "p00"), "q1": "q1", "q2": "q1", "r1": "r1", "s1": "s1"}
    # The connection holds nothing the rebuild used along the way.
    assert {name for (name,) in con.execute("SHOW TABLES").fetchall()} == {
        "contributor",
        "edge",
        table,
    }


def test_a_threshold_above_an_edge_parts_its_keys_and_recluster_reads_the_rebuilt_components() -> (
    None
):
    con = duckdb.connect()
    edges_table(con, ["a", "b", "c"], [("a", "b", 0.999), ("b", "c", 0.97)])
    con.execute(
        "CREATE TABLE component AS SELECT * FROM (VALUES ('a', 'a'), ('a', 'b'), ('a', 'c'))"
        " AS t(cluster_id, contributor_key)"
    )

    components = components_at(con, cluster_threshold=0.99)
    result = recluster(con, max_keys=200, cluster_threshold=0.99, components=components)

    rows = con.execute(
        "SELECT contributor_key, cluster_id, match_probability FROM cluster ORDER BY 1"
    ).fetchall()
    assert rows == [("a", "a", 0.999), ("b", "a", 0.999), ("c", "c", None)]
    assert (result.components, result.largest_before) == (0, 2)
    # Linkage's components stand.
    assert con.execute("SELECT count(DISTINCT cluster_id) FROM component").fetchall() == [(1,)]
