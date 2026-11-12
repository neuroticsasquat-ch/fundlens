"""Two cycles in gold at once (NEU-2059, spec §3.4, §4): the 2024 fixture cycle and a tiny 1998 one,
which FEC publishes no `ccl` for, transformed, resolved together, and each loaded and published
in turn, so the second load rebuilds gold from both cycles' live builds."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from fundlens import cli, markers, paths
from fundlens.api.app import create_app
from fundlens.publish import gold as gold_publish
from fundlens.publish.gold import NothingToPublish
from fundlens.r2 import R2
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.integration.conftest import Snapshot, build_snapshot, restore, scratch_database
from tests.integration.test_api_donors import silver_rows
from tests.integration.test_api_routes import ok
from tests.integration.test_resolve import MEMORY_LIMIT, MODEL, resolve
from tests.integration.test_transform import (
    BUILD,
    parquet_rows,
    put_bronze,
    seats_report,
    transform,
)

FIXTURE_CYCLE = fec_fixture.CYCLE
EARLY = 1998
# A second build of 2024, published after both cycles are live.
REBUILT = "20261105T030000Z"
CALDER, PARRISH = "H8MD05201", "H8MD05202"
CALDER_COMMITTEE, PARRISH_COMMITTEE = "C00298001", "C00298002"
# The 2024 fixture's party committee, filed in 1998 under a shorter name.
BOTH_CYCLES_COMMITTEE = "C00800203"
# The Musk case's two 1998 gifts (tests/fixtures/fec/1998/indiv.csv).
MUSK_1998 = (4199810000000000001, 4199810000000000002)
EXPECTED = fec_fixture.expected()


def _publish(cycle: int, store: R2, data_dir: Path) -> None:
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        gold_publish.publish(
            cycle, store, conn=conn, data_dir=data_dir, purge=None, sleep=lambda _: None
        )


def _load_and_publish(cycle: int, build_id: str, store: R2) -> None:
    result = CliRunner().invoke(cli.app, ["load", "--cycle", str(cycle), "--build-id", build_id])
    assert result.exit_code == 0, result.output
    _publish(cycle, store, get_settings().data_dir)


@pytest.fixture(scope="module")
def two_cycles(
    transformed_snapshot: Snapshot,
    migrated_template: str,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Snapshot]:
    """The 2024 fixture cycle (`transformed_snapshot`) and 1998, both transformed as build
    `BUILD`, resolved together as model `MODEL`, then 2024 loaded and published, then 1998."""

    def steps(env: pytest.MonkeyPatch) -> None:
        store = R2.from_settings(get_settings())
        put_bronze(store, EARLY)
        seats_report(EARLY)
        result = transform(EARLY)
        assert result.exit_code == 0, result.output
        env.setenv("DUCKDB_MEMORY_LIMIT", MEMORY_LIMIT)
        get_settings.cache_clear()
        resolved = resolve("--full", "--build-id", MODEL)
        assert resolved.exit_code == 0, resolved.output
        for cycle in (FIXTURE_CYCLE, EARLY):
            _load_and_publish(cycle, BUILD, store)

    yield from build_snapshot(
        "two-cycles",
        tmp_path_factory,
        template=migrated_template,
        steps=steps,
        parent=transformed_snapshot,
    )


@pytest.fixture(scope="module")
def client(two_cycles: Snapshot) -> Iterator[TestClient]:
    """The API over a copy of the two-cycle database and the snapshot's silver, read only."""
    with scratch_database(template=two_cycles.database) as conninfo:
        settings = get_settings().model_copy(
            update={"database_url": conninfo, "data_dir": two_cycles.data_dir}
        )
        with TestClient(create_app(settings)) as client:
            yield client


def _all_pages(client: TestClient, url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        page = ok(client.get(url, params={"cursor": cursor} if cursor else None))
        rows += page["contributions"]
        cursor = page["next_cursor"]
        if cursor is None:
            return rows


def test_a_1998_candidate_links_to_its_committee_without_ccl(
    two_cycles: Snapshot, client: TestClient
) -> None:
    links = parquet_rows(
        paths.local_path(
            two_cycles.data_dir,
            f"{paths.silver_partition('candidate_committee_link', EARLY, BUILD)}/{paths.part(0)}",
        )
    )
    race = ok(client.get(f"/v1/races/{EARLY}/house/MD-05"))

    # CALDER through her `cn` row's principal committee, PARRISH through his committee's `cm` row.
    assert {
        (row["candidate_id"], row["committee_id"], row["designation"], row["linkage_id"])
        for row in links
    } == {(CALDER, CALDER_COMMITTEE, "P", None), (PARRISH, PARRISH_COMMITTEE, "P", None)}
    assert {
        candidate["candidate_id"]: (
            candidate["principal_committee_id"],
            candidate["total_individual"],
            candidate["total_committee"],
        )
        for candidate in race["candidates"]
    } == {CALDER: (CALDER_COMMITTEE, 1000, 2000), PARRISH: (PARRISH_COMMITTEE, 750, 0)}
    assert (race["total_individual"], race["total_committee"]) == (1750, 2000)


def test_cycles_lists_both_cycles_with_their_own_totals(client: TestClient) -> None:
    races = {cycle: ok(client.get(f"/v1/cycles/{cycle}/races")) for cycle in (FIXTURE_CYCLE, EARLY)}

    assert ok(client.get("/v1/cycles")) == [
        {
            "cycle": FIXTURE_CYCLE,
            "race_count": len(races[FIXTURE_CYCLE]),
            "contribution_count": EXPECTED["silver"]["contribution"],
            "total_amount": EXPECTED["contributions"]["total_amount"],
        },
        {
            "cycle": EARLY,
            "race_count": len(races[EARLY]),
            "contribution_count": 3,
            "total_amount": 2250,
        },
    ]
    assert all(race["cycle"] == EARLY for race in races[EARLY])


def test_meta_names_each_cycles_live_build(client: TestClient) -> None:
    meta = ok(client.get("/v1/meta"))

    assert {cycle: entry["build_id"] for cycle, entry in meta["cycles"].items()} == {
        str(EARLY): BUILD,
        str(FIXTURE_CYCLE): BUILD,
    }
    assert "ccl" not in meta["cycles"][str(EARLY)]["source_dates"]


def test_the_musk_donor_page_shows_rows_from_both_cycles(
    two_cycles: Snapshot, client: TestClient
) -> None:
    [musk] = {
        donor_id
        for donor_id, *_ in silver_rows(
            two_cycles.data_dir,
            EARLY,
            BUILD,
            f"source_record_id IN ({', '.join(map(str, MUSK_1998))})",
        )
    }

    donor = ok(client.get(f"/v1/donors/{musk}"))
    rows = _all_pages(client, f"/v1/donors/{musk}/contributions")

    assert (donor["first_cycle"], donor["last_cycle"]) == (EARLY, FIXTURE_CYCLE)
    assert [cycle["cycle"] for cycle in donor["cycles"]] == [FIXTURE_CYCLE, EARLY]
    assert {row["cycle"] for row in rows} == {FIXTURE_CYCLE, EARLY}
    assert {row["source_record_id"] for row in rows if row["cycle"] == EARLY} == {
        str(sub_id) for sub_id in MUSK_1998
    }
    assert donor["total_all_cycles"] == sum(cycle["amount"] for cycle in donor["cycles"])


def test_a_committee_of_both_cycles_is_one_committee_named_as_its_newest_cycle_names_it(
    client: TestClient,
) -> None:
    committee = ok(client.get(f"/v1/committees/{BOTH_CYCLES_COMMITTEE}"))

    assert committee["name"] == "OLD LINE REPUBLICAN COMMITTEE"
    assert [cycle["cycle"] for cycle in committee["cycles"]] == [FIXTURE_CYCLE, EARLY]
    [early] = [cycle for cycle in committee["cycles"] if cycle["cycle"] == EARLY]
    assert early["total_individual"] == 500


def _copy_build(store: R2, cycle: int, source: str, target: str) -> None:
    """Every silver partition and the `transformed` marker of `source`, as build `target`: a new
    build of the cycle, as far as `load` and `publish` can tell, without transforming again."""
    for key in store.list_keys("silver/"):
        if paths.cycle_of(key) == cycle and paths.build_of(key) == source:
            new_key = key.replace(f"/build={source}/", f"/build={target}/")
            store.client.copy_object(
                Bucket=store.bucket, Key=new_key, CopySource={"Bucket": store.bucket, "Key": key}
            )
    marker = paths.marker(cycle, source, "transformed")
    store.put(paths.marker(cycle, target, "transformed"), store.get(marker))


def test_publishing_a_new_2024_build_leaves_1998_live(
    two_cycles: Snapshot, store: R2, cli_env: Path, migrated_db: str
) -> None:
    restore(two_cycles, store=store, data_dir=cli_env, conninfo=migrated_db)
    _copy_build(store, FIXTURE_CYCLE, BUILD, REBUILT)

    result = CliRunner().invoke(
        cli.app, ["load", "--cycle", str(FIXTURE_CYCLE), "--build-id", REBUILT]
    )
    assert result.exit_code == 0, result.output
    # gold_build holds 2024's load, so 1998's publish refuses it rather than swap it in.
    with pytest.raises(NothingToPublish):
        _publish(EARLY, store, cli_env)
    _publish(FIXTURE_CYCLE, store, cli_env)

    with psycopg.connect(migrated_db) as conn:
        row = conn.execute("SELECT cycles FROM gold.meta").fetchone()
    assert row is not None
    assert {cycle: entry["build_id"] for cycle, entry in row[0].items()} == {
        str(EARLY): BUILD,
        str(FIXTURE_CYCLE): REBUILT,
    }
    assert markers.read_live(store) == {EARLY: BUILD, FIXTURE_CYCLE: REBUILT}
    settings = get_settings().model_copy(update={"database_url": migrated_db})
    with TestClient(create_app(settings)) as client:
        page = ok(client.get(f"/v1/committees/{CALDER_COMMITTEE}/contributions?cycle={EARLY}"))
        assert [row["source_record_id"] for row in page["contributions"]] == [str(MUSK_1998[0])]
        assert [cycle["cycle"] for cycle in ok(client.get("/v1/cycles"))] == [FIXTURE_CYCLE, EARLY]


def test_a_load_with_no_manifest_keeps_every_cycle_live_gold_holds(
    two_cycles: Snapshot, store: R2, cli_env: Path, migrated_db: str
) -> None:
    """Gold published before `markers/live.json` existed: the live `gold.meta.cycles` stands in,
    and a cycle carried over keeps the download dates its live build was transformed from."""
    restore(two_cycles, store=store, data_dir=cli_env, conninfo=migrated_db)
    store.delete_keys([paths.LIVE_BUILDS])
    # A newer download of 2024, not yet transformed, is not what 2024's live build serves.
    newer = paths.bronze_zip(FIXTURE_CYCLE, "cm", date(2026, 11, 11))
    store.put(newer, b"")
    with psycopg.connect(migrated_db) as conn:
        [(live,)] = conn.execute("SELECT cycles FROM gold.meta").fetchall()

    result = CliRunner().invoke(cli.app, ["load", "--cycle", str(EARLY), "--build-id", BUILD])

    assert result.exit_code == 0, result.output
    with psycopg.connect(migrated_db) as conn:
        [(staged,)] = conn.execute("SELECT cycles FROM gold_build.meta").fetchall()
    assert staged == live
