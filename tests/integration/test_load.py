"""`fundlens load` on the fixture cycle: silver in MinIO to `gold_build` in a Postgres database
of its own (spec §5.5, NEU-2039 §4.1, §6)."""

import shutil
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, get_args

import duckdb
import psycopg
import pytest
from psycopg import sql
from psycopg.rows import dict_row
from typer.testing import CliRunner, Result

from fundlens import cli, markers, paths
from fundlens.load.gold import GoldTable
from fundlens.paths import SilverTable
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import ChecksFailed
from tests import fec_fixture
from tests.integration.conftest import REPO_ROOT
from tests.integration.test_resolve import BEYOND_LINKAGE
from tests.integration.test_transform import (
    BUILD,
    failing_rows,
    put_bronze,
    transform,
)

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
    store: R2, transformed: Path, migrated_db: str
) -> None:

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
        assert dollars(race["total_jfc_transfers"]) == totals["total_jfc_transfers"], race_id
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
        assert dollars(cycle_row["total_jfc_transfers"]) == totals["total_jfc_transfers"], (
            candidate_id
        )
        assert dollars(cycle_row["self_funding"]) == totals["self_funding"], candidate_id
        assert (cycle_row["ie_support"], cycle_row["ie_oppose"]) == (0, 0)
        assert cycle_row["contributor_count"] is None
        if totals["race_id"] is not None:
            race_row = race_candidates[candidate_id]
            assert race_row["race_id"] == totals["race_id"]
            assert (
                race_row["total_individual"],
                race_row["total_jfc_transfers"],
                race_row["self_funding"],
            ) == (
                cycle_row["total_individual"],
                cycle_row["total_jfc_transfers"],
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
    organizations = expected["organization_receipts"]
    non_contribution = expected["non_contribution_account"]
    for committee_id, totals in expected["committees"].items():
        row = committee_cycles[committee_id]
        assert dollars(row["total_individual"]) == totals["total_individual"], committee_id
        assert dollars(row["self_funding"]) == totals["self_funding"], committee_id
        assert dollars(row["total_from_committees"]) == totals["total_from_committees"]
        assert dollars(row["total_to_candidates"]) == totals["total_to_candidates"]
        assert dollars(row["total_returned_by_candidates"]) == expected["returned_by_candidates"][
            "by_committee"
        ].get(committee_id, 0), committee_id
        # Organization money (ADR-0011): the super PAC's is CHESAPEAKE STEEL's gifts less its
        # refund, the party committee's BALTIMORE HARBOR PILOTS' 15; 0, never NULL, for the rest.
        # The hybrid PAC's non-contribution account is in neither this nor total_individual, but in
        # its own figure (NEU-2192), and the party accounts' gifts are in total_other_lines
        # (NEU-2205).
        assert dollars(row["total_from_organizations"]) == organizations["by_committee"].get(
            committee_id, 0
        ) - non_contribution["organizations_by_committee"].get(committee_id, 0) - expected[
            "other_lines"
        ]["organizations_by_committee"].get(committee_id, 0), committee_id
        assert dollars(row["total_non_contribution_account"]) == non_contribution[
            "by_committee"
        ].get(committee_id, 0), committee_id
        # Money on a line no total_individual counts is in its own figure, individuals' and
        # organizations' alike (NEU-2193, NEU-2205).
        assert dollars(row["total_other_lines"]) == expected["other_lines"]["by_committee"].get(
            committee_id, 0
        ), committee_id
        # The refunds counted in those two totals, which stay net of them (NEU-2265): not the
        # non-contribution account's 20Y nor a party account's 41Y.
        assert dollars(row["total_refunds"]) == expected["refunds"]["by_committee"].get(
            committee_id, 0
        ), committee_id
        assert row["ie_total"] == 0

    # Each committee's organizations by rank, CHESAPEAKE STEEL once under its most-money spelling.
    top_organizations: dict[str, list[list[str | int]]] = defaultdict(list)
    for row in sorted(
        rows(migrated_db, "committee_top_organization"),
        key=lambda row: (row["committee_id"], row["rank"]),
    ):
        assert row["cycle"] == 2024
        top_organizations[row["committee_id"]].append(
            [row["organization_key"], row["name"], dollars(row["amount"])]
        )
    assert top_organizations == organizations["top_by_committee"]

    [cycle] = rows(migrated_db, "cycle")
    assert cycle["cycle"] == 2024
    assert cycle["race_count"] == len(races)
    assert cycle["contribution_count"] == expected["silver"]["contribution"]
    assert dollars(cycle["total_amount"]) == expected["contributions"]["total_amount"]

    candidates = {row["candidate_id"]: row for row in rows(migrated_db, "candidate")}
    assert set(candidates) == set(expected["candidates"])
    assert candidates["H4MD09109"]["cycles"] == [2024]
    # A candidate alias is in no table above but this one (NEU-2127).
    redirects = rows(migrated_db, "candidate_redirect")
    assert {row["old_candidate_id"]: row["candidate_id"] for row in redirects} == expected[
        "aliases"
    ]
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
    # A same-cycle refund nets inside its gift: BRICKLAYERS' to YANG, $2,500 less $500 (NEU-2204).
    assert {row["recipient_id"]: dollars(row["amount"]) for row in recipients}["H4MD05108"] == 2000

    # A void of an earlier cycle's gift, the giver's only 24K to the candidate this cycle, is a
    # return, not a gift: OLD LINE REPUBLICAN COMMITTEE's of a 2022 gift to CALLOWAY is in neither
    # its total_to_candidates nor its top recipients, nor in CALLOWAY's total_committee.
    old_line = committee_cycles["C00800203"]
    assert dollars(old_line["total_returned_by_candidates"]) == -1000
    assert dollars(old_line["total_to_candidates"]) == 6000
    assert "H4MD05106" not in {
        row["recipient_id"]
        for row in rows(migrated_db, "committee_top_recipient")
        if row["committee_id"] == "C00800203"
    }
    assert dollars(candidate_cycles["H4MD05106"]["total_committee"]) == 10000
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
    assert dollars(search[("candidate", "S4MD00103")]["weight"]) == 50700 + 5000
    assert dollars(search[("committee", "C00800103")]["weight"]) == 38550 + 45500
    assert {kind for kind, _ in search} == {"candidate", "committee", "race"}

    [meta] = rows(migrated_db, "meta")
    assert meta["build_id"] == BUILD
    assert meta["published_at"] is None
    # No resolve has saved a model, so there is no live one and no run record.
    columns = ("resolver_version", "model_version", "overrides_count", "adjudications_applied")
    assert [meta[column] for column in columns] == [None] * len(columns)
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
    assert not (transformed / "scratch" / f"load-2024-{BUILD}").exists()
    assert (transformed / "silver" / "contribution").exists()


def test_a_jfc_attribution_adds_nothing_to_its_participants_or_its_races_totals(
    store: R2, transformed: Path, migrated_db: str
) -> None:
    # Evidence, never money (spec §6.11): the participant's share is the JFC's transfer.
    def totals() -> list[dict[str, Any]]:
        return [
            next(r for r in rows(migrated_db, table) if r[column] == value)
            for table, column, value in (
                ("committee_cycle", "committee_id", "C00800103"),
                ("candidate_cycle", "candidate_id", "S4MD00103"),
                ("race", "race_id", "2024-S-MD-00"),
                ("cycle", "cycle", 2024),
            )
        ]

    assert load().exit_code == 0
    before = totals()
    oth = fec_fixture.bulk_text("oth") + (
        "C00800103|N|12G|G2024|1|15J|IND|HARTWELL, EUGENIA|BALTIMORE|MD|21210|RETIRED|RETIRED|"
        "10202024|1000000||SA.1|1900123|X|* OKAFOR VICTORY FUND|4249999999999999961\n"
    )
    put_bronze(store, texts={"oth": oth})
    assert run("seats", "--cycle", "2024", build_id=NEWER).exit_code == 0
    newer = run("transform", "--cycle", "2024", build_id=NEWER)
    assert newer.exit_code == 0, newer.output
    attributions = fec_fixture.expected()["silver"]["jfc_attribution"] + 1
    assert f"jfc_attribution: {attributions} rows" in newer.output

    result = load(NEWER)

    assert result.exit_code == 0, result.output
    assert totals() == before


def silver(data_dir: Path, table: SilverTable, columns: str) -> list[dict[str, Any]]:
    """`columns` of every row of the build's silver `table`, from its local partition."""
    part = paths.local_path(data_dir, paths.silver_partition(table, 2024, BUILD))
    with duckdb.connect() as con:
        cursor = con.execute(
            f"SELECT {columns} FROM read_parquet(?, hive_partitioning = false)",
            [str(part / "**" / "*.parquet")],
        )
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def test_load_of_a_resolved_build_builds_the_donor_tables(
    store: R2, resolved: Path, migrated_db: str
) -> None:
    # A redirect the crosswalk wrote earlier: gold serves app's, whichever ids it names.
    with psycopg.connect(migrated_db) as conn:
        conn.execute("INSERT INTO app.donor_redirect (old_donor_id, donor_id) VALUES (9001, 1)")

    result = load()

    assert result.exit_code == 0, result.output
    expected = fec_fixture.expected()
    lines = silver(
        resolved,
        "contribution",
        "source_record_id, contributor_key, donor_id, candidate_id, amount, is_self_funding",
    )
    attributions = silver(resolved, "jfc_attribution", "source_record_id, donor_id")
    donor_of = {line["source_record_id"]: line["donor_id"] for line in lines + attributions}

    def donor(name: str) -> int:
        [donor_id] = {donor_of[sub_id] for sub_id in expected["donors"][name]["sub_ids"]}
        return donor_id

    donors = {row["donor_id"]: row for row in rows(migrated_db, "donor")}
    donor_cycles = {row["donor_id"]: row for row in rows(migrated_db, "donor_cycle")}
    # One donor per donor_id among the contributions and the attributions.
    assert set(donors) == set(donor_cycles) == set(donor_of.values())
    # Each planted donor linkage resolves (the overrides' and adjudication's cases need the
    # fixture's overrides and verdicts) is one donor with all of their money, their own included.
    for name, planted in expected["donors"].items():
        if planted["resolved_by"] in BEYOND_LINKAGE:
            continue
        donor_id = donor(name)
        assert dollars(donors[donor_id]["total_all_cycles"]) == planted["amount"], name
        assert dollars(donor_cycles[donor_id]["amount"]) == planted["amount"], name
        assert donor_cycles[donor_id]["contribution_count"] == len(planted["sub_ids"]), name

    # MARLOWE (the fixture's Musk) gave under five spellings; the one with the most money, $10,000
    # against $3,300 each, is his display name. The others are what search also matches.
    musk = donor("musk_case")
    assert donors[musk]["display_name"] == "MARLOWE, AUGUSTINE MR."
    assert (donors[musk]["first_cycle"], donors[musk]["last_cycle"]) == (2024, 2024)
    assert donors[musk]["contributor_key_count"] == len(
        {line["contributor_key"] for line in lines if line["donor_id"] == musk}
    )

    senate = "2024-S-MD-00"
    senators = {
        row["candidate_id"]
        for row in rows(migrated_db, "race_candidate")
        if row["race_id"] == senate
    }
    top = [row for row in rows(migrated_db, "race_top_donor") if row["race_id"] == senate]
    [musk_row] = [row for row in top if row["donor_id"] == musk]
    musk_lines = [
        line for line in lines if line["donor_id"] == musk and line["candidate_id"] in senators
    ]
    assert musk_lines
    assert musk_row["amount"] == sum(line["amount"] for line in musk_lines)
    assert musk_row["display_name"] == "MARLOWE, AUGUSTINE MR."
    # His one gift to the race, to WHITLOCK.
    assert musk_row["candidates"] == [{"candidate_id": "S4MD00104", "amount": 3300}]
    # Whitlock's own money is self-funding, never a top donor; nor is Okafor's to her own campaign.
    whitlock, okafor = donor("self_funder"), donor("candidate_as_donor")
    assert whitlock not in {row["donor_id"] for row in top}
    assert okafor not in {row["donor_id"] for row in top}
    for table, column, value in (
        ("candidate_top_donor", "candidate_id", "S4MD00104"),
        ("committee_top_donor", "committee_id", "C00800104"),
    ):
        listed = {row["donor_id"] for row in rows(migrated_db, table) if row[column] == value}
        assert listed, table
        assert whitlock not in listed, table
    # The ranks follow the money.
    assert [row["amount"] for row in sorted(top, key=lambda row: row["rank"])] == sorted(
        (row["amount"] for row in top), reverse=True
    )

    # Every recipient of MARLOWE's: candidates through their committees, else the committee.
    recipients = [
        row for row in rows(migrated_db, "donor_top_recipient") if row["donor_id"] == musk
    ]
    assert sum(row["amount"] for row in recipients) == donors[musk]["total_all_cycles"]
    assert {row["recipient_kind"] for row in recipients} == {"candidate", "committee"}
    assert all(row["name"] for row in recipients)

    # A donor known only from a JFC attribution has no money and is on no list, but is found.
    [only] = expected["attributions"]["attribution_only"]
    achterberg = donor_of[only]
    assert donors[achterberg]["display_name"] == "ACHTERBERG, LIESBETH"
    assert (donors[achterberg]["total_all_cycles"], donor_cycles[achterberg]["amount"]) == (0, 0)
    assert donor_cycles[achterberg]["contribution_count"] == 0
    for table in ("race_top_donor", "candidate_top_donor", "committee_top_donor"):
        assert achterberg not in {row["donor_id"] for row in rows(migrated_db, table)}, table

    with psycopg.connect(migrated_db) as conn:
        found = conn.execute(
            "SELECT id, aliases, weight FROM gold_build.search_entity"
            " WHERE kind = 'donor' AND name % 'marlowe'"
        ).fetchall()
        attributed = conn.execute(
            "SELECT weight FROM gold_build.search_entity WHERE kind = 'donor' AND id = %s",
            (str(achterberg),),
        ).fetchone()
    [(musk_id, aliases, weight)] = found
    assert musk_id == str(musk)
    assert dollars(weight) == expected["donors"]["musk_case"]["amount"]
    assert "MARLOWE, AUGUSTINE REEVE" in aliases
    assert "MARLOWE, AUGUSTINE MR." not in aliases
    assert attributed == (0,)

    # contributor_count counts the candidate's donors, the candidate's own money aside.
    okafor_cycle = next(
        r for r in rows(migrated_db, "candidate_cycle") if r["candidate_id"] == "S4MD00103"
    )
    assert okafor_cycle["contributor_count"] == len(
        {
            line["donor_id"]
            for line in lines
            if line["candidate_id"] == "S4MD00103" and not line["is_self_funding"]
        }
    )
    assert rows(migrated_db, "donor_redirect") == [{"old_donor_id": 9001, "donor_id": 1}]
    marker = markers.read("loaded", store, cycle=2024, build_id=BUILD)
    assert marker is not None
    assert marker.row_counts == {table: len(rows(migrated_db, table)) for table in GOLD_TABLES}


def test_load_without_a_build_id_takes_the_newest_transformed_build(
    store: R2, transformed: Path, migrated_db: str
) -> None:
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
    store: R2, transformed: Path, migrated_db: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_a_top_donor_list_counting_own_money_fails_its_check(
    store: R2, resolved: Path, migrated_db: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sql_dir = tmp_path / "sql"
    shutil.copytree(REPO_ROOT / "sql", sql_dir)
    model = sql_dir / "gold" / "14_candidate_top_donor.sql"
    filtered = "AND NOT is_self_funding "
    assert filtered in model.read_text()
    model.write_text(model.read_text().replace(filtered, ""))
    monkeypatch.setenv("SQL_DIR", str(sql_dir))
    get_settings.cache_clear()

    result = load()

    # WHITLOCK's own money makes him his campaign's top donor.
    assert isinstance(result.exception, ChecksFailed)
    assert "gold_top_donor_not_self_funding.sql" in str(result.exception)
    assert not schema_exists(migrated_db, "gold_build")


def test_the_top_organization_amount_check_fails_on_a_row_silver_does_not_add_up_to() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA silver")
        con.execute(
            "CREATE TABLE silver.organization_receipt AS SELECT * FROM (VALUES"
            " ('C1', 'ACME', 'ACME INC', 500), ('C1', 'ACME', 'ACME, INC.', 250),"
            " ('C1', 'BOLT', 'BOLT LLC', 100), ('C2', 'ACME', 'ACME INC', 75)"
            ") AS t(recipient_committee_id, organization_key, organization_name, amount)"
        )
        con.execute(
            "CREATE TABLE committee_top_organization AS SELECT * FROM (VALUES"
            " ('C1', 1, 'ACME', 'ACME INC', 750), ('C1', 2, 'BOLT', 'BOLT LLC', 90),"
            " ('C2', 1, 'ACME', 'ACME CORP', 75), ('C3', 1, 'ACME', 'ACME INC', 10)"
            ") AS t(committee_id, rank, organization_key, name, amount)"
        )

        # BOLT's amount is not its net receipts, ACME CORP is no spelling ACME reported, and C3
        # received nothing from ACME.
        assert sorted(failing_rows(con, "gold_committee_top_organization_amount.sql")) == [
            ("C1", "BOLT", "BOLT LLC", 90, 100),
            ("C2", "ACME", "ACME CORP", 75, 75),
            ("C3", "ACME", "ACME INC", 10, None),
        ]


def test_the_given_check_fails_on_a_negative_gift_figure() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE committee_cycle AS SELECT * FROM (VALUES"
            " ('C1', 500, -1000), ('C2', -2000, 0), ('C3', 0, 250)"
            ") AS t(committee_id, total_to_candidates, total_returned_by_candidates)"
        )
        con.execute(
            "CREATE TABLE committee_top_recipient AS SELECT * FROM (VALUES"
            " ('C1', 'H1', 500), ('C2', 'H2', -1000)"
            ") AS t(committee_id, recipient_id, amount)"
        )
        con.execute(
            "CREATE TABLE candidate_cycle AS SELECT * FROM (VALUES ('H1', 500), ('H2', -1000))"
            " AS t(candidate_id, total_committee)"
        )
        con.execute(
            "CREATE TABLE race_top_committee AS SELECT * FROM (VALUES"
            " ('2024-H-MD-05', 'C1', 500), ('2024-H-MD-05', 'C2', -1000)"
            ") AS t(race_id, committee_id, amount)"
        )

        # C1's return of an earlier cycle's gift is where it belongs (NEU-2204); C2's is netted
        # into its gifts, and C3's return is positive.
        assert sorted(failing_rows(con, "gold_given_not_negative.sql")) == [
            ("candidate_cycle.total_committee", "H2", -1000),
            ("committee_cycle.total_returned_by_candidates", "C3", 250),
            ("committee_cycle.total_to_candidates", "C2", -2000),
            ("committee_top_recipient.amount", "C2 H2", -1000),
            ("race_top_committee.amount", "2024-H-MD-05 C2", -1000),
        ]


def test_the_refunds_check_fails_on_a_positive_refunds_figure() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE committee_cycle AS SELECT * FROM (VALUES"
            " ('C1', -500.00), ('C2', 0.00), ('C3', 0.01)"
            ") AS t(committee_id, total_refunds)"
        )

        # C3's refunds add to its totals rather than subtracting.
        assert failing_rows(con, "gold_committee_cycle_refunds.sql") == [("C3", Decimal("0.01"))]


def test_the_conduit_floor_check_fails_on_a_conduit_below_minus_1m() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE committee AS SELECT * FROM (VALUES"
            " ('A1', true), ('A2', true), ('A3', true), ('C1', false)"
            ") AS t(committee_id, is_conduit)"
        )
        con.execute(
            "CREATE TABLE committee_cycle AS SELECT * FROM (VALUES"
            " ('A1', 500.00), ('A2', -1000000.00), ('A3', -1000000.01), ('C1', -2300000.00)"
            ") AS t(committee_id, total_individual)"
        )

        # A2 is at the floor and A3 past it; C1, a retiring candidate's campaign refunding
        # earlier cycles' gifts, is no conduit.
        assert failing_rows(con, "gold_conduit_individual_floor.sql") == [
            ("A3", Decimal("-1000000.01"))
        ]


def test_load_twice_for_the_same_build_rebuilds_gold_build(
    store: R2, transformed: Path, migrated_db: str
) -> None:

    assert load().exit_code == 0
    result = load()

    assert result.exit_code == 0, result.output
    assert [row["build_id"] for row in rows(migrated_db, "meta")] == [BUILD]
    assert len(rows(migrated_db, "cycle")) == 1


def test_an_odd_cycle_is_a_usage_error(cli_env: Path) -> None:
    assert run("load", "--cycle", "2025").exit_code == 2
