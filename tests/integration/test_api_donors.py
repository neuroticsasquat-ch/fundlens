"""The donor routes against the fixture cycle resolved, loaded and swapped in once for the module:
gold's donor tables, a merged-away id's 301, and the donor's contributions read from their
`donor_id % 256` bucket of each cycle's silver (spec §7.2, ADR-0006)."""

import json
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
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
from fundlens.api.cache import CACHE_CONTROL
from fundlens.api.deps import get_itemized, get_page_size
from fundlens.api.itemized import ItemizedReader, read_live_builds
from fundlens.load.db import create_pool
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.integration.test_api_routes import BUILD, CYCLE, ok, published_fixture_cycle

# A cycle before the fixture's, staged with a copy of MARLOWE's 2024 gifts, so a donor's walk has
# two cycles to cross.
EARLIER = 2022
EARLIER_BUILD = "20261029T030000Z"
# A donor_id no resolution gave, which a merge sent on to MARLOWE.
MERGED_AWAY = 9001
EXPECTED = fec_fixture.expected()
MUSK = EXPECTED["donors"]["musk_case"]
# Five gifts a cycle: a page of three holds the end of one cycle and the start of the next.
PAGE = 3


@dataclass(frozen=True)
class Published:
    conninfo: str
    data_dir: Path
    # The fixture's Musk, MARLOWE, AUGUSTINE: five spellings resolved into one donor.
    musk: int


def silver_rows(data_dir: Path, cycle: int, build_id: str, where: str = "true") -> list[Any]:
    """`(donor_id, source_record_id, contributor_name)` of every contribution in a build matching
    `where`, in the order the API pages them."""
    files = paths.local_path(data_dir, paths.silver_partition("contribution", cycle, build_id))
    return duckdb.execute(
        "SELECT donor_id, source_record_id, contributor_name"
        " FROM read_parquet(?, hive_partitioning = false)"
        f" WHERE {where} ORDER BY date DESC NULLS LAST, source_record_id",
        [str(files / "**" / "*.parquet")],
    ).fetchall()


@pytest.fixture(scope="module")
def published(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Published]:
    data_dir = tmp_path_factory.mktemp("data")
    with published_fixture_cycle(data_dir, resolved=True) as conninfo:
        sub_ids = ", ".join(str(sub_id) for sub_id in MUSK["sub_ids"])
        [musk] = {
            donor_id
            for donor_id, *_ in silver_rows(
                data_dir, CYCLE, BUILD, f"source_record_id IN ({sub_ids})"
            )
        }
        with psycopg.connect(conninfo, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO gold.donor_redirect (old_donor_id, donor_id) VALUES (%s, %s)",
                (MERGED_AWAY, musk),
            )
        yield Published(conninfo, data_dir, musk)


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
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.clear()


def bucket(published: Published, cycle: int, build_id: str) -> Path:
    return paths.local_path(
        published.data_dir, paths.silver_bucket(cycle, build_id, published.musk % paths.BUCKETS)
    )


@pytest.fixture
def earlier_cycle(published: Published) -> Iterator[list[int]]:
    """A live 2022 build holding MARLOWE's 2024 gifts again, under new ids; those ids.

    Undone after the test: `gold.meta` names no 2022 build again. Read through a reader of the
    app's that caches no live build (`TtlCache` would keep the module's first answer a minute).
    """
    staged = bucket(published, EARLIER, EARLIER_BUILD)
    staged.mkdir(parents=True)
    live = bucket(published, CYCLE, BUILD)
    duckdb.execute(
        f"""
        COPY (
            SELECT * REPLACE ({EARLIER} AS cycle, source_record_id + 1000000 AS source_record_id)
            FROM read_parquet('{live}/*.parquet', hive_partitioning = false)
        ) TO '{staged / paths.part(0)}' (FORMAT parquet)
        """
    )
    with psycopg.connect(published.conninfo, autocommit=True) as conn:
        conn.execute(
            "UPDATE gold.meta SET cycles = jsonb_set(cycles, %s, %s)",
            ([str(EARLIER)], Jsonb({"build_id": EARLIER_BUILD, "source_dates": {}})),
        )
    try:
        yield [
            record
            for _, record, _ in silver_rows(
                published.data_dir, EARLIER, EARLIER_BUILD, f"donor_id = {published.musk}"
            )
        ]
    finally:
        with psycopg.connect(published.conninfo, autocommit=True) as conn:
            conn.execute("UPDATE gold.meta SET cycles = cycles - %s", (str(EARLIER),))
        shutil.rmtree(staged.parents[1])


@pytest.fixture
def uncached(app: FastAPI, published: Published) -> Iterator[ItemizedReader]:
    """The app's reader, re-made to read the live builds afresh on every request."""
    with create_pool(published.conninfo) as pool:
        reader = ItemizedReader(published.data_dir, lambda: read_live_builds(pool))
        app.dependency_overrides[get_itemized] = lambda: reader
        try:
            yield reader
        finally:
            reader.close()


def walk(
    client: TestClient, url: str, params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Every row `url` pages through, following `next_cursor` to the last page."""
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        query = (params or {}) | ({"cursor": cursor} if cursor else {})
        body = ok(client.get(url, params=query))
        rows += body["contributions"]
        cursor = body["next_cursor"]
        if cursor is None:
            return rows
        assert len(body["contributions"]) == PAGE


def small_pages(app: FastAPI) -> None:
    app.dependency_overrides[get_page_size] = lambda: PAGE


def test_a_donor_page_carries_their_combined_totals_and_top_recipients(
    client: TestClient, published: Published
) -> None:
    body = ok(client.get(f"/v1/donors/{published.musk}"))

    assert body["donor_id"] == published.musk
    assert body["display_name"] == "MARLOWE, AUGUSTINE MR."
    # Every spelling's money, in one donor.
    assert body["total_all_cycles"] == MUSK["amount"]
    assert body["contributor_key_count"] > 1
    assert body["cycles"] == [
        {"cycle": CYCLE, "amount": MUSK["amount"], "contribution_count": len(MUSK["sub_ids"])}
    ]
    recipients = body["top_recipients"]
    assert [row["rank"] for row in recipients] == list(range(1, len(recipients) + 1))
    assert sum(row["amount"] for row in recipients) == MUSK["amount"]
    assert {row["recipient_kind"] for row in recipients} == {"candidate", "committee"}


def test_a_merged_away_id_is_a_cacheable_redirect_to_the_donor_it_became(
    client: TestClient, published: Published
) -> None:
    page = client.get(f"/v1/donors/{MERGED_AWAY}")
    rows = client.get(
        f"/v1/donors/{MERGED_AWAY}/contributions", params={"cycle": CYCLE, "cursor": "x"}
    )

    assert page.status_code == 301, page.text
    assert page.headers["location"] == f"/v1/donors/{published.musk}"
    assert page.headers["cache-control"] == CACHE_CONTROL
    assert rows.status_code == 301, rows.text
    assert rows.headers["location"] == (
        f"/v1/donors/{published.musk}/contributions?cycle={CYCLE}&cursor=x"
    )
    followed = TestClient(client.app).get(f"/v1/donors/{MERGED_AWAY}")
    assert ok(followed)["donor_id"] == published.musk
    # The id as it parses, however the path spelled it.
    padded = client.get(f"/v1/donors/0{MERGED_AWAY}/contributions")
    assert padded.headers["location"] == f"/v1/donors/{published.musk}/contributions"


@pytest.mark.parametrize(
    ("url", "status"),
    [
        ("/v1/donors/8999", 404),
        ("/v1/donors/8999/contributions", 404),
        ("/v1/donors/0", 422),
        ("/v1/donors/marlowe", 422),
        (f"/v1/donors/{2**63}", 422),
    ],
)
def test_a_request_that_names_no_donor_is_a_problem(
    client: TestClient, url: str, status: int
) -> None:
    response = client.get(url)

    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/problem+json"


def test_a_donors_contributions_hold_every_variants_rows_in_cursor_order(
    app: FastAPI, client: TestClient, published: Published
) -> None:
    small_pages(app)
    expected = silver_rows(published.data_dir, CYCLE, BUILD, f"donor_id = {published.musk}")

    rows = walk(client, f"/v1/donors/{published.musk}/contributions")

    assert [row["source_record_id"] for row in rows] == [str(record) for _, record, _ in expected]
    assert sorted(int(row["source_record_id"]) for row in rows) == sorted(MUSK["sub_ids"])
    # Five spellings of one man.
    assert len({row["contributor_name"] for row in rows}) == len(MUSK["sub_ids"])
    assert {row["cycle"] for row in rows} == {CYCLE}
    assert rows == walk(client, f"/v1/donors/{published.musk}/contributions", {"cycle": CYCLE})


def test_a_donors_walk_crosses_every_cycle_newest_first(
    app: FastAPI,
    client: TestClient,
    published: Published,
    earlier_cycle: list[int],
    uncached: ItemizedReader,
) -> None:
    small_pages(app)
    url = f"/v1/donors/{published.musk}/contributions"
    latest = [
        record
        for _, record, _ in silver_rows(
            published.data_dir, CYCLE, BUILD, f"donor_id = {published.musk}"
        )
    ]

    rows = walk(client, url)
    earlier = walk(client, url, {"cycle": EARLIER})

    assert len(latest) % PAGE != 0
    assert [row["source_record_id"] for row in rows] == [
        str(record) for record in latest + earlier_cycle
    ]
    assert [row["cycle"] for row in rows] == [CYCLE] * len(latest) + [EARLIER] * len(latest)
    assert earlier == rows[len(latest) :]

    # DUBOIS gave in 2024 only: 2022 has no directory for his bucket, and is no rows of his.
    sub_ids = ", ".join(str(sub_id) for sub_id in EXPECTED["donors"]["employer_variant"]["sub_ids"])
    dubois = silver_rows(published.data_dir, CYCLE, BUILD, f"source_record_id IN ({sub_ids})")
    [donor_id] = {donor_id for donor_id, *_ in dubois}
    assert not paths.local_path(
        published.data_dir,
        paths.silver_bucket(EARLIER, EARLIER_BUILD, donor_id % paths.BUCKETS),
    ).exists()
    assert [
        row["source_record_id"] for row in walk(client, f"/v1/donors/{donor_id}/contributions")
    ] == [str(record) for _, record, _ in dubois]


def test_a_donors_walk_reads_only_their_bucket_of_each_cycle(
    published: Published, earlier_cycle: list[int], uncached: ItemizedReader
) -> None:
    scan = uncached.donor_scan(published.musk, cycle=None, cursor=None)
    query, params = scan.query()

    with duckdb.connect() as con:
        [(_, plan)] = con.execute(f"EXPLAIN (ANALYZE, FORMAT json) {query}", params).fetchall()
    read = sorted(
        name.strip()
        for operator in walk_plan(json.loads(plan)["operator"])
        if "Filename(s)" in operator["extra_info"]
        for name in operator["extra_info"]["Filename(s)"].split(",")
    )

    buckets = [bucket(published, CYCLE, BUILD), bucket(published, EARLIER, EARLIER_BUILD)]
    assert read == sorted(
        str(part) for directory in buckets for part in directory.glob("*.parquet")
    )
    assert {Path(name).parent for name in read} == set(buckets)


def walk_plan(operators: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """Every operator of an `EXPLAIN (FORMAT json)` plan."""
    for operator in operators:
        yield operator
        yield from walk_plan(operator.get("children", []))


def test_a_cursor_of_another_cycle_is_refused(
    app: FastAPI,
    client: TestClient,
    published: Published,
    earlier_cycle: list[int],
    uncached: ItemizedReader,
) -> None:
    small_pages(app)
    url = f"/v1/donors/{published.musk}/contributions"
    first = ok(client.get(url, params={"cycle": CYCLE}))

    response = client.get(url, params={"cycle": EARLIER, "cursor": first["next_cursor"]})

    assert response.status_code == 400, response.text


def test_a_donor_known_only_from_attributions_has_no_contributions(
    client: TestClient, published: Published
) -> None:
    [only] = EXPECTED["attributions"]["attribution_only"]
    files = paths.local_path(
        published.data_dir, paths.silver_partition("jfc_attribution", CYCLE, BUILD)
    )
    [(donor_id,)] = duckdb.execute(
        "SELECT donor_id FROM read_parquet(?) WHERE source_record_id = ?",
        [str(files / "*.parquet"), only],
    ).fetchall()

    body = ok(client.get(f"/v1/donors/{donor_id}/contributions"))

    assert body == {"contributions": [], "next_cursor": None}
    assert ok(client.get(f"/v1/donors/{donor_id}"))["total_all_cycles"] == 0
