"""The Cloudflare zone purge that follows a publish (spec §5.5, §10.2; NEU-2039 §4.3).

Every API response is cached at the edge for a week under the live build's `ETag`
(`api.cache`), so a new build is visible only once the zone is purged. One `POST` to
`purge_cache` with `purge_everything`, over `urllib` like `heartbeat` (no new dependency),
retried because a purge is idempotent. The token reaches a request header and nothing else:
not a log line, not an exception.
"""

import json
import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import partial
from typing import cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fundlens.settings import Settings

log = logging.getLogger(__name__)

PURGE_URL = "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
ATTEMPTS = 3
RETRY_SECONDS = 5.0
TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes


# `(url, headers, body) -> response`; the tests hand in a recorder.
Post = Callable[[str, Mapping[str, str], bytes], Response]
Sleep = Callable[[float], None]
# A configured purge, ready to call with nothing: what `publish` is handed, or None in dev.
Purge = Callable[[], None]


class PurgeFailed(Exception):
    """Every attempt failed: the edge may still serve the previous build (see §4.4, resume)."""


def http_post(url: str, headers: Mapping[str, str], body: bytes) -> Response:
    request = Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return Response(response.status, response.read())
    except HTTPError as exc:
        # A 4xx or 5xx is an answer, with Cloudflare's `errors` in its body.
        return Response(exc.code, exc.read())


def _outcome(response: Response) -> str | None:
    """None when Cloudflare reports success, else what went wrong."""
    try:
        payload: object = json.loads(response.body)
    except ValueError:
        payload = None
    fields = cast(dict[str, object], payload) if isinstance(payload, dict) else {}
    if response.status == 200 and fields.get("success") is True:
        return None
    errors = fields.get("errors")
    return f"HTTP {response.status}: {errors if errors else response.body[:200]!r}"


def purge_zone(
    zone_id: str, token: str, *, post: Post = http_post, sleep: Sleep = time.sleep
) -> None:
    """Purge everything in zone `zone_id`; raise `PurgeFailed` after `ATTEMPTS` failures."""
    url = PURGE_URL.format(zone_id=zone_id)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = json.dumps({"purge_everything": True}).encode()
    failure = ""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            failure = _outcome(post(url, headers, body)) or ""
        except OSError as exc:  # URLError and a timeout both are
            failure = f"{type(exc).__name__}: {exc}"
        if not failure:
            log.info("cloudflare zone %s purged", zone_id)
            return
        log.warning(
            "cloudflare purge of zone %s failed (attempt %d of %d): %s",
            zone_id,
            attempt,
            ATTEMPTS,
            failure,
        )
        if attempt < ATTEMPTS:
            sleep(RETRY_SECONDS)
    raise PurgeFailed(f"cloudflare purge of zone {zone_id} failed {ATTEMPTS} times: {failure}")


def purge_for(settings: Settings) -> Purge | None:
    """The zone purge the settings configure, or None (dev and CI have no zone)."""
    token = settings.cloudflare_api_token
    if not settings.cloudflare_zone_id or token is None or not token.get_secret_value():
        return None
    return partial(purge_zone, settings.cloudflare_zone_id, token.get_secret_value())
