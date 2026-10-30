"""`fundlens extract`: one cycle's FEC bulk zips into R2 bronze (spec §3.3, §5.1; ADR-0002).

Each catalogued file FEC publishes for the cycle is checked with a HEAD of its URL: when its
`Last-Modified` and size match the metadata of the newest bronze object for that (cycle, file),
nothing is downloaded or uploaded. Otherwise the zip is streamed to the local cache, uploaded
to `bronze/cycle=<c>/<file>/<download date>.zip` with the source's `Last-Modified` and size as
object metadata, and dropped from disk unless the cycle is the current one, the only cycle kept
locally (spec §3.4). The current cycle's zip is also fetched back from R2 when only the disk
copy is missing, so transform finds it.
"""

import logging
import shutil
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from email.message import Message
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fundlens import markers, paths
from fundlens.fec.files import CATALOGUE, BulkFile, FecFile, current_cycle, files_for
from fundlens.r2 import R2

log = logging.getLogger(__name__)

# Object metadata on each bronze zip: what FEC served, to compare the next HEAD against.
LAST_MODIFIED = "source-last-modified"
SIZE = "source-size"

USER_AGENT = "fundlens (+https://fundlens.org)"
TIMEOUT_SECONDS = 60
CHUNK_BYTES = 1024 * 1024

# Five tries in all, 2 s apart and doubling: a transient FEC or S3 failure has about half a
# minute to clear before the step fails.
ATTEMPTS = 5
BACKOFF_SECONDS = 2.0

Sleep = Callable[[float], None]


class DownloadError(Exception):
    """A response that cannot be a whole zip: worth another try."""


@dataclass(frozen=True)
class Source:
    """What FEC says about one zip: enough to tell whether it changed since the last download."""

    last_modified: str
    size: int

    @classmethod
    def from_headers(cls, url: str, headers: Message) -> "Source":
        last_modified = headers.get("Last-Modified")
        size = headers.get("Content-Length")
        if not last_modified or not size:
            # Without both there is nothing to compare, and every run would download again.
            raise DownloadError(f"{url}: no Last-Modified or Content-Length")
        return cls(last_modified, int(size))

    @classmethod
    def from_metadata(cls, metadata: dict[str, str]) -> "Source | None":
        if LAST_MODIFIED not in metadata or SIZE not in metadata:
            return None
        return cls(metadata[LAST_MODIFIED], int(metadata[SIZE]))

    def metadata(self) -> dict[str, str]:
        return {LAST_MODIFIED: self.last_modified, SIZE: str(self.size)}


@dataclass(frozen=True)
class Extracted:
    """One file's outcome: the bronze object that now holds it, and whether it was downloaded."""

    file: FecFile
    key: str
    downloaded: bool


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, HTTPError):
        return exc.code in (408, 429) or exc.code >= 500
    # URLError covers a connection that never opened; the rest one that dropped mid-response.
    return isinstance(
        exc, URLError | HTTPException | ConnectionError | TimeoutError | DownloadError
    )


def _with_retries[T](what: str, attempt: Callable[[], T], sleep: Sleep) -> T:
    for n in range(1, ATTEMPTS + 1):
        try:
            return attempt()
        except Exception as exc:
            if n == ATTEMPTS or not _retryable(exc):
                raise
            delay = BACKOFF_SECONDS * 2 ** (n - 1)
            log.warning("%s failed (%s); try %d of %d in %.0f s", what, exc, n + 1, ATTEMPTS, delay)
            sleep(delay)
    raise AssertionError("unreachable")


def _request(url: str, method: str) -> Request:
    return Request(url, method=method, headers={"User-Agent": USER_AGENT})


def _head(url: str) -> Source:
    # urllib follows FEC's redirect to S3 and keeps the method HEAD.
    with urlopen(_request(url, "HEAD"), timeout=TIMEOUT_SECONDS) as response:
        return Source.from_headers(url, response.headers)


def _download(url: str, dest: Path) -> Source:
    """Stream `url` to `dest`, which appears only once the zip is whole (via a `.part` file)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    try:
        with urlopen(_request(url, "GET"), timeout=TIMEOUT_SECONDS) as response:
            # This response's own headers, not the HEAD's: the file may have changed in between.
            source = Source.from_headers(url, response.headers)
            with partial.open("wb") as out:
                shutil.copyfileobj(response, out, CHUNK_BYTES)
        received = partial.stat().st_size
        if received != source.size:
            raise DownloadError(f"{url}: got {received} of {source.size} bytes")
        if not zipfile.is_zipfile(partial):
            raise DownloadError(f"{url}: not a zip")
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(dest)
    return source


def _newest(store: R2, cycle: int, file: FecFile) -> tuple[str, Source | None] | None:
    """The newest bronze object for (cycle, file) and what FEC served for it, if there is one."""
    # Keys end in an ISO download date, so key order is download order.
    keys = sorted(store.list_keys(paths.bronze_dir(cycle, file)))
    if not keys:
        return None
    return keys[-1], Source.from_metadata(store.metadata(keys[-1]))


def _keep_only(directory: Path, keep: Path | None) -> None:
    """Delete every file in `directory` but `keep`: older downloads, and leftover `.part`s."""
    if not directory.is_dir():
        return
    for path in directory.iterdir():
        if path.is_file() and path != keep:
            path.unlink()


def _drop_historical(data_dir: Path, current: int) -> None:
    """Delete every cycle's local bronze but the current one's (spec §3.4).

    What keeps a cycle's zips off the disk once it has rolled over, and what a crashed
    historical extract left behind.
    """
    bronze = data_dir / "bronze"
    if not bronze.is_dir():
        return
    for cycle_dir in bronze.iterdir():
        if cycle_dir.is_dir() and cycle_dir.name != f"cycle={current}":
            shutil.rmtree(cycle_dir)


def extract_file(
    file: BulkFile,
    cycle: int,
    store: R2,
    *,
    data_dir: Path,
    base_url: str,
    today: date,
    sleep: Sleep = time.sleep,
) -> Extracted:
    """Bring one file for one cycle into bronze, unless bronze already holds what FEC serves."""
    url = file.url(base_url, cycle)
    keep_local = cycle == current_cycle(today)
    local_dir = paths.local_path(data_dir, paths.bronze_dir(cycle, file.name))

    remote = _with_retries(f"HEAD {url}", lambda: _head(url), sleep)
    newest = _newest(store, cycle, file.name)
    if newest is not None and newest[1] == remote:
        key = newest[0]
        local = paths.local_path(data_dir, key)
        # A copy cut short by a crash is fetched again, as a missing one is.
        if keep_local and (not local.exists() or local.stat().st_size != remote.size):
            store.download_to(key, local)
        _keep_only(local_dir, local if keep_local else None)
        log.info("%s %d unchanged since %s", file.name, cycle, key)
        return Extracted(file.name, key, downloaded=False)

    key = paths.bronze_zip(cycle, file.name, today)
    local = paths.local_path(data_dir, key)
    source = _with_retries(f"GET {url}", lambda: _download(url, local), sleep)
    try:
        store.put(key, local, metadata=source.metadata())
    finally:
        # Even when the upload fails: a historical zip never stays on disk.
        _keep_only(local_dir, local if keep_local else None)
    log.info("%s %d downloaded to %s (%d bytes)", file.name, cycle, key, source.size)
    return Extracted(file.name, key, downloaded=True)


def extract(
    cycle: int,
    store: R2,
    *,
    build_id: str,
    data_dir: Path,
    base_url: str,
    file: FecFile | None = None,
    today: date | None = None,
    sleep: Sleep = time.sleep,
) -> list[Extracted]:
    """Extract every file FEC publishes for `cycle` (or only `file`) into bronze.

    Writes the `extracted` marker for `build_id` only when every file was extracted: one file
    on its own is not the step finished.
    """
    started_at = datetime.now(UTC)
    today = today or started_at.date()
    if file is None:
        wanted = files_for(cycle)
    elif CATALOGUE[file].first_cycle > cycle:
        raise ValueError(f"FEC publishes no {file} file before {CATALOGUE[file].first_cycle}")
    else:
        wanted = [CATALOGUE[file]]
    _drop_historical(data_dir, current_cycle(today))
    results = [
        extract_file(
            bulk, cycle, store, data_dir=data_dir, base_url=base_url, today=today, sleep=sleep
        )
        for bulk in wanted
    ]
    if file is None:
        markers.write(
            "extracted",
            store,
            cycle=cycle,
            build_id=build_id,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            # Extract writes zips, not rows; transform counts those.
            row_counts={},
        )
    return results
