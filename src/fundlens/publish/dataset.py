"""`fundlens dataset --snapshot`: publish the live build as an open dataset snapshot (spec §9).

A snapshot is a directory of the public bucket named for its date, `v1/<YYYY-MM-DD>/`:

- `<table>/cycle=<c>/*.parquet` for each silver table of `DATASET_TABLES`, every cycle's live
  build (`gold.meta.cycles`), copied object by object from the private bucket, server-side: the
  bytes never leave R2. A contribution build's `bucket=<xx>/part-<n>.parquet` becomes
  `bucket-<xx>-part-<n>.parquet`, so each cycle is one flat directory a reader globs. A
  backfill-pending table (`paths.BACKFILL_PENDING`, CONTEXT.md) may be missing from a live build
  transformed before it existed: that cycle has no files of it, and the manifest lists the table
  with the cycles that have it;
- `donor.parquet`, `gold.donor` (spec §7.1): the one dataset table with no cycle, since a donor
  spans every cycle they gave in, so it sits beside the crosswalk rather than under `cycle=`;
- `crosswalk.parquet`, the crosswalk as of the live build's publish
  (`resolution/build=<build_id>/crosswalk.parquet`, spec §5.5), not as `app.crosswalk` stands
  now, which a later resolve may have moved past what the live build holds;
- `overrides.yaml`, the manual merges and splits (`OVERRIDES_PATH`);
- `manifest.json` (`Manifest`), written last: a snapshot directory without one is unfinished.

Before it, on every run, the dataset's documentation (`DOCS`, from `docs/dataset/`) is put at
`v1/` wherever the bucket's copy differs, so the license and the 11 CFR 104.15 notice are there
before any data they cover and a corrected README goes out with the next run, snapshot or not.
A run whose documentation is not all there (`DocsMissing`) copies nothing.

Then `v1/latest/` is made a copy of the newest snapshot (R2 has no symlinks) and every snapshot
but the newest `KEEP` is deleted.

The two bulk copies, of the silver files into the snapshot and of the snapshot into `latest/`,
run `workers` objects at a time (`DATASET_COPY_WORKERS`, NEU-2067): one at a time, the first full
snapshot took 3h41m, nearly all of it server-side copies. Every partition is listed and checked
before the first copy, and the manifest is the same at any worker count.

Idempotent per date: when the day's manifest exists, nothing is copied again, `latest/` is
copied only if its manifest is not the newest snapshot's, and a second run the same day writes
nothing. A snapshot that crashed before its manifest is cleared and taken again.
"""

import hashlib
import logging
import shutil
import time
from collections.abc import Callable, Sequence
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import psycopg
from psycopg import Connection
from psycopg.rows import TupleRow
from pydantic import BaseModel

from fundlens import paths
from fundlens.paths import SilverTable
from fundlens.publish.dataset_schema import SCHEMA_DIR
from fundlens.r2 import MULTIPART_BYTES, R2, Listed, multipart_etag
from fundlens.transform.runner import literal

log = logging.getLogger(__name__)

# The silver tables of the dataset (spec §9), in the manifest's order. `jfc_attribution` is
# evidence, never money (spec §6.11), and stays out.
DATASET_TABLES: tuple[SilverTable, ...] = (
    "contribution",
    "contributor",
    "committee",
    "candidate",
    "candidate_committee_link",
    "race",
    "independent_expenditure",
    "committee_transfer",
    "organization_receipt",
)
# How many snapshots the public bucket keeps (spec §9).
KEEP = 8
MANIFEST = "manifest.json"
DONOR = "donor.parquet"
CROSSWALK = "crosswalk.parquet"
OVERRIDES = "overrides.yaml"
LICENSE = "CC BY 4.0"
ATTRIBUTION = "fundlens (fundlens.org), CC BY 4.0"
# Every table a manifest lists, each with a schema at `schema/<table>.json`.
MANIFEST_TABLES: tuple[str, ...] = (*DATASET_TABLES, "donor", "crosswalk")
# The documentation beside the snapshots (spec §9): each file's path below `docs/dataset/`, which
# is its path below `v1/`, and the type it is served as. Then a schema per manifest table.
DOCS: dict[str, str] = {
    "README.md": "text/markdown; charset=utf-8",
    "LICENSE": "text/plain; charset=utf-8",
    "CHANGELOG.md": "text/markdown; charset=utf-8",
}
_SCHEMA_TYPE = "application/json"
# `manifest.json`'s, which the copy into `latest/` keeps.
_MANIFEST_TYPE = "application/json"

# `gold.donor` (sql/gold/ddl/donor.sql) as Postgres writes it in CSV, typed for DuckDB.
_DONOR_COLUMNS = (
    "donor_id",
    "display_name",
    "employer",
    "occupation",
    "city",
    "state",
    "zip5",
    "total_all_cycles",
    "first_cycle",
    "last_cycle",
    "contributor_key_count",
)
_DONOR_TYPES = (
    "{'donor_id': 'BIGINT', 'display_name': 'VARCHAR', 'employer': 'VARCHAR',"
    " 'occupation': 'VARCHAR', 'city': 'VARCHAR', 'state': 'VARCHAR', 'zip5': 'VARCHAR',"
    " 'total_all_cycles': 'DECIMAL(16,2)', 'first_cycle': 'INTEGER', 'last_cycle': 'INTEGER',"
    " 'contributor_key_count': 'INTEGER'}"
)
_CSV = """header = false, delim = ',', quote = '"', escape = '"', auto_detect = false"""


class NothingPublished(Exception):
    """No live gold build to take a snapshot of."""


class BuildNotReady(Exception):
    """The live build lacks a table the dataset needs (a backfill-pending one aside), holds no
    Parquet of one, or is being rewritten."""


class DocsMissing(Exception):
    """A file of the dataset's documentation is not there to publish beside it."""


class ManifestFile(BaseModel):
    # Relative to the snapshot's directory, so the manifest holds for `latest/` too.
    path: str
    sha256: str
    bytes: int


class ManifestTable(BaseModel):
    rows: int
    files: list[ManifestFile]


class Manifest(BaseModel):
    """`manifest.json`, the M6 shared contract: what a snapshot holds and how to check it."""

    snapshot_date: date
    # The build `gold` was last published from; `cycles` is each cycle's live build.
    build_id: str
    cycles: dict[int, str]
    tables: dict[str, ManifestTable]
    overrides: ManifestFile
    # Resolution quality against DIME (spec §6.9), None when the live model is unvalidated.
    precision: float | None
    recall: float | None
    license: str = LICENSE
    attribution: str = ATTRIBUTION


@dataclass(frozen=True)
class Snapshot:
    """What `snapshot` did."""

    snapshot_date: date
    build_id: str
    # False when the day's snapshot existed already.
    created: bool
    # Whether `latest/` was copied: False when it held the newest snapshot already.
    latest_copied: bool
    # The snapshots deleted as beyond the newest `KEEP`, oldest first.
    removed: list[date]
    # The documentation's keys put, because the bucket lacked them or held other bytes.
    docs_put: list[str]


@dataclass(frozen=True)
class _Live:
    build_id: str
    cycles: dict[int, str]
    precision: float | None
    recall: float | None


@dataclass(frozen=True)
class _Digest:
    sha256: str
    rows: int


@dataclass(frozen=True)
class _SilverCopy:
    """One silver object a snapshot copies: from `obj` in the private bucket to `path` below the
    snapshot's directory, hashed from `local` when that is R2's copy byte for byte."""

    table: SilverTable
    obj: Listed
    path: str
    local: Path


def _pooled[T, R](fn: Callable[[T], R], items: Sequence[T], *, workers: int) -> list[R]:
    """`fn` of every item, `workers` at a time, in `items`' order (so a manifest is the same at
    any worker count). On the first exception, the calls not started are cancelled, those in
    flight finish, and it is raised."""
    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        futures = [pool.submit(fn, item) for item in items]
        done, _ = wait(futures, return_when=FIRST_EXCEPTION)
        for future in futures:
            if future in done and (exc := future.exception()) is not None:
                raise exc
        return [future.result() for future in futures]
    finally:
        pool.shutdown(cancel_futures=True)


def _live(conn: Connection[TupleRow]) -> _Live:
    """The live build, from `gold.meta`. Raises `NothingPublished` when there is none."""
    try:
        row = conn.execute("SELECT build_id, cycles, precision, recall FROM gold.meta").fetchone()
    except psycopg.errors.UndefinedTable as exc:
        raise NothingPublished("no live gold build: run `fundlens publish` first") from exc
    if row is None:
        raise NothingPublished("gold.meta holds no build: run `fundlens publish` first")
    build_id, cycles, precision, recall = row
    return _Live(
        build_id=str(build_id),
        cycles={int(cycle): entry["build_id"] for cycle, entry in sorted(cycles.items())},
        precision=None if precision is None else float(precision),
        recall=None if recall is None else float(recall),
    )


def _hash(path: Path, etag: str | None = None) -> tuple[str, bool]:
    """`path`'s SHA-256, and whether its bytes are the object whose ETag is `etag` (False when
    `etag` is None)."""
    sha256 = hashlib.sha256()
    whole = hashlib.md5()
    parts: list[bytes] = []
    with path.open("rb") as file:
        while chunk := file.read(MULTIPART_BYTES):
            sha256.update(chunk)
            whole.update(chunk)
            parts.append(hashlib.md5(chunk).digest())
    if etag is None:
        matches = False
    elif "-" in etag:
        # Put or copied in parts, which `R2` sizes at `MULTIPART_BYTES`.
        matches = etag == multipart_etag(parts)
    else:
        matches = etag == whole.hexdigest()
    return sha256.hexdigest(), matches


def _rows(path: Path) -> int:
    with duckdb.connect() as con:
        row = con.execute(
            f"SELECT sum(num_rows)::BIGINT FROM parquet_file_metadata({literal(path)})"
        ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _digest(store: R2, obj: Listed, *, local: Path | None, download: Path) -> _Digest:
    """`obj`'s SHA-256 and rows, from `local`, the local cache's copy, when it is R2's byte for
    byte (its ETag says so), else from a download to `download`, a path of this object's own (the
    snapshot hashes several at once), deleted after. S3 keeps no SHA-256 of an object."""
    if local is not None and local.is_file() and local.stat().st_size == obj.size:
        sha256, matches = _hash(local, obj.etag)
        if matches:
            return _Digest(sha256, _rows(local))
    log.info("hashing %s from R2: no local copy matches it", obj.key)
    download = store.download_to(obj.key, download)
    try:
        sha256, _ = _hash(download)
        return _Digest(sha256, _rows(download))
    finally:
        download.unlink(missing_ok=True)


def _flat(relative: str) -> str:
    """A part's path below its partition as one file name: `bucket=0a/part-0000.parquet` is
    `bucket-0a-part-0000.parquet`."""
    return relative.replace("=", "-").replace("/", "-")


def _silver_copies(live: _Live, store: R2, *, data_dir: Path) -> list[_SilverCopy]:
    """Every object of every cycle's live partition of each table of `DATASET_TABLES`, in the
    manifest's order; none for a backfill-pending table a cycle's live build lacks, R2 holding
    nothing under its partition. Raises `BuildNotReady`, before the snapshot copies anything, when
    a partition is having its donor ids rewritten or holds no Parquet, or a table that is not
    backfill-pending is missing."""
    copies: list[_SilverCopy] = []
    for table in DATASET_TABLES:
        for cycle, build_id in live.cycles.items():
            partition = paths.silver_partition(table, cycle, build_id) + "/"
            objects = store.list_objects(partition)
            if not objects and table in paths.BACKFILL_PENDING:
                log.info(
                    "the live build %s of %s has no %s: backfill-pending, not in the snapshot",
                    build_id,
                    cycle,
                    table,
                )
                continue
            if table == "contribution" and any(
                obj.key == paths.rewrite_sentinel(cycle, build_id) for obj in objects
            ):
                raise BuildNotReady(
                    f"build {build_id} of {cycle} is having its donor ids rewritten: snapshot it"
                    " once `fundlens resolve` has finished"
                )
            parts = [obj for obj in objects if obj.key.endswith(".parquet")]
            if not parts:
                raise BuildNotReady(f"the live build {build_id} of {cycle} has no {table}")
            copies.extend(
                _SilverCopy(
                    table=table,
                    obj=obj,
                    path=f"{table}/cycle={cycle}/{_flat(obj.key.removeprefix(partition))}",
                    local=paths.local_path(data_dir, obj.key),
                )
                for obj in parts
            )
    return copies


def _silver_tables(
    live: _Live,
    store: R2,
    public: R2,
    *,
    root: str,
    data_dir: Path,
    work: Path,
    workers: int,
) -> dict[str, ManifestTable]:
    """Hash and copy every table's live partitions under `root`, `workers` objects at a time;
    their manifest entries, by table."""
    copies = _silver_copies(live, store, data_dir=data_dir)

    def copy(job: _SilverCopy) -> _Digest:
        digest = _digest(store, job.obj, local=job.local, download=work / _flat(job.path))
        # Only the bytes just hashed: a rewrite since then fails the copy.
        public.copy_from(store, job.obj.key, root + job.path, if_match=job.obj.etag)
        return digest

    started = time.monotonic()
    digests = _pooled(copy, copies, workers=workers)
    log.info(
        "hashed and copied %d objects to %s in %.0fs, %d at a time",
        len(copies),
        root,
        time.monotonic() - started,
        workers,
    )
    files: dict[str, list[ManifestFile]] = {table: [] for table in DATASET_TABLES}
    rows = dict.fromkeys(DATASET_TABLES, 0)
    for job, digest in zip(copies, digests, strict=True):
        files[job.table].append(
            ManifestFile(path=job.path, sha256=digest.sha256, bytes=job.obj.size)
        )
        rows[job.table] += digest.rows
    return {table: ManifestTable(rows=rows[table], files=files[table]) for table in DATASET_TABLES}


def _put(public: R2, root: str, name: str, local: Path, *, rows: int) -> ManifestTable:
    """Put the local file `local` at `root + name`; its manifest entry."""
    sha256, _ = _hash(local)
    public.put(root + name, local)
    file = ManifestFile(path=name, sha256=sha256, bytes=local.stat().st_size)
    return ManifestTable(rows=rows, files=[file])


def _donor(conn: Connection[TupleRow], work: Path) -> Path:
    """`gold.donor` as Parquet in `work`."""
    csv, parquet = work / "donor.csv", work / DONOR
    columns = ", ".join(_DONOR_COLUMNS)
    with (
        conn.cursor() as cur,
        cur.copy(
            f"COPY (SELECT {columns} FROM gold.donor ORDER BY donor_id) TO STDOUT (FORMAT csv)"
        ) as copy,
        csv.open("wb") as out,
    ):
        for chunk in copy:
            out.write(chunk)
    with duckdb.connect() as con:
        con.execute(
            f"COPY (SELECT * FROM read_csv({literal(csv)}, {_CSV},"
            f" columns = {_DONOR_TYPES})) TO {literal(parquet)}"
            " (FORMAT parquet, COMPRESSION zstd)"
        )
    csv.unlink()
    return parquet


def _crosswalk(live: _Live, store: R2, public: R2, *, root: str, work: Path) -> ManifestTable:
    """Copy the crosswalk as of the live build's publish to `root`; its manifest entry."""
    key = paths.resolution_snapshot(live.build_id, "crosswalk")
    listed = [obj for obj in store.list_objects(key) if obj.key == key]
    if not listed:
        raise BuildNotReady(
            f"no crosswalk snapshot for the live build {live.build_id} ({key}): re-run its"
            " `fundlens publish`"
        )
    obj = listed[0]
    # Never in the local cache: `publish` writes it from scratch space it then clears.
    digest = _digest(store, obj, local=None, download=work / CROSSWALK)
    public.copy_from(store, key, root + CROSSWALK, if_match=obj.etag)
    file = ManifestFile(path=CROSSWALK, sha256=digest.sha256, bytes=obj.size)
    return ManifestTable(rows=digest.rows, files=[file])


def _take(
    live: _Live,
    conn: Connection[TupleRow],
    store: R2,
    public: R2,
    *,
    root: str,
    snapshot_date: date,
    data_dir: Path,
    overrides_path: Path,
    workers: int,
) -> None:
    """Write the snapshot's files under `root`, its manifest last."""
    # Whatever a crashed attempt left: it may have been of another live build.
    public.delete_prefix(root)
    work = paths.scratch_dir(data_dir) / f"dataset-{snapshot_date.isoformat()}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        tables = _silver_tables(
            live, store, public, root=root, data_dir=data_dir, work=work, workers=workers
        )
        donor = _donor(conn, work)
        tables["donor"] = _put(public, root, DONOR, donor, rows=_rows(donor))
        tables["crosswalk"] = _crosswalk(live, store, public, root=root, work=work)
        overrides = _put(public, root, OVERRIDES, overrides_path, rows=0).files[0]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    manifest = Manifest(
        snapshot_date=snapshot_date,
        build_id=live.build_id,
        cycles=live.cycles,
        tables=tables,
        overrides=overrides,
        precision=live.precision,
        recall=live.recall,
    )
    public.put(
        root + MANIFEST,
        manifest.model_dump_json(indent=2).encode(),
        content_type=_MANIFEST_TYPE,
    )


def snapshot_dates(public: R2) -> list[date]:
    """The date of every snapshot directory in the public bucket, oldest first."""
    found = (paths.snapshot_date_of(prefix) for prefix in public.list_dirs(paths.DATASET_PREFIX))
    return sorted(found_date for found_date in found if found_date is not None)


def _refresh_latest(public: R2, *, workers: int) -> bool:
    """Make `latest/` a copy of the newest finished snapshot, `workers` objects at a time;
    whether anything was copied.

    The manifest goes last, alone, so a `latest/manifest.json` naming a snapshot means its files are
    all there; then whatever the previous snapshot had that this one lacks is deleted.
    """
    newest = next(
        (
            root
            for root in map(paths.dataset_snapshot, reversed(snapshot_dates(public)))
            if public.exists(root + MANIFEST)
        ),
        None,
    )
    if newest is None:
        return False
    keys = public.list_keys(newest)
    wanted = {paths.DATASET_LATEST + key.removeprefix(newest) for key in keys}
    try:
        current = public.get(paths.DATASET_LATEST + MANIFEST)
    except FileNotFoundError:
        current = None
    copied = current != public.get(newest + MANIFEST)
    if copied:

        def copy(key: str) -> None:
            public.copy_from(public, key, paths.DATASET_LATEST + key.removeprefix(newest))

        manifest = newest + MANIFEST
        started = time.monotonic()
        _pooled(copy, [key for key in keys if key != manifest], workers=workers)
        copy(manifest)
        log.info(
            "copied %d objects to %s in %.0fs, %d at a time",
            len(keys),
            paths.DATASET_LATEST,
            time.monotonic() - started,
            workers,
        )
        log.info("latest/ is now %s", newest)
    stale = [key for key in public.list_keys(paths.DATASET_LATEST) if key not in wanted]
    public.delete_keys(stale)
    return copied


def _docs(docs_dir: Path) -> dict[str, Path]:
    """The documentation to publish, by its path below `v1/`: `DOCS` and a schema of every
    manifest table. Raises `DocsMissing` when `docs_dir` lacks one."""
    names = [*DOCS, *(f"{SCHEMA_DIR}/{table}.json" for table in MANIFEST_TABLES)]
    missing = [name for name in names if not (docs_dir / name).is_file()]
    if missing:
        raise DocsMissing(
            f"{docs_dir} lacks {', '.join(missing)}: the dataset is never published without its"
            " license, notice and schemas"
        )
    return {name: docs_dir / name for name in names}


def publish_docs(public: R2, docs_dir: Path) -> list[str]:
    """Put the documentation in `docs_dir` at `v1/` wherever the bucket's copy differs, and
    delete each schema there that is no manifest table's; the keys put. Raises `DocsMissing`
    when `docs_dir` lacks a file of it, before anything is put."""
    docs = _docs(docs_dir)
    schemas = paths.DATASET_PREFIX + SCHEMA_DIR + "/"
    held = {
        obj.key: obj.etag
        for prefix in [*(paths.DATASET_PREFIX + name for name in DOCS), schemas]
        for obj in public.list_objects(prefix)
    }
    put: list[str] = []
    for name, local in docs.items():
        key = paths.DATASET_PREFIX + name
        etag = held.get(key)
        if etag is not None and _hash(local, etag)[1]:
            continue
        public.put(key, local, content_type=DOCS.get(name, _SCHEMA_TYPE))
        put.append(key)
    wanted = {paths.DATASET_PREFIX + name for name in docs}
    public.delete_keys([key for key in held if key.startswith(schemas) and key not in wanted])
    if put:
        log.info("put %d documentation files at %s", len(put), paths.DATASET_PREFIX)
    return put


def _retain(public: R2) -> list[date]:
    """Delete every finished snapshot but the newest `KEEP`, and every unfinished one (a crashed
    attempt never retried that day, which no reader should take for a snapshot); the dates
    deleted. Called once the day's own snapshot is finished."""
    dates = snapshot_dates(public)
    finished = [day for day in dates if public.exists(paths.dataset_snapshot(day) + MANIFEST)]
    unfinished = [day for day in dates if day not in finished]
    removed = sorted(unfinished + (finished[:-KEEP] if len(finished) > KEEP else []))
    for removed_date in removed:
        objects = public.delete_prefix(paths.dataset_snapshot(removed_date))
        log.info("removed snapshot %s (%d objects)", removed_date, objects)
    return removed


def snapshot(
    conn: Connection[TupleRow],
    store: R2,
    public: R2,
    *,
    snapshot_date: date,
    data_dir: Path,
    overrides_path: Path,
    docs_dir: Path,
    workers: int,
) -> Snapshot:
    """Publish the documentation in `docs_dir` (`publish_docs`), then take the live build's
    dataset snapshot for `snapshot_date` from `store` into `public`, unless it exists; then
    refresh `latest/` and delete all but the newest `KEEP` snapshots. The copies into the
    snapshot and into `latest/` run `workers` at a time.

    Raises `NothingPublished` when no gold build is live, `DocsMissing` when `docs_dir` lacks a
    file of the documentation, and `BuildNotReady` when the live build lacks a dataset table
    (a backfill-pending one aside) or its crosswalk snapshot, or its contributions are being
    rewritten.
    """
    live = _live(conn)
    docs_put = publish_docs(public, docs_dir)
    root = paths.dataset_snapshot(snapshot_date)
    created = not public.exists(root + MANIFEST)
    build_id = live.build_id
    if created:
        _take(
            live,
            conn,
            store,
            public,
            root=root,
            snapshot_date=snapshot_date,
            data_dir=data_dir,
            overrides_path=overrides_path,
            workers=workers,
        )
        log.info("took snapshot %s of build %s", snapshot_date, live.build_id)
    else:
        # The build it holds, which a publish since may have replaced.
        build_id = Manifest.model_validate_json(public.get(root + MANIFEST)).build_id
        log.info("snapshot %s of build %s exists already: not taken again", snapshot_date, build_id)
    latest_copied = _refresh_latest(public, workers=workers)
    removed = _retain(public)
    return Snapshot(snapshot_date, build_id, created, latest_copied, removed, docs_put)
