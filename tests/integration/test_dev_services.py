"""The services `docker-compose.yml` starts beside `app` are up and are the ones the spec names:
Postgres 18 and an S3-compatible store standing in for R2."""

from urllib.request import urlopen

import psycopg

from fundlens.settings import get_settings


def test_postgres_is_version_18() -> None:
    with psycopg.connect(get_settings().database_url) as conn:
        row = conn.execute("SHOW server_version_num").fetchone()

    assert row is not None
    assert int(row[0]) // 10000 == 18


def test_object_store_is_live() -> None:
    with urlopen(f"{get_settings().r2_endpoint}/minio/health/live", timeout=5) as response:
        assert response.status == 200
