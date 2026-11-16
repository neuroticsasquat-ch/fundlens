"""Predicted pairs into clusters of contributor keys (spec §6.4, NEU-2122, ADR-0010).

The model scores the pairs its blocking rules choose, keeping those at or above the match
threshold as edges; the edges at or above the cluster threshold join their keys, and each
connected component is a component. A connected component ignores every pair it did not link,
so a path of strong pairs can join people the model would never pair directly: a chain.
Re-clustering rebuilds each component that holds a vetoed pair, or more keys than the cluster
cap, from its own joining edges, strongest first, refusing any union that would put a vetoed
pair in one cluster or exceed the cap. Every other component is a cluster as it stands. The
offending components are read from DuckDB a batch of whole components at a time, so Python never
holds them all (NEU-2325).
`components_at` rebuilds the components from the kept edges at another cluster threshold, for the
threshold sweep (NEU-2182), without predicting again.
"""

import hashlib
import logging
import resource
from collections import defaultdict
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass

import duckdb
from splink import Linker

from fundlens.resolve.model import FIRST_NAME_VETO_JW, initial_pair_sql, nickname_pair_sql

log = logging.getLogger(__name__)

# Every predicted pair at or above the match threshold, once (`contributor_key_l` the lower key),
# with its `match_probability`. Kept after the run: re-clustering reads it.
EDGE_TABLE = "edge"
# Every key, in the connected component linkage put it in (`cluster_id`, its lowest key).
COMPONENT_TABLE = "component"
# Every key, in its cluster after re-clustering. `match_probability` is the strongest joining
# edge between the key and another key of its cluster; NULL for a key clustered alone.
CLUSTER_TABLE = "cluster"
# The components `components_at` rebuilds, beside `component` and never over it.
REBUILT_COMPONENT_TABLE = "component_at"

_CONTRIBUTOR_TABLE = "contributor"

# About how many keys of offending components `recluster` holds in Python at once: a batch is
# whole components in `cluster_id` order, a new one starting once this many keys came before.
# One component larger than it is held whole all the same.
BATCH_KEYS = 100_000


@dataclass(frozen=True)
class Reclustered:
    """What `recluster` did."""

    # Components holding more keys than the cap, and components holding a vetoed pair; a
    # component may be both.
    oversized: int
    inconsistent: int
    # Components rebuilt (those either way), and the clusters they became.
    components: int
    pieces: int
    # The most keys in one component, and in one cluster after.
    largest_before: int
    largest_after: int
    # Keys whose cluster is not their component.
    keys_moved: int

    def summary(self) -> str:
        return (
            f"{self.components:,} components ({self.oversized:,} oversized,"
            f" {self.inconsistent:,} inconsistent) into {self.pieces:,} pieces;"
            f" largest {self.largest_before:,} → {self.largest_after:,}"
        )


def cluster(
    linker: Linker,
    con: duckdb.DuckDBPyConnection,
    *,
    match_threshold: float,
    cluster_threshold: float,
) -> int:
    """Predict and cluster, writing the tables `edge(contributor_key_l, contributor_key_r,
    match_probability)` and `component(cluster_id, contributor_key)` on `con`, the linker's own
    connection; the component row count, one per key. `recluster` makes `cluster` from them."""
    predictions = linker.inference.predict(
        threshold_match_probability=match_threshold, warning_mode="never"
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {EDGE_TABLE} AS
        SELECT
            least(contributor_key_l, contributor_key_r) AS contributor_key_l,
            greatest(contributor_key_l, contributor_key_r) AS contributor_key_r,
            max(match_probability) AS match_probability
        FROM {predictions.physical_name}
        GROUP BY ALL
        """
    )
    components = linker.clustering.cluster_pairwise_predictions_at_threshold(
        predictions, threshold_match_probability=cluster_threshold
    )
    con.execute(
        f"CREATE OR REPLACE TABLE {COMPONENT_TABLE} AS"
        f" SELECT cluster_id, contributor_key FROM {components.physical_name}"
    )
    [(rows,)] = con.execute(f"SELECT count(*) FROM {COMPONENT_TABLE}").fetchall()
    return rows


def recluster_component(
    members: Mapping[str, str | None],
    edges: Iterable[tuple[str, str, float]],
    vetoed: Set[frozenset[str]],
    max_keys: int,
) -> dict[str, str]:
    """Each of a component's keys, and the cluster re-clustering puts it in: its lowest key.

    `members` is each key and its first name (None when it has none), `edges` the joining edges
    between them, `vetoed` the pairs of first names no cluster may hold. The edges are taken
    strongest first, ties in key order; each unions the clusters of its two keys unless the union
    would hold a vetoed pair or more than `max_keys` keys. A refused union is never retried: a
    cluster only grows, so it never becomes allowed. A component with no vetoed pair and at most
    `max_keys` keys comes back as one cluster.
    """
    parent = {key: key for key in members}
    size = dict.fromkeys(members, 1)
    names = {key: {name} if name is not None else set[str]() for key, name in members.items()}
    partners: dict[str, set[str]] = defaultdict(set)
    for pair in vetoed:
        a, b = sorted(pair)
        partners[a].add(b)
        partners[b].add(a)

    def root(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for left, right, _ in sorted(edges, key=lambda edge: (-edge[2], edge[0], edge[1])):
        a, b = root(left), root(right)
        if a == b or size[a] + size[b] > max_keys:
            continue
        few, many = sorted((names[a], names[b]), key=len)
        if any(not partners[name].isdisjoint(many) for name in few if name in partners):
            continue
        if size[a] < size[b]:
            a, b = b, a
        parent[b] = a
        size[a] += size[b]
        names[a] |= names.pop(b)
    lowest: dict[str, str] = {}
    for key in members:
        piece = root(key)
        lowest[piece] = min(lowest.get(piece, key), key)
    return {key: lowest[root(key)] for key in members}


def _vetoed_pairs(components: str) -> str:
    """SQL for each component's vetoed pairs of first names, as `(cluster_id, a, b)`, `a` the
    lower: both present, not equal, Jaro-Winkler under `FIRST_NAME_VETO_JW` (the parameter
    `$jw`) and neither an initial pair nor a nickname pair, the model's else level
    (`model._first_name`) to the letter."""
    initial = initial_pair_sql("a.first_name", "b.first_name")
    nickname = nickname_pair_sql(
        "a.first_name", "a.first_name_nicknames", "b.first_name", "b.first_name_nicknames"
    )
    return f"""
        WITH name AS (
            SELECT DISTINCT c.cluster_id, k.first_name, k.first_name_nicknames
            FROM {components} AS c
            JOIN {_CONTRIBUTOR_TABLE} AS k USING (contributor_key)
            WHERE k.first_name IS NOT NULL
        )
        SELECT a.cluster_id, a.first_name AS a, b.first_name AS b
        FROM name AS a
        JOIN name AS b ON b.cluster_id = a.cluster_id AND b.first_name > a.first_name
        WHERE jaro_winkler_similarity(a.first_name, b.first_name) < $jw
            AND NOT {initial}
            AND NOT {nickname}
        """


def components_at(con: duckdb.DuckDBPyConnection, *, cluster_threshold: float) -> str:
    """Write the temp table `component_at(cluster_id, contributor_key)` on `con`: every key of
    `contributor` in its connected component over the `edge`s at or above `cluster_threshold`,
    named by its lowest key as linkage names components; the table's name. `component` is left
    as it stands.

    Each key takes the lowest label among itself and its neighbours, then its label's own label,
    until no label changes: labels only fall, and the lowest key of a component never moves, so
    every key ends on it.
    """
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE joining AS
        SELECT contributor_key_l AS contributor_key, contributor_key_r AS neighbour
        FROM {EDGE_TABLE} WHERE match_probability >= $threshold
        UNION ALL
        SELECT contributor_key_r, contributor_key_l
        FROM {EDGE_TABLE} WHERE match_probability >= $threshold
        """,
        {"threshold": cluster_threshold},
    )
    # Only keys with a joining edge can move; every other key is a component of its own.
    con.execute(
        "CREATE OR REPLACE TEMP TABLE label AS"
        " SELECT DISTINCT contributor_key, contributor_key AS cluster_id FROM joining"
    )
    changed = True
    while changed:
        con.execute(
            """
            CREATE OR REPLACE TEMP TABLE lowered AS
            SELECT l.contributor_key, least(l.cluster_id, min(n.cluster_id)) AS cluster_id
            FROM label AS l
            JOIN joining AS j USING (contributor_key)
            JOIN label AS n ON n.contributor_key = j.neighbour
            GROUP BY l.contributor_key, l.cluster_id
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TEMP TABLE jumped AS
            SELECT k.contributor_key, least(k.cluster_id, l.cluster_id) AS cluster_id
            FROM lowered AS k
            JOIN lowered AS l ON l.contributor_key = k.cluster_id
            """
        )
        [(moved,)] = con.execute(
            "SELECT count(*) FROM jumped JOIN label USING (contributor_key)"
            " WHERE jumped.cluster_id <> label.cluster_id"
        ).fetchall()
        changed = moved > 0
        con.execute("CREATE OR REPLACE TEMP TABLE label AS SELECT * FROM jumped")
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE {REBUILT_COMPONENT_TABLE} AS
        SELECT coalesce(l.cluster_id, k.contributor_key) AS cluster_id, k.contributor_key
        FROM {_CONTRIBUTOR_TABLE} AS k
        LEFT JOIN label AS l USING (contributor_key)
        """
    )
    for scratch in ("joining", "label", "lowered", "jumped"):
        con.execute(f"DROP TABLE {scratch}")
    return REBUILT_COMPONENT_TABLE


# The temp tables `recluster` works in, dropped when it is done.
_RECLUSTER_SCRATCH = ("vetoed", "offending", "offending_member", "offending_edge", "moved")


def _by_component[T](rows: Iterable[tuple[str, T]]) -> dict[str, list[T]]:
    grouped: dict[str, list[T]] = defaultdict(list)
    for cluster_id, row in rows:
        grouped[cluster_id].append(row)
    return grouped


def _log_offending(con: duckdb.DuckDBPyConnection) -> None:
    """Log what re-clustering is about to hold: the offending components, their keys and
    joining edges, and the largest one's keys, distinct first names and vetoed pairs. For
    reading `resolve.log` after a large run, with the peak memory `recluster` logs after."""
    [(components, keys)] = con.execute(
        "SELECT count(*), coalesce(sum(keys), 0) FROM offending"
    ).fetchall()
    [(edges,)] = con.execute("SELECT count(*) FROM offending_edge").fetchall()
    log.info(
        "resolve recluster: %d offending components, %d keys, %d joining edges",
        components,
        keys,
        edges,
    )
    largest = con.execute(
        """
        SELECT
            o.keys,
            (SELECT count(DISTINCT first_name) FROM offending_member AS m
                WHERE m.cluster_id = o.cluster_id),
            (SELECT count(*) FROM vetoed AS v WHERE v.cluster_id = o.cluster_id)
        FROM offending AS o
        ORDER BY o.keys DESC, o.cluster_id
        LIMIT 1
        """
    ).fetchall()
    for keys, names, vetoed in largest:
        log.info(
            "resolve recluster: largest offending component %d keys, %d distinct first names,"
            " %d vetoed pairs",
            keys,
            names,
            vetoed,
        )


def recluster(
    con: duckdb.DuckDBPyConnection,
    *,
    max_keys: int,
    cluster_threshold: float,
    components: str = COMPONENT_TABLE,
) -> Reclustered:
    """Write the table `cluster(cluster_id, contributor_key, match_probability)` on `con` from
    its `components` (linkage's `component` unless `components_at` rebuilt them), `edge` and
    `contributor` tables: each component holding a vetoed pair or more than `max_keys` keys
    re-clustered (`recluster_component`) over its edges at or above `cluster_threshold`, every
    other component as it stands.

    The offending components, their members, joining edges and vetoed pairs are gathered in
    DuckDB, then read into Python a batch of about `BATCH_KEYS` keys at a time, and the keys
    each batch moves are written back before the next is read. All on `con` itself: a cursor
    sees neither its temp tables (`components_at`'s) nor its open transaction
    (`runner.recluster_working_file`'s)."""
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE vetoed AS {_vetoed_pairs(components)}",
        {"jw": FIRST_NAME_VETO_JW},
    )
    # Each offending component, and the batch it is read in: the keys of every component before
    # it in `cluster_id` order, in whole `BATCH_KEYS`.
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE offending AS
        WITH flagged AS (
            SELECT
                cluster_id,
                count(*) AS keys,
                count(*) > $n AS oversized,
                cluster_id IN (SELECT cluster_id FROM vetoed) AS inconsistent
            FROM {components}
            GROUP BY cluster_id
        )
        SELECT
            *,
            (sum(keys) OVER (ORDER BY cluster_id) - keys) // $batch AS batch
        FROM flagged
        WHERE oversized OR inconsistent
        """,
        {"n": max_keys, "batch": BATCH_KEYS},
    )
    # Ordered by batch, so reading one skips the others' row groups.
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE offending_member AS
        SELECT o.batch, c.cluster_id, c.contributor_key, k.first_name
        FROM {components} AS c
        JOIN offending AS o USING (cluster_id)
        JOIN {_CONTRIBUTOR_TABLE} AS k USING (contributor_key)
        ORDER BY o.batch, c.cluster_id, c.contributor_key
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE offending_edge AS
        SELECT o.batch, l.cluster_id, e.contributor_key_l, e.contributor_key_r, e.match_probability
        FROM {EDGE_TABLE} AS e
        JOIN {components} AS l ON l.contributor_key = e.contributor_key_l
        JOIN {components} AS r ON r.contributor_key = e.contributor_key_r
        JOIN offending AS o ON o.cluster_id = l.cluster_id
        WHERE r.cluster_id = l.cluster_id AND e.match_probability >= $threshold
        ORDER BY o.batch, l.cluster_id
        """,
        {"threshold": cluster_threshold},
    )
    con.execute("CREATE OR REPLACE TEMP TABLE moved (contributor_key VARCHAR, cluster_id VARCHAR)")
    _log_offending(con)
    pieces = keys_moved = 0
    batches = [
        batch
        for (batch,) in con.execute(
            "SELECT DISTINCT batch FROM offending ORDER BY batch"
        ).fetchall()
    ]
    for batch in batches:
        members = _by_component(
            (cluster_id, (key, first_name))
            for cluster_id, key, first_name in con.execute(
                "SELECT cluster_id, contributor_key, first_name FROM offending_member"
                " WHERE batch = $batch ORDER BY cluster_id, contributor_key",
                {"batch": batch},
            ).fetchall()
        )
        edges = _by_component(
            (cluster_id, (left, right, probability))
            for cluster_id, left, right, probability in con.execute(
                "SELECT cluster_id, contributor_key_l, contributor_key_r, match_probability"
                " FROM offending_edge WHERE batch = $batch",
                {"batch": batch},
            ).fetchall()
        )
        vetoed = _by_component(
            (cluster_id, frozenset((a, b)))
            for cluster_id, a, b in con.execute(
                "SELECT v.cluster_id, v.a, v.b FROM vetoed AS v"
                " JOIN offending AS o USING (cluster_id) WHERE o.batch = $batch",
                {"batch": batch},
            ).fetchall()
        )
        moved: dict[str, str] = {}
        for cluster_id, named in members.items():
            piece_of = recluster_component(
                dict(named), edges.get(cluster_id, []), set(vetoed.get(cluster_id, [])), max_keys
            )
            pieces += len(set(piece_of.values()))
            moved |= {key: piece for key, piece in piece_of.items() if piece != cluster_id}
        con.execute(
            "INSERT INTO moved SELECT unnest($keys::VARCHAR[]), unnest($pieces::VARCHAR[])",
            {"keys": list(moved), "pieces": list(moved.values())},
        )
        keys_moved += len(moved)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {CLUSTER_TABLE} AS
        WITH
            placed AS (
                SELECT coalesce(moved.cluster_id, c.cluster_id) AS cluster_id, c.contributor_key
                FROM {components} AS c
                LEFT JOIN moved USING (contributor_key)
            ),
            inside AS (
                SELECT e.contributor_key_l, e.contributor_key_r, e.match_probability
                FROM {EDGE_TABLE} AS e
                JOIN placed AS l ON l.contributor_key = e.contributor_key_l
                JOIN placed AS r ON r.contributor_key = e.contributor_key_r
                WHERE r.cluster_id = l.cluster_id AND e.match_probability >= $threshold
            ),
            joining AS (
                SELECT contributor_key_l AS contributor_key, match_probability FROM inside
                UNION ALL
                SELECT contributor_key_r, match_probability FROM inside
            )
        SELECT p.cluster_id, p.contributor_key, max(j.match_probability) AS match_probability
        FROM placed AS p
        LEFT JOIN joining AS j USING (contributor_key)
        GROUP BY ALL
        """,
        {"threshold": cluster_threshold},
    )
    [(oversized, inconsistent, offending)] = con.execute(
        "SELECT count(*) FILTER (oversized), count(*) FILTER (inconsistent), count(*)"
        " FROM offending"
    ).fetchall()
    for scratch in _RECLUSTER_SCRATCH:
        con.execute(f"DROP TABLE {scratch}")
    [(largest_before,)] = con.execute(
        f"SELECT coalesce(max(n), 0) FROM"
        f" (SELECT count(*) AS n FROM {components} GROUP BY cluster_id)"
    ).fetchall()
    [(largest_after,)] = con.execute(
        f"SELECT coalesce(max(n), 0) FROM"
        f" (SELECT count(*) AS n FROM {CLUSTER_TABLE} GROUP BY cluster_id)"
    ).fetchall()
    result = Reclustered(
        oversized=oversized,
        inconsistent=inconsistent,
        components=offending,
        pieces=pieces,
        largest_before=largest_before,
        largest_after=largest_after,
        keys_moved=keys_moved,
    )
    log.info("resolve recluster: %s", result.summary())
    # Linux reports the peak resident set in KiB.
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20
    log.info("resolve recluster: peak resident memory %.2f GiB", peak)
    return result


def cluster_fingerprint(keys: Iterable[str]) -> str:
    """A cluster's identity across runs: the SHA-1 of its member keys, sorted and one per line.

    The same keys always give the same fingerprint, however linkage ordered or named the cluster;
    one key more or fewer gives another. No contributor key holds a newline.
    """
    return hashlib.sha1("\n".join(sorted(keys)).encode()).hexdigest()
