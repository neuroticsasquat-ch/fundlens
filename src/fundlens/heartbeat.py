"""Uptime Kuma push client: one push monitor per job family (spec §10.3).

Kuma reads a push as `GET <url>?status=up|down&msg=…&ping=…`. It has no start signal and no
`/fail` path (those are healthchecks.io's), so `start()` sends nothing: it starts the clock that
`ok()` reports as the run's duration, and a run that hangs or never starts is caught by the
monitor's interval expiring. `fail()` is the `status=down` push.

Every push is best effort: one that cannot get out is logged and swallowed, so the deadman never
changes the outcome of the job it watches. With no URL configured every push is a no-op.
"""

import logging
import time
from collections.abc import Callable
from typing import Literal
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import urlopen

from fundlens.settings import Settings

log = logging.getLogger(__name__)

# The job families with a push monitor of their own: `fundlens/weekly` and `fundlens/publish`.
JobFamily = Literal["weekly", "publish"]

# Kuma stores the message whole; a traceback's worth of it helps nobody in an alert.
MAX_MESSAGE = 250

PUSH_TIMEOUT_SECONDS = 5.0

Send = Callable[[str], None]


def http_get(url: str) -> None:
    with urlopen(url, timeout=PUSH_TIMEOUT_SECONDS):
        pass


class Heartbeat:
    """Pushes one job family's outcomes to its Kuma monitor."""

    def __init__(
        self,
        url: str | None,
        *,
        send: Send = http_get,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = url
        self._send = send
        self._clock = clock
        self._started: float | None = None

    def start(self) -> None:
        """Start the clock `ok()` reports. Sends nothing: Kuma has no start signal."""
        self._started = self._clock()

    def ok(self, msg: str = "ok") -> None:
        """Push `status=up`, with the milliseconds since `start()` when it was called."""
        duration_ms = (
            None if self._started is None else round((self._clock() - self._started) * 1000)
        )
        self._push("up", msg, duration_ms)

    def fail(self, msg: str) -> None:
        """Push `status=down` with `msg` (truncated to `MAX_MESSAGE`)."""
        self._push("down", msg, None)

    def _push(self, status: Literal["up", "down"], msg: str, duration_ms: int | None) -> None:
        if not self._url:
            return
        params = {"status": status, "msg": msg[:MAX_MESSAGE]}
        if duration_ms is not None:
            params["ping"] = str(duration_ms)
        # Replaces any query already on the URL: Kuma's UI shows the push URL with
        # `?status=up&msg=OK&ping=` on the end, and a URL pasted whole must not leave a stale
        # `status=up` on a down.
        url = urlunsplit(urlsplit(self._url)._replace(query=urlencode(params)))
        try:
            self._send(url)
        except Exception as exc:
            # The exception's text only, never the URL: the token in its path is the
            # monitor's credential. `RedactingFilter` would scrub it, but there is no reason
            # to hand it the chance.
            log.warning("kuma push (%s) failed: %s: %s", status, type(exc).__name__, exc)


def heartbeat_for(
    family: JobFamily | None, settings: Settings, *, send: Send = http_get
) -> Heartbeat:
    """The heartbeat for `family`; a silent one for a job with no monitor of its own."""
    secret = {
        "weekly": settings.kuma_push_weekly,
        "publish": settings.kuma_push_publish,
        None: None,
    }[family]
    return Heartbeat(secret.get_secret_value() if secret else None, send=send)
