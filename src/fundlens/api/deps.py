"""Request dependencies: what a route is handed instead of reaching into `app.state`."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from psycopg import Connection
from psycopg.rows import TupleRow

from fundlens.load.db import Pool
from fundlens.settings import Settings


def get_pool(request: Request) -> Pool:
    return request.app.state.pool


def get_conn(request: Request) -> Iterator[Connection[TupleRow]]:
    """A pooled connection for the length of the request."""
    with get_pool(request).connection() as conn:
        yield conn


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


PoolDep = Annotated[Pool, Depends(get_pool)]
Conn = Annotated[Connection[TupleRow], Depends(get_conn)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
