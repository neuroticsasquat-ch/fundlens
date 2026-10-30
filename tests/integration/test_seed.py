"""`task db:seed` (`tests.seed`) against MinIO and a migrated Postgres (spec §12)."""

from collections.abc import Iterator
from pathlib import Path
from typing import get_args

import psycopg
import pytest
from fastapi.testclient import TestClient

from fundlens import cli, markers, paths
from fundlens.api.app import create_app
from fundlens.fec.files import FecFile
from fundlens.r2 import R2
from fundlens.settings import get_settings
from tests import fec_fixture, seed
from tests.integration.conftest import TEST_BUCKET


@pytest.fixture
def seed_env(
    monkeypatch: pytest.MonkeyPatch, store: R2, migrated_db: str, tmp_path: Path
) -> Iterator[str]:
    """Point the seed at the test bucket, a migrated database and a scratch `DATA_DIR`."""

    def leave_logging_alone(level: str) -> None:
        # The callback reconfigures the root logger, which would outlive the test.
        pass

    monkeypatch.setattr(cli, "configure_logging", leave_logging_alone)
    monkeypatch.setenv("R2_BUCKET", TEST_BUCKET)
    monkeypatch.setenv("DATABASE_URL", migrated_db)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield migrated_db
    get_settings.cache_clear()


def test_the_seed_extracts_the_fixture_and_records_its_unmatched_filing_on_every_run(
    seed_env: str, store: R2
) -> None:
    first = seed.seed()
    bronze = sorted(store.list_keys("bronze/"))
    second = seed.seed()

    # Every fixture file, once: the second run found bronze unchanged and uploaded nothing new.
    assert [key.split("/")[2] for key in bronze] == sorted(get_args(FecFile))
    assert sorted(store.list_keys("bronze/")) == bronze
    for build_id in (first, second):
        assert markers.exists("extracted", store, cycle=2024, build_id=build_id)
        assert markers.exists("transformed", store, cycle=2024, build_id=build_id)
        assert markers.exists("loaded", store, cycle=2024, build_id=build_id)
        assert markers.exists("published", store, cycle=2024, build_id=build_id)
        # The second publish prunes nothing: the first build is the previous live one.
        assert store.list_keys(paths.silver_partition("race", 2024, build_id))
    with psycopg.connect(seed_env) as conn:
        unmatched = conn.execute(
            "SELECT candidate_id FROM app.unmatched_filing WHERE cycle = 2024"
        ).fetchall()
    assert [row[0] for row in unmatched] == fec_fixture.expected()["unmatched_filings"]

    # The seeded gold is live: `GET /v1/meta` answers with the second build (the ticket's DoD).
    settings = get_settings().model_copy(update={"database_url": seed_env})
    with TestClient(create_app(settings)) as client:
        response = client.get("/v1/meta")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["build_id"] == second
    assert body["published_at"] is not None
    assert (body["resolver_version"], body["model_version"]) == (None, None)
    assert body["cycles"]["2024"]["build_id"] == second
