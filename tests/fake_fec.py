"""A stand-in for FEC's bulk-download server, since tests never reach the network (spec §12).

Serves the files a test gives it, zips and CSVs, over real HTTP on localhost, with the
`Last-Modified`, `Content-Length` and `Content-Type` FEC's S3 bucket sends, and logs every
request so a test can assert what was (and was not) downloaded.
"""

import io
import threading
import zipfile
from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# What FEC's bucket sent for a 2024 file on the day this was written.
LAST_MODIFIED = "Fri, 30 Oct 2026 05:43:50 GMT"
ZIP = "application/zip"
CSV = "text/csv"


def zipped(member: str, text: str | bytes) -> bytes:
    """A zip holding one file, as FEC's bulk zips do."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, text)
    return buffer.getvalue()


class FakeFec:
    def __init__(self) -> None:
        # URL path → (body, Last-Modified, Content-Type).
        self.files: dict[str, tuple[bytes, str, str]] = {}
        # URL path → statuses to answer GETs with, in order, before serving the file.
        self.failures: dict[str, list[int]] = {}
        # (method, path) of every request, in arrival order.
        self.requests: list[tuple[str, str]] = []
        self.url = ""

    def serve(
        self, cycle: int, name: str, body: bytes | None = None, last_modified: str = LAST_MODIFIED
    ) -> str:
        """Publish `<name><yy>.zip` for `cycle`; its URL path."""
        return self.serve_path(
            f"/{cycle}/{name}{cycle % 100:02d}.zip",
            body or zipped(f"{name}.txt", f"{name}|{cycle}\n"),
            last_modified=last_modified,
        )

    def serve_path(
        self,
        path: str,
        body: bytes,
        *,
        content_type: str = ZIP,
        last_modified: str = LAST_MODIFIED,
    ) -> str:
        """Publish `body` at URL path `path` (`/2024/sample_2024.csv`); the path."""
        self.files[path] = (body, last_modified, content_type)
        return path

    def gets(self) -> list[str]:
        return [path for method, path in self.requests if method == "GET"]

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_HEAD(self) -> None:
                self._answer(with_body=False)

            def do_GET(self) -> None:
                self._answer(with_body=True)

            def _answer(self, *, with_body: bool) -> None:
                fake.requests.append((self.command, self.path))
                pending = fake.failures.get(self.path)
                if with_body and pending:
                    self.send_error(pending.pop(0))
                    return
                if self.path not in fake.files:
                    self.send_error(404)
                    return
                body, last_modified, content_type = fake.files[self.path]
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Last-Modified", last_modified)
                self.end_headers()
                if with_body:
                    self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                pass

        return Handler

    @contextmanager
    def running(self) -> Generator["FakeFec"]:
        server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{server.server_address[1]}"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield self
        finally:
            server.shutdown()
            server.server_close()
