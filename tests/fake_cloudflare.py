"""A stand-in for Cloudflare's `purge_cache` endpoint: records every POST and answers from a
script, so a test can assert the request and drive the client's retries (spec §12: no network)."""

import json
from collections.abc import Mapping

from fundlens.publish.cloudflare import Response

ZONE, TOKEN = "z0ne1d", "cfPurg3Tok"
OK = Response(200, json.dumps({"success": True, "errors": [], "result": {"id": ZONE}}).encode())
DENIED = Response(
    403, json.dumps({"success": False, "errors": [{"code": 10000, "message": "denied"}]}).encode()
)
UPSTREAM = Response(500, b"upstream error")


class FakeCloudflare:
    """Answers each POST with the next scripted response; the last one repeats."""

    def __init__(self, *responses: Response) -> None:
        self.responses = list(responses) or [OK]
        self.posts: list[tuple[str, dict[str, str], bytes]] = []

    def __call__(self, url: str, headers: Mapping[str, str], body: bytes) -> Response:
        self.posts.append((url, dict(headers), body))
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
