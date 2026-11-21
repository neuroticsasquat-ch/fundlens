"""The gold-backed routes against the fixture cycle, built, loaded and swapped in once for the
module (spec §7.2, §12)."""

import time
from collections.abc import Generator, Iterator, Mapping
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, LiteralString, cast

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from typer.testing import CliRunner

from fundlens import cli
from fundlens.api.app import create_app
from fundlens.api.cache import CACHE_CONTROL
from fundlens.api.deps import get_page_size
from fundlens.api.problems import NO_GOLD
from fundlens.fec.files import files_for
from fundlens.publish import gold as gold_publish
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.integration.conftest import Published, cli_pointed_at, empty_store, scratch_database
from tests.integration.test_publish import load, transform
from tests.integration.test_resolve import MODEL
from tests.integration.test_transform import put_bronze
from tests.timing import assert_within

BUILD = "20261030T030000Z"
CYCLE = fec_fixture.CYCLE
OFFICE_NAMES = {"P": "president", "S": "senate", "H": "house"}
EXPECTED = fec_fixture.expected()


@contextmanager
def published_fixture_cycle(
    data_dir: Path, template: str, *, resolved: bool = False
) -> Generator[str]:
    """A database whose live `gold` is the fixture cycle's, as `publish` leaves it, with that
    build's silver under `data_dir`; the database's conninfo. Copied from the migrated database
    `template`. `resolved`, its donors resolved (with no overrides) before the load, so gold has
    its donor tables and silver its buckets."""
    with scratch_database(template=template) as conninfo:
        store = empty_store()
        try:
            with cli_pointed_at(conninfo=conninfo, data_dir=data_dir):
                put_bronze(store)
                transform(BUILD)
                if resolved:
                    result = CliRunner().invoke(cli.app, ["resolve", "--full", "--build-id", MODEL])
                    assert result.exit_code == 0, result.output
                load(BUILD)
        finally:
            store.delete_prefix("")
        with psycopg.connect(conninfo, autocommit=True) as conn:
            gold_publish.swap(conn)
        yield conninfo


@pytest.fixture(scope="module")
def gold_db(published: Published) -> str:
    """A database whose live `gold` is the fixture cycle's, as `publish` leaves it: the session's,
    which this module's tests only read."""
    return published.conninfo


@pytest.fixture(scope="module")
def client(gold_db: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    data_dir = tmp_path_factory.mktemp("api")
    (data_dir / "silver").mkdir()
    settings = get_settings().model_copy(update={"database_url": gold_db, "data_dir": data_dir})
    with TestClient(create_app(settings)) as client:
        yield client


def slug(race_id: str) -> str:
    """`2024-H-MD-05` → `2024/house/MD-05` (the M2 shared contract)."""
    cycle, office, state, district, *special = race_id.split("-")
    place = f"{state}-{district}" if office == "H" else state
    return f"{cycle}/{OFFICE_NAMES[office]}/{place}" + ("-special" if special else "")


def race_url(race_id: str) -> str:
    """The race page's URL: its slug, a special's suffix as `?special=1`."""
    path = slug(race_id)
    if path.endswith("-special"):
        return f"/v1/races/{path.removesuffix('-special')}?special=1"
    return f"/v1/races/{path}"


def ok(response: Response) -> Any:
    assert response.status_code == 200, response.text
    return response.json()


def assert_not_found(response: Response) -> None:
    assert response.status_code == 404, response.text
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["status"] == 404


def totals(body: dict[str, Any], expected: Mapping[str, object]) -> dict[str, object]:
    """`body`'s figures for the keys `expected` names."""
    return {key: body[key] for key in expected}


def test_cycles_lists_the_fixture_cycle(client: TestClient) -> None:
    races = ok(client.get(f"/v1/cycles/{CYCLE}/races"))

    assert ok(client.get("/v1/cycles")) == [
        {
            "cycle": CYCLE,
            "race_count": len(races),
            "contribution_count": EXPECTED["silver"]["contribution"],
            "total_amount": EXPECTED["contributions"]["total_amount"],
        }
    ]


def test_a_cycles_races_carry_their_totals_president_first(client: TestClient) -> None:
    races = ok(client.get(f"/v1/cycles/{CYCLE}/races"))

    by_id = {race["race_id"]: race for race in races}
    for race_id, expected in EXPECTED["races"].items():
        assert totals(by_id[race_id], expected) == expected, race_id
    assert races[0]["race_id"] == "2024-P-US-00"
    offices = [race["office"] for race in races]
    assert offices == sorted(offices, key="PSH".index)


def test_races_filter_by_office_and_state(client: TestClient) -> None:
    senate_ne = ok(client.get(f"/v1/cycles/{CYCLE}/races", params={"office": "S", "state": "NE"}))
    house_md = ok(client.get(f"/v1/cycles/{CYCLE}/races", params={"office": "H", "state": "MD"}))

    assert [race["slug"] for race in senate_ne] == ["2024/senate/NE", "2024/senate/NE-special"]
    assert [race["district"] for race in house_md] == [f"0{n}" for n in range(1, 9)]


def test_races_for_an_unknown_cycle_is_a_404_and_a_bad_filter_a_422(client: TestClient) -> None:
    assert_not_found(client.get("/v1/cycles/1999/races"))
    assert ok(client.get(f"/v1/cycles/{CYCLE}/races", params={"state": "ZZ"})) == []

    response = client.get(f"/v1/cycles/{CYCLE}/races", params={"state": "md"})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize("race_id", list(EXPECTED["races"]))
def test_a_race_page_has_its_candidates_and_top_committees(
    client: TestClient, race_id: str
) -> None:
    race = ok(client.get(race_url(race_id)))

    expected = EXPECTED["races"][race_id]
    assert race["race_id"] == race_id
    assert totals(race, expected) == expected
    candidates = {
        candidate_id: totals_
        for candidate_id, totals_ in EXPECTED["candidates"].items()
        if totals_["race_id"] == race_id
    }
    assert {c["candidate_id"] for c in race["candidates"]} == set(candidates)
    for candidate in race["candidates"]:
        want = {k: v for k, v in candidates[candidate["candidate_id"]].items() if k != "race_id"}
        assert totals(candidate, want) == want, candidate["candidate_id"]
    raised = [
        c["total_individual"] + c["total_committee"] + c["total_jfc_transfers"] + c["self_funding"]
        for c in race["candidates"]
    ]
    assert raised == sorted(raised, reverse=True)
    # Givers and spenders ranked together (NEU-2057).
    top = race["top_committees"]
    assert [c["rank"] for c in top] == list(range(1, len(top) + 1))
    assert [[c["kind"], c["committee_id"], c["amount"]] for c in top] == EXPECTED[
        "race_top_committees"
    ].get(race_id, [])
    assert sum(c["amount"] for c in top if c["kind"] == "contribution") == race["total_committee"]


def test_a_race_page_counts_jfc_transfers_apart_from_its_other_money(client: TestClient) -> None:
    race = ok(client.get("/v1/races/2024/senate/MD"))

    # OKAFOR VICTORY FUND's transfers to OKAFOR's campaign (an 18J, an 18G and a 15J), in neither
    # her individual nor her committee total (NEU-2124).
    assert race["total_jfc_transfers"] == 19500
    assert {c["candidate_id"]: c["total_jfc_transfers"] for c in race["candidates"]} == {
        "S4MD00103": 19500,
        "S4MD00104": 0,
        "S4MD00105": 0,
        "S4MD00111": 0,
    }
    okafor = next(c for c in race["candidates"] if c["candidate_id"] == "S4MD00103")
    assert (okafor["total_individual"], okafor["total_committee"]) == (50700, 5000)


def test_a_race_page_names_its_committees(client: TestClient) -> None:
    race = ok(client.get(race_url("2024-H-MD-05")))

    assert race["slug"] == "2024/house/MD-05"
    # The super PAC's independent expenditures for CALLOWAY and against DRISCOLL (NEU-2057), then
    # BRICKLAYERS' gifts to CALLOWAY, DRISCOLL and YANG, the last net of its refund. OLD LINE
    # REPUBLICAN COMMITTEE's void of a 2022 gift to CALLOWAY is no gift here (NEU-2204).
    assert race["top_committees"][:2] == [
        {
            "rank": 1,
            "committee_id": "C00800201",
            "name": "MARYLAND FORWARD PAC",
            "amount": 40000.0,
            "kind": "ie",
        },
        {
            "rank": 2,
            "committee_id": "C00800202",
            "name": "BRICKLAYERS UNITED PAC",
            "amount": 9500.0,
            "kind": "contribution",
        },
    ]
    assert "C00800203" not in {c["committee_id"] for c in race["top_committees"]}


def test_an_unknown_race_is_a_404(client: TestClient) -> None:
    # The fixture's unmatched filing: no 9th district in Maryland, so no race.
    assert_not_found(client.get("/v1/races/2024/house/MD-09"))
    assert_not_found(client.get("/v1/races/2024/senate/MD?special=1"))
    assert client.get("/v1/races/2024/governor/MD").status_code == 422


@pytest.mark.parametrize("candidate_id", list(EXPECTED["candidates"]))
def test_a_candidate_page_has_its_cycle(client: TestClient, candidate_id: str) -> None:
    candidate = ok(client.get(f"/v1/candidates/{candidate_id}"))

    assert candidate["candidate_id"] == candidate_id
    [cycle] = candidate["cycles"]
    expected = EXPECTED["candidates"][candidate_id]
    assert cycle["cycle"] == CYCLE
    assert totals(cycle, expected) == expected
    race_id = EXPECTED["candidates"][candidate_id]["race_id"]
    assert cycle["race_slug"] == (None if race_id is None else slug(race_id))
    assert cycle["contributor_count"] is None


def test_a_candidate_page_names_the_candidate(client: TestClient) -> None:
    candidate = ok(client.get("/v1/candidates/S4MD00103"))

    assert {k: v for k, v in candidate.items() if k != "cycles"} == {
        "candidate_id": "S4MD00103",
        "name": "OKAFOR, DIANA",
        "party": "DEM",
        "office": "S",
        "state": "MD",
        "district": "00",
    }
    assert candidate["cycles"][0]["race_slug"] == "2024/senate/MD"


@pytest.mark.parametrize("committee_id", list(EXPECTED["committees"]))
def test_a_committee_page_has_its_cycle_and_top_recipients(
    client: TestClient, committee_id: str
) -> None:
    committee = ok(client.get(f"/v1/committees/{committee_id}"))

    assert committee["committee_id"] == committee_id
    [cycle] = committee["cycles"]
    expected = EXPECTED["committees"][committee_id]
    assert cycle["cycle"] == CYCLE
    assert totals(cycle, expected) == expected
    recipients = cycle["top_recipients"]
    assert [r["rank"] for r in recipients] == list(range(1, len(recipients) + 1))
    assert [[r["recipient_kind"], r["recipient_id"], r["amount"]] for r in recipients] == EXPECTED[
        "top_recipients"
    ].get(committee_id, [])
    assert (
        sum(r["amount"] for r in recipients if r["recipient_kind"] == "candidate")
        == cycle["total_to_candidates"]
    )
    assert cycle["total_returned_by_candidates"] == EXPECTED["returned_by_candidates"][
        "by_committee"
    ].get(committee_id, 0)


def test_a_committee_page_names_whom_it_gave_to(client: TestClient) -> None:
    committee = ok(client.get("/v1/committees/C00800114"))

    assert committee["name"] == "CALLOWAY LEADERSHIP FUND"
    assert committee["designation"] == "D"
    assert committee["is_conduit"] is False
    assert committee["cycles"][0]["top_recipients"] == [
        {
            "rank": 1,
            "recipient_kind": "candidate",
            "recipient_id": "H4MD05106",
            "name": "CALLOWAY, RUTH",
            "amount": 5000.0,
        }
    ]


@pytest.mark.parametrize("committee_id", list(EXPECTED["committees"]))
def test_a_committee_page_has_its_organization_money(client: TestClient, committee_id: str) -> None:
    # The super PAC's is CHESAPEAKE STEEL's gifts less its refund, once under its most-money
    # spelling; a committee no organization gave to has 0 and an empty list (ADR-0011). A hybrid
    # PAC's non-contribution account is in its top organizations but not its total (NEU-2192), and
    # so are a party account's givers (NEU-2205). A cost coming back to the committee, the IRS's
    # payroll-tax refund to the party, is in neither: no organization gave it (NEU-2402).
    organizations = EXPECTED["organization_receipts"]
    non_contribution = EXPECTED["non_contribution_account"]["organizations_by_committee"]
    other_lines = EXPECTED["other_lines"]["organizations_by_committee"]
    [cycle] = ok(client.get(f"/v1/committees/{committee_id}"))["cycles"]

    assert cycle["total_from_organizations"] == organizations["by_committee"].get(
        committee_id, 0
    ) - non_contribution.get(committee_id, 0) - other_lines.get(committee_id, 0)
    assert [
        [o["organization_key"], o["name"], o["amount"]] for o in cycle["top_organizations"]
    ] == organizations["top_by_committee"].get(committee_id, [])
    assert [o["rank"] for o in cycle["top_organizations"]] == list(
        range(1, len(cycle["top_organizations"]) + 1)
    )


@pytest.mark.parametrize("committee_id", list(EXPECTED["committees"]))
def test_a_committee_page_has_its_non_contribution_account(
    client: TestClient, committee_id: str
) -> None:
    # A hybrid PAC's non-contribution account, individuals' and organizations' gifts net of
    # refunds, is its own figure, in neither total_individual nor total_from_organizations; 0 at
    # every committee that has none (NEU-2192).
    [cycle] = ok(client.get(f"/v1/committees/{committee_id}"))["cycles"]

    assert cycle["total_non_contribution_account"] == EXPECTED["non_contribution_account"][
        "by_committee"
    ].get(committee_id, 0)


@pytest.mark.parametrize("committee_id", list(EXPECTED["committees"]))
def test_a_committee_page_has_its_refunds(client: TestClient, committee_id: str) -> None:
    # The refunds netted into total_individual and total_from_organizations, so 0 or less; 0 at
    # every committee that made none (NEU-2265).
    [cycle] = ok(client.get(f"/v1/committees/{committee_id}"))["cycles"]

    assert cycle["total_refunds"] == EXPECTED["refunds"]["by_committee"].get(committee_id, 0)


def test_a_super_pac_page_lists_the_organizations_that_gave_to_it(client: TestClient) -> None:
    committee = ok(client.get("/v1/committees/C00800201"))

    # ONE NATION, a Form 5 filer, is an organization; RESTORATION PAC, a super PAC its filer typed
    # ORG, is a committee and no organization (NEU-2195). TIDEWATER MARINE SUPPLY's gift is on a Q2
    # filing and on the amendment that supersedes it, and counts once (NEU-2196). MAGOTHY HOLDINGS's
    # gift is only a memo line, which counts; SEVERN CAPITAL's is a row its partners' memo lines
    # attribute, which count nowhere (NEU-2198). SEVERN STATE LEADERSHIP FUND's gift is on line
    # 11(c) by its TRAN_ID: listed, since it gave, but in total_other_lines (NEU-2276). CHOPTANK
    # RIVER FOUNDATION's 10 names the non-contribution account in its memo: listed, but in
    # total_non_contribution_account, though `cm` types the committee O (NEU-2400).
    assert committee["cycles"][0]["total_from_organizations"] == 122500.0
    assert committee["cycles"][0]["total_non_contribution_account"] == 30000.0
    assert committee["cycles"][0]["top_organizations"] == [
        {
            "rank": 1,
            "name": "CHESAPEAKE STEEL, INC.",
            "organization_key": "CHESAPEAKE STEEL",
            "amount": 72500.0,
        },
        {"rank": 2, "name": "ONE NATION", "organization_key": "ONE NATION", "amount": 40000.0},
        {
            "rank": 3,
            "name": "CHOPTANK RIVER FOUNDATION",
            "organization_key": "CHOPTANK RIVER FOUNDATION",
            "amount": 30000.0,
        },
        {
            "rank": 4,
            "name": "SEVERN STATE LEADERSHIP FUND",
            "organization_key": "SEVERN STATE LEADERSHIP FUND",
            "amount": 20000.0,
        },
        {
            "rank": 5,
            "name": "TIDEWATER MARINE SUPPLY LLC",
            "organization_key": "TIDEWATER MARINE SUPPLY",
            "amount": 5000.0,
        },
        {
            "rank": 6,
            "name": "MAGOTHY HOLDINGS LLC",
            "organization_key": "MAGOTHY HOLDINGS",
            "amount": 3000.0,
        },
        {
            "rank": 7,
            "name": "SEVERN CAPITAL LLC",
            "organization_key": "SEVERN CAPITAL",
            "amount": 2000.0,
        },
    ]


def test_a_build_loaded_before_resolution_lists_no_top_donors(client: TestClient) -> None:
    race = ok(client.get("/v1/races/2024/senate/MD"))
    candidate = ok(client.get("/v1/candidates/S4MD00104"))
    committee = ok(client.get("/v1/committees/C00800104"))

    assert race["top_donors"] == []
    assert [cycle["top_donors"] for cycle in candidate["cycles"]] == [[]]
    assert [cycle["top_donors"] for cycle in committee["cycles"]] == [[]]


def test_unknown_candidates_and_committees_are_404s(client: TestClient) -> None:
    assert_not_found(client.get("/v1/candidates/H0XX00000"))
    assert_not_found(client.get("/v1/committees/C99999999"))


REPORTED_COLUMNS = EXPECTED["reported_totals"]["columns"]
GOLD_REPORTED = EXPECTED["gold_reported"]


def as_json(value: object) -> object:
    """A gold value as the API's JSON carries it: money a number, a date ISO 8601."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def expected_reported(row: list[Any] | None) -> dict[str, object] | None:
    """An `expected.yaml` reported-totals row as the API's `reported` object."""
    return None if row is None else dict(zip(REPORTED_COLUMNS, map(as_json, row), strict=True))


def gold_reported(conninfo: str, candidate_id: str) -> tuple[dict[str, object] | None, list[Any]]:
    """The candidate's 2024 `reported` object and gift sizes as gold holds them."""
    columns = cast(LiteralString, ", ".join(f"reported_{column}" for column in REPORTED_COLUMNS))
    with psycopg.connect(conninfo) as conn:
        row = conn.execute(
            "SELECT "
            + columns
            + " FROM gold.candidate_cycle WHERE candidate_id = %s AND cycle = %s",
            (candidate_id, CYCLE),
        ).fetchone()
        gift_sizes = conn.execute(
            "SELECT bucket, amount, donors FROM gold.candidate_gift_size"
            " WHERE candidate_id = %s AND cycle = %s",
            (candidate_id, CYCLE),
        ).fetchall()
    assert row is not None
    reported = None if row[0] is None else expected_reported(list(row))
    return reported, [
        {"bucket": bucket, "amount": float(amount), "donors": donors}
        for bucket, amount, donors in gift_sizes
    ]


@pytest.mark.parametrize("candidate_id", list(GOLD_REPORTED["candidates"]))
def test_a_candidate_page_has_its_reported_totals_and_gift_sizes(
    client: TestClient, gold_db: str, candidate_id: str
) -> None:
    """The reported totals of the candidate's credited committees, their itemized total and the
    one over the other, as gold has them (every-FEC-dollar spec §4.3, §4.4); and, on a build loaded
    before resolution, only the unitemized gift-size bucket (§4.6)."""
    [cycle] = ok(client.get(f"/v1/candidates/{candidate_id}"))["cycles"]
    receipts, cash, itemized_total, coverage, converted = GOLD_REPORTED["candidates"][candidate_id]
    reported, gift_sizes = gold_reported(gold_db, candidate_id)

    assert cycle["reported"] == reported
    headline = cycle["reported"] and (
        cycle["reported"]["receipts"],
        cycle["reported"]["cash_on_hand_end"],
    )
    assert headline == (None if receipts is None else (receipts, cash))
    assert cycle["itemized_total"] == itemized_total
    assert (cycle["coverage"] and round(cycle["coverage"], 4)) == coverage
    assert cycle["reported_includes_converted_committee"] is converted
    assert sorted(cycle["gift_sizes"], key=lambda row: row["bucket"]) == sorted(
        gift_sizes, key=lambda row: row["bucket"]
    )
    assert {row["bucket"] for row in cycle["gift_sizes"]} <= {"unitemized"}


def test_a_handoffs_first_candidate_has_no_reported_figures(client: TestClient) -> None:
    """BIDEN's committee is HARRIS's whole from the handoff (spec §4.3): no reported row, no
    itemized figure, no unitemized bucket."""
    [cycle] = ok(client.get("/v1/candidates/P80000722"))["cycles"]

    assert (cycle["reported"], cycle["itemized_total"], cycle["coverage"]) == (None, None, None)
    assert cycle["gift_sizes"] == []


@pytest.mark.parametrize("committee_id", list(GOLD_REPORTED["committees"]))
def test_a_committee_page_has_its_reported_totals_and_coverage(
    client: TestClient, committee_id: str
) -> None:
    [cycle] = ok(client.get(f"/v1/committees/{committee_id}"))["cycles"]
    itemized_total, individual_itemized, cash, coverage = GOLD_REPORTED["committees"][committee_id]

    assert cycle["reported"] == expected_reported(
        EXPECTED["reported_totals"]["reported_total"][CYCLE].get(committee_id)
    )
    assert cycle["reported"]["individual_itemized"] == individual_itemized
    assert cycle["reported"]["cash_on_hand_end"] == cash
    assert cycle["itemized_total"] == itemized_total
    assert (cycle["coverage"] and round(cycle["coverage"], 4)) == coverage


@pytest.mark.parametrize("race_id", list(GOLD_REPORTED["races"]))
def test_a_race_has_its_reported_cash_on_hand_and_its_candidates_coverage(
    client: TestClient, race_id: str
) -> None:
    race = ok(client.get(race_url(race_id)))
    [listed] = [
        summary
        for summary in ok(client.get(f"/v1/cycles/{CYCLE}/races"))
        if summary["race_id"] == race_id
    ]

    assert race["reported_cash_on_hand"] == GOLD_REPORTED["races"][race_id]
    assert listed["reported_cash_on_hand"] == GOLD_REPORTED["races"][race_id]
    for candidate in race["candidates"]:
        receipts, cash, itemized_total, coverage, _ = GOLD_REPORTED["candidates"][
            candidate["candidate_id"]
        ]
        reported = candidate["reported"]
        assert (reported and (reported["receipts"], reported["cash_on_hand_end"])) == (
            None if receipts is None else (receipts, cash)
        ), candidate["candidate_id"]
        assert candidate["itemized_total"] == itemized_total
        assert (candidate["coverage"] and round(candidate["coverage"], 4)) == coverage


def test_reconciliation_lists_the_committees_over_their_reported_figure(
    client: TestClient,
) -> None:
    page = ok(client.get("/v1/reconciliation", params={"cycle": CYCLE}))

    # Both measures (every-FEC-dollar spec §4.5, §5.6), the largest excess first.
    listed: list[tuple[int, str, str, list[Any]]] = [
        (fundlens - reported, committee_id, measure, [fundlens, reported, ratio])
        for measure, committees in GOLD_REPORTED["reconciliation"].items()
        for committee_id, (fundlens, reported, ratio) in committees.items()
    ]
    expected = [
        [committee_id, measure, *figures]
        for _, committee_id, measure, figures in sorted(
            listed, key=lambda row: (-row[0], row[1], row[2])
        )
    ]
    assert [
        [
            row["committee_id"],
            row["measure"],
            row["fundlens"],
            row["reported"],
            None if row["ratio"] is None else round(row["ratio"], 4),
        ]
        for row in page["rows"]
    ] == expected
    assert [row["name"] for row in page["rows"]] == [
        ok(client.get(f"/v1/committees/{row['committee_id']}"))["name"] for row in page["rows"]
    ]
    assert all(row["cycle"] == CYCLE for row in page["rows"])
    assert page["next_cursor"] is None


@contextmanager
def planted_reconciliation(conninfo: str, rows: list[tuple[str, int, int]]) -> Generator[None]:
    """`rows` (committee_id, fundlens, reported) in the live `gold.reconciliation` for the fixture
    cycle, deleted again after: the session's gold is shared, and its one row cannot page."""
    with psycopg.connect(conninfo, autocommit=True) as conn:
        for committee_id, fundlens, reported in rows:
            conn.execute(
                "INSERT INTO gold.reconciliation VALUES"
                " (%s, %s, 'individual_itemized', %s, %s, %s::numeric / %s)",
                (committee_id, CYCLE, fundlens, reported, fundlens, reported),
            )
        try:
            yield
        finally:
            conn.execute(
                "DELETE FROM gold.reconciliation WHERE committee_id = ANY(%s) AND cycle = %s",
                ([committee_id for committee_id, *_ in rows], CYCLE),
            )


def test_reconciliation_pages_by_excess_then_committee(client: TestClient, gold_db: str) -> None:
    """One row a page: the largest excess first, a tie by committee id (C00800109's itemized
    figure is $100 over; the fixture's spending rows, §5.6, lie between)."""
    app = cast(FastAPI, client.app)
    app.dependency_overrides[get_page_size] = lambda: 1
    seen: list[str] = []
    try:
        with planted_reconciliation(
            gold_db, [("C00800101", 19725, 19625), ("C00800102", 35650, 35150)]
        ):
            cursor: str | None = None
            while True:
                params: dict[str, str | int] = {"cycle": CYCLE}
                if cursor is not None:
                    params["cursor"] = cursor
                page = ok(client.get("/v1/reconciliation", params=params))
                seen += [row["committee_id"] for row in page["rows"]]
                cursor = page["next_cursor"]
                if cursor is None:
                    break
    finally:
        del app.dependency_overrides[get_page_size]

    assert seen == [
        "C00703975",
        "C00800205",
        "C00800115",
        "C00800102",
        "C00800203",
        "C00800114",
        "C00800101",
        "C00800109",
    ]


def test_reconciliation_needs_a_known_cycle_and_its_own_cursor(client: TestClient) -> None:
    assert_not_found(client.get("/v1/reconciliation", params={"cycle": 2022}))
    assert client.get("/v1/reconciliation").status_code == 422
    assert client.get("/v1/reconciliation", params={"cycle": 2023}).status_code == 422
    bad = client.get("/v1/reconciliation", params={"cycle": CYCLE, "cursor": "not-a-cursor"})
    assert bad.status_code == 400, bad.text


def test_a_candidate_alias_is_a_cacheable_redirect_to_the_id_holding_the_money(
    client: TestClient,
) -> None:
    [(alias, canonical)] = EXPECTED["aliases"].items()

    page = client.get(f"/v1/candidates/{alias}", follow_redirects=False)
    rows = client.get(
        f"/v1/candidates/{alias}/contributions",
        params={"cycle": CYCLE, "cursor": "x"},
        follow_redirects=False,
    )

    assert page.status_code == 301, page.text
    assert page.headers["location"] == f"/v1/candidates/{canonical}"
    assert page.headers["cache-control"] == CACHE_CONTROL
    assert rows.status_code == 301, rows.text
    assert rows.headers["location"] == (
        f"/v1/candidates/{canonical}/contributions?cycle={CYCLE}&cursor=x"
    )
    assert ok(client.get(f"/v1/candidates/{alias}"))["candidate_id"] == canonical


def test_search_finds_a_person_under_one_candidate_id(client: TestClient) -> None:
    [canonical] = EXPECTED["aliases"].values()

    results = ok(client.get("/v1/search", params={"q": "driscoll", "kind": "candidate"}))

    # One DRISCOLL, under the id holding his money: never his alias.
    assert [r["id"] for r in results] == [canonical]


def test_search_ranks_trigram_matches_fast(client: TestClient) -> None:
    client.get("/v1/search", params={"q": "calloway"})  # A warm pool and build-id cache.
    responses: list[Response] = []

    def search() -> float:
        started = time.perf_counter()
        responses.append(client.get("/v1/search", params={"q": "calloway"}))
        return time.perf_counter() - started

    assert_within(0.05, search)
    results = ok(responses[-1])
    assert {(r["kind"], r["id"]) for r in results} >= {
        ("candidate", "H4MD05106"),
        ("committee", "C00800106"),
        ("committee", "C00800114"),
    }
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert len(results) <= 20


def test_search_matches_aliases_and_filters_by_kind(client: TestClient) -> None:
    races = ok(client.get("/v1/search", params={"q": "2024/senate/MD", "kind": "race"}))
    committees = ok(client.get("/v1/search", params={"q": "calloway", "kind": "committee"}))

    assert races[0]["id"] == "2024-S-MD-00"
    assert races[0]["aliases"] == "2024/senate/MD"
    assert {r["kind"] for r in races} == {"race"}
    assert {r["kind"] for r in committees} == {"committee"}


def test_search_needs_a_query(client: TestClient) -> None:
    assert client.get("/v1/search").status_code == 422
    assert client.get("/v1/search", params={"q": "x"}).status_code == 422
    assert client.get("/v1/search", params={"q": "calloway", "kind": "pac"}).status_code == 422


def test_meta_names_the_build_and_its_source_dates(client: TestClient) -> None:
    meta = ok(client.get("/v1/meta"))

    assert meta["build_id"] == BUILD
    assert meta["cycles"][str(CYCLE)]["build_id"] == BUILD
    assert set(meta["cycles"][str(CYCLE)]["source_dates"]) == {f.name for f in files_for(CYCLE)}


def test_routes_are_cached_under_the_build(client: TestClient) -> None:
    response = client.get("/v1/committees/C00800114")

    assert response.headers["cache-control"] == CACHE_CONTROL
    assert response.headers["etag"] == f'"{BUILD}"'


@pytest.mark.parametrize(
    "path",
    [
        "/v1/cycles",
        f"/v1/cycles/{CYCLE}/races",
        "/v1/races/2024/senate/MD",
        "/v1/candidates/S4MD00103",
        "/v1/committees/C00800114",
        f"/v1/reconciliation?cycle={CYCLE}",
        "/v1/search?q=calloway",
    ],
)
def test_every_route_is_a_503_before_any_gold_exists(
    scratch_db: str, tmp_path: Path, path: str
) -> None:
    (tmp_path / "silver").mkdir()
    settings = get_settings().model_copy(update={"database_url": scratch_db, "data_dir": tmp_path})
    with TestClient(create_app(settings)) as client:
        response = client.get(path)

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == NO_GOLD
    assert response.headers["cache-control"] == "no-store"


def test_a_table_missing_from_a_live_gold_is_a_500_not_a_503(
    scratch_db: str, tmp_path: Path
) -> None:
    with psycopg.connect(scratch_db, autocommit=True) as conn:
        conn.execute("CREATE SCHEMA gold")
    (tmp_path / "silver").mkdir()
    settings = get_settings().model_copy(update={"database_url": scratch_db, "data_dir": tmp_path})
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        response = client.get("/v1/cycles")

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
