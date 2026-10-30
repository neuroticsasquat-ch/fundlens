"""psycopg 3 connections to the fundlens Postgres (spec §7.3).

`prepare_threshold=None` on every connection: psycopg otherwise turns a query it has run five
times into a server-side prepared statement, and a prepared plan can outlive the
`ALTER SCHEMA … RENAME` that swaps a new gold build in (§5.5). Every query names `gold.`
explicitly rather than relying on `search_path`.
"""

from psycopg import Connection
from psycopg.rows import TupleRow
from psycopg_pool import ConnectionPool

type Pool = ConnectionPool[Connection[TupleRow]]

# Small: the API's lookups are single indexed reads, and Cloudflare absorbs nearly all traffic.
POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 10
# How long a request waits for a free connection before it fails, rather than queueing for the
# pool's default 30 s.
POOL_TIMEOUT_SECONDS = 5.0


def create_pool(conninfo: str) -> Pool:
    """An unopened pool for read-only lookups; open it with `with create_pool(…) as pool:`.

    Autocommit, so a connection never sits idle in a transaction holding a lock on a gold table
    the pipeline is about to drop. Each connection is checked on checkout, so one a Postgres
    restart has severed is replaced instead of failing the request it is handed to.
    """
    return ConnectionPool(
        conninfo,
        kwargs={"prepare_threshold": None, "autocommit": True},
        min_size=POOL_MIN_SIZE,
        max_size=POOL_MAX_SIZE,
        timeout=POOL_TIMEOUT_SECONDS,
        check=ConnectionPool.check_connection,
        open=False,
    )
