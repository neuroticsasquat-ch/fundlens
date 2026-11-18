"""What `GET /v1/dataset` lists: the finished snapshots in the public bucket (spec §9).

Read from each snapshot's `manifest.json`, which the publisher writes last
(`publish.dataset`), so a snapshot directory without one is unfinished and not listed. The
public bucket is read with the API's own credentials, not over `data.fundlens.org`.

Not cached per gold build, unlike every other route: `run --dataset` takes the snapshot after
`publish` has swapped the build in and purged the zone, so a list cached under the new build
would leave out the snapshot taken of it until the next week's publish. Instead the list is
re-read at most once a minute per process (`TtlCache`), and the route sends its own
`DATASET_CACHE_CONTROL`, with no `ETag`, so the edge holds it for minutes, not a week. A
manifest is fetched only when its ETag is new: re-reading the list costs a listing of `v1/`
and of each snapshot's manifest key, not the manifests themselves.
"""

import logging
import re
import threading

from pydantic import ValidationError

from fundlens import paths
from fundlens.api.cache import TtlCache
from fundlens.api.schemas import Dataset, DatasetPart, DatasetSnapshot, DatasetTable
from fundlens.publish.dataset import MANIFEST, Manifest, ManifestFile, snapshot_dates
from fundlens.r2 import R2

log = logging.getLogger(__name__)

# Where `data.fundlens.org` serves the public bucket's `v1/` (spec §9).
PUBLIC_URL = "https://data.fundlens.org/v1/"
DATASET_CACHE_CONTROL = "public, max-age=300, s-maxage=300"
LIST_TTL_SECONDS = 60.0

# A cycled table's file: `contribution/cycle=2024/bucket-0a-part-0000.parquet`.
_PARTITIONED = re.compile(r"(?P<dir>[^/]+/cycle=(?P<cycle>\d+)/)[^/]+")


def summarize(manifest: Manifest) -> DatasetSnapshot:
    """A snapshot's entry in the list: its manifest's tables, each file counted into its
    cycle's part."""
    tables: list[DatasetTable] = []
    for name, table in manifest.tables.items():
        # Each part's files by its directory, or by the file's own path when it has no cycle.
        grouped: dict[tuple[str, int | None], list[ManifestFile]] = {}
        for file in table.files:
            match = _PARTITIONED.fullmatch(file.path)
            key = (file.path, None) if match is None else (match["dir"], int(match["cycle"]))
            grouped.setdefault(key, []).append(file)
        parts = [
            DatasetPart(
                cycle=cycle,
                # One file is linked to, which a browser can download; a directory it cannot.
                path=files[0].path if len(files) == 1 else path,
                files=len(files),
                bytes=sum(file.bytes for file in files),
            )
            for (path, cycle), files in grouped.items()
        ]
        tables.append(
            DatasetTable(
                name=name,
                rows=table.rows,
                files=len(table.files),
                bytes=sum(file.bytes for file in table.files),
                parts=parts,
            )
        )
    snapshot_date = manifest.snapshot_date
    return DatasetSnapshot(
        snapshot_date=snapshot_date,
        url=f"{PUBLIC_URL}{snapshot_date.isoformat()}/",
        build_id=manifest.build_id,
        cycles=sorted(manifest.cycles, reverse=True),
        tables=tables,
        precision=manifest.precision,
        recall=manifest.recall,
        license=manifest.license,
        attribution=manifest.attribution,
    )


class DatasetIndex:
    """The public bucket's finished snapshots, re-read at most every `ttl` seconds."""

    def __init__(self, public: R2, *, ttl: float = LIST_TTL_SECONDS) -> None:
        self._public = public
        # Manifest key → its ETag and its summary. Guarded, since routes run in a thread pool.
        self._read_manifests: dict[str, tuple[str, DatasetSnapshot]] = {}
        self._lock = threading.Lock()
        self._list = TtlCache(self._read, ttl=ttl)

    def get(self) -> Dataset:
        return self._list.get()

    def _manifest(self, key: str) -> DatasetSnapshot | None:
        """The manifest at `key`, summarized; None when there is none, or none this code can
        read, so one snapshot never takes the whole list down."""
        listed = [obj for obj in self._public.list_objects(key) if obj.key == key]
        if not listed:
            return None
        etag = listed[0].etag
        with self._lock:
            held = self._read_manifests.get(key)
        if held is not None and held[0] == etag:
            return held[1]
        try:
            manifest = Manifest.model_validate_json(self._public.get(key))
        except FileNotFoundError:
            # Deleted since the listing: retention, or a retake clearing its unfinished day.
            return None
        except ValidationError as exc:
            log.warning("dataset: %s is no manifest this API reads, leaving it out: %s", key, exc)
            return None
        summary = summarize(manifest)
        with self._lock:
            self._read_manifests[key] = (etag, summary)
        return summary

    def _read(self) -> Dataset:
        keys = [
            paths.dataset_snapshot(day) + MANIFEST for day in reversed(snapshot_dates(self._public))
        ]
        snapshots = [summary for key in keys if (summary := self._manifest(key)) is not None]
        latest_key = paths.DATASET_LATEST + MANIFEST
        latest = self._manifest(latest_key)
        with self._lock:
            # A snapshot deleted since is forgotten.
            for key in self._read_manifests.keys() - {*keys, latest_key}:
                del self._read_manifests[key]
        return Dataset(
            base_url=PUBLIC_URL,
            latest=None if latest is None else latest.snapshot_date,
            snapshots=snapshots,
        )
