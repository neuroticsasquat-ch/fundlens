"""The API skeleton against a Postgres database of its own (spec §7.2, §7.3)."""

from collections.abc import Iterator
from pathlib import Path
from typing import LiteralString, cast

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.types.json import Jsonb

from fundlens.api.app import create_app
from fundlens.api.cache import CACHE_CONTROL, NO_STORE, read_build_id
from fundlens.load.db import Pool
from fundlens.settings import get_settings

BUILD_ID = "20261102T030000Z"
NEXT_BUILD_ID = "20261109T030000Z"
META = "/v1/meta"
# psycopg prepares a query server-side once a connection has run it this many times.
PREPARE_THRESHOLD_DEFAULT = 5


def seed_meta(
    conninfo: str, schema: str, build_id: str, *, precision_type: LiteralString = "numeric"
) -> None:
    """A `<schema>.meta` with one row, shaped as the gold build will write it (spec §7.1)."""
    table = sql.Identifier(schema, "meta")
    with psycopg.connect(conninfo, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(
            sql.SQL(
                "CREATE TABLE {} (build_id text, published_at timestamptz, resolver_version text,"
                " model_version text, precision {}, recall numeric, cycles jsonb)"
            ).format(table, sql.SQL(precision_type))
        )
        conn.execute(
            sql.SQL(
                "INSERT INTO {} VALUES (%s, '2026-11-02T09:00:00Z', 'r1', 'm1', 0.97, 0.91, %s)"
            ).format(table),
            (build_id, Jsonb({"2026": {"build_id": build_id}})),
        )


def swap_in_gold_build(conninfo: str) -> None:
    """The publish swap (spec §5.5): `gold_build` becomes `gold`, the old one is dropped."""
    with psycopg.connect(conninfo, autocommit=True) as conn:
        conn.execute("ALTER SCHEMA gold RENAME TO gold_prev")
        conn.execute("ALTER SCHEMA gold_build RENAME TO gold")
        conn.execute("DROP SCHEMA gold_prev CASCADE")


@pytest.fixture
def client(scratch_db: str, tmp_path: Path) -> Iterator[TestClient]:
    (tmp_path / "silver").mkdir()
    settings = get_settings().model_copy(update={"database_url": scratch_db, "data_dir": tmp_path})
    # As a context manager, so the lifespan opens the pool.
    with TestClient(create_app(settings)) as client:
        yield client


def test_meta_returns_the_live_build_with_cache_headers(
    scratch_db: str, client: TestClient
) -> None:
    seed_meta(scratch_db, "gold", BUILD_ID)

    response = client.get(META)

    assert response.status_code == 200
    assert response.json() == {
        "build_id": BUILD_ID,
        "published_at": "2026-11-02T09:00:00Z",
        "resolver_version": "r1",
        "model_version": "m1",
        "precision": 0.97,
        "recall": 0.91,
        "cycles": {"2026": {"build_id": BUILD_ID}},
    }
    assert response.headers["cache-control"] == CACHE_CONTROL
    assert response.headers["etag"] == f'"{BUILD_ID}"'


def test_meta_is_503_and_uncached_before_any_gold_exists(client: TestClient) -> None:
    response = client.get(META)

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "No gold build has been published yet."
    assert response.headers["cache-control"] == NO_STORE
    assert "etag" not in response.headers


def test_meta_survives_a_gold_swap_under_a_live_pool(scratch_db: str, client: TestClient) -> None:
    seed_meta(scratch_db, "gold", BUILD_ID)
    # The rebuilt gold changed a column's type: a prepared plan for the old one cannot be reused.
    seed_meta(scratch_db, "gold_build", NEXT_BUILD_ID, precision_type="double precision")
    # Well past psycopg's default prepare threshold (5) on every pooled connection: the first
    # request holds one connection for the route and takes a second for the ETag's build-id
    # read, and the pool hands the two out in turn.
    for _ in range(4 * PREPARE_THRESHOLD_DEFAULT):
        assert client.get(META).json()["build_id"] == BUILD_ID

    swap_in_gold_build(scratch_db)
    response = client.get(META)

    assert response.status_code == 200, response.text
    assert response.json()["build_id"] == NEXT_BUILD_ID


def test_a_prepared_plan_does_not_survive_the_same_swap(scratch_db: str) -> None:
    # The control for the test above: without `prepare_threshold=None` the swap breaks a
    # connection, so that test would catch the setting being dropped.
    seed_meta(scratch_db, "gold", BUILD_ID)
    seed_meta(scratch_db, "gold_build", NEXT_BUILD_ID, precision_type="double precision")
    query = "SELECT build_id, precision FROM gold.meta"
    with psycopg.connect(scratch_db, autocommit=True, prepare_threshold=0) as conn:
        conn.execute(query)

        swap_in_gold_build(scratch_db)

        with pytest.raises(psycopg.errors.FeatureNotSupported, match="cached plan"):
            conn.execute(query)


def test_pooled_connections_never_prepare(client: TestClient) -> None:
    pool: Pool = cast(FastAPI, client.app).state.pool

    with pool.connection() as conn:
        assert conn.prepare_threshold is None


def test_healthz_is_ok_and_uncached(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"postgres": "ok", "silver": "ok"}
    assert response.headers["cache-control"] == NO_STORE


def test_healthz_is_503_without_the_silver_volume(scratch_db: str, tmp_path: Path) -> None:
    settings = get_settings().model_copy(update={"database_url": scratch_db, "data_dir": tmp_path})
    with TestClient(create_app(settings)) as client:
        response = client.get("/healthz")

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert "silver" in response.json()["detail"]
    assert response.headers["cache-control"] == NO_STORE


def test_cors_allows_the_spa_and_no_one_else(client: TestClient) -> None:
    allowed = client.get("/healthz", headers={"Origin": "https://fundlens.org"})
    other = client.get("/healthz", headers={"Origin": "https://example.com"})

    assert allowed.headers["access-control-allow-origin"] == "https://fundlens.org"
    assert other.headers["access-control-allow-origin"] == "https://fundlens.org"


def test_a_request_without_an_origin_is_answered_for_the_spa(client: TestClient) -> None:
    # The edge caches this response for every later caller, the SPA included.
    response = client.get("/healthz")

    assert response.headers["access-control-allow-origin"] == "https://fundlens.org"


def test_another_dev_origin_is_echoed(scratch_db: str, tmp_path: Path) -> None:
    settings = get_settings().model_copy(
        update={
            "database_url": scratch_db,
            "data_dir": tmp_path,
            "cors_origins": ["https://fundlens.org", "http://localhost:5180"],
        }
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/v1/meta", headers={"Origin": "http://localhost:5180"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5180"


def test_an_unreadable_build_id_means_no_etag_not_a_500(client: TestClient) -> None:
    pool: Pool = cast(FastAPI, client.app).state.pool
    pool.close()

    assert read_build_id(pool) is None
