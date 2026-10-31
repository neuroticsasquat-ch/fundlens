"""Predicted pairs into clusters of contributor keys (spec §6.4).

The model scores the pairs its blocking rules choose, keeping those at or above the match
threshold; the pairs at or above the cluster threshold join their keys, and each connected
component is one cluster: the keys linkage judges to be one person.
"""

import hashlib
from collections.abc import Iterable

import duckdb
from splink import Linker

# Every key, in the cluster linkage put it in. `match_probability` is the strongest pair joining
# the key to the rest of its cluster; NULL for a key clustered alone.
CLUSTER_TABLE = "cluster"


def cluster(
    linker: Linker,
    con: duckdb.DuckDBPyConnection,
    *,
    match_threshold: float,
    cluster_threshold: float,
) -> int:
    """Predict, cluster, and write the table `cluster(cluster_id, contributor_key,
    match_probability)` on `con`, the linker's own connection; its row count, one per key."""
    predictions = linker.inference.predict(
        threshold_match_probability=match_threshold, warning_mode="never"
    )
    clusters = linker.clustering.cluster_pairwise_predictions_at_threshold(
        predictions, threshold_match_probability=cluster_threshold
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {CLUSTER_TABLE} AS
        WITH edge AS (
            SELECT contributor_key_l AS contributor_key, contributor_key_r AS other,
                match_probability
            FROM {predictions.physical_name}
            WHERE match_probability >= $threshold
            UNION ALL
            SELECT contributor_key_r, contributor_key_l, match_probability
            FROM {predictions.physical_name}
            WHERE match_probability >= $threshold
        )
        SELECT
            c.cluster_id,
            c.contributor_key,
            max(edge.match_probability) AS match_probability
        FROM {clusters.physical_name} AS c
        LEFT JOIN edge ON edge.contributor_key = c.contributor_key
        GROUP BY ALL
        """,
        {"threshold": cluster_threshold},
    )
    [(rows,)] = con.execute(f"SELECT count(*) FROM {CLUSTER_TABLE}").fetchall()
    return rows


def cluster_fingerprint(keys: Iterable[str]) -> str:
    """A cluster's identity across runs: the SHA-1 of its member keys, sorted and one per line.

    The same keys always give the same fingerprint, however linkage ordered or named the cluster;
    one key more or fewer gives another. No contributor key holds a newline.
    """
    return hashlib.sha1("\n".join(sorted(keys)).encode()).hexdigest()
