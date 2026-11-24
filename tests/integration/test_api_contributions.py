"""`/contributions`, `/independent-expenditures` and `/expenditures` against the fixture cycle's
silver, read by the API's DuckDB through the live build `gold.meta.cycles` names (spec §7.2,
ADR-0006)."""

import hashlib
import shutil
import statistics
import time
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
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
from tests.integration.conftest import Published
from tests.integration.test_api_routes import BUILD, CYCLE, EXPECTED, ok
from tests.timing import assert_within

NEXT_BUILD = "20261106T030000Z"
# The committee with the most counted contributions in the fixture (OKAFOR's principal).
COMMITTEE = "C00800103"
PAGE = 7
ACTBLUE = "C00401224"
# MARYLAND FORWARD PAC, the fixture's super PAC, and OLD LINE REPUBLICAN COMMITTEE, a party
# committee with an independent expenditure and a coordinated one.
SUPER_PAC = "C00800201"
PARTY = "C00800203"
# A Form 5 filer whose independent expenditures are all the 24/48-hour file's (NEU-2165).
ONE_NATION = "C90800206"
SPENDING = EXPECTED["operating_expenditures"]
# CALLOWAY FOR CONGRESS, the fixture committee with the most spending categories; WHITLOCK FOR
# SENATE, whose card bill heads a chain; HARGROVE FOR AMERICA, whose memo parent counts.
CALLOWAY = "C00800106"
WHITLOCK = "C00800104"
HARGROVE = "C00800101"


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


def test_a_build_loaded_before_resolution_has_no_donor_ids(client: TestClient) -> None:
    body = ok(client.get(f"/v1/committees/{COMMITTEE}/contributions", params={"cycle": CYCLE}))

    assert body["contributions"]
    assert {row["donor_id"] for row in body["contributions"]} == {None}


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
    # The conduit receives only gifts to itself: its own rows of an earmark, 24T or 15, and its
    # refunds of earmarks are dropped (ADR-0004, NEU-2199), and a tip to ActBlue, and its refund,
    # name no conduit.
    assert sorted(
        (r["memo_text"], r["conduit_committee_id"]) for r in actblue["contributions"]
    ) == [("CONTRIBUTION TO ACTBLUE", None), ("REFUND OF CONTRIBUTION TO ACTBLUE", None)]


def walk_independent_expenditures(client: TestClient, committee_id: str) -> list[dict[str, Any]]:
    """Every independent expenditure the committee's pages hold, following `next_cursor`."""
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params = {"cycle": CYCLE} | ({"cursor": cursor} if cursor else {})
        body = ok(
            client.get(f"/v1/committees/{committee_id}/independent-expenditures", params=params)
        )
        rows += body["expenditures"]
        cursor = body["next_cursor"]
        if cursor is None:
            return rows


def test_a_super_pacs_independent_expenditures_page_newest_first(
    app: FastAPI, client: TestClient
) -> None:
    small_pages(app, 4)

    rows = walk_independent_expenditures(client, SUPER_PAC)

    assert [
        (row["date"], row["amount"], row["support_oppose"], row["candidate_id"]) for row in rows
    ] == [
        ("2024-10-28", 400000.0, "S", "P40000101"),
        ("2024-10-22", 30000.0, "S", "S4MD00103"),
        ("2024-10-14", 15000.0, "O", "H4MD05107"),
        ("2024-10-12", 25000.0, "S", "H4MD05106"),
        ("2024-10-05", 80000.0, "O", "S4MD00104"),
        ("2024-09-20", 120000.0, "S", "S4MD00103"),
    ]
    assert rows[0] | {"source_record_id": None} == {
        "cycle": CYCLE,
        "source_record_id": None,
        "date": "2024-10-28",
        "amount": 400000.0,
        "committee_id": SUPER_PAC,
        "candidate_id": "P40000101",
        "candidate_name": "HARGROVE, ELLEN",
        "race_id": "2024-P-US-00",
        "support_oppose": "S",
        "transaction_type": "24E",
        "source_file": "pas2",
        "payee_name": "BLUE CRAB MEDIA LLC",
        "purpose": None,
    }
    # The rows the committee page's ie_total sums.
    [committee_cycle] = ok(client.get(f"/v1/committees/{SUPER_PAC}"))["cycles"]
    assert sum(row["amount"] for row in rows) == committee_cycle["ie_total"]


def test_a_spenders_24_48_hour_rows_page_by_their_text_keys(
    app: FastAPI, client: TestClient
) -> None:
    # ONE NATION, a Form 5 filer with no `pas2` row: every row of its own is the 24/48-hour file's,
    # keyed `<file_num>:<tran_id>` (NEU-2165), so each page's cursor holds a text key.
    small_pages(app, 3)

    rows = walk_independent_expenditures(client, ONE_NATION)

    keys = [row["source_record_id"] for row in rows]
    assert sorted(keys) == EXPECTED["ie_24_48"]["by_spender"]["source_record_ids"]
    assert len(set(keys)) == len(keys)
    dates = [row["date"] for row in rows]
    assert dates == sorted(dates, reverse=True)
    [committee_cycle] = ok(client.get(f"/v1/committees/{ONE_NATION}"))["cycles"]
    assert sum(row["amount"] for row in rows) == committee_cycle["ie_total"] == 30185.75
    # Each an estimate from a 24- or 48-hour report, with its payee and purpose as filed.
    assert {row["source_file"] for row in rows} == {"ie_24_48"}
    first = next(row for row in rows if row["source_record_id"] == "1910001:SE.4128")
    assert (first["payee_name"], first["purpose"]) == (
        "Tidewater Digital LLC",
        "Digital advertising",
    )


def test_a_coordinated_expenditure_is_no_independent_expenditure(client: TestClient) -> None:
    body = ok(
        client.get(f"/v1/committees/{PARTY}/independent-expenditures", params={"cycle": CYCLE})
    )

    # Its 24A against OKAFOR, not its 24C for WHITLOCK.
    assert [(row["transaction_type"], row["candidate_name"]) for row in body["expenditures"]] == [
        ("24A", "OKAFOR, DIANA")
    ]
    assert body["next_cursor"] is None


def test_a_committee_that_spent_nothing_has_no_independent_expenditures(client: TestClient) -> None:
    body = ok(
        client.get(f"/v1/committees/{COMMITTEE}/independent-expenditures", params={"cycle": CYCLE})
    )

    assert body == {"expenditures": [], "next_cursor": None}


def walk_expenditures(client: TestClient, committee_id: str, **params: str) -> list[dict[str, Any]]:
    """Every operating expenditure the committee's pages hold, following `next_cursor`."""
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        query = {"cycle": CYCLE, **params} | ({"cursor": cursor} if cursor else {})
        body = ok(client.get(f"/v1/committees/{committee_id}/expenditures", params=query))
        rows += body["expenditures"]
        cursor = body["next_cursor"]
        if cursor is None:
            return rows


def nested(rows: list[dict[str, Any]]) -> Iterator[tuple[dict[str, Any], dict[str, Any] | None]]:
    """Each row of `rows`, and each sub-item under them, with the row it is nested under."""
    stack: list[tuple[dict[str, Any], dict[str, Any] | None]] = [(row, None) for row in rows]
    while stack:
        row, parent = stack.pop()
        yield row, parent
        stack += [(sub_item, row) for sub_item in row["sub_items"]]


def top_level_ids(published: Published, committee_id: str, sort: str) -> list[str]:
    """The committee's rows that are no sub-item, in the order `sort` pages them."""
    files = str(
        paths.local_path(
            published.data_dir, paths.silver_partition("operating_expenditure", CYCLE, BUILD)
        )
        / "*.parquet"
    )
    rows = duckdb.execute(
        "SELECT source_record_id FROM read_parquet(?)"
        " WHERE committee_id = ? AND parent_source_record_id IS NULL"
        f" ORDER BY {sort} DESC NULLS LAST, source_record_id",
        [files, committee_id],
    ).fetchall()
    return [str(record) for (record,) in rows]


def test_every_committees_expenditures_list_each_row_once_under_its_parent(
    client: TestClient,
) -> None:
    # Every row silver keeps, counted or not, each sub-item under the row it itemizes; the counted
    # ones add up to the committee's total_operating_expenditures (every-FEC-dollar spec §5.2).
    seen: dict[str, dict[str, Any]] = {}
    parents: dict[str, str] = {}
    for committee_id, total in SPENDING["by_committee"].items():
        rows = list(nested(walk_expenditures(client, committee_id)))
        for row, parent in rows:
            assert row["committee_id"] == committee_id
            seen[row["source_record_id"]] = row
            if parent is not None:
                parents[row["source_record_id"]] = parent["source_record_id"]
        assert sum(Decimal(str(row["amount"])) for row, _ in rows if row["counted"]) == Decimal(
            total
        ), committee_id

    assert len(seen) == EXPECTED["silver"]["operating_expenditure"]
    assert parents == {
        str(sub_item): str(parent) for sub_item, parent in SPENDING["parents"].items()
    }
    assert {record for record, row in seen.items() if not row["counted"]} == {
        str(record) for record in SPENDING["not_counted"]
    }
    assert {record for record, row in seen.items() if row["is_in_kind"]} == {
        str(record) for record in SPENDING["in_kind"]
    }
    assert not {str(record) for record in SPENDING["dropped"]} & set(seen)


def test_a_card_bill_lists_its_two_charges_under_it_not_counted(client: TestClient) -> None:
    rows = walk_expenditures(client, COMMITTEE, category="credit_card")

    [bill] = [row for row in rows if row["source_record_id"] == "4240400000000000003"]
    assert bill | {"sub_items": None} == {
        "cycle": CYCLE,
        "source_record_id": "4240400000000000003",
        "date": "2024-03-05",
        "amount": 1250.0,
        "committee_id": COMMITTEE,
        "candidate_id": "S4MD00103",
        "payee_name": "AMERICAN EXPRESS",
        "payee_key": "AMERICAN EXPRESS",
        "payee_id": hashlib.sha256(b"AMERICAN EXPRESS").hexdigest()[:16],
        "payee_city": "NEW YORK",
        "payee_state": "NY",
        "payee_zip": "10285",
        "purpose": "CREDIT CARD PAYMENT",
        "spending_category": "credit_card",
        "category_source": "purpose_rule",
        "fec_category": None,
        "memo_code": None,
        "memo_text": None,
        "counted": True,
        "is_in_kind": False,
        "image_num": "202420103010000001",
        "sub_items": None,
    }
    # Newest first, as the page is; each a travel charge, in none of the committee's totals.
    assert [
        (
            c["source_record_id"],
            c["payee_name"],
            c["spending_category"],
            c["counted"],
            c["sub_items"],
        )
        for c in bill["sub_items"]
    ] == [
        ("4240400000000000005", "PATAPSCO INN", "travel", False, []),
        ("4240400000000000004", "SKYLINE AIR", "travel", False, []),
    ]


def test_a_chain_nests_each_sub_item_under_the_one_it_itemizes(client: TestClient) -> None:
    [bill] = walk_expenditures(client, WHITLOCK, category="credit_card")

    [agency] = bill["sub_items"]
    [agencys_payee] = agency["sub_items"]
    assert (bill["counted"], agency["counted"], agencys_payee["counted"]) == (True, False, False)
    assert (agency["payee_name"], agencys_payee["payee_name"], agencys_payee["sub_items"]) == (
        "TIDEMARK MEDIA GROUP",
        "SOCIALREACH ADS",
        [],
    )


def test_a_payee_with_no_page_has_no_payee_id(client: TestClient) -> None:
    # A person's key, and PETTY CASH, which fec/payee_no_page.csv names, have no page; a memo
    # parent counts, its sub-item not.
    rows = list(nested(walk_expenditures(client, HARGROVE)))

    payees = {row["payee_name"]: row["payee_id"] for row, _ in rows}
    assert payees["BENNETT, LOGAN"] is None
    assert payees["PETTY CASH"] is None
    assert (
        payees["TIDEMARK MEDIA GROUP"] == hashlib.sha256(b"TIDEMARK MEDIA GROUP").hexdigest()[:16]
    )
    [memo_parent] = [row for row, _ in rows if row["payee_name"] == "BENNETT, LOGAN"]
    assert (memo_parent["memo_code"], memo_parent["counted"]) == ("X", True)
    assert [c["counted"] for c in memo_parent["sub_items"]] == [False]


@pytest.mark.parametrize("category", list(SPENDING["by_committee_category"][CALLOWAY]))
def test_a_category_lists_the_payments_its_amount_adds_up(
    client: TestClient, category: str
) -> None:
    rows = walk_expenditures(client, CALLOWAY, category=category)

    assert {row["spending_category"] for row in rows} == {category}
    assert sum(Decimal(str(row["amount"])) for row in rows if row["counted"]) == Decimal(
        SPENDING["by_committee_category"][CALLOWAY][category]
    )


@pytest.mark.parametrize("sort", ["date", "amount"])
def test_a_committees_expenditures_page_in_their_sort_order(
    app: FastAPI, client: TestClient, published: Published, sort: str
) -> None:
    small_pages(app, 2)

    rows = walk_expenditures(client, CALLOWAY, sort=sort)

    expected = top_level_ids(published, CALLOWAY, sort)
    assert len(expected) > 3 * 2
    assert [row["source_record_id"] for row in rows] == expected
    if sort == "amount":
        amounts = [row["amount"] for row in rows]
        assert amounts == sorted(amounts, reverse=True)


def test_a_cursor_pages_only_the_sort_it_was_issued_for(app: FastAPI, client: TestClient) -> None:
    small_pages(app, 2)
    url = f"/v1/committees/{CALLOWAY}/expenditures"
    first = ok(client.get(url, params={"cycle": CYCLE}))

    response = client.get(
        url, params={"cycle": CYCLE, "sort": "amount", "cursor": first["next_cursor"]}
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    ("url", "params", "status"),
    [
        ("/v1/committees/C99999999/expenditures", {"cycle": CYCLE}, 404),
        (f"/v1/committees/{CALLOWAY}/expenditures", {"cycle": 2022}, 404),
        (f"/v1/committees/{CALLOWAY}/expenditures", {}, 422),
        (f"/v1/committees/{CALLOWAY}/expenditures", {"cycle": CYCLE, "category": "food"}, 422),
        (f"/v1/committees/{CALLOWAY}/expenditures", {"cycle": CYCLE, "sort": "payee"}, 422),
        (f"/v1/committees/{CALLOWAY}/expenditures", {"cycle": CYCLE, "cursor": "nope"}, 400),
        ("/v1/committees/C99999999/independent-expenditures", {"cycle": CYCLE}, 404),
        (f"/v1/committees/{SUPER_PAC}/independent-expenditures", {"cycle": 2022}, 404),
        (f"/v1/committees/{SUPER_PAC}/independent-expenditures", {}, 422),
        (
            f"/v1/committees/{SUPER_PAC}/independent-expenditures",
            {"cycle": CYCLE, "cursor": "nope"},
            400,
        ),
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

    def p95() -> float:
        timings: list[float] = []
        for _ in range(40):
            started = time.perf_counter()
            ok(client.get(url, params={"cycle": CYCLE}))
            timings.append(time.perf_counter() - started)
        return statistics.quantiles(timings, n=20)[18]

    assert_within(0.1, p95)
