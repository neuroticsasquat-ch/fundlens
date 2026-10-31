"""Request dependencies: what a route is handed instead of reaching into `app.state`."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from psycopg import Connection
from psycopg.rows import TupleRow

from fundlens.api.itemized import PAGE_SIZE, ItemizedReader
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


def get_itemized(request: Request) -> ItemizedReader:
    return request.app.state.itemized


def get_page_size() -> int:
    """Rows per `/contributions` page; a dependency so a test can page a small fixture."""
    return PAGE_SIZE


PoolDep = Annotated[Pool, Depends(get_pool)]
Conn = Annotated[Connection[TupleRow], Depends(get_conn)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
Itemized = Annotated[ItemizedReader, Depends(get_itemized)]
PageSize = Annotated[int, Depends(get_page_size)]
