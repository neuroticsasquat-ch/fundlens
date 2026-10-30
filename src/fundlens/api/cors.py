"""An `Access-Control-Allow-Origin` on every response, not only those asked with an `Origin`.

Cloudflare caches every response under `api.fundlens.org` for a week and ignores
`Vary: Origin` (spec §10.2). Starlette's `CORSMiddleware` adds the header only when the request
carries an `Origin`, so the first request for a URL from curl or a crawler would be cached
without it, and the SPA's requests for that URL would then fail CORS until the next purge.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class DefaultAllowOrigin:
    """Sets `Access-Control-Allow-Origin: <origin>` on a response that has none.

    Inside `CORSMiddleware`, which still answers preflights and echoes any other allowed origin
    over this default.
    """

    def __init__(self, app: ASGIApp, origin: str) -> None:
        self.app = app
        self.origin = origin

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_origin(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("Access-Control-Allow-Origin", self.origin)
            await send(message)

        await self.app(scope, receive, send_with_origin)
