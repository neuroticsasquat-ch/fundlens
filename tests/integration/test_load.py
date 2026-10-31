"""`fundlens load` on the fixture cycle: silver in MinIO to `gold_build` in a Postgres database
of its own (spec §5.5, NEU-2039 §4.1, §6)."""

import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any, get_args

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import dict_row
from typer.testing import CliRunner, Result

from fundlens import cli, markers
from fundlens.load.gold import GoldTable
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import ChecksFailed
from tests import fec_fixture
from tests.integration.conftest import REPO_ROOT
from tests.integration.test_transform import BUILD, put_bronze, seats_report, transform

NEWER = "20261031T030000Z"
GOLD_TABLES: tuple[GoldTable, ...] = get_args(GoldTable)


def run(*args: str, build_id: str | None = BUILD) -> Result:
    extra = [] if build_id is None else ["--build-id", build_id]
    return CliRunner().invoke(cli.app, [*args, *extra])


def load(build_id: str | None = BUILD) -> Result:
    return run("load", "--cycle", "2024", build_id=build_id)


def rows(conninfo: str, table: str, schema: str = "gold_build") -> list[dict[str, Any]]:
    with psycopg.connect(conninfo) as conn:
        return (
            conn.cursor(row_factory=dict_row)
            .execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(schema, table)))
            .fetchall()
        )


def schema_exists(conninfo: str, schema: str) -> bool:
    with psycopg.connect(conninfo) as conn:
        row = conn.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,)).fetchone()
    return row is not None


def dollars(value: Decimal) -> int:
    return int(value)


def test_load_builds_every_gold_table_to_the_expected_totals(
    store: R2, cli_env: Path, migrated_db: str
) -> None:
    put_bronze(store)
    seats_report()
    assert transform().exit_code == 0

    result = load()

    assert result.exit_code == 0, result.output
    expected = fec_fixture.expected()

    races = {row["race_id"]: row for row in rows(migrated_db, "race")}
    assert set(races) >= set(expected["races"])
    for race_id, totals in expected["races"].items():
        race = races[race_id]
        assert race["candidate_count"] == totals["candidate_count"], race_id
        assert dollars(race["total_individual"]) == totals["total_individual"], race_id
        assert dollars(race["total_committee"]) == totals["total_committee"], race_id
        # Independent expenditures arrive with NEU-2057.
        assert (race["ie_support"], race["ie_oppose"]) == (0, 0), race_id
    assert races["2024-S-MD-00"]["slug"] == "2024/senate/MD"
    assert races["2024-S-NE-00-special"]["is_special"] is True

    race_candidates = {row["candidate_id"]: row for row in rows(migrated_db, "race_candidate")}
    candidate_cycles = {row["candidate_id"]: row for row in rows(migrated_db, "candidate_cycle")}
    assert set(candidate_cycles) == set(expected["candidates"])
    assert set(race_candidates) == {
        candidate_id
        for candidate_id, totals in expected["candidates"].items()
        if totals["race_id"] is not None
    }
    for candidate_id, totals in expected["candidates"].items():
        cycle_row = candidate_cycles[candidate_id]
        assert cycle_row["race_id"] == totals["race_id"], candidate_id
        assert dollars(cycle_row["total_individual"]) == totals["total_individual"], candidate_id
        assert dollars(cycle_row["total_committee"]) == totals["total_committee"], candidate_id
        assert dollars(cycle_row["self_funding"]) == totals["self_funding"], candidate_id
        assert (cycle_row["ie_support"], cycle_row["ie_oppose"]) == (0, 0)
        assert cycle_row["contributor_count"] is None
        if totals["race_id"] is not None:
            race_row = race_candidates[candidate_id]
            assert race_row["race_id"] == totals["race_id"]
            assert (race_row["total_individual"], race_row["self_funding"]) == (
                cycle_row["total_individual"],
                cycle_row["self_funding"],
            )
    okafor = race_candidates["S4MD00103"]
    assert (okafor["name"], okafor["party"], okafor["principal_committee_id"]) == (
        "OKAFOR, DIANA",
        "DEM",
        "C00800103",
    )

    committee_cycles = {row["committee_id"]: row for row in rows(migrated_db, "committee_cycle")}
    assert set(committee_cycles) == set(expected["committees"])
    for committee_id, totals in expected["committees"].items():
        row = committee_cycles[committee_id]
        assert dollars(row["total_individual"]) == totals["total_individual"], committee_id
        assert dollars(row["self_funding"]) == totals["self_funding"], committee_id
        assert dollars(row["total_from_committees"]) == totals["total_from_committees"]
        assert dollars(row["total_to_candidates"]) == totals["total_to_candidates"]
        assert row["ie_total"] == 0

    [cycle] = rows(migrated_db, "cycle")
    assert cycle["cycle"] == 2024
    assert cycle["race_count"] == len(races)
    assert cycle["contribution_count"] == expected["silver"]["contribution"]
    assert dollars(cycle["total_amount"]) == expected["contributions"]["total_amount"]

    candidates = {row["candidate_id"]: row for row in rows(migrated_db, "candidate")}
    assert set(candidates) == set(expected["candidates"])
    assert candidates["H4MD09109"]["cycles"] == [2024]
    committees = {row["committee_id"]: row for row in rows(migrated_db, "committee")}
    assert committees["C00401224"]["is_conduit"] is True
    assert committees["C00401224"]["cycles"] == [2024]

    # BRICKLAYERS' gifts, ranked by amount and then by candidate id, add up to its
    # total_to_candidates (its gift to the super PAC is credited to no candidate, so is in neither,
    # NEU-2075).
    recipients = sorted(
        (
            row
            for row in rows(migrated_db, "committee_top_recipient")
            if row["committee_id"] == "C00800202"
        ),
        key=lambda row: row["rank"],
    )
    assert [row["rank"] for row in recipients] == list(range(1, len(recipients) + 1))
    assert (
        sum(dollars(row["amount"]) for row in recipients)
        == expected["committees"]["C00800202"]["total_to_candidates"]
    )
    assert [(row["amount"], row["recipient_id"]) for row in recipients] == sorted(
        ((row["amount"], row["recipient_id"]) for row in recipients),
        key=lambda pair: (-pair[0], pair[1]),
    )
    assert {row["recipient_kind"] for row in recipients} == {"candidate"}
    assert all(row["name"] for row in recipients)
    senate = sorted(
        (
            row
            for row in rows(migrated_db, "race_top_committee")
            if row["race_id"] == "2024-S-MD-00"
        ),
        key=lambda row: row["rank"],
    )
    assert (
        sum(dollars(row["amount"]) for row in senate)
        == expected["races"]["2024-S-MD-00"]["total_committee"]
    )
    assert [row["rank"] for row in senate] == list(range(1, len(senate) + 1))
    assert {row["kind"] for row in senate} == {"contribution"}

    search = {(row["kind"], row["id"]): row for row in rows(migrated_db, "search_entity")}
    assert search[("race", "2024-S-MD-00")]["name"] == "2024 Senate MD"
    assert search[("race", "2024-S-MD-00")]["aliases"] == "2024/senate/MD"
    assert search[("race", "2024-H-MD-05")]["name"] == "2024 House MD-05"
    assert search[("race", "2024-P-US-00")]["name"] == "2024 President"
    assert search[("race", "2024-S-NE-00-special")]["name"] == "2024 Senate NE special"
    assert search[("candidate", "S4MD00103")]["aliases"] == "OKAFOR FOR MARYLAND"
    assert dollars(search[("candidate", "S4MD00103")]["weight"]) == 49700 + 5000
    assert dollars(search[("committee", "C00800103")]["weight"]) == 37550 + 25000
    assert {kind for kind, _ in search} == {"candidate", "committee", "race"}

    [meta] = rows(migrated_db, "meta")
    assert meta["build_id"] == BUILD
    assert meta["published_at"] is None
    assert (meta["resolver_version"], meta["model_version"]) == (None, None)
    assert meta["cycles"] == {
        "2024": {
            "build_id": BUILD,
            "source_dates": dict.fromkeys(
                ("cm", "cn", "ccl", "indiv", "pas2", "oth"), "2026-10-30"
            ),
        }
    }

    marker = markers.read("loaded", store, cycle=2024, build_id=BUILD)
    assert marker is not None
    assert marker.row_counts == {table: len(rows(migrated_db, table)) for table in GOLD_TABLES}
    assert (marker.row_counts["meta"], marker.row_counts["cycle"]) == (1, 1)
    for table, count in marker.row_counts.items():
        assert f"{table}: {count} rows" in result.output
    assert f"loaded build {BUILD}" in result.output

    with psycopg.connect(migrated_db) as conn:
        indexes = conn.execute(
            "SELECT indexdef FROM pg_indexes WHERE schemaname = 'gold_build'"
        ).fetchall()
        extension_schema = conn.execute(
            "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace"
            " WHERE e.extname = 'pg_trgm'"
        ).fetchone()
    assert any("USING gin (name gin_trgm_ops)" in definition for (definition,) in indexes)
    assert any("UNIQUE INDEX race_slug" in definition for (definition,) in indexes)
    assert extension_schema == ("public",)
    # The work directory is gone; the silver partitions it read stay cached.
    assert not (cli_env / "scratch" / f"load-2024-{BUILD}").exists()
    assert (cli_env / "silver" / "contribution").exists()


def test_load_without_a_build_id_takes_the_newest_transformed_build(
    store: R2, cli_env: Path, migrated_db: str
) -> None:
    put_bronze(store)
    seats_report()
    assert transform().exit_code == 0
    assert run("seats", "--cycle", "2024", build_id=NEWER).exit_code == 0
    assert run("transform", "--cycle", "2024", build_id=NEWER).exit_code == 0

    result = load(build_id=None)

    assert result.exit_code == 0, result.output
    [meta] = rows(migrated_db, "meta")
    assert meta["build_id"] == NEWER
    assert markers.exists("loaded", store, cycle=2024, build_id=NEWER)
    assert not markers.exists("loaded", store, cycle=2024, build_id=BUILD)


def test_load_with_nothing_transformed_says_to_transform(store: R2, cli_env: Path) -> None:
    result = load(build_id=None)

    assert result.exit_code == 1
    assert "fundlens transform --cycle 2024" in result.output

    named = load()

    assert named.exit_code == 1
    assert f"fundlens transform --cycle 2024 --build-id {BUILD}" in named.output


def test_load_with_the_race_partition_under_another_build_says_to_run_seats(
    store: R2, cli_env: Path, migrated_db: str
) -> None:
    put_bronze(store)
    # The seat calendar for another build; the unmatched filing it records is per cycle, so
    # transform's race check still passes.
    assert run("seats", "--cycle", "2024", "--report", build_id=NEWER).exit_code == 0
    assert transform().exit_code == 0

    result = load()

    assert result.exit_code == 1
    assert "silver race" in result.output
    assert f"fundlens seats --cycle 2024 --build-id {BUILD}" in result.output
    assert not schema_exists(migrated_db, "gold_build")
    assert not markers.exists("loaded", store, cycle=2024, build_id=BUILD)


def test_a_failing_gold_check_leaves_no_gold_build_and_no_marker(
    store: R2, cli_env: Path, migrated_db: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    put_bronze(store)
    seats_report()
    assert transform().exit_code == 0
    sql_dir = tmp_path / "sql"
    shutil.copytree(REPO_ROOT / "sql", sql_dir)
    (sql_dir / "checks" / "gold_always_fails.sql").write_text("SELECT 'boom' AS what;\n")
    monkeypatch.setenv("SQL_DIR", str(sql_dir))
    get_settings.cache_clear()

    result = load()

    assert isinstance(result.exception, ChecksFailed)
    assert "gold_always_fails.sql" in str(result.exception)
    assert "nothing loaded" in str(result.exception)
    assert not schema_exists(migrated_db, "gold_build")
    assert not markers.exists("loaded", store, cycle=2024, build_id=BUILD)


def test_load_twice_for_the_same_build_rebuilds_gold_build(
    store: R2, cli_env: Path, migrated_db: str
) -> None:
    put_bronze(store)
    seats_report()
    assert transform().exit_code == 0

    assert load().exit_code == 0
    result = load()

    assert result.exit_code == 0, result.output
    assert [row["build_id"] for row in rows(migrated_db, "meta")] == [BUILD]
    assert len(rows(migrated_db, "cycle")) == 1


def test_an_odd_cycle_is_a_usage_error(cli_env: Path) -> None:
    assert run("load", "--cycle", "2025").exit_code == 2
