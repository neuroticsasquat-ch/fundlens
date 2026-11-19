"""`fundlens dataset --snapshot` against MinIO, with a private and a public bucket (spec §9).

The fixture cycle is resolved, loaded and published once for the module, into a private bucket
and database of the module's own; each test snapshots it into an empty public bucket.

Here too the committed schemas (`docs/dataset/schema/`) are checked against that snapshot's files,
the README's DuckDB one-liner is run against it over plain HTTP (NEU-2065), and `GET /v1/dataset`
lists it (NEU-2066).
"""

import hashlib
import json
import os
import re
import shutil
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import duckdb
import psycopg
import pytest
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from fundlens import cli, paths, r2
from fundlens.api.app import create_app
from fundlens.api.dataset import DATASET_CACHE_CONTROL, PUBLIC_URL, DatasetIndex, summarize
from fundlens.api.schemas import Dataset
from fundlens.paths import SilverTable
from fundlens.publish import dataset, dataset_schema
from fundlens.publish.dataset import DATASET_TABLES, BuildNotReady, DocsMissing, Manifest
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import literal
from tests import fec_fixture

# Pipeline state saved for the session: not a dataset snapshot (CONTEXT.md), whence the name.
from tests.integration.conftest import Snapshot as SavedState
from tests.integration.conftest import (
    bucket_name,
    cli_pointed_at,
    copy_files,
    empty_store,
    scratch_database,
)
from tests.integration.test_transform import BUILD

CYCLE = fec_fixture.CYCLE
DAY = date(2026, 11, 22)
REPO_ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = REPO_ROOT / "resolution" / "overrides.yaml"
DOCS = REPO_ROOT / "docs" / "dataset"
# Set by `task dataset:schema`: write the schemas rather than check them.
WRITE_SCHEMAS = os.environ.get("DATASET_SCHEMA_WRITE") == "1"
# The copies a snapshot runs at once, unless a test says otherwise (NEU-2067).
WORKERS = 4


def run(*args: str) -> Any:
    result = CliRunner().invoke(cli.app, list(args))
    assert result.exit_code == 0, result.output
    return result


@dataclass(frozen=True)
class Published:
    """The module's private bucket, database and `DATA_DIR`, the fixture cycle live in them."""

    store: R2
    conninfo: str
    data_dir: Path


@pytest.fixture(scope="module")
def published(
    resolved_snapshot: SavedState, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Published]:
    """`resolved_snapshot`, loaded and published as build `BUILD`."""
    data_dir = tmp_path_factory.mktemp("dataset")
    store = empty_store(bucket_name("dataset"))
    try:
        copy_files(resolved_snapshot, store=store, data_dir=data_dir)
        with scratch_database(template=resolved_snapshot.database) as conninfo:
            with cli_pointed_at(conninfo=conninfo, data_dir=data_dir, bucket=store.bucket) as env:
                env.delenv("CLOUDFLARE_ZONE_ID", raising=False)
                run("load", "--cycle", str(CYCLE), "--build-id", BUILD)
                run("publish", "--cycle", str(CYCLE), "--build-id", BUILD)
            yield Published(store, conninfo, data_dir)
    finally:
        store.delete_prefix("")


@pytest.fixture
def public() -> Iterator[R2]:
    """An empty public bucket of the test's own."""
    bucket = empty_store(bucket_name("public"))
    yield bucket
    bucket.delete_prefix("")


def take(
    published: Published,
    public: R2,
    day: date = DAY,
    *,
    data_dir: Path | None = None,
    docs_dir: Path = DOCS,
    workers: int = WORKERS,
) -> dataset.Snapshot:
    with psycopg.connect(published.conninfo, autocommit=True) as conn:
        return dataset.snapshot(
            conn,
            published.store,
            public,
            snapshot_date=day,
            data_dir=data_dir or published.data_dir,
            overrides_path=OVERRIDES,
            docs_dir=docs_dir,
            workers=workers,
        )


class InFlight:
    """`R2.copy_from`, counting the copies in flight at once into each of the snapshot's
    directory and `latest/`.

    Each copy waits until another one into the same directory is in flight before it runs, so
    overlap is observed, never inferred from elapsed time (NEU-2340). A copy that waits 5 s for
    company stops the waiting for every copy into its directory after it, so a pass that copies one
    at a time fails rather than hangs, and an odd number of objects never strands the last one.
    """

    def __init__(self) -> None:
        self._copy = R2.copy_from
        self._lock = threading.Lock()
        self._now: dict[str, int] = {}
        self._company = {into: threading.Event() for into in ("snapshot", paths.DATASET_LATEST)}
        self.most: dict[str, int] = {}

    def copy_from(
        self, target: R2, source: R2, key: str, dest: str, *, if_match: str | None = None
    ) -> None:
        into = paths.DATASET_LATEST if dest.startswith(paths.DATASET_LATEST) else "snapshot"
        with self._lock:
            self._now[into] = self._now.get(into, 0) + 1
            self.most[into] = max(self.most.get(into, 0), self._now[into])
            if self._now[into] > 1:
                self._company[into].set()
        try:
            if not self._company[into].wait(timeout=5):
                self._company[into].set()
            self._copy(target, source, key, dest, if_match=if_match)
        finally:
            with self._lock:
                self._now[into] -= 1


@dataclass(frozen=True)
class Taken:
    """A public bucket holding the module's one snapshot, of `DAY`, what taking it did, and the
    most copies it had in flight at once into each directory."""

    public: R2
    result: dataset.Snapshot
    most_in_flight: dict[str, int]


@pytest.fixture(scope="module")
def taken(published: Published) -> Iterator[Taken]:
    """`DAY`'s snapshot of `published`, `WORKERS` copies at a time, taken once for the tests that
    only read it (each snapshot copies every file)."""
    public = empty_store(bucket_name("public-taken"))
    observed = InFlight()
    try:

        def copy_from(
            target: R2, source: R2, key: str, dest: str, *, if_match: str | None = None
        ) -> None:
            observed.copy_from(target, source, key, dest, if_match=if_match)

        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(R2, "copy_from", copy_from)
            result = take(published, public)
        yield Taken(public, result, observed.most)
    finally:
        public.delete_prefix("")


def manifest(public: R2, root: str) -> Manifest:
    return Manifest.model_validate_json(public.get(root + dataset.MANIFEST))


def silver_rows(data_dir: Path, table: SilverTable) -> int:
    partition = paths.local_path(data_dir, paths.silver_partition(table, CYCLE, BUILD))
    with duckdb.connect() as con:
        row = con.execute(
            "SELECT count(*) FROM read_parquet(?, hive_partitioning = false)",
            [f"{partition}/**/*.parquet"],
        ).fetchone()
    assert row is not None
    return int(row[0])


def scalar(conninfo: str, query: str) -> int:
    with psycopg.connect(conninfo) as conn:
        row = conn.execute(query.encode()).fetchone()
    assert row is not None
    return int(row[0])


def listing(public: R2) -> dict[str, tuple[str, Any]]:
    """Every object of the bucket, as its ETag and last-modified time."""
    found: dict[str, tuple[str, Any]] = {}
    for page in public.client.get_paginator("list_objects_v2").paginate(Bucket=public.bucket):
        for obj in page.get("Contents", []):
            found[obj.get("Key", "")] = (obj.get("ETag", ""), obj.get("LastModified"))
    return found


def test_a_snapshot_lays_out_every_table_by_cycle_with_a_manifest_of_its_rows(
    published: Published, taken: Taken
) -> None:
    public = taken.public

    assert taken.result.created
    root = paths.dataset_snapshot(DAY)
    held = manifest(public, root)
    assert held.snapshot_date == DAY
    assert (held.build_id, held.cycles) == (BUILD, {CYCLE: BUILD})
    assert held.license == "CC BY 4.0"
    for table in DATASET_TABLES:
        assert held.tables[table].rows == silver_rows(published.data_dir, table), table
        assert held.tables[table].files, table
        for file in held.tables[table].files:
            assert file.path.startswith(f"{table}/cycle={CYCLE}/")
            assert "/" not in file.path.removeprefix(f"{table}/cycle={CYCLE}/")
    assert held.tables["contribution"].rows == fec_fixture.expected()["silver"]["contribution"]
    assert held.tables["donor"].rows == scalar(
        published.conninfo, "SELECT count(*) FROM gold.donor"
    )
    assert held.tables["crosswalk"].rows == scalar(
        published.conninfo, "SELECT count(*) FROM app.crosswalk"
    )
    # Every file the manifest names is there, byte for byte, and nothing else is.
    files = [file for entry in held.tables.values() for file in entry.files] + [held.overrides]
    for file in files:
        body = public.get(root + file.path)
        assert (len(body), hashlib.sha256(body).hexdigest()) == (file.bytes, file.sha256)
    assert set(public.list_keys(root)) == {root + file.path for file in files} | {
        root + dataset.MANIFEST
    }
    # `latest/` is a copy of it.
    latest = public.list_keys(paths.DATASET_LATEST)
    assert latest == [
        paths.DATASET_LATEST + key.removeprefix(root) for key in public.list_keys(root)
    ]
    assert public.get(paths.DATASET_LATEST + dataset.MANIFEST) == public.get(
        root + dataset.MANIFEST
    )
    # Both manifests are served as JSON: the copy into `latest/` keeps the type.
    for key in (root + dataset.MANIFEST, paths.DATASET_LATEST + dataset.MANIFEST):
        served = public.client.head_object(Bucket=public.bucket, Key=key)
        assert served.get("ContentType") == "application/json", key


def test_the_snapshot_pass_copies_several_objects_at_a_time(taken: Taken) -> None:
    assert taken.most_in_flight["snapshot"] >= 2


def test_the_latest_pass_copies_several_objects_at_a_time(taken: Taken) -> None:
    assert taken.most_in_flight[paths.DATASET_LATEST] >= 2


def test_one_worker_and_many_take_the_same_manifest(
    published: Published, taken: Taken, public: R2
) -> None:
    take(published, public, workers=1)

    one = manifest(public, paths.dataset_snapshot(DAY))
    many = manifest(taken.public, paths.dataset_snapshot(DAY))
    # Files and all, in the same order.
    assert one.tables == many.tables


def test_a_failed_copy_fails_the_snapshot_and_a_rerun_takes_it(
    published: Published, public: R2, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = paths.dataset_snapshot(DAY)
    copy_from = R2.copy_from
    failed: list[str] = []
    lock = threading.Lock()

    def failing(
        target: R2, source: R2, key: str, dest: str, *, if_match: str | None = None
    ) -> None:
        # One key only: the first `race` file to be copied.
        with lock:
            fail = dest.startswith(root + "race/") and not failed
            if fail:
                failed.append(dest)
        if fail:
            raise ConnectionError("R2 went away")
        copy_from(target, source, key, dest, if_match=if_match)

    with monkeypatch.context() as patch:
        patch.setattr(R2, "copy_from", failing)
        with pytest.raises(ConnectionError, match="went away"):
            take(published, public)

    assert len(failed) == 1
    assert not public.exists(root + dataset.MANIFEST)
    assert not public.list_keys(paths.DATASET_LATEST)
    again = take(published, public)
    assert again.created and again.latest_copied
    assert public.exists(root + dataset.MANIFEST)


def test_a_second_snapshot_the_same_day_writes_nothing(published: Published, taken: Taken) -> None:
    before = listing(taken.public)

    again = take(published, taken.public)

    assert (again.created, again.latest_copied, again.removed, again.docs_put) == (
        False,
        False,
        [],
        [],
    )
    assert again.build_id == BUILD
    assert listing(taken.public) == before


def test_a_ninth_snapshot_removes_the_oldest_and_latest_follows_the_newest(
    published: Published, taken: Taken, public: R2, tmp_path: Path
) -> None:
    held = taken.public.get(paths.dataset_snapshot(DAY) + dataset.MANIFEST)
    # Eight earlier snapshots, as manifests alone: retention reads only directories.
    earlier = [DAY - timedelta(weeks=week) for week in range(7, -1, -1)]
    for day in earlier:
        public.put(paths.dataset_snapshot(day) + dataset.MANIFEST, held)
    # And an attempt that crashed before its manifest, never retried: no snapshot at all.
    crashed = DAY - timedelta(days=3)
    public.put(paths.dataset_snapshot(crashed) + "race/cycle=2024/part-0000.parquet", b"")
    ninth = DAY + timedelta(weeks=1)

    # With no local silver: every file is hashed from a download of R2's copy instead, several
    # at once, each to a file of its own.
    result = take(published, public, ninth, data_dir=tmp_path / "empty")

    assert result.created and result.latest_copied
    assert result.removed == [earlier[0], crashed]
    assert not public.list_keys(paths.dataset_snapshot(earlier[0]))
    assert not public.list_keys(paths.dataset_snapshot(crashed))
    newest = paths.dataset_snapshot(ninth)
    assert public.get(paths.DATASET_LATEST + dataset.MANIFEST) == public.get(
        newest + dataset.MANIFEST
    )
    assert public.list_keys(paths.DATASET_LATEST) == [
        paths.DATASET_LATEST + key.removeprefix(newest) for key in public.list_keys(newest)
    ]
    # The same files hash the same from a download as from the local cache.
    assert manifest(public, newest).tables == Manifest.model_validate_json(held).tables


def test_duckdb_reads_latest_contributions_from_minio_over_http(taken: Taken) -> None:
    settings = get_settings()
    endpoint = urlsplit(settings.r2_endpoint)
    assert endpoint.scheme == "http"

    with duckdb.connect() as con:
        con.execute("LOAD httpfs")
        con.execute(
            f"CREATE SECRET minio (TYPE s3, KEY_ID {literal(settings.r2_access_key_id)},"
            f" SECRET {literal(settings.r2_secret_access_key.get_secret_value())},"
            f" ENDPOINT {literal(endpoint.netloc)}, URL_STYLE 'path', USE_SSL false,"
            " REGION 'auto')"
        )
        row = con.execute(
            "SELECT count(*) FROM read_parquet(?)",
            [
                f"s3://{taken.public.bucket}/{paths.DATASET_LATEST}contribution"
                f"/cycle={CYCLE}/*.parquet"
            ],
        ).fetchone()

    assert row is not None
    assert row[0] == fec_fixture.expected()["silver"]["contribution"]


def test_a_build_having_its_donor_ids_rewritten_is_not_snapshotted(
    published: Published, public: R2
) -> None:
    sentinel = paths.rewrite_sentinel(CYCLE, BUILD)
    published.store.put(sentinel, b"")
    try:
        with pytest.raises(BuildNotReady, match="rewritten"):
            take(published, public)
    finally:
        published.store.delete_keys([sentinel])
    # Every partition is checked before the first copy: nothing of the snapshot is there.
    assert not public.list_keys(paths.dataset_snapshot(DAY))


def test_a_build_lacking_its_last_table_copies_nothing(
    published: Published, public: R2, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The last table of the manifest, so a check made table by table would have copied the others;
    # not backfill-pending here, so a build lacking it is not ready.
    monkeypatch.setattr(paths, "BACKFILL_PENDING", frozenset[SilverTable]())
    last = DATASET_TABLES[-1]
    partition = paths.silver_partition(last, CYCLE, BUILD) + "/"
    list_objects = R2.list_objects

    def without_last(store: R2, prefix: str) -> list[r2.Listed]:
        return [] if prefix == partition else list_objects(store, prefix)

    monkeypatch.setattr(R2, "list_objects", without_last)

    with pytest.raises(BuildNotReady, match=f"has no {last}"):
        take(published, public)

    assert not public.list_keys(paths.dataset_snapshot(DAY))


def test_the_cli_snapshots_into_the_public_bucket_once_a_day(
    published: Published, taken: Taken, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "_today", lambda: DAY)
    with cli_pointed_at(
        conninfo=published.conninfo, data_dir=published.data_dir, bucket=published.store.bucket
    ) as env:
        env.setenv("R2_PUBLIC_BUCKET", taken.public.bucket)
        get_settings.cache_clear()
        result = run("dataset", "--snapshot")

    assert "docs: unchanged" in result.output
    assert f"already took snapshot {DAY} of build {BUILD}" in result.output
    assert "latest/: already the newest" in result.output


def test_the_cli_with_nothing_published_exits_1(cli_env: Path) -> None:
    result = CliRunner().invoke(cli.app, ["dataset", "--snapshot"])

    assert result.exit_code == 1
    assert "no live gold build" in result.output


def test_a_local_copy_put_in_parts_is_recognised_by_its_etag(
    store: R2, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # MinIO's smallest part is 5 MiB: two parts, the second short.
    part = 5 * 1024 * 1024
    monkeypatch.setattr(
        r2, "_TRANSFER", TransferConfig(multipart_threshold=part, multipart_chunksize=part)
    )
    monkeypatch.setattr(dataset, "MULTIPART_BYTES", part)
    local = tmp_path / "object.bin"
    local.write_bytes(os.urandom(part + 1024))
    store.put("object.bin", local)
    [listed] = store.list_objects("object.bin")

    sha256, matches = dataset._hash(local, listed.etag)  # pyright: ignore[reportPrivateUsage]

    assert listed.etag.endswith("-2")
    assert matches
    assert sha256 == hashlib.sha256(local.read_bytes()).hexdigest()
    local.write_bytes(os.urandom(part + 1024))
    assert not dataset._hash(local, listed.etag)[1]  # pyright: ignore[reportPrivateUsage]


def test_a_copy_pinned_to_an_etag_fails_once_the_object_changes(store: R2) -> None:
    store.put("object.bin", b"hashed")
    [listed] = store.list_objects("object.bin")
    store.put("object.bin", b"rewritten since")

    with pytest.raises(ClientError):
        store.copy_from(store, "object.bin", "copy.bin", if_match=listed.etag)

    assert not store.exists("copy.bin")


def test_the_documentation_is_published_at_v1_beside_the_snapshots(taken: Taken) -> None:
    public = taken.public

    names = [*dataset.DOCS, *(f"schema/{table}.json" for table in dataset.MANIFEST_TABLES)]
    for name in names:
        key = paths.DATASET_PREFIX + name
        assert public.get(key) == (DOCS / name).read_bytes(), name
    assert sorted(taken.result.docs_put) == sorted(paths.DATASET_PREFIX + name for name in names)
    served = public.client.head_object(Bucket=public.bucket, Key=f"{paths.DATASET_PREFIX}README.md")
    assert served.get("ContentType") == "text/markdown; charset=utf-8"


def test_only_changed_documentation_is_put_and_stale_schemas_are_deleted(
    public: R2, tmp_path: Path
) -> None:
    docs = tmp_path / "docs"
    shutil.copytree(DOCS, docs)
    dataset.publish_docs(public, docs)
    stale = f"{paths.DATASET_PREFIX}schema/dropped_table.json"
    public.put(stale, b"{}")
    (docs / "CHANGELOG.md").write_text((DOCS / "CHANGELOG.md").read_text() + "\nA change.\n")

    put = dataset.publish_docs(public, docs)

    assert put == [f"{paths.DATASET_PREFIX}CHANGELOG.md"]
    assert not public.exists(stale)
    assert public.get(put[0]) == (docs / "CHANGELOG.md").read_bytes()


def test_a_snapshot_without_its_license_copies_nothing(
    published: Published, public: R2, tmp_path: Path
) -> None:
    docs = tmp_path / "docs"
    shutil.copytree(DOCS, docs)
    (docs / "LICENSE").unlink()

    with pytest.raises(DocsMissing, match="LICENSE"):
        take(published, public, docs_dir=docs)

    assert not public.list_keys("")


def snapshot_files(published: Published, work: Path) -> dict[str, Path]:
    """One file of each table a snapshot of `published` would hold, by table: the silver files it
    copies byte for byte, the donor file it writes and the crosswalk snapshot it copies. Not from
    a snapshot itself, which is refused while a schema is missing (`DocsMissing`), so a new
    table's schema can be written here."""
    files: dict[str, Path] = {}
    for table in DATASET_TABLES:
        partition = paths.local_path(
            published.data_dir, paths.silver_partition(table, CYCLE, BUILD)
        )
        files[table] = min(partition.rglob("*.parquet"))
    with psycopg.connect(published.conninfo, autocommit=True) as conn:
        files["donor"] = dataset._donor(conn, work)  # pyright: ignore[reportPrivateUsage]
    files["crosswalk"] = published.store.download_to(
        paths.resolution_snapshot(BUILD, "crosswalk"), work / dataset.CROSSWALK
    )
    assert sorted(files) == sorted(dataset.MANIFEST_TABLES)
    return files


def test_the_committed_schemas_are_the_snapshots(published: Published, tmp_path: Path) -> None:
    """Each table's schema, generated from its Parquet file and `columns.yaml`, is the one
    committed: a silver column changed without its description and schema fails here. With
    `DATASET_SCHEMA_WRITE=1` (`task dataset:schema`), the schemas are written instead."""
    files = snapshot_files(published, tmp_path)

    generated = dataset_schema.generate(files, DOCS / dataset_schema.COLUMNS)

    assert sorted(generated) == sorted(f"schema/{table}.json" for table in files)
    if WRITE_SCHEMAS:
        dataset_schema.write(DOCS, generated)
    stale = dataset_schema.differences(DOCS, generated)
    assert not stale, (
        f"docs/dataset/{', '.join(stale)} not as generated: run `task dataset:schema`, and add a"
        " docs/dataset/CHANGELOG.md entry for the schema change"
    )


def readme_duckdb_one_liner() -> str:
    """The SQL of the README's DuckDB one-liner, `duckdb -c "…"`, as written."""
    found = re.findall(r'^duckdb -c "(.+?)"$', (DOCS / "README.md").read_text(), re.M | re.S)
    assert len(found) == 1, "the README holds one `duckdb -c` one-liner"
    return found[0]


def test_the_readme_duckdb_one_liner_reads_latest_over_plain_http(taken: Taken) -> None:
    # Anyone may read, as on data.fundlens.org; DuckDB is given no credentials.
    bucket = taken.public.bucket
    taken.public.client.put_bucket_policy(
        Bucket=bucket,
        Policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket}/*"],
                    }
                ],
            }
        ),
    )
    origin = f"{get_settings().r2_endpoint}/{bucket}/"
    sql = readme_duckdb_one_liner().replace("https://data.fundlens.org/", origin)
    assert origin in sql

    with duckdb.connect() as con:
        row = con.execute(sql).fetchone()

    assert row is not None
    contributions = manifest(taken.public, paths.DATASET_LATEST).tables["contribution"].rows
    assert row[0] == contributions == fec_fixture.expected()["silver"]["contribution"]


def test_v1_dataset_lists_the_snapshot_from_its_manifest(
    published: Published, taken: Taken
) -> None:
    settings = get_settings().model_copy(
        update={
            "database_url": published.conninfo,
            "data_dir": published.data_dir,
            "r2_public_bucket": taken.public.bucket,
        }
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/v1/dataset")

    assert response.status_code == 200, response.text
    # Not the gold build's week at the edge: the snapshot is taken after its build is published.
    assert response.headers["cache-control"] == DATASET_CACHE_CONTROL
    assert "etag" not in response.headers
    body = Dataset.model_validate(response.json())
    assert body.base_url == PUBLIC_URL
    assert body.latest == DAY
    (snapshot,) = body.snapshots
    assert snapshot == summarize(manifest(taken.public, paths.dataset_snapshot(DAY)))
    assert [table.name for table in snapshot.tables] == list(dataset.MANIFEST_TABLES)
    # Every cycled table's part is in the fixture cycle's directory on data.fundlens.org.
    for table in snapshot.tables:
        for part in table.parts:
            url = snapshot.url + part.path
            if table.name in ("donor", "crosswalk"):
                assert url == f"https://data.fundlens.org/v1/{DAY}/{table.name}.parquet"
            else:
                assert url.startswith(
                    f"https://data.fundlens.org/v1/{DAY}/{table.name}/cycle={CYCLE}/"
                )
                assert part.cycle == CYCLE


def test_the_dataset_index_lists_finished_snapshots_newest_first(public: R2, taken: Taken) -> None:
    index = DatasetIndex(public, ttl=0)
    assert index.get() == Dataset(base_url=PUBLIC_URL, latest=None, snapshots=[])

    held = manifest(taken.public, paths.dataset_snapshot(DAY))
    earlier = DAY - timedelta(days=7)

    def put(day: date, build_id: str) -> None:
        body = held.model_copy(update={"snapshot_date": day, "build_id": build_id})
        public.put(paths.dataset_snapshot(day) + dataset.MANIFEST, body.model_dump_json().encode())

    put(DAY, held.build_id)
    put(earlier, "20261115T030000Z")
    # Unreadable: left out, rather than failing the list.
    public.put(paths.dataset_snapshot(DAY - timedelta(days=14)) + dataset.MANIFEST, b"{}")
    # Unfinished: no manifest, so not a snapshot yet.
    public.put(paths.dataset_snapshot(DAY + timedelta(days=7)) + "race/cycle=2024/x.parquet", b"")
    public.copy_from(
        public,
        paths.dataset_snapshot(DAY) + dataset.MANIFEST,
        paths.DATASET_LATEST + dataset.MANIFEST,
    )

    listed = index.get()
    assert [snapshot.snapshot_date for snapshot in listed.snapshots] == [DAY, earlier]
    assert listed.latest == DAY

    # A manifest is read again when its ETag changes, and a deleted snapshot leaves the list.
    put(earlier, "20261116T030000Z")
    public.delete_prefix(paths.dataset_snapshot(DAY))
    relisted = index.get()
    assert [(s.snapshot_date, s.build_id) for s in relisted.snapshots] == [
        (earlier, "20261116T030000Z")
    ]
