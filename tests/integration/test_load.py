"""`fundlens load` on the fixture cycle: silver in MinIO to `gold_build` in a Postgres database
of its own (spec §5.5, NEU-2039 §4.1, §6)."""

import hashlib
import shutil
from collections import defaultdict
from datetime import date
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
from fundlens.fec.files import FecFile
from fundlens.load import gold
from fundlens.load.gold import GoldTable
from fundlens.paths import SilverTable
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import ChecksFailed, render
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


def whole(value: Decimal | None) -> int | None:
    """A nullable dollar figure, as `expected.yaml` lists it."""
    return None if value is None else int(value)


def ratio(value: float | None) -> float | None:
    """A ratio to four places, as `expected.yaml` lists it."""
    return None if value is None else round(value, 4)


def ranked(lists: dict[str, list[list[str | int]]]) -> dict[str, list[tuple[str | int, ...]]]:
    """expected.yaml's ranked lists, each row a tuple as the test builds gold's."""
    return {key: [tuple(row) for row in rows] for key, rows in lists.items()}


def page(key: str) -> str:
    """A payee key's payee_id: the first 16 hexadecimal characters of its SHA-256 (spec §5.4)."""
    return hashlib.sha256(key.encode()).hexdigest()[:16]


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
        # Independent expenditures for and against its candidates, by anyone (NEU-2057).
        assert dollars(race["ie_support"]) == totals["ie_support"], race_id
        assert dollars(race["ie_oppose"]) == totals["ie_oppose"], race_id
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
        assert dollars(cycle_row["ie_support"]) == totals["ie_support"], candidate_id
        assert dollars(cycle_row["ie_oppose"]) == totals["ie_oppose"], candidate_id
        assert cycle_row["contributor_count"] is None
        if totals["race_id"] is not None:
            race_row = race_candidates[candidate_id]
            assert race_row["race_id"] == totals["race_id"]
            assert (
                race_row["total_individual"],
                race_row["total_jfc_transfers"],
                race_row["self_funding"],
                race_row["ie_support"],
                race_row["ie_oppose"],
            ) == (
                cycle_row["total_individual"],
                cycle_row["total_jfc_transfers"],
                cycle_row["self_funding"],
                cycle_row["ie_support"],
                cycle_row["ie_oppose"],
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
        # Its independent expenditures for and against candidates; not the party's 24C.
        assert dollars(row["ie_total"]) == totals["ie_total"], committee_id

    # FEC's reported figures beside fundlens's itemized one (every-FEC-dollar spec §4.4): coverage 1
    # where the two agree, above 1 where fundlens counts more, NULL at a conduit or a reported 0.
    reported = expected["gold_reported"]
    assert {
        committee_id: [
            dollars(row["itemized_total"]),
            whole(row["reported_individual_itemized"]),
            whole(row["reported_cash_on_hand_end"]),
            ratio(row["coverage"]),
        ]
        for committee_id, row in committee_cycles.items()
    } == reported["committees"]
    whitlock_committee = committee_cycles["C00800104"]
    assert (
        whitlock_committee["reported_source_file"],
        whitlock_committee["reported_period_start"],
        whitlock_committee["reported_period_end"],
        whole(whitlock_committee["reported_candidate_loans"]),
    ) == ("committee_summary", date(2023, 1, 1), date(2024, 12, 31), 1500000)
    # A candidate's are its credited committees' added up: OKAFOR's two, HARRIS's handed-off
    # committee whole and BIDEN none, STRATTON's campaign turned leadership PAC (§4.3).
    assert {
        candidate_id: [
            whole(row["reported_receipts"]),
            whole(row["reported_cash_on_hand_end"]),
            whole(row["itemized_total"]),
            ratio(row["coverage"]),
            row["reported_includes_converted_committee"],
        ]
        for candidate_id, row in candidate_cycles.items()
    } == reported["candidates"]
    assert {
        candidate_id: row["reported_source_file"]
        for candidate_id, row in candidate_cycles.items()
        if row["reported_source_file"] is not None
    } == {
        candidate_id: "committee_summary"
        for candidate_id, figures in reported["candidates"].items()
        if figures[0] is not None
    }
    for candidate_id, row in race_candidates.items():
        figures = (
            "reported_receipts",
            "reported_disbursements",
            "reported_cash_on_hand_end",
            "reported_debts_owed_by",
            "coverage",
        )
        assert {f: row[f] for f in figures} == {
            f: candidate_cycles[candidate_id][f] for f in figures
        }, candidate_id
    assert {
        race_id: whole(races[race_id]["reported_cash_on_hand"]) for race_id in reported["races"]
    } == reported["races"]
    # FENWICK FOR CONGRESS, its itemized figure filed more than 1% under fundlens's; not YANG FOR
    # MARYLAND's, under by less (§4.5). HARRIS FOR PRESIDENT's counted spending over its reported
    # figure, and four committees' beside a reported 0 (§5.6).
    reconciled: dict[str, dict[str, list[Any]]] = defaultdict(dict)
    for row in rows(migrated_db, "reconciliation"):
        assert row["cycle"] == 2024
        reconciled[row["measure"]][row["committee_id"]] = [
            dollars(row["fundlens"]),
            dollars(row["reported"]),
            ratio(row["ratio"]),
        ]
    assert reconciled == reported["reconciliation"]
    # An unresolved build has no donors, so no itemized gift-size bucket: only FEC's unitemized
    # lump, where a candidate has one (BIDEN, whose committee is HARRIS's, has none).
    gift_sizes = rows(migrated_db, "candidate_gift_size")
    assert {row["bucket"] for row in gift_sizes} == {"unitemized"}
    assert {row["candidate_id"]: (dollars(row["amount"]), row["donors"]) for row in gift_sizes} == {
        candidate_id: (dollars(row["reported_individual_unitemized"]), None)
        for candidate_id, row in candidate_cycles.items()
        if row["reported_individual_unitemized"] is not None
    }
    assert "P80000722" not in {row["candidate_id"] for row in gift_sizes}

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

    # Spending (every-FEC-dollar spec §5.5): each committee's and candidate's counted operating
    # expenditures, NULL where it has none, never 0; a race's its candidates' added up. A card
    # bill counts once, at the parent. No receipt figure above moved for it.
    spending = expected["operating_expenditures"]
    assert {
        committee_id: f"{row['total_operating_expenditures']:.2f}"
        for committee_id, row in committee_cycles.items()
        if row["total_operating_expenditures"] is not None
    } == spending["by_committee"]
    assert {
        candidate_id: f"{row['total_operating_expenditures']:.2f}"
        for candidate_id, row in candidate_cycles.items()
        if row["total_operating_expenditures"] is not None
    } == spending["by_candidate"]
    for candidate_id, row in race_candidates.items():
        assert (
            row["total_operating_expenditures"]
            == candidate_cycles[candidate_id]["total_operating_expenditures"]
        ), candidate_id
    by_race: dict[str, list[Decimal]] = defaultdict(list)
    for row in race_candidates.values():
        if row["total_operating_expenditures"] is not None:
            by_race[row["race_id"]].append(row["total_operating_expenditures"])
    assert {
        race_id: race["total_operating_expenditures"]
        for race_id, race in races.items()
        if race["total_operating_expenditures"] is not None
    } == {race_id: sum(amounts, Decimal(0)) for race_id, amounts in by_race.items()}
    categories: dict[str, dict[str, str]] = defaultdict(dict)
    for row in rows(migrated_db, "committee_spending_category"):
        assert row["cycle"] == 2024
        categories[row["committee_id"]][row["category"]] = f"{row['amount']:.2f}"
    assert categories == spending["by_committee_category"]
    # Each committee's payees by rank, a person's key with no page (§5.4).
    top_payees: dict[str, list[list[str | bool]]] = defaultdict(list)
    for row in sorted(
        rows(migrated_db, "committee_top_payee"), key=lambda row: (row["committee_id"], row["rank"])
    ):
        assert row["cycle"] == 2024
        assert row["payee_id"] in (page(row["payee_key"]), None), row
        top_payees[row["committee_id"]].append(
            [row["payee_key"], row["name"], f"{row['amount']:.2f}", row["payee_id"] is not None]
        )
    assert top_payees == spending["top_payees"]
    # Every payee with a page (§5.4, §5.5): BLUE HARBOR STRATEGIES once, under its most-money
    # spelling, with both committees that paid it among its top payers.
    payee_cycles = {row["payee_id"]: row for row in rows(migrated_db, "payee_cycle")}
    payers: dict[str, list[list[str | None]]] = defaultdict(list)
    for row in sorted(
        rows(migrated_db, "payee_top_payer"), key=lambda row: (row["payee_id"], row["rank"])
    ):
        assert row["cycle"] == 2024
        payers[row["payee_id"]].append(
            [row["committee_id"], row["candidate_id"], f"{row['amount']:.2f}"]
        )
    payees: dict[str, dict[str, Any]] = {}
    for row in rows(migrated_db, "payee"):
        assert row["payee_id"] == page(row["payee_key"]), row
        assert (row["first_cycle"], row["last_cycle"]) == (2024, 2024), row
        cycle_row = payee_cycles.pop(row["payee_id"])
        assert (cycle_row["cycle"], cycle_row["total"]) == (2024, row["total_all_cycles"]), row
        payees[row["payee_key"]] = {
            "name": row["display_name"],
            "city": row["city"],
            "state": row["state"],
            "total": f"{row['total_all_cycles']:.2f}",
            "committees": cycle_row["committee_count"],
            "payers": payers.pop(row["payee_id"], []),
        }
    assert payees == spending["payees"]
    assert not payee_cycles and not payers

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

    # Every committee's recipients, candidates and committees ranked together by amount, then kind,
    # then id (NEU-2057). BRICKLAYERS' candidate rows add up to its total_to_candidates; its gift to
    # the super PAC is credited to no candidate (NEU-2075), a committee row. A gift to a candidate's
    # committee is its 24K and its recipient's 18K: in the candidate's row alone, never also the
    # committee's. A same-cycle refund nets inside its gift: BRICKLAYERS' to YANG, $2,500 less $500
    # (NEU-2204).
    recipients: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for row in sorted(
        rows(migrated_db, "committee_top_recipient"),
        key=lambda row: (row["committee_id"], row["rank"]),
    ):
        assert row["cycle"] == 2024
        assert row["name"], row
        assert row["rank"] == len(recipients[row["committee_id"]]) + 1
        recipients[row["committee_id"]].append(
            (row["recipient_kind"], row["recipient_id"], dollars(row["amount"]))
        )
    assert recipients == ranked(expected["top_recipients"])
    for committee_id, listed in recipients.items():
        assert (
            sum(amount for kind, _, amount in listed if kind == "candidate")
            == expected["committees"][committee_id]["total_to_candidates"]
        ), committee_id

    # A void of an earlier cycle's gift, the giver's only 24K to the candidate this cycle, is a
    # return, not a gift: OLD LINE REPUBLICAN COMMITTEE's of a 2022 gift to CALLOWAY is in neither
    # its total_to_candidates nor its top recipients, nor in CALLOWAY's total_committee.
    old_line = committee_cycles["C00800203"]
    assert dollars(old_line["total_returned_by_candidates"]) == -1000
    assert dollars(old_line["total_to_candidates"]) == 6000
    assert "H4MD05106" not in {recipient_id for _, recipient_id, _ in recipients["C00800203"]}
    assert dollars(candidate_cycles["H4MD05106"]["total_committee"]) == 10000

    # Each race's committees, givers and spenders ranked together (NEU-2057): the contribution rows
    # add up to its total_committee, the ie rows to its ie_support and ie_oppose. The super PAC is
    # there for its independent expenditures; a conduit (ActBlue, WinRed), whose 24Ks are no gifts,
    # is in no list.
    top_committees: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for row in sorted(
        rows(migrated_db, "race_top_committee"), key=lambda row: (row["race_id"], row["rank"])
    ):
        assert row["name"], row
        assert row["rank"] == len(top_committees[row["race_id"]]) + 1
        top_committees[row["race_id"]].append(
            (row["kind"], row["committee_id"], dollars(row["amount"]))
        )
    assert top_committees == ranked(expected["race_top_committees"])
    for race_id, listed in top_committees.items():
        totals = expected["races"][race_id]
        assert (
            sum(a for kind, _, a in listed if kind == "contribution") == totals["total_committee"]
        ), race_id
        assert sum(a for kind, _, a in listed if kind == "ie") == (
            totals["ie_support"] + totals["ie_oppose"]
        ), race_id
        assert not {committee_id for _, committee_id, _ in listed} & {"C00401224", "C00694323"}

    search = {(row["kind"], row["id"]): row for row in rows(migrated_db, "search_entity")}
    assert search[("race", "2024-S-MD-00")]["name"] == "2024 Senate MD"
    assert search[("race", "2024-S-MD-00")]["aliases"] == "2024/senate/MD"
    assert search[("race", "2024-H-MD-05")]["name"] == "2024 House MD-05"
    assert search[("race", "2024-P-US-00")]["name"] == "2024 President"
    assert search[("race", "2024-S-NE-00-special")]["name"] == "2024 Senate NE special"
    assert search[("candidate", "S4MD00103")]["aliases"] == "OKAFOR FOR MARYLAND"
    assert dollars(search[("candidate", "S4MD00103")]["weight"]) == 50700 + 5000
    assert dollars(search[("committee", "C00800103")]["weight"]) == 38550 + 45500
    # A payee with a page is searched by its display name, its other spellings its aliases (§5.5);
    # an unresolved build has no donors.
    assert {kind for kind, _ in search} == {"candidate", "committee", "race", "payee"}
    assert {id_ for kind, id_ in search if kind == "payee"} == {
        page(key) for key in spending["payees"]
    }
    blue_harbor = search[("payee", page("BLUE HARBOR STRATEGIES"))]
    assert (blue_harbor["name"], blue_harbor["aliases"]) == (
        "BLUE HARBOR STRATEGIES LLC",
        "BLUE HARBOR STRATEGIES, L.L.C.",
    )
    assert f"{blue_harbor['weight']:.2f}" == spending["payees"]["BLUE HARBOR STRATEGIES"]["total"]

    [meta] = rows(migrated_db, "meta")
    assert meta["build_id"] == BUILD
    assert meta["published_at"] is None
    # No resolve has saved a model, so there is no live one and no run record.
    columns = ("resolver_version", "model_version", "overrides_count", "adjudications_applied")
    assert [meta[column] for column in columns] == [None] * len(columns)
    assert meta["cycles"] == {
        "2024": {
            "build_id": BUILD,
            "source_dates": dict.fromkeys(get_args(FecFile), "2026-10-30"),
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

    # Each donor's bucket is their net gifts to the candidate (every-FEC-dollar spec §4.6):
    # THACKERAY's twenty $50 gifts to BRANNIGAN are one $1,000 donor, in under_2000.
    gift_sizes: dict[str, dict[str, list[int | None]]] = defaultdict(dict)
    for row in rows(migrated_db, "candidate_gift_size"):
        gift_sizes[row["candidate_id"]][row["bucket"]] = [dollars(row["amount"]), row["donors"]]
    brannigan = "S4MD00111"
    assert gift_sizes[brannigan] == expected["gold_reported"]["gift_sizes"][brannigan]
    assert donor_cycles[donor("twenty_small_gifts")]["contribution_count"] == 20
    # Every candidate with counted money has the five itemized buckets, adding up to it; QUILL, with
    # none, has no row.
    for candidate_id, totals in expected["candidates"].items():
        itemized = {b: v for b, v in gift_sizes.get(candidate_id, {}).items() if b != "unitemized"}
        if totals["total_individual"] == 0:
            assert itemized == {}, candidate_id
            continue
        assert len(itemized) == 5, candidate_id
        assert sum(amount or 0 for amount, _ in itemized.values()) == totals["total_individual"]
    assert "P40000110" not in gift_sizes

    assert rows(migrated_db, "donor_redirect") == [{"old_donor_id": 9001, "donor_id": 1}]
    marker = markers.read("loaded", store, cycle=2024, build_id=BUILD)
    assert marker is not None
    assert marker.row_counts == {table: len(rows(migrated_db, table)) for table in GOLD_TABLES}


def test_a_file_with_no_bronze_has_no_source_date(store: R2) -> None:
    # A cycle transformed before the summary files were catalogued, and not extracted since, has
    # none of them in bronze (NEU-2142): `gold.meta` names only the files it downloaded.
    store.put(paths.bronze_zip(2024, "cm", date(2026, 10, 30)), b"")
    store.put(paths.bronze_zip(2024, "cm", date(2026, 11, 6)), b"")
    store.put(paths.bronze_zip(2024, "indiv", date(2026, 10, 30)), b"")

    dates = gold._source_dates(store, 2024)  # pyright: ignore[reportPrivateUsage]

    assert dates == {"cm": "2026-11-06", "indiv": "2026-10-30"}


def test_load_without_a_build_id_takes_the_newest_transformed_build(
    store: R2, transformed: Path, migrated_db: str
) -> None:
    """…and a payee keeps its payee_id in it: the id is its key's, not the build's (spec §5.4).
    The expected-totals test finds the first build's ids are the same keys', so the two builds
    agree without loading both here."""
    assert run("seats", "--cycle", "2024", build_id=NEWER).exit_code == 0
    assert run("transform", "--cycle", "2024", build_id=NEWER).exit_code == 0

    result = load(build_id=None)

    assert result.exit_code == 0, result.output
    [meta] = rows(migrated_db, "meta")
    assert meta["build_id"] == NEWER
    assert markers.exists("loaded", store, cycle=2024, build_id=NEWER)
    assert not markers.exists("loaded", store, cycle=2024, build_id=BUILD)
    assert {row["payee_key"]: row["payee_id"] for row in rows(migrated_db, "payee")} == {
        key: page(key) for key in fec_fixture.expected()["operating_expenditures"]["payees"]
    }


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
            " (2024, 'C1', 'ACME', 'ACME INC', 500, false),"
            " (2024, 'C1', 'ACME', 'ACME, INC.', 250, false),"
            " (2024, 'C1', 'ACME', 'ACME INC', 300, true),"
            " (2024, 'C1', 'BOLT', 'BOLT LLC', 100, false),"
            " (2024, 'C2', 'ACME', 'ACME INC', 75, NULL),"
            " (1998, 'C4', 'ACME', 'ACME INC', 40, false),"
            " (2024, 'C4', 'ACME', 'ACME CO', 60, false),"
            " (2024, 'C5', 'IRS', 'DEPARTMENT OF THE TREASURY', 800, true)"
            ") AS t(cycle, recipient_committee_id, organization_key, organization_name, amount,"
            " is_returned_cost)"
        )
        con.execute(
            "CREATE TABLE committee_top_organization AS SELECT * FROM (VALUES"
            " ('C1', 2024, 1, 'ACME', 'ACME INC', 750), ('C1', 2024, 2, 'BOLT', 'BOLT LLC', 90),"
            " ('C2', 2024, 1, 'ACME', 'ACME CORP', 75), ('C3', 2024, 1, 'ACME', 'ACME INC', 10),"
            " ('C4', 1998, 1, 'ACME', 'ACME CO', 40),"
            " ('C5', 2024, 1, 'IRS', 'DEPARTMENT OF THE TREASURY', 800)"
            ") AS t(committee_id, cycle, rank, organization_key, name, amount)"
        )

        # BOLT's amount is not its net receipts, ACME CORP is no spelling ACME reported, C3
        # received nothing from ACME, and ACME CO is a spelling of 2024's only, not 1998's. A cost
        # coming back to the committee is no gift (NEU-2402): C1's ACME total leaves its $300 out,
        # and C5's IRS refund is listed from no receipt. A build from before the flag (NULL) counts
        # every receipt.
        assert sorted(failing_rows(con, "gold_committee_top_organization_amount.sql")) == [
            (1998, "C4", "ACME", "ACME CO", 40, 40),
            (2024, "C1", "BOLT", "BOLT LLC", 90, 100),
            (2024, "C2", "ACME", "ACME CORP", 75, 75),
            (2024, "C3", "ACME", "ACME INC", 10, None),
            (2024, "C5", "IRS", "DEPARTMENT OF THE TREASURY", 800, None),
        ]


def test_the_spending_category_check_fails_on_categories_not_adding_up_to_the_total() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE committee_cycle AS SELECT * FROM (VALUES"
            " ('C1', 2024, 1500.00), ('C2', 2024, 900.00), ('C3', 2024, NULL),"
            " ('C4', 2024, NULL), ('C5', 2024, 0.00)"
            ") AS t(committee_id, cycle, total_operating_expenditures)"
        )
        con.execute(
            "CREATE TABLE committee_spending_category AS SELECT * FROM (VALUES"
            " ('C1', 2024, 'media', 2000.00), ('C1', 2024, 'other', -500.00),"
            " ('C2', 2024, 'media', 800.00), ('C3', 2024, 'travel', 50.00),"
            " ('C5', 2024, 'digital', 100.00), ('C5', 2024, 'other', -100.00),"
            " ('C6', 2024, 'mail', 75.00)"
            ") AS t(committee_id, cycle, category, amount)"
        )

        # C1's other nets below $0 and is kept, so its rows add up; C5's net to $0, its total 0.
        # C2's rows miss $100 (a hand-broken row), C3 has rows beside no total, and C6 rows beside
        # no committee_cycle row. C4 spent nothing and has none.
        assert sorted(failing_rows(con, "gold_committee_spending_category_total.sql")) == [
            ("C2", 2024, Decimal("900.00"), Decimal("800.00")),
            ("C3", 2024, None, Decimal("50.00")),
            ("C6", 2024, None, Decimal("75.00")),
        ]


OPERATING_EXPENDITURES = (
    "CREATE TABLE silver.operating_expenditure AS SELECT * FROM (VALUES {rows})"
    " AS t(cycle, committee_id, payee_key, payee_name, payee_is_person, is_in_kind, counted,"
    " amount)"
)


def test_the_top_payee_amount_check_fails_on_a_row_silver_does_not_add_up_to() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA silver")
        con.execute(
            OPERATING_EXPENDITURES.format(
                rows="(2024, 'C1', 'ACME', 'ACME INC', false, false, true, 500),"
                " (2024, 'C1', 'ACME', 'ACME, INC.', false, false, true, 250),"
                " (2024, 'C1', 'ACME', 'ACME INC', false, false, false, 300),"
                " (2024, 'C1', 'BOLT', 'BOLT LLC', false, false, true, 100),"
                " (2024, 'C1', 'BOLT', 'BOLT LLC', false, true, true, 40),"
                " (2024, 'C2', 'ACME', 'ACME INC', false, false, true, 75)"
            )
        )
        acme = page("ACME")
        con.execute(
            "CREATE TABLE committee_top_payee AS SELECT * FROM (VALUES"
            f" ('C1', 2024, 1, 'ACME', '{acme}', 'ACME INC', 750),"
            " ('C1', 2024, 2, 'BOLT', NULL, 'BOLT LLC', 140),"
            f" ('C2', 2024, 1, 'ACME', '{acme}', 'ACME CORP', 75),"
            f" ('C3', 2024, 1, 'ACME', '{acme}', 'ACME INC', 10),"
            " ('C4', 2024, 1, 'ACME', 'acme', 'ACME INC', 75)"
            ") AS t(committee_id, cycle, rank, payee_key, payee_id, name, amount)"
        )

        # C1's ACME leaves its uncounted row out. BOLT's amount takes in its in-kind outlay, ACME
        # CORP is no spelling ACME was paid under, C3 paid ACME nothing, and C4's payee_id is not
        # ACME's (C4 paid nothing either).
        assert sorted(failing_rows(con, "gold_committee_top_payee_amount.sql")) == [
            (2024, "C1", "BOLT", "BOLT LLC", None, 140, 100),
            (2024, "C2", "ACME", "ACME CORP", acme, 75, 75),
            (2024, "C3", "ACME", "ACME INC", acme, 10, None),
            (2024, "C4", "ACME", "ACME INC", "acme", 75, None),
        ]


PAYEE_MODELS = ("22_payee", "23_committee_top_payee", "24_payee_cycle", "25_payee_top_payer")
PAYEES = (
    "CREATE TABLE silver.operating_expenditure AS SELECT * FROM (VALUES {rows})"
    " AS t(cycle, committee_id, candidate_id, payee_key, payee_name, payee_city, payee_state,"
    " payee_is_person, is_in_kind, counted, amount)"
)


def build_payees(con: duckdb.DuckDBPyConnection, *, no_page: tuple[str, ...] = ()) -> None:
    """The payee models over `silver.operating_expenditure`, as the loader runs them: the no-page
    list registered, `payee` first. A test table without the display and credit columns has them
    NULL."""
    for column in ("candidate_id", "payee_city", "payee_state"):
        con.execute(
            f"ALTER TABLE silver.operating_expenditure ADD COLUMN IF NOT EXISTS {column} VARCHAR"
        )
    con.execute("CREATE TABLE payee_no_page (payee_key VARCHAR PRIMARY KEY)")
    if no_page:
        con.executemany("INSERT INTO payee_no_page VALUES (?)", [(key,) for key in no_page])
    for model in PAYEE_MODELS:
        con.execute(render(REPO_ROOT / "sql" / "gold" / f"{model}.sql", {}))


def test_a_top_payee_list_holds_payee_rows_netting_above_0_and_a_persons_key_has_no_page() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA silver")
        con.execute(
            OPERATING_EXPENDITURES.format(
                rows="(2024, 'C1', 'ACME', 'ACME INC', false, false, true, 500),"
                " (2024, 'C2', 'ACME', 'ACME, INC.', false, false, true, 900),"
                " (2024, 'C1', 'BOLT', 'BOLT LLC', false, false, true, 500),"
                " (2024, 'C1', 'DOE JANE', 'DOE, JANE', true, false, true, 300),"
                " (2022, 'C1', 'DOE JANE', 'DOE JANE', false, false, true, 200),"
                " (2024, 'C1', 'ROE RAY', 'ROE, RAY', true, false, true, 200),"
                " (2022, 'C1', 'ROE RAY', 'ROE RAY', false, false, true, 400),"
                " (2024, 'C1', 'GIFT', 'GIFT', false, true, true, 9000),"
                " (2024, 'C1', 'CARD', 'CARD', false, false, false, 9000),"
                " (2024, 'C1', 'VOID', 'VOID', false, false, true, 100),"
                " (2024, 'C1', 'VOID', 'VOID', false, false, true, -100),"
                " (2024, 'C1', 'REFUNDS', 'REFUNDS INC', false, false, true, 50),"
                " (2022, 'C2', 'REFUNDS', 'REFUNDS INC', false, false, true, -400),"
                " (2024, 'C1', 'PETTY CASH', 'PETTY CASH', false, false, true, 70),"
                " (2024, 'C1', NULL, NULL, false, false, true, 9000)"
            )
        )
        build_payees(con, no_page=("PETTY CASH",))

        listed = con.execute(
            "SELECT committee_id, cycle, rank, payee_key, payee_id, name, amount"
            " FROM committee_top_payee ORDER BY committee_id, cycle, rank"
        ).fetchall()

    # ACME and BOLT tie at C1 and go by key; ACME is named by its most-dollar spelling, C2's. DOE
    # JANE is a person on 300 of her 500 dollars over both cycles, so no page; ROE RAY on 200 of
    # 600, so one. REFUNDS nets below $0 over both cycles with no person row: a firm's key, with a
    # page. PETTY CASH is on the no-page list, so it has none. An in-kind outlay, an uncounted
    # row, a key netting to $0 and a row with no key are in no list.
    assert listed == [
        ("C1", 2022, 1, "ROE RAY", page("ROE RAY"), "ROE RAY", Decimal("400.00")),
        ("C1", 2022, 2, "DOE JANE", None, "DOE JANE", Decimal("200.00")),
        ("C1", 2024, 1, "ACME", page("ACME"), "ACME, INC.", Decimal("500.00")),
        ("C1", 2024, 2, "BOLT", page("BOLT"), "BOLT LLC", Decimal("500.00")),
        ("C1", 2024, 3, "DOE JANE", None, "DOE, JANE", Decimal("300.00")),
        ("C1", 2024, 4, "ROE RAY", page("ROE RAY"), "ROE, RAY", Decimal("200.00")),
        ("C1", 2024, 5, "PETTY CASH", None, "PETTY CASH", Decimal("70.00")),
        ("C1", 2024, 6, "REFUNDS", page("REFUNDS"), "REFUNDS INC", Decimal("50.00")),
        ("C2", 2024, 1, "ACME", page("ACME"), "ACME, INC.", Decimal("900.00")),
    ]


# ACME over two cycles and three spellings, BOLT credited by a handoff to two candidates, a
# person, a key on the no-page list and a key netting below $0.
PAYEE_PAGE_ROWS = (
    "(2024, 'C1', 'H1', 'ACME', 'ACME INC', 'ESSEX', 'MD', false, false, true, 500),"
    " (2022, 'C1', 'H1', 'ACME', 'ACME CORP', 'ESSEX', 'MD', false, false, true, 600),"
    " (2024, 'C2', NULL, 'ACME', 'ACME, INC.', 'BOWIE', 'MD', false, false, true, 900),"
    " (2024, 'C2', NULL, 'ACME', 'ACME', 'LAUREL', 'MD', false, true, true, 9000),"
    " (2024, 'C2', NULL, 'ACME', 'ACME', 'LAUREL', 'MD', false, false, false, 9000),"
    " (2024, 'C9', 'P1', 'BOLT', 'BOLT LLC', NULL, 'DE', false, false, true, 300),"
    " (2024, 'C9', 'P2', 'BOLT', 'BOLT LLC', NULL, 'DE', false, false, true, 700),"
    " (2024, 'C9', NULL, 'BOLT', 'BOLT LLC', NULL, 'DE', false, false, true, 50),"
    " (2024, 'C8', NULL, 'BOLT', 'BOLT LLC', NULL, 'DE', false, false, true, 100),"
    " (2024, 'C8', NULL, 'BOLT', 'BOLT LLC', NULL, 'DE', false, false, true, -100),"
    " (2024, 'C1', 'H1', 'DOE JANE', 'DOE, JANE', 'ELK', 'MD', true, false, true, 300),"
    " (2024, 'C1', 'H1', 'PETTY CASH', 'PETTY CASH', NULL, NULL, false, false, true, 70),"
    " (2024, 'C1', 'H1', 'REFUNDS', 'REFUNDS INC', NULL, NULL, false, false, true, -400)"
)


def test_a_payee_page_holds_its_payee_rows_over_every_cycle_and_its_top_payers() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA silver")
        con.execute(PAYEES.format(rows=PAYEE_PAGE_ROWS))
        build_payees(con, no_page=("PETTY CASH",))

        payees = con.execute("SELECT * FROM payee ORDER BY payee_key").fetchall()
        cycles = con.execute("SELECT * FROM payee_cycle ORDER BY payee_id, cycle").fetchall()
        payers = con.execute(
            "SELECT * FROM payee_top_payer ORDER BY payee_id, cycle, rank"
        ).fetchall()
        checks = [
            failing_rows(con, "gold_payee_page.sql"),
            failing_rows(con, "gold_payee_top_payer_amount.sql"),
        ]

    # ACME's name is its most-dollar spelling over both cycles, ACME, INC.'s $900, and its city,
    # chosen alone, ESSEX's $1,100 over two spellings. Its gift and its uncounted row are in
    # no figure. BOLT's C9 rows a handoff credits to P1 and P2 are P2's, who has more of them; C8's
    # net to $0, so C8 is no top payer but is one of the 2 committees that paid it. No row gives
    # BOLT a city. REFUNDS nets below $0 and keeps its page, with no top payer. DOE JANE, a
    # person, and PETTY CASH, on the no-page list, have no page and no figure.
    acme, bolt, refunds = page("ACME"), page("BOLT"), page("REFUNDS")
    assert payees == [
        (acme, "ACME", "ACME, INC.", "ESSEX", "MD", Decimal("2000.00"), 2022, 2024),
        (bolt, "BOLT", "BOLT LLC", None, "DE", Decimal("1050.00"), 2024, 2024),
        (refunds, "REFUNDS", "REFUNDS INC", None, None, Decimal("-400.00"), 2024, 2024),
    ]
    assert sorted(cycles) == sorted(
        [
            (acme, 2022, Decimal("600.00"), 1),
            (acme, 2024, Decimal("1400.00"), 2),
            (bolt, 2024, Decimal("1050.00"), 2),
            (refunds, 2024, Decimal("-400.00"), 1),
        ]
    )
    assert sorted(payers) == sorted(
        [
            (acme, 2022, 1, "C1", "H1", Decimal("600.00")),
            (acme, 2024, 1, "C2", None, Decimal("900.00")),
            (acme, 2024, 2, "C1", "H1", Decimal("500.00")),
            (bolt, 2024, 1, "C9", "P2", Decimal("1050.00")),
        ]
    )
    assert checks == [[], []]


def test_the_payee_page_check_fails_on_a_duplicate_a_foreign_id_or_a_listed_key() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE TABLE payee_no_page AS SELECT 'PETTY CASH' AS payee_key")
        con.execute(
            "CREATE TABLE payee AS SELECT * FROM (VALUES"
            f" ('{page('ACME')}', 'ACME'), ('{page('ACME')}', 'ACME CORP'),"
            " ('bolt', 'BOLT'),"
            f" ('{page('PETTY CASH')}', 'PETTY CASH')"
            ") AS t(payee_id, payee_key)"
        )
        con.execute(
            "CREATE TABLE committee_top_payee AS SELECT * FROM (VALUES"
            f" ('ACME', '{page('ACME')}'), ('ACME', NULL), ('ROE', '{page('ROE')}'),"
            " ('DOE JANE', NULL)"
            ") AS t(payee_key, payee_id)"
        )

        # ACME CORP shares ACME's payee_id, which is not its own; BOLT's is no key's; PETTY CASH
        # is listed. One of C's ACME rows links to no page though ACME has one; ROE's links to a
        # page no payee has. DOE JANE, with no page, links to none, as it should.
        assert sorted(failing_rows(con, "gold_payee_page.sql"), key=str) == sorted(
            [
                ("payee", page("ACME"), None, "payee_id not unique"),
                ("payee", page("ACME"), "ACME CORP", "payee_id is not the key's"),
                ("payee", "bolt", "BOLT", "payee_id is not the key's"),
                ("payee", page("PETTY CASH"), "PETTY CASH", "listed in payee_no_page"),
                ("committee_top_payee", None, "ACME", "not its key's page"),
                ("committee_top_payee", page("ROE"), "ROE", "not its key's page"),
            ],
            key=str,
        )


def test_the_top_payer_check_fails_on_an_amount_or_candidate_silver_does_not_give() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA silver")
        con.execute(
            PAYEES.format(
                rows="(2024, 'C1', 'H1', 'ACME', 'ACME INC', NULL, NULL, false, false, true, 500),"
                " (2024, 'C1', 'H1', 'ACME', 'ACME INC', NULL, NULL, false, true, true, 40),"
                " (2024, 'C2', 'H2', 'ACME', 'ACME INC', NULL, NULL, false, false, true, 300),"
                " (2024, 'C3', NULL, 'ACME', 'ACME INC', NULL, NULL, false, false, true, 200),"
                " (2024, 'C4', 'H4', 'ACME', 'ACME INC', NULL, NULL, false, false, true, 100)"
            )
        )
        acme = page("ACME")
        con.execute(f"CREATE TABLE payee AS SELECT '{acme}' AS payee_id, 'ACME' AS payee_key")
        con.execute(
            "CREATE TABLE payee_top_payer AS SELECT * FROM (VALUES"
            f" ('{acme}', 2024, 1, 'C1', 'H1', 540.00),"
            f" ('{acme}', 2024, 2, 'C2', 'H9', 300.00),"
            f" ('{acme}', 2024, 3, 'C3', NULL, 200.00),"
            f" ('{acme}', 2024, 4, 'C4', NULL, 100.00),"
            " ('nobody', 2024, 1, 'C1', 'H1', 500.00)"
            ") AS t(payee_id, cycle, rank, committee_id, candidate_id, amount)"
        )

        # C1's amount takes in its in-kind outlay; H9 is no candidate C2's rows are credited to;
        # C4's rows are H4's, so a NULL candidate is wrong; `nobody` is no payee's id. C3's rows
        # are credited to no one, so its NULL is right.
        assert sorted(failing_rows(con, "gold_payee_top_payer_amount.sql"), key=str) == sorted(
            [
                (acme, 2024, "C1", "H1", Decimal("540.00"), Decimal("500")),
                (acme, 2024, "C2", "H9", Decimal("300.00"), Decimal("300")),
                (acme, 2024, "C4", None, Decimal("100.00"), Decimal("100")),
                ("nobody", 2024, "C1", "H1", Decimal("500.00"), None),
            ],
            key=str,
        )


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


def test_the_recipient_check_fails_on_a_committee_recipient_of_no_committee() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE TABLE committee AS SELECT 'C1' AS committee_id")
        con.execute(
            "CREATE TABLE committee_top_recipient AS SELECT * FROM (VALUES"
            " ('C1', 1, 'committee', 'C1'), ('C1', 2, 'committee', 'C9'),"
            " ('C1', 3, 'candidate', 'C9')"
            ") AS t(committee_id, rank, recipient_kind, recipient_id)"
        )

        assert failing_rows(con, "gold_committee_top_recipient_committee.sql") == [("C1", 2, "C9")]


def test_the_refunds_check_fails_on_a_positive_refunds_figure() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE committee_cycle AS SELECT * FROM (VALUES"
            " ('C1', -500.00), ('C2', 0.00), ('C3', 0.01)"
            ") AS t(committee_id, total_refunds)"
        )

        # C3's refunds add to its totals rather than subtracting.
        assert failing_rows(con, "gold_committee_cycle_refunds.sql") == [("C3", Decimal("0.01"))]


ITEMIZED_BUCKETS = ("200_or_less", "under_500", "under_1000", "under_2000", "2000_or_more")


def test_the_gift_size_check_fails_on_buckets_not_adding_up_to_the_candidates_money() -> None:
    buckets = {
        # Five buckets adding up to the candidate's money, and FEC's lump beside them.
        "H1": [("unitemized", 9000), *zip(ITEMIZED_BUCKETS, (100, 200, 300, 400, 0), strict=True)],
        "H2": list(zip(ITEMIZED_BUCKETS, (100, 100, 100, 100, 0), strict=True)),
        "H3": list(zip(ITEMIZED_BUCKETS[:4], (250, 250, 250, 250), strict=True)),
    }
    values = ", ".join(
        f"('{candidate}', 2024, '{bucket}', {amount})"
        for candidate, rows_ in buckets.items()
        for bucket, amount in rows_
    )
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA silver")
        # H7's gift and its refund net to $0: a counted contribution all the same.
        con.execute(
            "CREATE TABLE silver.contribution AS SELECT * FROM (VALUES"
            " (2024, 'H4', 250, false, false), (2024, 'H5', 900, true, false),"
            " (2024, 'H7', 300, false, false), (2024, 'H7', -300, false, false)"
            ") AS t(cycle, candidate_id, amount, is_self_funding, is_other_line)"
        )
        con.execute(
            "CREATE TABLE candidate_cycle AS SELECT * FROM (VALUES"
            " ('H1', 2024, 1000, 4), ('H2', 2024, 500, 3), ('H3', 2024, 1000, 4),"
            " ('H4', 2024, 250, 1), ('H5', 2024, 0, 0), ('H6', 2024, 750, NULL),"
            " ('H7', 2024, 0, 1)"
            ") AS t(candidate_id, cycle, total_individual, contributor_count)"
        )
        con.execute(
            f"CREATE TABLE candidate_gift_size AS SELECT * FROM (VALUES {values})"
            " AS t(candidate_id, cycle, bucket, amount)"
        )

        # H2's buckets miss $100, H3 has four, H4's money is in none, H7's gifts netting to $0 have
        # no buckets; H5 has only its own money, and H6's cycle was loaded before `resolve`.
        assert sorted(failing_rows(con, "gold_candidate_gift_size_total.sql")) == [
            ("H2", 2024, 500, 400, 5),
            ("H3", 2024, 1000, 1000, 4),
            ("H4", 2024, 250, None, None),
            ("H7", 2024, 0, None, None),
        ]


def test_reconciliation_lists_a_committee_over_by_more_than_1pct_or_over_a_reported_0() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA silver")
        con.execute(
            "CREATE TABLE silver.committee AS SELECT * FROM (VALUES"
            " (2024, 'C1', false), (2024, 'C2', false), (2024, 'C3', false), (2024, 'C4', false),"
            " (2024, 'C5', false), (2024, 'C6', true), (2024, 'C7', false)"
            ") AS t(cycle, committee_id, is_conduit)"
        )
        con.execute(
            "CREATE TABLE committee_cycle AS SELECT * FROM (VALUES"
            " ('C1', 2024, 3800.00, 3700.00, NULL, NULL),"
            " ('C2', 2024, 6400.00, 6350.00, 100.00, 99.50),"
            " ('C3', 2024, 500.00, 0.00, 250.00, 0.00), ('C4', 2024, 0.00, 0.00, NULL, 0.00),"
            " ('C5', 2024, 900.00, NULL, 50.00, NULL),"
            " ('C6', 2024, 9000.00, 780.00, 800.00, 700.00),"
            " ('C7', 2024, 100.00, 400.00, 300.00, 400.00)"
            ") AS t(committee_id, cycle, itemized_total, reported_individual_itemized,"
            " total_operating_expenditures, reported_operating_expenditures)"
        )
        con.execute(render(REPO_ROOT / "sql" / "gold" / "19_reconciliation.sql", {}))

        # C1 is 2.7% over; C2 within 1%. C3's reported 0 is a figure FEC gives, so it is listed
        # with no ratio; C4 has nothing over it. C5's blank figure, the conduit C6 and C7's
        # shortfall are not listed. On spending (§5.6) the same, but that the conduit C6 is listed,
        # 14.3% over, and C4 spent nothing beside its reported 0.
        listed = con.execute(
            "SELECT committee_id, measure, fundlens, reported, round(ratio, 4)"
            " FROM reconciliation ORDER BY committee_id, measure"
        ).fetchall()
    assert listed == [
        ("C1", "individual_itemized", Decimal("3800.00"), Decimal("3700.00"), 1.027),
        ("C3", "individual_itemized", Decimal("500.00"), Decimal("0.00"), None),
        ("C3", "operating_expenditures", Decimal("250.00"), Decimal("0.00"), None),
        ("C6", "operating_expenditures", Decimal("800.00"), Decimal("700.00"), 1.1429),
    ]


def test_the_coverage_check_fails_on_a_figure_where_none_is_due_or_none_where_one_is() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA silver")
        con.execute(
            "CREATE TABLE silver.committee AS SELECT * FROM (VALUES"
            " (2024, 'C1', false), (2024, 'C2', false), (2024, 'C3', false), (2024, 'C4', true),"
            " (2024, 'C5', false), (2024, 'C6', false)"
            ") AS t(cycle, committee_id, is_conduit)"
        )
        con.execute(
            "CREATE TABLE committee_cycle AS SELECT * FROM (VALUES"
            " ('C1', 2024, 1000, 0.95), ('C2', 2024, NULL, NULL), ('C3', 2024, 0, 1.0),"
            " ('C4', 2024, 780, 0.01), ('C5', 2024, 500, NULL), ('C6', 2024, 0, NULL)"
            ") AS t(committee_id, cycle, reported_individual_itemized, coverage)"
        )

        # C3's reported figure is 0 and C4 is a conduit, yet each has a coverage; C5 has a figure
        # to divide by and none.
        assert sorted(failing_rows(con, "gold_committee_cycle_coverage.sql")) == [
            ("C3", 2024, 0, False, Decimal("1.0")),
            ("C4", 2024, 780, True, Decimal("0.01")),
            ("C5", 2024, 500, False, None),
        ]


def test_a_committee_cm_lists_as_a_skeleton_keeps_the_name_an_earlier_cycle_gave_it() -> None:
    # `cm` lists a committee as a skeleton row now and then: its id and filing frequency `T`, every
    # other column blank (NEU-2296: 2018's C00575308, named in 2016; 2016's C00603068, named in no
    # cycle).
    gold = REPO_ROOT / "sql" / "gold"
    with duckdb.connect() as con:
        con.execute("CREATE MACRO pg_array(l) AS '{' || array_to_string(l, ',') || '}'")
        con.execute("CREATE SCHEMA silver")
        con.execute(
            "CREATE TABLE silver.committee AS SELECT * FROM (VALUES"
            " (2016, 'C1', 'FRIENDS OF ROE', 'H', 'P', 'DEM', NULL, false),"
            " (2018, 'C1', NULL, NULL, NULL, NULL, NULL, false),"
            " (2016, 'C2', NULL, NULL, NULL, NULL, NULL, false),"
            " (2016, 'C3', 'ROE PAC', 'Q', 'U', NULL, 'ROE INC', false),"
            " (2018, 'C3', 'ROE FOR AMERICA PAC', 'Q', 'U', NULL, 'ROE INC', false)"
            ") AS t(cycle, committee_id, name, type, designation, party, connected_org, is_conduit)"
        )
        con.execute(
            "CREATE TABLE committee_cycle AS SELECT * FROM (VALUES"
            " ('C1', 100.00, 0.00), ('C2', 50.00, 0.00), ('C3', 0.00, 25.00)"
            ") AS t(committee_id, total_individual, total_from_committees)"
        )
        # Every other kind search_entity lists, empty.
        con.execute("CREATE TABLE candidate (candidate_id VARCHAR, name VARCHAR)")
        con.execute(
            "CREATE TABLE candidate_cycle (candidate_id VARCHAR,"
            " total_individual DECIMAL(16, 2), total_committee DECIMAL(16, 2))"
        )
        con.execute(
            "CREATE TABLE silver.candidate (cycle INTEGER, candidate_id VARCHAR,"
            " principal_committee_id VARCHAR, alias_of VARCHAR)"
        )
        con.execute(
            "CREATE TABLE race (race_id VARCHAR, cycle INTEGER, office VARCHAR, state VARCHAR,"
            " district VARCHAR, is_special BOOLEAN, slug VARCHAR, total_individual DECIMAL(16, 2))"
        )
        con.execute(
            "CREATE TABLE donor"
            " (donor_id BIGINT, display_name VARCHAR, total_all_cycles DECIMAL(16, 2))"
        )
        con.execute(
            "CREATE TABLE donor_variant (donor_id BIGINT, field VARCHAR, value VARCHAR,"
            " amount DECIMAL(16, 2), contributions INTEGER)"
        )
        con.execute(
            "CREATE TABLE payee (payee_id VARCHAR, payee_key VARCHAR, display_name VARCHAR,"
            " total_all_cycles DECIMAL(16, 2))"
        )
        con.execute(
            "CREATE TABLE payee_row (payee_key VARCHAR, payee_name VARCHAR, amount DECIMAL(14, 2))"
        )

        con.execute(render(gold / "06_committee.sql", {}))
        con.execute(render(gold / "26_search_entity.sql", {}))

        committees = con.execute(
            "SELECT committee_id, name, type, designation, party, cycles FROM committee"
            " ORDER BY committee_id"
        ).fetchall()
        searched = con.execute("SELECT id, name FROM search_entity ORDER BY id").fetchall()
        failures = failing_rows(con, "gold_search_entity_name.sql")

    assert committees == [
        ("C1", "FRIENDS OF ROE", "H", "P", "DEM", "{2016,2018}"),
        ("C2", None, None, None, None, "{2016}"),
        # A committee named in both cycles takes the newest name, as before.
        ("C3", "ROE FOR AMERICA PAC", "Q", "U", None, "{2016,2018}"),
    ]
    assert searched == [("C1", "FRIENDS OF ROE"), ("C3", "ROE FOR AMERICA PAC")]
    assert failures == []


def test_a_candidate_cn_lists_as_a_skeleton_keeps_an_earlier_name_or_is_not_searched() -> None:
    # `cn` lists a candidate as a skeleton row now and then: its id, year, state, office, status
    # and principal committee, every other column blank (NEU-2323: 2026's H6AZ08210, named in no
    # cycle, whose principal committee has a name of its own).
    gold = REPO_ROOT / "sql" / "gold"
    with duckdb.connect() as con:
        con.execute("CREATE MACRO pg_array(l) AS '{' || array_to_string(l, ',') || '}'")
        con.execute("CREATE SCHEMA silver")
        con.execute(
            "CREATE TABLE silver.candidate AS SELECT * FROM (VALUES"
            " (2024, 'H1', 'ROE, JANE', 'DEM', 'H', 'AZ', '08', 'C1', CAST(NULL AS VARCHAR)),"
            " (2026, 'H1', NULL, NULL, 'H', 'AZ', NULL, 'C1', NULL),"
            " (2026, 'H2', NULL, NULL, 'H', 'AZ', NULL, 'C2', NULL),"
            " (2024, 'H3', 'DOE, JOHN', 'REP', 'H', 'AZ', '01', 'C3', NULL),"
            " (2026, 'H3', 'DOE, JOHN Q', 'REP', 'H', 'AZ', '02', 'C3', NULL)"
            ") AS t(cycle, candidate_id, name, party, office, state, district,"
            " principal_committee_id, alias_of)"
        )
        con.execute(
            "CREATE TABLE candidate_cycle AS SELECT * FROM (VALUES"
            " ('H1', 100.00, 0.00), ('H2', 50.00, 0.00), ('H3', 0.00, 25.00)"
            ") AS t(candidate_id, total_individual, total_committee)"
        )
        con.execute(
            "CREATE TABLE committee AS SELECT * FROM (VALUES"
            " ('C2', 'ROE FOR AZ', CAST(NULL AS VARCHAR))"
            ") AS t(committee_id, name, connected_org)"
        )
        # Every other kind search_entity lists, empty.
        con.execute(
            "CREATE TABLE committee_cycle (committee_id VARCHAR,"
            " total_individual DECIMAL(16, 2), total_from_committees DECIMAL(16, 2))"
        )
        con.execute(
            "CREATE TABLE race (race_id VARCHAR, cycle INTEGER, office VARCHAR, state VARCHAR,"
            " district VARCHAR, is_special BOOLEAN, slug VARCHAR, total_individual DECIMAL(16, 2))"
        )
        con.execute(
            "CREATE TABLE donor"
            " (donor_id BIGINT, display_name VARCHAR, total_all_cycles DECIMAL(16, 2))"
        )
        con.execute(
            "CREATE TABLE donor_variant (donor_id BIGINT, field VARCHAR, value VARCHAR,"
            " amount DECIMAL(16, 2), contributions INTEGER)"
        )
        con.execute(
            "CREATE TABLE payee (payee_id VARCHAR, payee_key VARCHAR, display_name VARCHAR,"
            " total_all_cycles DECIMAL(16, 2))"
        )
        con.execute(
            "CREATE TABLE payee_row (payee_key VARCHAR, payee_name VARCHAR, amount DECIMAL(14, 2))"
        )

        con.execute(render(gold / "05_candidate.sql", {}))
        con.execute(render(gold / "26_search_entity.sql", {}))

        candidates = con.execute(
            "SELECT candidate_id, name, party, office, state, district, cycles FROM candidate"
            " ORDER BY candidate_id"
        ).fetchall()
        searched = con.execute("SELECT id, name FROM search_entity ORDER BY id").fetchall()
        failures = failing_rows(con, "gold_search_entity_name.sql")

    assert candidates == [
        ("H1", "ROE, JANE", "DEM", "H", "AZ", "08", "{2024,2026}"),
        ("H2", None, None, "H", "AZ", None, "{2026}"),
        # A candidate named in both cycles takes the newest row, as before.
        ("H3", "DOE, JOHN Q", "REP", "H", "AZ", "02", "{2024,2026}"),
    ]
    # H2 is left out though its principal committee has a name: that is not the candidate's.
    assert searched == [("H1", "ROE, JANE"), ("H3", "DOE, JOHN Q")]
    assert failures == []


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
