"""The gold-backed routes against the fixture cycle, built, loaded and swapped in once for the
module (spec §7.2, §12)."""

import time
from collections.abc import Generator, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
import pytest
from alembic import command
from fastapi.testclient import TestClient
from httpx2 import Response
from typer.testing import CliRunner

from fundlens import cli
from fundlens.api.app import create_app
from fundlens.api.cache import CACHE_CONTROL
from fundlens.api.problems import NO_GOLD
from fundlens.fec.files import files_for
from fundlens.publish import gold as gold_publish
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.integration.conftest import (
    NO_OVERRIDES,
    TEST_BUCKET,
    alembic_config,
    empty_store,
    scratch_database,
)
from tests.integration.test_publish import load, transform
from tests.integration.test_resolve import MODEL
from tests.integration.test_transform import put_bronze

BUILD = "20261030T030000Z"
CYCLE = fec_fixture.CYCLE
OFFICE_NAMES = {"P": "president", "S": "senate", "H": "house"}
EXPECTED = fec_fixture.expected()


def leave_logging_alone(level: str) -> None:
    # The CLI's callback reconfigures the root logger, which would outlive the module.
    pass


@contextmanager
def published_fixture_cycle(data_dir: Path, *, resolved: bool = False) -> Generator[str]:
    """A database whose live `gold` is the fixture cycle's, as `publish` leaves it, with that
    build's silver under `data_dir`; the database's conninfo. `resolved`, its donors resolved
    (with no overrides) before the load, so gold has its donor tables and silver its buckets."""
    with scratch_database() as conninfo:
        command.upgrade(alembic_config(conninfo), "head")
        store = empty_store()
        with pytest.MonkeyPatch.context() as env:
            env.setattr(cli, "configure_logging", leave_logging_alone)
            env.setenv("R2_BUCKET", TEST_BUCKET)
            env.setenv("DATABASE_URL", conninfo)
            env.setenv("DATA_DIR", str(data_dir))
            env.setenv("OVERRIDES_PATH", str(NO_OVERRIDES))
            get_settings.cache_clear()
            try:
                put_bronze(store)
                transform(BUILD)
                if resolved:
                    result = CliRunner().invoke(cli.app, ["resolve", "--full", "--build-id", MODEL])
                    assert result.exit_code == 0, result.output
                load(BUILD)
            finally:
                store.delete_prefix("")
                get_settings.cache_clear()
        with psycopg.connect(conninfo, autocommit=True) as conn:
            gold_publish.swap(conn)
        yield conninfo


@pytest.fixture(scope="module")
def gold_db(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """A database whose live `gold` is the fixture cycle's, as `publish` leaves it."""
    with published_fixture_cycle(tmp_path_factory.mktemp("data")) as conninfo:
        yield conninfo


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


IE_FIELDS = frozenset({"ie_support", "ie_oppose", "ie_total"})


def without_ies(expected: Mapping[str, object]) -> dict[str, object]:
    """`expected` as gold has it today: independent expenditures arrive with NEU-2057."""
    return {key: 0 if key in IE_FIELDS else value for key, value in expected.items()}


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
        want = without_ies(expected)
        assert totals(by_id[race_id], want) == want, race_id
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

    expected = without_ies(EXPECTED["races"][race_id])
    assert race["race_id"] == race_id
    assert totals(race, expected) == expected
    candidates = {
        candidate_id: totals_
        for candidate_id, totals_ in EXPECTED["candidates"].items()
        if totals_["race_id"] == race_id
    }
    assert {c["candidate_id"] for c in race["candidates"]} == set(candidates)
    for candidate in race["candidates"]:
        want = without_ies(candidates[candidate["candidate_id"]])
        del want["race_id"]
        assert totals(candidate, want) == want, candidate["candidate_id"]
    raised = [
        c["total_individual"] + c["total_committee"] + c["self_funding"] for c in race["candidates"]
    ]
    assert raised == sorted(raised, reverse=True)
    top = race["top_committees"]
    assert [c["rank"] for c in top] == list(range(1, len(top) + 1))
    assert sum(c["amount"] for c in top) == race["total_committee"]


def test_a_race_page_names_its_committees(client: TestClient) -> None:
    race = ok(client.get(race_url("2024-H-MD-05")))

    assert race["slug"] == "2024/house/MD-05"
    assert race["top_committees"][0] == {
        "rank": 1,
        "committee_id": "C00800202",
        "name": "BRICKLAYERS UNITED PAC",
        "amount": 7500.0,
        "kind": "contribution",
    }


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
    expected = without_ies(EXPECTED["candidates"][candidate_id])
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
    expected = without_ies(EXPECTED["committees"][committee_id])
    assert cycle["cycle"] == CYCLE
    assert totals(cycle, expected) == expected
    recipients = cycle["top_recipients"]
    assert [r["rank"] for r in recipients] == list(range(1, len(recipients) + 1))
    assert sum(r["amount"] for r in recipients) == cycle["total_to_candidates"]


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


def test_search_ranks_trigram_matches_fast(client: TestClient) -> None:
    client.get("/v1/search", params={"q": "calloway"})  # A warm pool and build-id cache.

    started = time.perf_counter()
    response = client.get("/v1/search", params={"q": "calloway"})
    elapsed = time.perf_counter() - started

    results = ok(response)
    assert elapsed < 0.05
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
