"""A MinIO bucket and a Postgres database of the integration tests' own."""

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from botocore.exceptions import ClientError
from psycopg import sql
from psycopg.conninfo import make_conninfo

from fundlens.r2 import R2
from fundlens.settings import get_settings

# Not `R2_BUCKET`: the dev seed writes there, and every test here empties its bucket afterwards.
TEST_BUCKET = "fundlens-test"

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def store() -> Iterator[R2]:
    """An empty MinIO bucket of its own, emptied again after the test."""
    r2 = R2.from_settings(get_settings(), bucket=TEST_BUCKET)
    try:
        r2.client.create_bucket(Bucket=TEST_BUCKET)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "BucketAlreadyOwnedByYou":
            raise
    r2.delete_prefix("")
    yield r2
    r2.delete_prefix("")


@pytest.fixture
def scratch_db() -> Iterator[str]:
    """The conninfo of an empty database of the test's own, dropped afterwards.

    Its own, not the dev database: a test that builds and swaps `gold` schemas would otherwise
    clobber whatever the dev seed loaded.
    """
    admin = get_settings().database_url
    name = f"fundlens_test_{uuid4().hex[:12]}"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        yield make_conninfo(admin, dbname=name)
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def alembic_config(conninfo: str) -> Config:
    """Alembic in-process, through the CLI's own `migrations/env.py`, against `conninfo`."""
    # No config file name, so env.py leaves pytest's log handlers alone.
    config = Config()
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    config.attributes["conninfo"] = conninfo
    return config


@pytest.fixture
def migrated_db(scratch_db: str) -> str:
    """A scratch database with the `app` schema migrated to head."""
    command.upgrade(alembic_config(scratch_db), "head")
    return scratch_db
