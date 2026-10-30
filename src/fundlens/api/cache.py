"""Cache headers Cloudflare honours (spec §7.2, §10.2).

Every response is cacheable for an hour in a browser and a week at the edge, and carries the
live gold build as its `ETag`: the data changes only when a publish swaps a new build in, and
publish purges the zone. `/healthz` and server errors say `no-store` instead.

The build id is read from `gold.meta` at most once a minute per process, not once a request.
So for up to `BUILD_ID_TTL_SECONDS` after a swap a response can carry the new build's body under
the old build's `ETag`; the publish step's zone purge must come at least that long after the
swap (spec §5.5), or the edge can keep such a response for a week.
"""

import logging
import time
from collections.abc import Callable
from typing import Protocol

import psycopg
from anyio import to_thread
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fundlens.load.db import Pool

log = logging.getLogger(__name__)

CACHE_CONTROL = "public, max-age=3600, s-maxage=604800"
NO_STORE = "no-store"
UNCACHED_PATHS = frozenset({"/healthz"})
BUILD_ID_TTL_SECONDS = 60.0


def read_build_id(pool: Pool) -> str | None:
    """The live gold build, or None when no build has been published yet or Postgres cannot
    say: a response without an `ETag` is still a good response, so a failed read must not turn
    it into a 500."""
    try:
        with pool.connection() as conn:
            row = conn.execute("SELECT build_id FROM gold.meta").fetchone()
    except psycopg.errors.UndefinedTable:
        return None
    except psycopg.Error as exc:  # PoolTimeout included
        log.warning("cache: build id unreadable, sending no ETag: %s", exc)
        return None
    return None if row is None else str(row[0])


class BuildIdCache:
    """`read()`'s answer, refreshed once it is `ttl` seconds old."""

    def __init__(
        self,
        read: Callable[[], str | None],
        *,
        ttl: float = BUILD_ID_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._read = read
        self._ttl = ttl
        self._clock = clock
        self._value: str | None = None
        self._expires_at: float | None = None

    def get(self) -> str | None:
        # A failed read is kept for the ttl like any other answer, so while Postgres is down
        # each request does not wait out the pool's timeout again just to omit the ETag.
        now = self._clock()
        if self._expires_at is None or now >= self._expires_at:
            # Two requests racing here both read; either answer is current, so no lock.
            self._value = self._read()
            self._expires_at = now + self._ttl
        return self._value


class BuildIds(Protocol):
    def get(self) -> str | None: ...


class CacheHeaders:
    """ASGI middleware setting `Cache-Control` and `ETag` from `app.state.build_ids`.

    A response that already carries `Cache-Control` keeps it, so a route can opt out.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        build_ids: BuildIds = scope["app"].state.build_ids

        async def send_with_cache_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if scope["path"] in UNCACHED_PATHS or message["status"] >= 500:
                    headers["Cache-Control"] = NO_STORE
                elif "cache-control" not in headers:
                    headers["Cache-Control"] = CACHE_CONTROL
                    # A Postgres read, so off the event loop.
                    build_id = await to_thread.run_sync(build_ids.get)
                    if build_id is not None:
                        headers["ETag"] = f'"{build_id}"'
            await send(message)

        await self.app(scope, receive, send_with_cache_headers)
