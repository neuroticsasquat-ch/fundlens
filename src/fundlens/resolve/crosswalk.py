"""The crosswalk: every contributor key's persistent `donor_id` (spec §6.6, ADR-0005), carried
onto silver (spec §3.4) and snapshotted to R2 at publish (spec §5.5).

Clusters are one run's; a `donor_id` must outlive every rebuild, or donor URLs break. So `assign`
reads `app.crosswalk` into resolution's DuckDB working file and gives each cluster an id by what
its members already carry, weighted by their contribution dollars:

- an id goes to the cluster holding the most of its dollars. When one former donor is now split
  across clusters, the larger-dollar one keeps the id and the others are given ids of their own;
- a cluster takes the heaviest id it was given. Any other it was given is merged away: its keys
  are re-pointed and `app.donor_redirect` sends it on to the id kept;
- a cluster given none (never-seen keys, or the lighter half of a split) draws a new id from
  `app.donor_id_seq`, all of them in one batch.

Ties go to the lower id, then the cluster whose first key sorts first. A redirect is written only
for an id no key carries any more, and a redirect pointing at it is pointed on, so every redirect
resolves in one hop to a live id. Only rows whose id changed are written, so a run over unchanged
clusters writes nothing and draws no id. Ids are never reused: a merged-away id is never assigned
again, and a key this run did not cluster keeps its row.

`onto_silver` then rewrites a cycle's `contribution` partition with each row's `donor_id`, in
`bucket=<hex2>` directories of `donor_id % 256` (the itemized reader scans one), and then its
`contributor` partition with the `donor_id` column, both in place under the same build. A cycle
whose `contributor` already carries every key's id is left alone: its contribution was rewritten
first, with the same ids. R2 is written first and the local cache swapped last. While R2's
contribution parts are being replaced the partition holds `paths.rewrite_sentinel`, and nothing
reads past it: a run that dies there leaves the cache in its old layout, which the next run reads
in place of R2's half-written one, and with no cache the cycle must be transformed again.
Swapping the cache is two renames, not one: an itemized request that lands between them, on a
build already live, fails once.

Postgres and DuckDB exchange rows as CSV over `COPY`, as gold does (ADR-0007).
"""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

import duckdb
from psycopg import Connection, sql
from psycopg.abc import Query
from psycopg.rows import TupleRow

from fundlens import paths
from fundlens.r2 import R2
from fundlens.resolve.cluster import CLUSTER_TABLE
from fundlens.transform.runner import CHUNK_BYTES, ROW_GROUP_ROWS, literal

log = logging.getLogger(__name__)

# Each contributor key this run clustered and the donor_id `assign` gave it, in the working file.
CROSSWALK_TABLE = "crosswalk"
# The working file's cross-cycle contributor table (`resolve.runner`), whose totals weigh ids.
CONTRIBUTOR_TABLE = "contributor"

# Postgres's CSV, spelled out: DuckDB cannot sniff the dialect of an empty file.
_CSV = """header = false, delim = ',', quote = '"', escape = '"', auto_detect = false"""
_KEY_ID = "{'contributor_key': 'VARCHAR', 'donor_id': 'BIGINT'}"
_SNAPSHOT_COLUMNS = (
    "{'contributor_key': 'VARCHAR', 'donor_id': 'BIGINT', 'assigned_at': 'TIMESTAMPTZ',"
    " 'build_id': 'VARCHAR'}"
)


@dataclass(frozen=True)
class Assigned:
    """What `assign` did."""

    # Contributor keys this run gave a donor_id.
    keys: int
    # Clusters given a new id from `app.donor_id_seq`.
    new_donors: int
    # Keys already in `app.crosswalk` whose donor_id changed.
    repointed: int
    # Ids merged away, each now redirecting to the id kept.
    redirects: int


def _copy_to(conn: Connection[TupleRow], statement: Query, path: Path) -> None:
    """Stream a `COPY … TO STDOUT` into `path`."""
    with conn.cursor() as cur, cur.copy(statement) as copy, path.open("wb") as out:
        for chunk in copy:
            out.write(chunk)


def _copy_from(conn: Connection[TupleRow], statement: Query, path: Path) -> None:
    """Stream `path` into a `COPY … FROM STDIN`."""
    with conn.cursor() as cur, cur.copy(statement) as copy, path.open("rb") as src:
        while chunk := src.read(CHUNK_BYTES):
            copy.write(chunk)


def _count(con: duckdb.DuckDBPyConnection, query: str) -> int:
    [(rows,)] = con.execute(f"SELECT count(*) FROM ({query})").fetchall()
    return rows


def _claim(con: duckdb.DuckDBPyConnection) -> int:
    """The tables `member`, `claim` (each cluster and the prior id it keeps) and `fresh` (each
    cluster keeping none, numbered); how many clusters are fresh."""
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE member AS
        SELECT c.cluster_id, c.contributor_key, coalesce(k.amount_total, 0) AS amount,
            p.donor_id AS prior_id
        FROM {CLUSTER_TABLE} AS c
        JOIN {CONTRIBUTOR_TABLE} AS k USING (contributor_key)
        LEFT JOIN prior AS p USING (contributor_key)
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE claim AS
        WITH holding AS (
            -- The dollars of each prior id each cluster holds.
            SELECT cluster_id, prior_id AS donor_id, sum(amount) AS amount,
                min(contributor_key) AS first_key
            FROM member
            WHERE prior_id IS NOT NULL
            GROUP BY ALL
        ),
        won AS (
            -- A split: the id stays with the cluster holding most of its dollars.
            SELECT * FROM holding
            QUALIFY row_number() OVER (
                PARTITION BY donor_id ORDER BY amount DESC, first_key
            ) = 1
        )
        -- A merge: the cluster keeps the heaviest id it won.
        SELECT cluster_id, donor_id FROM won
        QUALIFY row_number() OVER (PARTITION BY cluster_id ORDER BY amount DESC, donor_id) = 1
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE fresh AS
        SELECT cluster_id, row_number() OVER (ORDER BY min(contributor_key)) AS ordinal
        FROM member
        ANTI JOIN claim USING (cluster_id)
        GROUP BY cluster_id
        """
    )
    return _count(con, "SELECT * FROM fresh")


def _settle(con: duckdb.DuckDBPyConnection, work: Path) -> tuple[int, int, int]:
    """The working file's `crosswalk`, and under `work` the CSVs of the rows it changes
    (`changed.csv`) and the redirects it adds (`redirect.csv`); how many keys it holds, how many
    of them were already in the crosswalk under another id, and how many redirects it adds."""
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {CROSSWALK_TABLE} AS
        SELECT m.contributor_key, coalesce(claim.donor_id, fresh_id.donor_id) AS donor_id
        FROM member AS m
        LEFT JOIN claim USING (cluster_id)
        LEFT JOIN fresh USING (cluster_id)
        LEFT JOIN fresh_id USING (ordinal)
        """
    )
    changed = f"""
        SELECT x.contributor_key, x.donor_id
        FROM {CROSSWALK_TABLE} AS x
        LEFT JOIN prior AS p USING (contributor_key)
        WHERE p.donor_id IS DISTINCT FROM x.donor_id
    """
    # An id no key carries any more, neither one this run clustered nor one it did not, sends its
    # old URL on to the id that took most of its dollars.
    redirect = f"""
        WITH retired AS (
            SELECT donor_id FROM prior
            EXCEPT SELECT donor_id FROM {CROSSWALK_TABLE}
            EXCEPT SELECT donor_id FROM prior ANTI JOIN member USING (contributor_key)
        )
        SELECT p.donor_id AS old_donor_id, x.donor_id
        FROM prior AS p
        JOIN member AS m USING (contributor_key)
        JOIN {CROSSWALK_TABLE} AS x USING (contributor_key)
        WHERE p.donor_id IN (SELECT donor_id FROM retired)
        GROUP BY p.donor_id, x.donor_id
        QUALIFY row_number() OVER (
            PARTITION BY p.donor_id ORDER BY sum(m.amount) DESC, x.donor_id
        ) = 1
    """
    repointed = f"""
        SELECT * FROM {CROSSWALK_TABLE} AS x
        JOIN prior AS p USING (contributor_key)
        WHERE p.donor_id <> x.donor_id
    """
    for name, query in (("changed", changed), ("redirect", redirect)):
        con.execute(f"COPY ({query}) TO {literal(work / f'{name}.csv')} (FORMAT csv, HEADER false)")
    return (
        _count(con, f"SELECT * FROM {CROSSWALK_TABLE}"),
        _count(con, repointed),
        _count(con, redirect),
    )


def assign(
    con: duckdb.DuckDBPyConnection, conn: Connection[TupleRow], *, build_id: str, scratch: Path
) -> Assigned:
    """Give every key in the working file's `cluster` its donor_id and write the changes to
    `app.crosswalk` and `app.donor_redirect`, in one Postgres transaction.

    `con` is the working file, holding `cluster` and `contributor`; the run's assignment is left
    in it as the table `crosswalk`. Rows written carry `build_id`.
    """
    work = scratch / f"crosswalk-{build_id}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        with conn.transaction():
            # One assignment at a time: a second would read the crosswalk this one is rewriting.
            conn.execute("LOCK TABLE app.crosswalk IN SHARE ROW EXCLUSIVE MODE")
            _copy_to(
                conn,
                "COPY (SELECT contributor_key, donor_id FROM app.crosswalk) TO STDOUT (FORMAT csv)",
                work / "prior.csv",
            )
            con.execute(
                "CREATE OR REPLACE TEMP TABLE prior AS SELECT * FROM read_csv("
                f"{literal(work / 'prior.csv')}, {_CSV}, columns = {_KEY_ID})"
            )
            fresh = _claim(con)
            # Drawn in Postgres so no id is ever handed out twice, whatever this run does next.
            _copy_to(
                conn,
                sql.SQL(
                    "COPY (SELECT g, nextval('app.donor_id_seq') FROM generate_series(1, {}) AS g)"
                    " TO STDOUT (FORMAT csv)"
                ).format(sql.Literal(fresh)),
                work / "fresh.csv",
            )
            con.execute(
                "CREATE OR REPLACE TEMP TABLE fresh_id AS SELECT * FROM read_csv("
                f"{literal(work / 'fresh.csv')}, {_CSV},"
                " columns = {'ordinal': 'BIGINT', 'donor_id': 'BIGINT'})"
            )
            keys, repointed, redirects = _settle(con, work)
            conn.execute(
                "CREATE TEMP TABLE crosswalk_in (contributor_key text, donor_id bigint)"
                " ON COMMIT DROP"
            )
            _copy_from(conn, "COPY crosswalk_in FROM STDIN (FORMAT csv)", work / "changed.csv")
            conn.execute(
                """
                INSERT INTO app.crosswalk (contributor_key, donor_id, assigned_at, build_id)
                SELECT contributor_key, donor_id, now(), %s FROM crosswalk_in
                ON CONFLICT (contributor_key) DO UPDATE
                SET donor_id = EXCLUDED.donor_id, assigned_at = EXCLUDED.assigned_at,
                    build_id = EXCLUDED.build_id
                """,
                (build_id,),
            )
            conn.execute(
                "CREATE TEMP TABLE redirect_in (old_donor_id bigint, donor_id bigint)"
                " ON COMMIT DROP"
            )
            _copy_from(conn, "COPY redirect_in FROM STDIN (FORMAT csv)", work / "redirect.csv")
            # A redirect to an id merged away now goes straight on to the id that took it.
            conn.execute(
                """
                UPDATE app.donor_redirect AS r SET donor_id = i.donor_id
                FROM redirect_in AS i WHERE r.donor_id = i.old_donor_id
                """
            )
            conn.execute(
                """
                INSERT INTO app.donor_redirect (old_donor_id, donor_id)
                SELECT old_donor_id, donor_id FROM redirect_in
                ON CONFLICT (old_donor_id) DO UPDATE SET donor_id = EXCLUDED.donor_id
                """
            )
            # Dropped here as well as on commit: inside a caller's transaction this one is only
            # a savepoint, and a second `assign` on the connection would find them still there.
            conn.execute("DROP TABLE crosswalk_in, redirect_in")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    assigned = Assigned(keys, fresh, repointed, redirects)
    log.info(
        "crosswalk: %d keys, %d new donors, %d keys re-pointed, %d redirects",
        assigned.keys,
        assigned.new_donors,
        assigned.repointed,
        assigned.redirects,
    )
    return assigned


def _with_donor_id(con: duckdb.DuckDBPyConnection, files: str) -> str:
    """The select list of `files`' columns with `x.donor_id` after `contributor_key`, replacing
    any `donor_id` an earlier run wrote."""
    columns = [
        name
        for name, *_ in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({files}, hive_partitioning = false)"
        ).fetchall()
        if name != "donor_id"
    ]
    select: list[str] = []
    for name in columns:
        select.append(f"r.{name}")
        if name == "contributor_key":
            select.append("x.donor_id")
    return ", ".join(select)


def _local_partition(store: R2, prefix: str, *, cycle: int, build_id: str, data_dir: Path) -> Path:
    """The partition at `prefix` on local disk. A cached one is read as it is, never topped up
    from R2, which may hold a rewrite that died part way (module docstring).

    Raises `RuntimeError` when there is no cache and R2's parts are a rewrite that died.
    """
    local = paths.local_path(data_dir, prefix)
    if local.is_dir():
        return local
    keys = store.list_keys(prefix + "/")
    if not keys:
        raise FileNotFoundError(f"no silver partition at {prefix}")
    if paths.rewrite_sentinel(cycle, build_id) in keys:
        raise RuntimeError(
            f"a donor_id rewrite of silver contribution {cycle} build {build_id} died part way"
            f" and no local copy is left: run `fundlens transform --cycle {cycle} --build-id"
            f" {build_id}`, then `fundlens resolve --full` again"
        )
    for key in keys:
        store.download_to(key, paths.local_path(data_dir, key))
    return local


def _swap_in(store: R2, staged: Path, local: Path, prefix: str, sentinel: str | None) -> None:
    """`staged` becomes the partition at `prefix`: uploaded, the keys it does not replace
    deleted, then swapped in for the local copy. `sentinel`, if given, stands in R2 while the
    parts there are a mix of old and new."""
    before = set(store.list_keys(prefix + "/"))
    if sentinel is not None:
        store.put(sentinel, b"")
    after = set(store.upload_dir(staged, prefix))
    store.delete_keys(sorted(before - after - {sentinel or ""}))
    if sentinel is not None:
        store.delete_keys([sentinel])
    # Renamed beside the partition, not through scratch: silver may be a volume of its own.
    old = local.with_name(local.name + ".old")
    shutil.rmtree(old, ignore_errors=True)
    if local.exists():
        local.rename(old)
    staged.rename(local)
    shutil.rmtree(old, ignore_errors=True)


def _current(con: duckdb.DuckDBPyConnection, contributors: Path) -> bool:
    """Whether the `contributor` partition at `contributors` carries every key's donor_id."""
    files = literal(contributors / "*.parquet")
    columns = {
        name
        for name, *_ in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({files}, hive_partitioning = false)"
        ).fetchall()
    }
    if "donor_id" not in columns:
        return False
    stale = _count(
        con,
        f"SELECT * FROM read_parquet({files}, hive_partitioning = false) AS r"
        f" LEFT JOIN {CROSSWALK_TABLE} AS x USING (contributor_key)"
        " WHERE r.donor_id IS DISTINCT FROM x.donor_id",
    )
    return stale == 0


def onto_silver(
    con: duckdb.DuckDBPyConnection, store: R2, *, cycle: int, build_id: str, data_dir: Path
) -> int:
    """Rewrite the `contribution` and then the `contributor` partition of one build of `cycle`
    with each row's donor_id from the working file's `crosswalk`, contribution in `bucket=<hex2>`
    directories, unless `contributor` already carries them; the contribution rows.

    Raises `RuntimeError`, before anything is uploaded, if a row's key has no donor_id, or if a
    rewrite that died left R2 unreadable and no local copy (`_local_partition`).
    """
    sentinel = paths.rewrite_sentinel(cycle, build_id)
    contributors = _local_partition(
        store,
        paths.silver_partition("contributor", cycle, build_id),
        cycle=cycle,
        build_id=build_id,
        data_dir=data_dir,
    )
    if _current(con, contributors) and not store.exists(sentinel):
        contributions = _local_partition(
            store,
            paths.silver_partition("contribution", cycle, build_id),
            cycle=cycle,
            build_id=build_id,
            data_dir=data_dir,
        )
        rows = _count(
            con,
            f"SELECT * FROM read_parquet({literal(contributions / '**' / '*.parquet')},"
            " hive_partitioning = false)",
        )
        log.info("donor_id onto silver %d build %s: already current", cycle, build_id)
        return rows
    rows = 0
    for table in ("contribution", "contributor"):
        prefix = paths.silver_partition(table, cycle, build_id)
        local = _local_partition(store, prefix, cycle=cycle, build_id=build_id, data_dir=data_dir)
        files = literal(local / "**" / "*.parquet")
        staged = local.with_name(local.name + ".rewrite")
        shutil.rmtree(staged, ignore_errors=True)
        staged.mkdir(parents=True)
        source = (
            f"SELECT {_with_donor_id(con, files)}"
            f" FROM read_parquet({files}, hive_partitioning = false) AS r"
            f" JOIN {CROSSWALK_TABLE} AS x USING (contributor_key)"
        )
        if table == "contribution":
            con.execute(
                f"COPY (SELECT *, printf('%02x', donor_id % {paths.BUCKETS}) AS bucket"
                f" FROM ({source})) TO {literal(staged)} (FORMAT parquet, COMPRESSION zstd,"
                f" ROW_GROUP_SIZE {ROW_GROUP_ROWS}, PARTITION_BY (bucket),"
                " FILENAME_PATTERN 'part-{i}')"
            )
            # DuckDB numbers its parts without padding; silver's are `paths.part`'s.
            for part_file in staged.glob("bucket=*/part-*.parquet"):
                index = int(part_file.stem.removeprefix("part-"))
                part_file.rename(part_file.with_name(paths.part(index)))
        else:
            con.execute(
                f"COPY ({source}) TO {literal(staged / paths.part(0))}"
                f" (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE {ROW_GROUP_ROWS})"
            )
        read = _count(con, f"SELECT * FROM read_parquet({files}, hive_partitioning = false)")
        written = _count(
            con,
            f"SELECT * FROM read_parquet({literal(staged / '**' / '*.parquet')},"
            " hive_partitioning = false)",
        )
        if written != read:
            shutil.rmtree(staged, ignore_errors=True)
            raise RuntimeError(
                f"{table} {cycle} build {build_id}: {read - written} of {read} rows have a"
                " contributor key the crosswalk does not hold"
            )
        _swap_in(store, staged, local, prefix, sentinel if table == "contribution" else None)
        if table == "contribution":
            rows = written
    log.info("donor_id onto silver %d build %s: %d contributions", cycle, build_id, rows)
    return rows


def snapshot(conn: Connection[TupleRow], store: R2, *, build_id: str, scratch: Path) -> str:
    """`app.crosswalk` as Parquet in R2, as of the publish of `build_id`; its key."""
    key = paths.resolution_snapshot(build_id, "crosswalk")
    work = scratch / f"snapshot-{build_id}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        csv, parquet = work / "crosswalk.csv", work / "crosswalk.parquet"
        _copy_to(
            conn,
            "COPY (SELECT contributor_key, donor_id, assigned_at, build_id FROM app.crosswalk)"
            " TO STDOUT (FORMAT csv)",
            csv,
        )
        with duckdb.connect() as con:
            con.execute(
                f"COPY (SELECT * FROM read_csv({literal(csv)}, {_CSV},"
                f" columns = {_SNAPSHOT_COLUMNS})) TO {literal(parquet)}"
                " (FORMAT parquet, COMPRESSION zstd)"
            )
        store.put(key, parquet)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return key
