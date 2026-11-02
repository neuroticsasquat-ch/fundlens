"""Predicted pairs into clusters of contributor keys (spec §6.4, NEU-2122, ADR-0010).

The model scores the pairs its blocking rules choose, keeping those at or above the match
threshold as edges; the edges at or above the cluster threshold join their keys, and each
connected component is a component. A connected component ignores every pair it did not link,
so a path of strong pairs can join people the model would never pair directly: a chain.
Re-clustering rebuilds each component that holds a vetoed pair, or more keys than the cluster
cap, from its own joining edges, strongest first, refusing any union that would put a vetoed
pair in one cluster or exceed the cap. Every other component is a cluster as it stands.
"""

import hashlib
import logging
from collections import defaultdict
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass

import duckdb
from splink import Linker

from fundlens.resolve.model import FIRST_NAME_VETO_JW

log = logging.getLogger(__name__)

# Every predicted pair at or above the match threshold, once (`contributor_key_l` the lower key),
# with its `match_probability`. Kept after the run: re-clustering reads it.
EDGE_TABLE = "edge"
# Every key, in the connected component linkage put it in (`cluster_id`, its lowest key).
COMPONENT_TABLE = "component"
# Every key, in its cluster after re-clustering. `match_probability` is the strongest joining
# edge between the key and another key of its cluster; NULL for a key clustered alone.
CLUSTER_TABLE = "cluster"

_CONTRIBUTOR_TABLE = "contributor"


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


def _vetoed_pairs(con: duckdb.DuckDBPyConnection) -> dict[str, set[frozenset[str]]]:
    """Each component holding a vetoed pair, and its vetoed pairs of first names: both present,
    not equal, Jaro-Winkler under `FIRST_NAME_VETO_JW` and different first initials, the model's
    else level (`model._first_name`) to the letter."""
    rows = con.execute(
        f"""
        WITH name AS (
            SELECT DISTINCT c.cluster_id, k.first_name
            FROM {COMPONENT_TABLE} AS c
            JOIN {_CONTRIBUTOR_TABLE} AS k USING (contributor_key)
            WHERE k.first_name IS NOT NULL
        )
        SELECT a.cluster_id, a.first_name, b.first_name
        FROM name AS a
        JOIN name AS b ON b.cluster_id = a.cluster_id AND b.first_name > a.first_name
        WHERE jaro_winkler_similarity(a.first_name, b.first_name) < $jw
            AND left(a.first_name, 1) <> left(b.first_name, 1)
        """,
        {"jw": FIRST_NAME_VETO_JW},
    ).fetchall()
    vetoed: dict[str, set[frozenset[str]]] = defaultdict(set)
    for cluster_id, a, b in rows:
        vetoed[cluster_id].add(frozenset((a, b)))
    return vetoed


def recluster(
    con: duckdb.DuckDBPyConnection, *, max_keys: int, cluster_threshold: float
) -> Reclustered:
    """Write the table `cluster(cluster_id, contributor_key, match_probability)` on `con` from
    its `component`, `edge` and `contributor` tables: each component holding a vetoed pair or more
    than `max_keys` keys re-clustered (`recluster_component`) over its edges at or above
    `cluster_threshold`, every other component as it stands."""
    vetoed = _vetoed_pairs(con)
    oversized = {
        cluster_id
        for (cluster_id,) in con.execute(
            f"SELECT cluster_id FROM {COMPONENT_TABLE} GROUP BY cluster_id HAVING count(*) > $n",
            {"n": max_keys},
        ).fetchall()
    }
    offending = sorted(oversized | set(vetoed))
    con.execute(
        "CREATE OR REPLACE TEMP TABLE offending AS SELECT unnest($ids::VARCHAR[]) AS cluster_id",
        {"ids": offending},
    )
    members: dict[str, dict[str, str | None]] = defaultdict(dict)
    for cluster_id, key, first_name in con.execute(
        f"""
        SELECT c.cluster_id, c.contributor_key, k.first_name
        FROM {COMPONENT_TABLE} AS c
        JOIN offending USING (cluster_id)
        JOIN {_CONTRIBUTOR_TABLE} AS k USING (contributor_key)
        ORDER BY c.cluster_id, c.contributor_key
        """
    ).fetchall():
        members[cluster_id][key] = first_name
    edges: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for cluster_id, left, right, probability in con.execute(
        f"""
        SELECT l.cluster_id, e.contributor_key_l, e.contributor_key_r, e.match_probability
        FROM {EDGE_TABLE} AS e
        JOIN {COMPONENT_TABLE} AS l ON l.contributor_key = e.contributor_key_l
        JOIN {COMPONENT_TABLE} AS r ON r.contributor_key = e.contributor_key_r
        JOIN offending ON offending.cluster_id = l.cluster_id
        WHERE r.cluster_id = l.cluster_id AND e.match_probability >= $threshold
        ORDER BY l.cluster_id
        """,
        {"threshold": cluster_threshold},
    ).fetchall():
        edges[cluster_id].append((left, right, probability))
    moved: dict[str, str] = {}
    pieces = 0
    for cluster_id in offending:
        piece_of = recluster_component(
            members[cluster_id], edges[cluster_id], vetoed.get(cluster_id, set()), max_keys
        )
        pieces += len(set(piece_of.values()))
        moved |= {key: piece for key, piece in piece_of.items() if piece != cluster_id}
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {CLUSTER_TABLE} AS
        WITH
            moved AS (
                SELECT unnest($keys::VARCHAR[]) AS contributor_key,
                    unnest($pieces::VARCHAR[]) AS cluster_id
            ),
            placed AS (
                SELECT coalesce(moved.cluster_id, c.cluster_id) AS cluster_id, c.contributor_key
                FROM {COMPONENT_TABLE} AS c
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
        {"keys": list(moved), "pieces": list(moved.values()), "threshold": cluster_threshold},
    )
    con.execute("DROP TABLE offending")
    [(largest_before,)] = con.execute(
        f"SELECT coalesce(max(n), 0) FROM"
        f" (SELECT count(*) AS n FROM {COMPONENT_TABLE} GROUP BY cluster_id)"
    ).fetchall()
    [(largest_after,)] = con.execute(
        f"SELECT coalesce(max(n), 0) FROM"
        f" (SELECT count(*) AS n FROM {CLUSTER_TABLE} GROUP BY cluster_id)"
    ).fetchall()
    result = Reclustered(
        oversized=len(oversized),
        inconsistent=len(vetoed),
        components=len(offending),
        pieces=pieces,
        largest_before=largest_before,
        largest_after=largest_after,
        keys_moved=len(moved),
    )
    log.info("resolve recluster: %s", result.summary())
    return result


def cluster_fingerprint(keys: Iterable[str]) -> str:
    """A cluster's identity across runs: the SHA-1 of its member keys, sorted and one per line.

    The same keys always give the same fingerprint, however linkage ordered or named the cluster;
    one key more or fewer gives another. No contributor key holds a newline.
    """
    return hashlib.sha1("\n".join(sorted(keys)).encode()).hexdigest()
