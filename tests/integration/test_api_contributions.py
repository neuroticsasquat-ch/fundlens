"""`/contributions` against the fixture cycle's silver, read by the API's DuckDB through the live
build `gold.meta.cycles` names (spec §7.2, ADR-0006)."""

import shutil
import statistics
import time
from collections.abc import Iterator
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

import duckdb
import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from fundlens import paths
from fundlens.api.app import create_app
from fundlens.api.cache import BUILD_ID_TTL_SECONDS, TtlCache
from fundlens.api.deps import get_itemized, get_page_size
from fundlens.api.itemized import ItemizedReader, Recipient, read_live_builds
from fundlens.load.db import create_pool
from fundlens.settings import get_settings
from tests.integration.test_api_routes import BUILD, CYCLE, ok, published_fixture_cycle

NEXT_BUILD = "20261106T030000Z"
# The committee with the most counted contributions in the fixture (OKAFOR's principal).
COMMITTEE = "C00800103"
PAGE = 7
ACTBLUE = "C00401224"


@dataclass(frozen=True)
class Published:
    conninfo: str
    data_dir: Path


@pytest.fixture(scope="module")
def published(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Published]:
    data_dir = tmp_path_factory.mktemp("data")
    with published_fixture_cycle(data_dir) as conninfo:
        yield Published(conninfo, data_dir)


@pytest.fixture(scope="module")
def app(published: Published) -> Iterator[FastAPI]:
    settings = get_settings().model_copy(
        update={"database_url": published.conninfo, "data_dir": published.data_dir}
    )
    app = create_app(settings)
    with TestClient(app):
        yield app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """The module's app, its dependency overrides undone after each test."""
    yield TestClient(app)
    app.dependency_overrides.clear()


def partition(published: Published, build_id: str) -> Path:
    return paths.local_path(
        published.data_dir, paths.silver_partition("contribution", CYCLE, build_id)
    )


def expected_ids(
    published: Published, build_id: str, recipient: Recipient, value: str
) -> list[str]:
    """Every contribution's id in the partition for `value`, in the order the API pages them."""
    files = str(partition(published, build_id) / "*.parquet")
    rows = duckdb.execute(
        f"SELECT source_record_id FROM read_parquet(?) WHERE {recipient} = ?"
        " ORDER BY date DESC NULLS LAST, source_record_id",
        [files, value],
    ).fetchall()
    return [str(record) for (record,) in rows]


def walk(client: TestClient, url: str, *, page: int = PAGE) -> list[str]:
    """Every id `url` pages through, following `next_cursor` to the last page."""
    ids: list[str] = []
    cursor: str | None = None
    while True:
        params = {"cycle": CYCLE} | ({"cursor": cursor} if cursor else {})
        body = ok(client.get(url, params=params))
        ids += [row["source_record_id"] for row in body["contributions"]]
        cursor = body["next_cursor"]
        if cursor is None:
            return ids
        assert len(body["contributions"]) == page


def small_pages(app: FastAPI, size: int = PAGE) -> None:
    app.dependency_overrides[get_page_size] = lambda: size


def okafor(published: Published) -> str:
    [(candidate_id,)] = duckdb.execute(
        "SELECT DISTINCT candidate_id FROM read_parquet(?) WHERE recipient_committee_id = ?",
        [str(partition(published, BUILD) / "*.parquet"), COMMITTEE],
    ).fetchall()
    return candidate_id


def test_a_committees_pages_walk_every_contribution_once_in_order(
    app: FastAPI, client: TestClient, published: Published
) -> None:
    small_pages(app)
    expected = expected_ids(published, BUILD, "recipient_committee_id", COMMITTEE)

    ids = walk(client, f"/v1/committees/{COMMITTEE}/contributions")

    assert len(expected) > 3 * PAGE
    assert ids == expected


def test_a_candidates_pages_cover_every_committee_raising_for_them(
    app: FastAPI, client: TestClient, published: Published
) -> None:
    small_pages(app)
    candidate_id = okafor(published)
    expected = expected_ids(published, BUILD, "candidate_id", candidate_id)

    ids = walk(client, f"/v1/candidates/{candidate_id}/contributions")

    assert ids == expected
    assert len(expected) > len(expected_ids(published, BUILD, "recipient_committee_id", COMMITTEE))


def test_a_page_holds_a_hundred_rows_as_reported(client: TestClient, published: Published) -> None:
    body = ok(client.get(f"/v1/committees/{COMMITTEE}/contributions", params={"cycle": CYCLE}))

    expected = expected_ids(published, BUILD, "recipient_committee_id", COMMITTEE)
    assert len(expected) < 100
    assert [row["source_record_id"] for row in body["contributions"]] == expected
    assert body["next_cursor"] is None
    first = body["contributions"][0]
    assert first["recipient_committee_id"] == COMMITTEE
    assert first["contributor_name"]
    assert isinstance(first["amount"], float)


def test_an_earmark_is_listed_once_with_its_conduit(
    client: TestClient, published: Published
) -> None:
    [(recipient, record)] = duckdb.execute(
        "SELECT recipient_committee_id, source_record_id FROM read_parquet(?)"
        " WHERE conduit_committee_id IS NOT NULL ORDER BY source_record_id LIMIT 1",
        [str(partition(published, BUILD) / "*.parquet")],
    ).fetchall()

    body = ok(client.get(f"/v1/committees/{recipient}/contributions", params={"cycle": CYCLE}))
    actblue = ok(client.get(f"/v1/committees/{ACTBLUE}/contributions", params={"cycle": CYCLE}))

    [row] = [row for row in body["contributions"] if row["source_record_id"] == str(record)]
    assert row["conduit_committee_id"] is not None
    # The conduit receives only gifts to itself: its pass-through rows, 24T or 15, are dropped
    # (ADR-0004), and a tip to ActBlue names no conduit.
    assert [(r["memo_text"], r["conduit_committee_id"]) for r in actblue["contributions"]] == [
        ("CONTRIBUTION TO ACTBLUE", None)
    ]


@pytest.mark.parametrize(
    ("url", "params", "status"),
    [
        ("/v1/committees/C99999999/contributions", {"cycle": CYCLE}, 404),
        ("/v1/candidates/H9XX99999/contributions", {"cycle": CYCLE}, 404),
        (f"/v1/committees/{COMMITTEE}/contributions", {"cycle": 2022}, 404),
        (f"/v1/committees/{COMMITTEE}/contributions", {}, 422),
        (f"/v1/committees/{COMMITTEE}/contributions", {"cycle": 2023}, 422),
        (f"/v1/committees/{COMMITTEE}/contributions", {"cycle": CYCLE, "cursor": "nope"}, 400),
    ],
)
def test_a_request_that_names_nothing_is_a_problem(
    client: TestClient, url: str, params: dict[str, Any], status: int
) -> None:
    response = client.get(url, params=params)

    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/problem+json"


@dataclass
class Staged:
    """A newer build of the cycle, on the volume but not yet live."""

    build_id: str
    published: Published
    clock: list[float]

    def publish(self) -> None:
        """Make the build live, as a publish does, and let the API's live-build cache age a
        full minute, as it will have by the time the publish's purge lets requests through."""
        set_live(self.published, self.build_id)
        self.clock[0] += BUILD_ID_TTL_SECONDS


@pytest.fixture
def next_build(app: FastAPI, published: Published) -> Iterator[Staged]:
    """A newer build with three contributions to `COMMITTEE` the live one lacks (one dated after
    every other, two undated), and an app whose live-build cache runs on a clock the test moves.

    Undone after the test: `gold.meta` names `BUILD` again.
    """
    live = partition(published, BUILD)
    staged = partition(published, NEXT_BUILD)
    staged.mkdir(parents=True)
    duckdb.execute(
        f"""
        COPY (
            WITH live AS (SELECT * FROM read_parquet('{live}/*.parquet')),
            model AS (
                SELECT * FROM live WHERE recipient_committee_id = '{COMMITTEE}'
                ORDER BY source_record_id LIMIT 1
            )
            SELECT * FROM live
            UNION ALL
            SELECT * REPLACE (source_record_id + 1000000 AS source_record_id,
                DATE '2024-12-31' AS date) FROM model
            UNION ALL
            SELECT * REPLACE (source_record_id + 2000000 AS source_record_id,
                NULL AS date) FROM model
            UNION ALL
            SELECT * REPLACE (source_record_id + 3000000 AS source_record_id,
                NULL AS date) FROM model
        ) TO '{staged / paths.part(0)}' (FORMAT parquet)
        """
    )
    clock = [0.0]
    with create_pool(published.conninfo) as pool:
        live_builds = TtlCache(partial(read_live_builds, pool), clock=lambda: clock[0])
        reader = ItemizedReader(published.data_dir, live_builds.get)
        app.dependency_overrides[get_itemized] = lambda: reader
        try:
            yield Staged(NEXT_BUILD, published, clock)
        finally:
            reader.close()
            set_live(published, BUILD)
            shutil.rmtree(staged)


def set_live(published: Published, build_id: str) -> None:
    """Point `gold.meta.cycles` at `build_id`, as publishing a load of that build would."""
    with psycopg.connect(published.conninfo, autocommit=True) as conn:
        conn.execute(
            "UPDATE gold.meta SET cycles = jsonb_set(cycles, %s, %s)",
            ([str(CYCLE), "build_id"], Jsonb(build_id)),
        )


def test_a_published_build_is_read_without_a_restart(
    app: FastAPI, client: TestClient, published: Published, next_build: Staged
) -> None:
    url = f"/v1/committees/{COMMITTEE}/contributions"
    before = walk(client, url)
    # A page of one: every row ends a page, the undated ones included.
    small_pages(app, 1)

    next_build.publish()
    after = walk(client, url, page=1)

    assert after == expected_ids(published, NEXT_BUILD, "recipient_committee_id", COMMITTEE)
    assert len(after) == len(before) + 3
    # The new newest contribution leads; the undated ones come last.
    assert after[0] not in before and not set(after[-2:]) & set(before)


def test_a_cursor_keeps_reading_its_build_after_a_swap(
    app: FastAPI, client: TestClient, published: Published, next_build: Staged
) -> None:
    small_pages(app)
    url = f"/v1/committees/{COMMITTEE}/contributions"
    first = ok(client.get(url, params={"cycle": CYCLE}))

    next_build.publish()
    second = ok(client.get(url, params={"cycle": CYCLE, "cursor": first["next_cursor"]}))

    expected = expected_ids(published, BUILD, "recipient_committee_id", COMMITTEE)
    ids = [row["source_record_id"] for row in first["contributions"] + second["contributions"]]
    assert ids == expected[: 2 * PAGE]


def test_a_cursor_whose_build_was_pruned_is_gone(
    app: FastAPI, client: TestClient, published: Published, next_build: Staged
) -> None:
    small_pages(app)
    url = f"/v1/committees/{COMMITTEE}/contributions"
    first = ok(client.get(url, params={"cycle": CYCLE}))
    live = partition(published, BUILD)
    pruned = live.with_name(live.name + ".pruned")

    next_build.publish()
    live.rename(pruned)
    try:
        response = client.get(url, params={"cycle": CYCLE, "cursor": first["next_cursor"]})
    finally:
        pruned.rename(live)

    assert response.status_code == 410, response.text
    assert response.headers["content-type"] == "application/problem+json"
    assert "first page" in response.json()["detail"]


def test_a_page_is_answered_in_under_100_ms_at_p95(client: TestClient) -> None:
    url = f"/v1/committees/{COMMITTEE}/contributions"
    client.get(url, params={"cycle": CYCLE})  # DuckDB's first scan of the file
    timings: list[float] = []
    for _ in range(40):
        started = time.perf_counter()
        ok(client.get(url, params={"cycle": CYCLE}))
        timings.append(time.perf_counter() - started)

    p95 = statistics.quantiles(timings, n=20)[18]
    assert p95 < 0.1, f"p95 {p95 * 1000:.1f} ms"
