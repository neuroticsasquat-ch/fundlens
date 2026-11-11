"""A MinIO bucket and a Postgres database of the integration tests' own.

Each test's database is a copy of one migrated once per session (NEU-2267): `CREATE DATABASE …
TEMPLATE` takes milliseconds where `alembic upgrade head` takes most of a second.
"""

from collections.abc import Generator, Iterator
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

# Not `R2_BUCKET`: the dev seed writes there, and every test here empties its bucket afterwards.
TEST_BUCKET = "fundlens-test"

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
    get_settings.cache_clear()


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
