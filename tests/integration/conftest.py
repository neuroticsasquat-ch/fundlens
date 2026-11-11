"""A MinIO bucket and a Postgres database of the integration tests' own.

Each test's database is a copy of one migrated once per session (NEU-2267): `CREATE DATABASE …
TEMPLATE` takes milliseconds where `alembic upgrade head` takes most of a second. A test that
changes pipeline state starts from a copy of a session snapshot of it, not from a rebuild
(NEU-2268).

Under pytest-xdist each worker is a process of its own, with its own buckets (`bucket_name`),
snapshots and module fixtures; databases are uuid-named and data dirs come from `tmp_path`.
"""

import os
import shutil
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from botocore.exceptions import ClientError
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from fundlens import cli
from fundlens.r2 import R2
from fundlens.settings import get_settings


def bucket_name(purpose: str = "") -> str:
    """The name of a test bucket: `fundlens-test`, then `purpose` if any, then the xdist worker
    (`gw0`…) if the run is parallel, so no two workers ever share one."""
    parts = ["fundlens-test", purpose, os.environ.get("PYTEST_XDIST_WORKER", "")]
    return "-".join(part for part in parts if part)


# Not `R2_BUCKET`: the dev seed writes there, and every test here empties its bucket afterwards.
TEST_BUCKET = bucket_name()

REPO_ROOT = Path(__file__).resolve().parents[2]
# The overrides the CLI resolves with unless a test says otherwise: none (`fixtures/resolution/`).
NO_OVERRIDES = REPO_ROOT / "tests" / "fixtures" / "resolution" / "none.yaml"


def empty_store(bucket: str = TEST_BUCKET) -> R2:
    """The test bucket, or `bucket`, created if MinIO does not have it yet, and emptied."""
    r2 = R2.from_settings(get_settings(), bucket=bucket)
    try:
        r2.client.create_bucket(Bucket=bucket)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "BucketAlreadyOwnedByYou":
            raise
    r2.delete_prefix("")
    return r2


@pytest.fixture
def store() -> Iterator[R2]:
    """An empty MinIO bucket of its own, emptied again after the test."""
    r2 = empty_store()
    yield r2
    r2.delete_prefix("")


def database_name(conninfo: str) -> str:
    return str(conninfo_to_dict(conninfo)["dbname"])


@contextmanager
def scratch_database(template: str | None = None) -> Generator[str]:
    """The conninfo of a database of its own, empty or a copy of database `template` (which nothing
    may be connected to), dropped on exit.

    Its own, not the dev database: a test that builds and swaps `gold` schemas would otherwise
    clobber whatever the dev seed loaded.
    """
    # Read once, now: by teardown a test may have pointed DATABASE_URL at this very database.
    admin = get_settings().database_url
    dbname = f"fundlens_test_{uuid4().hex[:12]}"
    name = sql.Identifier(dbname)
    create = sql.SQL("CREATE DATABASE {}").format(name)
    if template is not None:
        create = sql.SQL("{} TEMPLATE {}").format(create, sql.Identifier(template))
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(create)
    try:
        yield make_conninfo(admin, dbname=dbname)
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(name))


@pytest.fixture
def scratch_db() -> Iterator[str]:
    """The conninfo of an empty database of the test's own, dropped afterwards."""
    with scratch_database() as conninfo:
        yield conninfo


def alembic_config(conninfo: str) -> Config:
    """Alembic in-process, through the CLI's own `migrations/env.py`, against `conninfo`."""
    # No config file name, so env.py leaves pytest's log handlers alone.
    config = Config()
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    config.attributes["conninfo"] = conninfo
    return config


@pytest.fixture(scope="session")
def migrated_template() -> Iterator[str]:
    """The name of a database with the `app` schema migrated to head, once per session, for each
    test's database to copy. Nothing stays connected to it, as `CREATE DATABASE … TEMPLATE`
    needs."""
    with scratch_database() as conninfo:
        command.upgrade(alembic_config(conninfo), "head")
        yield database_name(conninfo)


@pytest.fixture
def migrated_db(migrated_template: str) -> Iterator[str]:
    """A database of the test's own with the `app` schema migrated to head: a copy of the
    session's template. test_migrations runs the upgrade itself."""
    with scratch_database(template=migrated_template) as conninfo:
        yield conninfo


def leave_logging_alone(level: str) -> None:
    # The CLI's callback reconfigures the root logger, which would outlive the test.
    pass


def cap_duckdb(env: pytest.MonkeyPatch) -> None:
    """DuckDB's caps for every CLI-driven step, serial or parallel: eight workers stay within
    8 GB and 16 threads. A test that sets its own limit afterwards (`MEMORY_LIMIT`) wins."""
    env.setenv("DUCKDB_MEMORY_LIMIT", "1GB")
    env.setenv("DUCKDB_THREADS", "2")
    get_settings.cache_clear()


def point_cli_at(
    env: pytest.MonkeyPatch, *, conninfo: str, data_dir: Path, bucket: str = TEST_BUCKET
) -> None:
    """Point the CLI's settings at `bucket`, the database `conninfo`, `data_dir` and no
    overrides."""
    env.setattr(cli, "configure_logging", leave_logging_alone)
    env.setenv("R2_BUCKET", bucket)
    env.setenv("DATABASE_URL", conninfo)
    env.setenv("DATA_DIR", str(data_dir))
    env.setenv("OVERRIDES_PATH", str(NO_OVERRIDES))
    cap_duckdb(env)


@contextmanager
def cli_pointed_at(
    *, conninfo: str, data_dir: Path, bucket: str = TEST_BUCKET
) -> Generator[pytest.MonkeyPatch]:
    """`point_cli_at`, for a fixture wider than a test's own `monkeypatch`; undone on exit."""
    with pytest.MonkeyPatch.context() as env:
        point_cli_at(env, conninfo=conninfo, data_dir=data_dir, bucket=bucket)
        try:
            yield env
        finally:
            get_settings.cache_clear()


@pytest.fixture
def cli_env(
    monkeypatch: pytest.MonkeyPatch, store: R2, migrated_db: str, tmp_path: Path
) -> Iterator[Path]:
    """Point the CLI's settings at the test bucket, a migrated database, a scratch `DATA_DIR` and
    no overrides; that `DATA_DIR`."""
    point_cli_at(monkeypatch, conninfo=migrated_db, data_dir=tmp_path / "data")
    yield tmp_path / "data"
    get_settings.cache_clear()


@dataclass(frozen=True)
class Published:
    """A database whose live `gold` is the fixture cycle's unresolved build, and its data dir."""

    conninfo: str
    data_dir: Path


@pytest.fixture(scope="session")
def published(
    migrated_template: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Published]:
    """The fixture cycle transformed, loaded and published once for the session's API tests,
    which read it (NEU-2267). A test that changes it puts it back."""
    # Here, not at the top: the builder's module imports this one.
    from tests.integration.test_api_routes import published_fixture_cycle

    data_dir = tmp_path_factory.mktemp("published")
    with published_fixture_cycle(data_dir, migrated_template) as conninfo:
        yield Published(conninfo, data_dir)


@dataclass(frozen=True)
class Snapshot:
    """Pipeline state built once per session: its `DATA_DIR`, database and bucket. Nothing is
    connected to the database, which is only ever a `CREATE DATABASE … TEMPLATE` source."""

    data_dir: Path
    database: str
    store: R2


def copy_files(snapshot: Snapshot, *, store: R2, data_dir: Path) -> None:
    """`snapshot`'s `DATA_DIR` into `data_dir`, and its objects into `store`, server-side."""
    shutil.copytree(snapshot.data_dir, data_dir, dirs_exist_ok=True)
    source = snapshot.store.bucket
    for key in snapshot.store.list_keys(""):
        store.client.copy_object(
            Bucket=store.bucket, Key=key, CopySource={"Bucket": source, "Key": key}
        )


def restore(snapshot: Snapshot, *, store: R2, data_dir: Path, conninfo: str) -> None:
    """Make `store`, `data_dir` and the database `conninfo` over as copies of `snapshot`'s: the
    database keeps its name and becomes a copy of the snapshot's, sequences and `app` rows
    included."""
    copy_files(snapshot, store=store, data_dir=data_dir)
    name = sql.Identifier(database_name(conninfo))
    with psycopg.connect(make_conninfo(conninfo, dbname="postgres"), autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(name))
        conn.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                name, sql.Identifier(snapshot.database)
            )
        )


def build_snapshot(
    rung: str,
    tmp_path_factory: pytest.TempPathFactory,
    *,
    template: str,
    steps: Callable[[pytest.MonkeyPatch], None],
    parent: Snapshot | None = None,
) -> Generator[Snapshot]:
    """A session fixture's body: a bucket, database and `DATA_DIR` of `rung`'s own, holding
    `parent`'s state if given (else an empty bucket and a copy of database `template`), the CLI
    pointed at them while `steps` runs; the snapshot, emptied and dropped after the session."""
    data_dir = tmp_path_factory.mktemp(rung)
    store = empty_store(bucket_name(f"snapshot-{rung}"))
    with scratch_database(template=template if parent is None else parent.database) as conninfo:
        try:
            if parent is not None:
                copy_files(parent, store=store, data_dir=data_dir)
            with cli_pointed_at(conninfo=conninfo, data_dir=data_dir, bucket=store.bucket) as env:
                steps(env)
            yield Snapshot(data_dir, database_name(conninfo), store)
        finally:
            store.delete_prefix("")


# The three rungs below import their steps inside their bodies, as `published` does: the test
# modules that hold them import this one.


@pytest.fixture(scope="session")
def transformed_snapshot(
    migrated_template: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Snapshot]:
    """The fixture cycle's bronze and seat calendar, transformed as build `BUILD`."""
    from tests.integration.test_transform import put_bronze, seats_report, transform

    def steps(env: pytest.MonkeyPatch) -> None:
        put_bronze(R2.from_settings(get_settings()))
        seats_report()
        result = transform()
        assert result.exit_code == 0, result.output

    yield from build_snapshot(
        "transformed", tmp_path_factory, template=migrated_template, steps=steps
    )


@pytest.fixture(scope="session")
def resolved_snapshot(
    transformed_snapshot: Snapshot,
    migrated_template: str,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Snapshot]:
    """`transformed_snapshot` resolved as model `MODEL` under `MEMORY_LIMIT`, with no verdicts."""
    from tests.integration.test_resolve import MEMORY_LIMIT, MODEL, resolve

    def steps(env: pytest.MonkeyPatch) -> None:
        env.setenv("DUCKDB_MEMORY_LIMIT", MEMORY_LIMIT)
        get_settings.cache_clear()
        result = resolve("--full", "--build-id", MODEL)
        assert result.exit_code == 0, result.output

    yield from build_snapshot(
        "resolved",
        tmp_path_factory,
        template=migrated_template,
        steps=steps,
        parent=transformed_snapshot,
    )


@pytest.fixture(scope="session")
def validated_snapshot(
    resolved_snapshot: Snapshot,
    migrated_template: str,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Snapshot]:
    """`resolved_snapshot` adjudicated by the fake model, then resolved again as model `AGAIN`
    with the fixture overrides and the release name, as test_validate needs it.

    Resolved twice, as the overrides runbook does: the split names a donor_id, which only a first
    run without overrides hands out, and `adjudicate` chooses from the clusters of a run before it.
    """
    from fundlens.resolve import adjudicate as adjudication
    from fundlens.settings import Settings
    from tests.fake_adjudicator import FakeAdjudicator
    from tests.integration.test_resolve import AGAIN, MEMORY_LIMIT, resolve
    from tests.integration.test_validate import resolved_env, run

    def steps(env: pytest.MonkeyPatch) -> None:
        client = FakeAdjudicator()

        def client_for(settings: Settings) -> FakeAdjudicator:
            return client

        env.setattr(adjudication, "client_for", client_for)
        # As `resolved_snapshot` ran: the overrides and release name are the second resolve's.
        env.setenv("DUCKDB_MEMORY_LIMIT", MEMORY_LIMIT)
        get_settings.cache_clear()
        adjudicated = run("adjudicate")
        assert adjudicated.exit_code == 0, adjudicated.output
        resolved_env(env)
        again = resolve("--full", "--build-id", AGAIN)
        assert again.exit_code == 0, again.output

    yield from build_snapshot(
        "validated",
        tmp_path_factory,
        template=migrated_template,
        steps=steps,
        parent=resolved_snapshot,
    )


@pytest.fixture
def transformed(
    transformed_snapshot: Snapshot,
    store: R2,
    cli_env: Path,
    migrated_db: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """The fixture cycle transformed as build `BUILD`, copied into the test's own bucket, database
    and `DATA_DIR`, which the test may change, with the pipeline's DuckDB memory limit set; the
    `DATA_DIR`."""
    from tests.integration.test_resolve import MEMORY_LIMIT

    restore(transformed_snapshot, store=store, data_dir=cli_env, conninfo=migrated_db)
    monkeypatch.setenv("DUCKDB_MEMORY_LIMIT", MEMORY_LIMIT)
    get_settings.cache_clear()
    return cli_env


@pytest.fixture
def resolved(
    resolved_snapshot: Snapshot,
    store: R2,
    cli_env: Path,
    migrated_db: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """`transformed`, resolved once as model `MODEL` with no verdicts yet, copied into the test's
    own bucket, database and `DATA_DIR`; the `DATA_DIR`. test_validate has a `resolved` of its
    own, further along."""
    from tests.integration.test_resolve import MEMORY_LIMIT

    restore(resolved_snapshot, store=store, data_dir=cli_env, conninfo=migrated_db)
    monkeypatch.setenv("DUCKDB_MEMORY_LIMIT", MEMORY_LIMIT)
    get_settings.cache_clear()
    return cli_env
