"""`fundlens transform` on the fixture cycle, against MinIO bronze and a migrated Postgres
(spec §5.3)."""

import io
import logging
import zipfile
from collections.abc import Iterator, Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import duckdb
import pytest
from typer.testing import CliRunner, Result

from fundlens import cli, markers, paths
from fundlens.fec.files import FecFile, files_for
from fundlens.paths import SilverTable
from fundlens.r2 import R2
from fundlens.resolve import normalize
from fundlens.transform.runner import ChecksFailed, render
from tests import fec_fixture
from tests.fake_fec import zipped
from tests.integration.conftest import cli_pointed_at, empty_store, scratch_database

BUILD = "20261030T030000Z"
TABLES: tuple[SilverTable, ...] = (
    "committee",
    "candidate",
    "candidate_committee_link",
    "contribution",
    "committee_transfer",
    "organization_receipt",
    "jfc_attribution",
    "contributor",
    "independent_expenditure",
)
# The fixture's filing for Maryland's 9th district, which the 2020 census did not draw.
BAD = "H4MD09109"
ACTBLUE, WINRED = "C00401224", "C00694323"
# The fixture rows for what real files hold that the first fixture did not (NEU-2070).
PARK_TIP, PARK_EARMARK_CONDUIT_SIDE, NORRIS_UNKNOWN_RECIPIENT = (
    4240100000000000301,
    4240100000000000302,
    4240100000000000303,
)
# A conduit's refunds (NEU-2199): WinRed's of an earmark, ActBlue's of PARK's tip and of her
# earmark.
FAIRBANKS_EARMARK_REFUND, PARK_TIP_REFUND, PARK_EARMARK_REFUND = (
    4240100000000000348,
    4240100000000000349,
    4240100000000000350,
)
OTH_NOT_RECEIPTS = {
    4240200000000000010,  # pas2's 24K, repeated in oth
    4240200000000000003,  # pas2's 24A, repeated in oth
    4240300000000000011,  # a 15J memo line
    4240300000000000012,  # WHITLOCK's 16C loan to his campaign: a contribution (NEU-2071)
    4240300000000000029,  # and his campaign's 20C repayment of it
    # More 15J memo lines (spec §6.11): JFC attributions, an organization's, one to no committee.
    *range(4240300000000000015, 4240300000000000020),
    # 15J memo lines in the filings of the JFC's 18G and of its blank-OTHER_ID 15J.
    4240300000000000024,
    4240300000000000025,
    4240300000000000026,  # a union's gift to the party's building account: an organization's
    4240300000000000028,  # an organization's 32J to the party's recount account (NEU-2205)
}
OTH_PARTY_ACCOUNT_RECEIPT = 4240300000000000013
# Organization money (NEU-2131, ADR-0011): ACME's gift to PELL; CHESAPEAKE STEEL's two gifts to the
# super PAC under two spellings and the refund of the first; the union's 31K in `oth`.
ACME = 4240100000000000025
CHESAPEAKE, CHESAPEAKE_AGAIN, CHESAPEAKE_REFUND = (
    4240100000000000321,
    4240100000000000322,
    4240100000000000323,
)
UNION_RECEIPT = 4240300000000000026
SUPER_PAC, PARTY, BRICKLAYERS = "C00800201", "C00800203", "C00800202"
# A hybrid PAC's two accounts (NEU-2192): TREVELYAN's 15 to its contribution account and 10 to
# its non-contribution account, PATAPSCO HOLDINGS' 10 to the second, and TREVELYAN's 10 to the
# super PAC; and its 20Y refund to HAYWARD, who gave the second nothing, and 22Y to TREVELYAN, who
# gave both.
HYBRID_PAC = "C00800204"
CONTRIBUTION_ACCOUNT, NON_CONTRIBUTION_ACCOUNT, PATAPSCO, SUPER_PAC_TYPE_10 = (
    4240100000000000330,
    4240100000000000331,
    4240100000000000332,
    4240100000000000333,
)
MARKED_REFUND, UNMARKED_REFUND = 4240100000000000334, 4240100000000000336
# Money on a line no total_individual counts (NEU-2193): GALLAGHER's gift to the party's
# headquarters account, its refund, and her loan to WHITLOCK FOR SENATE.
HEADQUARTERS_ACCOUNT, HEADQUARTERS_REFUND, INDIVIDUAL_LOAN = (
    4240100000000000337,
    4240100000000000338,
    4240100000000000339,
)
# Organizations' money to the party (NEU-2205): a tribe's 31T to its headquarters account in
# `indiv`, BALTIMORE HARBOR PILOTS' 15 on line 11(a)(i), and a law firm's 32J to its recount
# account in `oth`, with the union's 31K.
TRIBE_ACCOUNT, PARTY_PILOTS, RECOUNT_RECEIPT = (
    4240100000000000346,
    4240100000000000347,
    4240300000000000028,
)
# 24Is (NEU-2203): BRICKLAYERS passing LACROIX's gift on to OKAFOR, and OKAFOR's own row of it; its
# 24I to WHITLOCK, who itemized none; the super PAC's receipt of an earmark through ActBlue, filed
# 24I; and the hybrid PAC's, to its non-contribution account under a memo naming it, and to its
# contribution account without one (NEU-2207).
(
    INTERMEDIARY_24I,
    INTERMEDIARY_TWIN,
    INTERMEDIARY_ONLY,
    RECIPIENT_24I,
    HYBRID_PAC_24I,
    HYBRID_PAC_CONTRIBUTION_24I,
) = (
    4240100000000000340,
    4240100000000000341,
    4240100000000000342,
    4240100000000000343,
    4240100000000000344,
    4240100000000000345,
)
# PAC-typed `indiv` rows with no OTHER_ID (NEU-2131): BRICKLAYERS' gift to the super PAC by name, a
# name that is no committee's, and the super PAC's own name; and `oth`'s blank-OTHER_ID 18K from
# BRICKLAYERS to OKAFOR, a receipt by the same rule.
NAMED_GIFT, NAMES_NONE, NAMES_SELF = (
    4240100000000000324,
    4240100000000000325,
    4240100000000000326,
)
OTH_NAMED_GIFT = 4240300000000000022
# ORG-typed `indiv` rows with no OTHER_ID naming one `cm` committee (NEU-2195): RESTORATION PAC, a
# super PAC, and ONE NATION, a Form 5 filer (type I).
RESTORATION, ONE_NATION = 4240100000000000355, 4240100000000000356
RESTORATION_PAC = "C00800205"
# Rows filed with no entity type (NEU-2132): ACME WIDGETS INC, an organization by the classifier;
# BANKS, JOHN, an individual; OLD LINE REPUBLICAN COMMITTEE, an organization naming one committee;
# and CHESAPEAKE STEEL INC's 15J line, an organization's.
ACME_WIDGETS, BANKS, OLD_LINE_BLANK = (
    4240100000000000327,
    4240100000000000328,
    4240100000000000329,
)
CLASSIFIED_LINE = 4240300000000000027
DRISCOLL_COMMITTEE = "C00800107"
# OKAFOR VICTORY FUND's 18J transfer to OKAFOR, and the 15J lines of the people behind it: one known
# from no contribution, and VANTERPOOL, who gave to the super PAC. An organization's 15J line and
# one to a committee missing from `cm` are no attribution.
JFC, JFC_TRANSFER = "C00800115", 4240300000000000014
# The same JFC's transfers as most are filed (NEU-2124): an 18G, and a 15J with OTHER_ID blank whose
# NAME names the JFC.
JFC_18G, JFC_NAMED_ONLY = 4240300000000000020, 4240300000000000021
ACHTERBERG, VANTERPOOL_LINE = 4240300000000000015, 4240300000000000016
VANTERPOOL = 4240100000000000030
NOT_ATTRIBUTIONS = {4240300000000000018, 4240300000000000019, CLASSIFIED_LINE}
# The Musk case's first contribution, and the same contributor written again with a comma and a JR.
MUSK, MUSK_AGAIN = 4240100000000000007, 4240100000000000011
# 24K gifts whose giver wrote a stale candidate id, and whose recipient raises for no candidate.
STALE_CAND_ID_GIFT, NO_CANDIDATE_GIFT = 4240200000000000017, 4240200000000000018
# The committee handed from BIDEN to HARRIS on 2024-07-21 (NEU-2126, fec/handoffs.csv): two gifts
# before the date, one on it, one after it and one with no date; and a committee's gift before it,
# as the giver's 24K and the recipient's 18K.
HANDED_OFF, BIDEN, HARRIS = "C00703975", "P80000722", "P00009423"
BEFORE_HANDOFF = (4240100000000000312, 4240100000000000313)
FROM_HANDOFF = (4240100000000000314, 4240100000000000315)
UNDATED = 4240100000000000316
HANDOFF_GIFT, HANDOFF_RECEIPT = 4240200000000000021, 4240300000000000023
# BRICKLAYERS' spending for BIDEN, his id as filed (NEU-2277): before the handoff, on it, undated
# and after it.
SPENT_BEFORE_HANDOFF, SPENT_ON_HANDOFF, SPENT_UNDATED, SPENT_AFTER_HANDOFF = (
    4240200000000000025,
    4240200000000000026,
    4240200000000000027,
    4240200000000000028,
)
# Rows whose TRAN_ID names their line (NEU-2276): DONNELLY's 15 to the party on line 15 (SA15) and
# SEVERN STATE LEADERSHIP FUND's 10 to the super PAC on 11(c) (SA11C), both off line 11(a)(i);
# the presidential committee's gifts on Form 3P line 17(a) (SA17A), individuals' money.
PARTY_OFFSET, OTHER_COMMITTEE_GIFT = 4240100000000000121, 4240100000000000378
# DRISCOLL's second id for MD-05, an alias of the one holding his money (NEU-2127).
DRISCOLL, DRISCOLL_ALIAS = "H4MD05107", "H6MD05113"
CHECKS = Path(__file__).resolve().parents[2] / "sql" / "checks"


def put_bronze(
    store: R2, cycle: int = 2024, texts: Mapping[FecFile, str | bytes] | None = None
) -> None:
    """Every file of `cycle` in bronze: the fixture's, or the text `texts` gives for it."""
    texts = texts or {}
    for bulk in files_for(cycle):
        text = texts.get(bulk.name, fec_fixture.bulk_text(bulk.name))
        body = zipped(fec_fixture.MEMBERS[bulk.name], text)
        store.put(paths.bronze_zip(cycle, bulk.name, date(2026, 10, 30)), body)


def run(*args: str) -> Result:
    return CliRunner().invoke(cli.app, [*args, "--build-id", BUILD])


def seats_report(cycle: int = 2024) -> None:
    result = run("seats", "--cycle", str(cycle), "--report")
    assert result.exit_code == 0, result.output


def transform(cycle: int = 2024) -> Result:
    return run("transform", "--cycle", str(cycle))


def read_silver(
    store: R2, table: SilverTable, tmp_path: Path, cycle: int = 2024
) -> list[dict[str, object]]:
    """The rows of one uploaded silver partition, fetched back from MinIO."""
    key = f"{paths.silver_partition(table, cycle, BUILD)}/{paths.part(0)}"
    return parquet_rows(store.download_to(key, tmp_path / "fetched" / f"{table}.parquet"))


def parquet_rows(path: Path) -> list[dict[str, object]]:
    with duckdb.connect() as con:
        # The file's own columns: DuckDB would otherwise add `build` from a hive-style path.
        cursor = con.execute(f"SELECT * FROM read_parquet('{path}', hive_partitioning = false)")
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def local_silver(data_dir: Path, table: SilverTable, cycle: int = 2024) -> list[dict[str, object]]:
    """The rows of one silver partition, as the transform left it under `data_dir`."""
    key = f"{paths.silver_partition(table, cycle, BUILD)}/{paths.part(0)}"
    return parquet_rows(paths.local_path(data_dir, key))


@pytest.fixture(scope="module")
def fixture_silver(
    migrated_template: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Path]:
    """The fixture cycle transformed once for the module's tests that only read its silver
    (NEU-2267); the `DATA_DIR`. They read it there, not from MinIO: every test's `store` empties
    the bucket."""
    data_dir = tmp_path_factory.mktemp("transformed")
    with scratch_database(template=migrated_template) as conninfo:
        store = empty_store()
        try:
            with cli_pointed_at(conninfo=conninfo, data_dir=data_dir):
                put_bronze(store)
                seats_report()
                result = transform()
                assert result.exit_code == 0, result.output
        finally:
            store.delete_prefix("")
    yield data_dir


def uploaded_silver(store: R2) -> list[str]:
    """Every silver key but the `race` partition `seats` writes."""
    return [key for key in store.list_keys("silver/") if not key.startswith("silver/race/")]


def test_transform_writes_the_fixture_tables_and_the_marker(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    put_bronze(store)
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    expected = fec_fixture.expected()
    counts = {table: expected["silver"][table] for table in TABLES}
    marker = markers.read("transformed", store, cycle=2024, build_id=BUILD)
    assert marker is not None
    assert marker.row_counts == counts
    for table in TABLES:
        assert f"{table}: {counts[table]} rows" in result.output
        assert len(read_silver(store, table, tmp_path)) == counts[table]

    committees = read_silver(store, "committee", tmp_path)
    assert list(committees[0]) == [
        "cycle",
        "committee_id",
        "source",
        "jurisdiction",
        "name",
        "treasurer",
        "street",
        "city",
        "state",
        "zip",
        "designation",
        "type",
        "party",
        "filing_frequency",
        "org_type",
        "connected_org",
        "candidate_id",
        "is_conduit",
    ]
    conduits = {row["committee_id"] for row in committees if row["is_conduit"]}
    assert conduits == set(expected["contributions"]["earmarked"])
    assert {(row["source"], row["jurisdiction"], row["cycle"]) for row in committees} == {
        ("fec", "US", 2024)
    }

    candidates = read_silver(store, "candidate", tmp_path)
    assert list(candidates[0]) == [
        "cycle",
        "candidate_id",
        "source",
        "jurisdiction",
        "name",
        "party",
        "election_year",
        "office",
        "state",
        "district",
        "incumbent_challenger_open",
        "status",
        "principal_committee_id",
        "race_id",
        "alias_of",
    ]
    # An alias stands in the race of the candidate it is an alias of.
    assert {row["candidate_id"]: row["race_id"] for row in candidates} == {
        **{c: totals["race_id"] for c, totals in expected["candidates"].items()},
        **{alias: expected["candidates"][c]["race_id"] for alias, c in expected["aliases"].items()},
    }
    assert {
        row["candidate_id"]: row["alias_of"] for row in candidates if row["alias_of"] is not None
    } == expected["aliases"]

    links = read_silver(store, "candidate_committee_link", tmp_path)
    assert list(links[0]) == [
        "cycle",
        "candidate_id",
        "committee_id",
        "source",
        "jurisdiction",
        "committee_type",
        "designation",
        "linkage_id",
    ]
    # OKAFOR's principal and authorized committees.
    designations = {row["committee_id"]: row["designation"] for row in links}
    assert (designations["C00800103"], designations["C00800113"]) == ("P", "A")

    contributions = read_silver(store, "contribution", tmp_path)
    assert list(contributions[0]) == [
        "cycle",
        "source",
        "source_record_id",
        "jurisdiction",
        "contributor_name",
        "contributor_city",
        "contributor_state",
        "contributor_zip",
        "contributor_employer",
        "contributor_occupation",
        "contributor_key",
        "recipient_committee_id",
        "candidate_id",
        "amount",
        "date",
        "transaction_type",
        "entity_type",
        "report_type",
        "amendment_indicator",
        "memo_text",
        "conduit_committee_id",
        "is_self_funding",
        "is_non_contribution_account",
        "fec_line",
        "is_other_line",
        "image_num",
        "file_num",
    ]

    transfers = read_silver(store, "committee_transfer", tmp_path)
    assert list(transfers[0]) == [
        "cycle",
        "source",
        "source_record_id",
        "jurisdiction",
        "from_committee_id",
        "to_committee_id",
        "candidate_id",
        "amount",
        "date",
        "transaction_type",
        "side",
    ]

    # Spending for or against a candidate (NEU-2057): the super PAC's 24E for OKAFOR and 24A
    # against WHITLOCK, and the party's 24C, kept with its kind but no independent expenditure.
    spending = {
        row["source_record_id"]: row
        for row in read_silver(store, "independent_expenditure", tmp_path)
    }
    assert list(next(iter(spending.values()))) == [
        "cycle",
        "source",
        "source_record_id",
        "jurisdiction",
        "committee_id",
        "candidate_id",
        "race_id",
        "support_oppose",
        "amount",
        "date",
        "transaction_type",
        "kind",
    ]
    assert {
        sub_id: (
            row["committee_id"],
            row["candidate_id"],
            row["race_id"],
            row["support_oppose"],
            row["kind"],
        )
        for sub_id, row in spending.items()
        if sub_id in (4240200000000000001, 4240200000000000003, 4240200000000000009)
    } == {
        4240200000000000001: ("C00800201", "S4MD00103", "2024-S-MD-00", "S", "ie"),
        4240200000000000003: ("C00800201", "S4MD00104", "2024-S-MD-00", "O", "ie"),
        4240200000000000009: ("C00800203", "S4MD00104", "2024-S-MD-00", "S", "coordinated"),
    }
    # Spending is never money given: no 24K is here, and no expenditure is a contribution or a
    # committee transfer.
    assert {row["transaction_type"] for row in spending.values()} == {"24A", "24E", "24C"}
    assert not set(spending) & {row["source_record_id"] for row in transfers}
    assert not set(spending) & {row["source_record_id"] for row in contributions}

    contributors = read_silver(store, "contributor", tmp_path)
    assert list(contributors[0]) == [
        "contributor_key",
        "name_raw",
        "name_first",
        "name_last",
        "name_suffix",
        "zip5",
        "city",
        "state",
        "employer_raw",
        "employer_norm",
        "occupation_raw",
        "occupation_norm",
        "contribution_count",
        "amount_total",
        "attribution_count",
        "first_cycle",
        "last_cycle",
    ]

    receipts = read_silver(store, "organization_receipt", tmp_path)
    assert list(receipts[0]) == [
        "cycle",
        "source",
        "source_record_id",
        "jurisdiction",
        "organization_name",
        "organization_key",
        "city",
        "state",
        "zip",
        "recipient_committee_id",
        "amount",
        "date",
        "transaction_type",
        "entity_type",
        "report_type",
        "amendment_indicator",
        "memo_text",
        "image_num",
        "file_num",
        "classified",
        "is_non_contribution_account",
        "fec_line",
        "is_other_line",
    ]

    attributions = read_silver(store, "jfc_attribution", tmp_path)
    assert list(attributions[0]) == [
        "cycle",
        "source",
        "source_record_id",
        "jurisdiction",
        "contributor_name",
        "contributor_city",
        "contributor_state",
        "contributor_zip",
        "contributor_employer",
        "contributor_occupation",
        "contributor_key",
        "participant_committee_id",
        "jfc_committee_id",
        "candidate_id",
        "amount",
        "date",
    ]


def test_transform_logs_each_check_write_and_upload_after_the_last_model(
    store: R2, cli_env: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # A memory peak sampled after the last model starts is placed at one step by these lines'
    # timestamps (NEU-2077).
    put_bronze(store)
    seats_report()
    caplog.set_level(logging.INFO, logger="fundlens.transform")

    result = transform()

    assert result.exit_code == 0, result.output
    models = sorted((CHECKS.parent / "silver").glob("*.sql"))
    tables: list[SilverTable] = [cast(SilverTable, path.stem.partition("_")[2]) for path in models]
    logged = [record.getMessage() for record in caplog.records]
    last = logged.index(f"silver {tables[-1]} 2024: {models[-1].name}")
    steps = [m for m in logged[last + 1 :] if m.startswith(("silver check ", "write ", "upload "))]
    assert steps == [
        *(f"silver check {path.name}" for path in sorted(CHECKS.glob("silver_*.sql"))),
        *(f"write {table} 2024" for table in tables),
        *(
            f"upload {paths.silver_partition(table, 2024, BUILD)}/{paths.part(0)}"
            for table in tables
        ),
    ]


def sum_by(rows: list[dict[str, object]], key: str) -> dict[object, int]:
    """Whole-dollar amount totals of `rows` by `key`, rows without one left out."""
    totals: dict[object, int] = {}
    for row in rows:
        if row[key] is not None:
            totals[row[key]] = totals.get(row[key], 0) + int(cast(Decimal, row["amount"]))
    return totals


def test_contributions_count_each_earmark_once_and_add_up_to_the_expected_totals(
    fixture_silver: Path,
) -> None:
    rows = local_silver(fixture_silver, "contribution")
    expected = fec_fixture.expected()
    by_id = {row["source_record_id"]: row for row in rows}

    assert (
        sum(int(cast(Decimal, row["amount"])) for row in rows)
        == (expected["contributions"]["total_amount"])
    )
    # Each planted earmark is three rows: the conduit's 24T, the memo line and the counted row.
    donors = expected["donors"]
    for donor, conduit in (("earmark_actblue", ACTBLUE), ("earmark_winred", WINRED)):
        [counted] = donors[donor]["sub_ids"]
        assert {counted - 2, counted - 1, counted} & set(by_id) == {counted}
        assert by_id[counted]["conduit_committee_id"] == conduit
        assert by_id[counted]["amount"] == donors[donor]["amount"]
    reyes = by_id[donors["earmark_actblue"]["sub_ids"][0]]
    assert (reyes["recipient_committee_id"], reyes["candidate_id"]) == ("C00800103", "S4MD00103")
    earmarked = sum_by([row | {"amount": 1} for row in rows], "conduit_committee_id")
    assert earmarked == expected["contributions"]["earmarked"]
    # A conduit is a recipient only of gifts to itself (PARK's tip to ActBlue, and its refund),
    # with no conduit; ActBlue's own line for an earmark, filed as a 15, is dropped like its 24T
    # (NEU-2070), and so is a conduit's refund of an earmark (NEU-2199).
    to_conduits = [row for row in rows if row["recipient_committee_id"] in (ACTBLUE, WINRED)]
    assert sorted(
        (row["source_record_id"], row["amount"], row["conduit_committee_id"]) for row in to_conduits
    ) == [(PARK_TIP, 5, None), (PARK_TIP_REFUND, -5, None)]
    assert PARK_EARMARK_CONDUIT_SIDE not in by_id
    assert FAIRBANKS_EARMARK_REFUND not in by_id
    assert PARK_EARMARK_REFUND not in by_id

    individual = [
        row
        for row in rows
        if not row["is_self_funding"]
        and not row["is_non_contribution_account"]
        and not row["is_other_line"]
    ]
    self_funding = [row for row in rows if row["is_self_funding"]]
    assert len(self_funding) == expected["contributions"]["self_funding"]
    committees = expected["committees"]
    # ActBlue's tip and its refund net to 0, a total the expected committees leave out.
    received = {
        c: total for c, total in sum_by(individual, "recipient_committee_id").items() if total
    }
    assert received == {
        committee_id: totals["total_individual"]
        for committee_id, totals in committees.items()
        if totals["total_individual"]
    }
    assert sum_by(self_funding, "recipient_committee_id") == {
        committee_id: totals["self_funding"]
        for committee_id, totals in committees.items()
        if totals["self_funding"]
    }
    candidates = expected["candidates"]
    assert sum_by(individual, "candidate_id") == {
        candidate_id: totals["total_individual"]
        for candidate_id, totals in candidates.items()
        if totals["total_individual"]
    }
    assert sum_by(self_funding, "candidate_id") == {
        candidate_id: totals["self_funding"]
        for candidate_id, totals in candidates.items()
        if totals["self_funding"]
    }
    races = {
        row["candidate_id"]: row["race_id"] for row in local_silver(fixture_silver, "candidate")
    }
    race_totals = sum_by(
        [
            row | {"race_id": races[row["candidate_id"]]}
            for row in individual
            if row["candidate_id"]
        ],
        "race_id",
    )
    for race_id, totals in expected["races"].items():
        assert race_totals.get(race_id, 0) == totals["total_individual"], race_id


def test_a_candidates_own_money_is_self_funding_only_to_their_own_committee(
    fixture_silver: Path,
) -> None:
    by_id = {row["source_record_id"]: row for row in local_silver(fixture_silver, "contribution")}
    donors = fec_fixture.expected()["donors"]

    gift, loan, oth_loan, repayment = (by_id[sub_id] for sub_id in donors["self_funder"]["sub_ids"])
    assert (loan["transaction_type"], loan["amount"], loan["is_self_funding"]) == (
        "16C",
        1500000,
        True,
    )
    assert gift["is_self_funding"] and gift["conduit_committee_id"] is None
    # His loan and its partial repayment filed in `oth` (NEU-2071): self-funding, the repayment
    # subtracting, and his whatever giver id the row names (the repayment's is an old House id).
    assert [
        (
            row["transaction_type"],
            row["amount"],
            row["candidate_id"],
            row["is_self_funding"],
            row["conduit_committee_id"],
        )
        for row in (oth_loan, repayment)
    ] == [
        ("16C", 250000, "S4MD00104", True, None),
        ("20C", -100000, "S4MD00104", True, None),
    ]
    assert oth_loan["contributor_key"] == loan["contributor_key"]
    own, other = (by_id[sub_id] for sub_id in donors["candidate_as_donor"]["sub_ids"])
    # OKAFOR to her own committee, then to CALLOWAY's: an ordinary contribution from a candidate.
    assert (own["candidate_id"], own["is_self_funding"]) == ("S4MD00103", True)
    assert (other["candidate_id"], other["entity_type"], other["is_self_funding"]) == (
        "H4MD05106",
        "CAN",
        False,
    )
    refund = by_id[donors["partial_refund"]["sub_ids"][1]]
    assert (refund["amount"], refund["date"]) == (-1000, date(2024, 3, 1))


def test_a_blank_entity_type_is_an_individual_and_self_funding_is_never_an_earmark(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    indiv = fec_fixture.bulk_text("indiv") + (
        # A paper or pre-2002 filing leaves ENTITY_TP blank: still an individual's gift.
        "C00800105|N|Q2|P2024|1|15||DOE, JANE|TOWSON|MD|21204|ACME|CLERK|05012024|100|"
        "|SA.1|1|||4249999999999999991\n"
        # WHITLOCK under a fuller form of his cn name: still his own money.
        "C00800104|N|Q2|P2024|1|15C|CAN|WHITLOCK, GORDON R. MR|POTOMAC|MD|20854|"
        "WHITLOCK HOLDINGS|EXECUTIVE|05012024|1000||SA.2|1|||4249999999999999992\n"
        # WHITLOCK through his WinRed page: an earmark, so not self-funding.
        "C00800104|N|Q2|P2024|1|15E|CAN|WHITLOCK, GORDON|POTOMAC|MD|20854|WHITLOCK HOLDINGS|"
        "EXECUTIVE|05022024|500|C00694323|SA.3|1||EARMARKED THROUGH WINRED|4249999999999999993\n"
    )
    put_bronze(store, texts={"indiv": indiv})
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    by_id = {row["source_record_id"]: row for row in read_silver(store, "contribution", tmp_path)}
    blank, variant, earmarked = (by_id[4249999999999999990 + n] for n in (1, 2, 3))
    assert (blank["entity_type"], blank["candidate_id"], blank["is_self_funding"]) == (
        None,
        "S4MD00105",
        False,
    )
    assert variant["is_self_funding"]
    assert (earmarked["conduit_committee_id"], earmarked["is_self_funding"]) == (WINRED, False)


def test_a_15c_is_the_candidates_own_money_whatever_its_entity_type_name_or_route(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # 15C is FEC's "contribution from the candidate": the filer's line choice is the evidence, so
    # none of these is an individual's gift (NEU-2194).
    indiv = fec_fixture.bulk_text("indiv") + (
        # Typed IND under a variant name, as VIVEK 2024 and MARYOTT FOR CONGRESS file theirs.
        "C00800104|N|Q2|P2024|1|15C|IND|WHITLOCK - PERSONAL FUNDS, GORDON|POTOMAC|MD|20854|"
        "WHITLOCK HOLDINGS|EXECUTIVE|05012024|1000||SA.1|1|||4249999999999999971\n"
        # Typed CAN under a misspelled name ('TORRESS, JERRY').
        "C00800104|N|Q2|P2024|1|15C|CAN|WHITLOK, GORDON|POTOMAC|MD|20854|"
        "WHITLOCK HOLDINGS|EXECUTIVE|05022024|2000||SA.2|1|||4249999999999999972\n"
        # Through his WinRed page, still on line 11(d).
        "C00800104|N|Q2|P2024|1|15C|CAN|WHITLOCK, GORDON|POTOMAC|MD|20854|WHITLOCK HOLDINGS|"
        "EXECUTIVE|05032024|500|C00694323|SA.3|1||EARMARKED THROUGH WINRED|4249999999999999973\n"
        # At a committee raising for no candidate (COURAGEOUS LEADERS): the committee's
        # self_funding, no candidate's.
        "C00800201|N|Q2|P2024|1|15C|IND|ASHWORTH, NINA|BALTIMORE|MD|21202|"
        "SELF|EXECUTIVE|05042024|3000||SA.4|1|||4249999999999999974\n"
    )
    put_bronze(store, texts={"indiv": indiv})
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    by_id = {row["source_record_id"]: row for row in read_silver(store, "contribution", tmp_path)}
    typed_ind, misspelled, earmarked, unlinked = (
        by_id[4249999999999999970 + n] for n in (1, 2, 3, 4)
    )
    assert typed_ind["is_self_funding"] and misspelled["is_self_funding"]
    assert (earmarked["conduit_committee_id"], earmarked["is_self_funding"]) == (WINRED, True)
    assert (unlinked["candidate_id"], unlinked["is_self_funding"]) == (None, True)


def test_a_file_mixing_encodings_is_read_whole(store: R2, cli_env: Path, tmp_path: Path) -> None:
    # The names as filers sent them: UTF-8, a Windows-1252 apostrophe, and a byte Windows-1252
    # leaves undefined. DuckDB's own latin-1 reader refused all three (NEU-2069).
    names = [b"SOLAGES, CARRI\xc3\x89", b"O\x92BRIEN, PAT", b"X\x81Y, ZED"]
    indiv = fec_fixture.bulk_text("indiv").encode() + b"".join(
        b"C00800105|N|Q2|P2024|1|15|IND|" + name + b"|TOWSON|MD|21204|ACME|CLERK|05012024|100|"
        b"|SA.%d|1|||424999999999999998%d\n" % (n, n)
        for n, name in enumerate(names, start=1)
    )
    put_bronze(store, texts={"indiv": indiv})
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    by_id = {row["source_record_id"]: row for row in read_silver(store, "contribution", tmp_path)}
    assert [by_id[4249999999999999980 + n]["contributor_name"] for n in (1, 2, 3)] == [
        "SOLAGES, CARRIÉ",
        "O’BRIEN, PAT",
        "X\x81Y, ZED",
    ]


def test_a_refund_subtracts_whichever_sign_its_filer_wrote_and_a_void_adds_back(
    fixture_silver: Path,
) -> None:
    # The fixture's OSEI and LINDQVIST rows (NEU-2073): a gift and its refund written negative;
    # a gift, its refund written positive, and the refund check voided by a mirroring negative.
    by_id = {row["source_record_id"]: row for row in local_silver(fixture_silver, "contribution")}
    osei, osei_refund, lindqvist, lindqvist_refund, lindqvist_void = (
        by_id[4240100000000000300 + n]["amount"] for n in (4, 5, 6, 7, 8)
    )
    assert (osei, osei_refund) == (300, -300)
    assert (lindqvist, lindqvist_refund, lindqvist_void) == (500, -200, 200)


def test_a_void_reverses_one_refund_and_a_second_negative_refund_subtracts(
    fixture_silver: Path,
) -> None:
    # The fixture's BRANDVOLD rows (NEU-2269): a gift, a refund written positive, its void, and a
    # second refund of the same size written negative. Both negatives mirror the one refund; only
    # the first, by date, voids it.
    by_id = {row["source_record_id"]: row for row in local_silver(fixture_silver, "contribution")}
    amounts = tuple(by_id[4240100000000000350 + n]["amount"] for n in (1, 2, 3, 4))
    assert amounts == (1000, -400, 400, -400)


def test_a_gift_to_a_committee_missing_from_the_committee_file_is_dropped(
    fixture_silver: Path,
) -> None:
    # The fixture's NORRIS row: a few fringe filers report gifts to a committee FEC's `cm` lacks,
    # which would belong to no committee (NEU-2070).
    rows = local_silver(fixture_silver, "contribution")
    assert NORRIS_UNKNOWN_RECIPIENT not in {row["source_record_id"] for row in rows}
    assert "C00899999" not in {row["recipient_committee_id"] for row in rows}


def test_a_filing_a_later_amendment_supersedes_counts_nowhere(fixture_silver: Path) -> None:
    # The fixture's super PAC filings (NEU-2196): a Q2 report whose 30S amendment restates both of
    # its gifts, CARVALHO's and TIDEWATER MARINE SUPPLY's, so the Q2 rows count nowhere; and a Q3
    # report a later YE amendment repeats a third of, ESPINOZA's gift, so both of hers count.
    contributions = {
        row["source_record_id"] for row in local_silver(fixture_silver, "contribution")
    }
    receipts = {
        row["source_record_id"] for row in local_silver(fixture_silver, "organization_receipt")
    }
    superseded, restated = {4240100000000000357, 4240100000000000358}, {4240100000000000359}
    assert superseded.isdisjoint(contributions | receipts)
    assert restated <= contributions and 4240100000000000360 in receipts
    assert {4240100000000000362, 4240100000000000365} <= contributions


def test_a_memo_line_counts_only_when_it_is_the_only_record_of_a_gift(
    fixture_silver: Path,
) -> None:
    # The super PAC's filing 1900215 (NEU-2198): THORVALDSEN's and IKEDA's shares of a partnership's
    # gift whose row the filing lacks, and ROSENKRANTZ's trust attribution, count as contributions,
    # and MAGOTHY HOLDINGS LLC's own memo line as an organization receipt. SEVERN CAPITAL's partners
    # attribute its row ($1,998 against $2,000, written in whole dollars), MAGOTHY's partners its
    # memo line, MBEKI's line restates her counted gift and PELLEGRINO's is no attribution: none
    # counts anywhere.
    contributions = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "contribution")
    }
    receipts = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "organization_receipt")
    }
    transfers = {
        row["source_record_id"] for row in local_silver(fixture_silver, "committee_transfer")
    }
    orphaned = {4240100000000000366, 4240100000000000367, 4240100000000000372}
    assert orphaned <= contributions.keys()
    assert [contributions[s]["amount"] for s in sorted(orphaned)] == [5000, 5000, 2500]
    assert receipts[4240100000000000375]["organization_name"] == "MAGOTHY HOLDINGS LLC"
    assert 4240100000000000368 in receipts
    dropped = {
        4240100000000000369,
        4240100000000000370,
        4240100000000000371,
        4240100000000000373,
        4240100000000000374,
        4240100000000000376,
        4240100000000000377,
    }
    assert dropped.isdisjoint(contributions.keys() | receipts.keys() | transfers)


def key_of(row: Mapping[str, object]) -> str:
    """A silver contribution's contributor key as resolve.normalize builds it."""

    def reported(column: str) -> str | None:
        return cast(str | None, row[f"contributor_{column}"])

    return normalize.contributor_key(
        normalize.normalize_name(reported("name")).norm,
        normalize.zip5(reported("zip")),
        normalize.normalize_employer(reported("employer")),
        normalize.normalize_occupation(reported("occupation")),
    )


def test_contributions_reduce_to_contributor_keys_spelled_as_the_normalizers_spell_them(
    fixture_silver: Path,
) -> None:
    contributions = local_silver(fixture_silver, "contribution")
    contributors = {
        row["contributor_key"]: row for row in local_silver(fixture_silver, "contributor")
    }
    attributions = local_silver(fixture_silver, "jfc_attribution")
    assert all(row["contributor_key"] == key_of(row) for row in [*contributions, *attributions])
    assert {row["contributor_key"] for row in [*contributions, *attributions]} == (
        contributors.keys()
    )
    assert sum(cast(int, c["contribution_count"]) for c in contributors.values()) == len(
        contributions
    )
    assert sum(cast(int, c["attribution_count"]) for c in contributors.values()) == len(
        attributions
    )
    assert sum(cast(Decimal, c["amount_total"]) for c in contributors.values()) == sum(
        cast(Decimal, row["amount"]) for row in contributions
    )

    by_id = {row["source_record_id"]: row for row in contributions}
    musk = [by_id[sub_id] for sub_id in fec_fixture.expected()["donors"]["musk_case"]["sub_ids"]]
    # 'MARLOWE, AUGUSTINE' written again as 'MARLOWE,AUGUSTINE JR.': one key. The other variants
    # differ by more than punctuation and suffix, and are linkage's to group.
    assert [row["contributor_name"] for row in (by_id[MUSK], by_id[MUSK_AGAIN])] == [
        "MARLOWE, AUGUSTINE",
        "MARLOWE,AUGUSTINE JR.",
    ]
    assert by_id[MUSK]["contributor_key"] == by_id[MUSK_AGAIN]["contributor_key"]
    assert len({row["contributor_key"] for row in musk}) == 4
    assert contributors[by_id[MUSK]["contributor_key"]] == {
        "contributor_key": "MARLOWE, AUGUSTINE|90250|ASTRAX|CEO",
        # Both spellings report one contribution of 3300: the first in order is the key's.
        "name_raw": "MARLOWE, AUGUSTINE",
        "name_first": "AUGUSTINE",
        "name_last": "MARLOWE",
        "name_suffix": None,
        "zip5": "90250",
        "city": "HAWTHORNE",
        "state": "CA",
        "employer_raw": "ASTRAX",
        "employer_norm": "ASTRAX",
        "occupation_raw": "CEO",
        "occupation_norm": "CEO",
        "contribution_count": 2,
        "amount_total": 6600,
        "attribution_count": 0,
        "first_cycle": 2024,
        "last_cycle": 2024,
    }
    # DUBOIS's employer written two ways, one an alias of the other: one key.
    dubois = fec_fixture.expected()["donors"]["employer_variant"]["sub_ids"]
    assert {by_id[sub_id]["contributor_key"] for sub_id in dubois} == {
        "DUBOIS, RAYMOND|20850|ASTRAX|ENGINEER"
    }


def test_the_race_check_fails_until_the_bad_district_is_an_unmatched_filing(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    put_bronze(store)

    # No `seats --report` yet: app.unmatched_filing does not hold the filing.
    failed = transform()

    assert isinstance(failed.exception, ChecksFailed)
    assert "silver_candidate_race.sql" in str(failed.exception)
    assert BAD in str(failed.exception)
    assert uploaded_silver(store) == []
    assert not markers.exists("transformed", store, cycle=2024, build_id=BUILD)

    seats_report()
    result = transform()

    assert result.exit_code == 0, result.output
    fenwick = [
        row for row in read_silver(store, "candidate", tmp_path) if row["candidate_id"] == BAD
    ]
    assert fenwick == [fenwick[0] | {"district": "09", "race_id": None}]


def test_a_duplicated_committee_aborts_the_run_before_any_upload(store: R2, cli_env: Path) -> None:
    cm = fec_fixture.bulk_text("cm")
    put_bronze(store, texts={"cm": cm + cm.splitlines(keepends=True)[2]})
    seats_report()

    result = transform()

    assert isinstance(result.exception, ChecksFailed)
    assert "silver_committee_key.sql" in str(result.exception)
    # The other checks pass: only the duplicate is reported.
    assert "silver_candidate_race.sql" not in str(result.exception)
    assert uploaded_silver(store) == []
    assert not markers.exists("transformed", store, cycle=2024, build_id=BUILD)
    assert not (cli_env / "silver" / "committee").exists()


def test_a_zip_is_read_by_its_member_name_not_as_its_only_file(store: R2, cli_env: Path) -> None:
    put_bronze(store)
    # FEC's `indiv` zip holds the same rows twice, the second time split by date under
    # `by_date/`. Read as well, a copy like this would trip the committee key check.
    cm = fec_fixture.bulk_text("cm")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("cm.txt", cm)
        archive.writestr("by_date/cm_2024.txt", cm)
    store.put(paths.bronze_zip(2024, "cm", date(2026, 10, 31)), buffer.getvalue())
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    assert f"committee: {fec_fixture.expected()['silver']['committee']} rows" in result.output


def test_a_filing_for_a_seat_with_a_special_beside_it_joins_the_regular_race(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # Nebraska elects a regular class 1 senator and fills its class 2 seat in 2024.
    nebraska = "S4NE00120|DOE, JANE|DEM|2024|NE|S|00|C|C||1 MAIN ST||OMAHA|NE|68102\n"
    put_bronze(store, texts={"cn": fec_fixture.bulk_text("cn") + nebraska})
    seats_report()

    assert transform().exit_code == 0
    races = {
        row["candidate_id"]: row["race_id"] for row in read_silver(store, "candidate", tmp_path)
    }
    assert races["S4NE00120"] == "2024-S-NE-00"


def test_a_filing_for_a_lone_special_joins_it_and_a_later_cycles_filing_joins_nothing(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # Ohio's 2026 Senate race is only the special: neither of its classes is up.
    cn = (
        "S6OH00130|ROE, SAM|REP|2026|OH|S|00|C|C||1 HIGH ST||COLUMBUS|OH|43215\n"
        # Registered in the 2026 file for the 2028 race: it stands in no 2026 race, and the
        # race check leaves it alone.
        "S8MD00140|LOE, KIM|DEM|2028|MD|S|00|C|C||2 HIGH ST||BALTIMORE|MD|21201\n"
    )
    put_bronze(
        store, 2026, texts={"cm": "", "cn": cn, "ccl": "", "indiv": "", "pas2": "", "oth": ""}
    )

    result = transform(2026)

    assert result.exit_code == 0, result.output
    candidates = read_silver(store, "candidate", tmp_path, cycle=2026)
    assert {row["candidate_id"]: row["race_id"] for row in candidates} == {
        "S6OH00130": "2026-S-OH-00-special",
        "S8MD00140": None,
    }


def test_a_pair_linked_for_two_elections_keeps_this_cycles_link(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    later = "P40000101|2028|2024|C00800101|P|P|124000000099\n"
    put_bronze(store, texts={"ccl": fec_fixture.bulk_text("ccl") + later})
    seats_report()

    assert transform().exit_code == 0
    links = read_silver(store, "candidate_committee_link", tmp_path)
    assert len(links) == fec_fixture.expected()["silver"]["candidate_committee_link"]
    hargrove = [row["linkage_id"] for row in links if row["candidate_id"] == "P40000101"]
    assert hargrove == [124000000001]


def test_a_handed_off_committees_money_is_split_between_its_candidates_by_date(
    fixture_silver: Path,
) -> None:
    contributions = {
        row["source_record_id"]: row
        for row in local_silver(fixture_silver, "contribution")
        if row["recipient_committee_id"] == HANDED_OFF
    }
    transfers = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "committee_transfer")
    }

    # Before the handoff date the committee's money is BIDEN's; on and after it, HARRIS's, and a
    # gift with no date is HARRIS's, the committee's holder now. `ccl` links it to both, and the
    # lower candidate_id alone, HARRIS's, would take it all.
    assert {sub_id: row["candidate_id"] for sub_id, row in contributions.items()} == {
        **dict.fromkeys(BEFORE_HANDOFF, BIDEN),
        **dict.fromkeys(FROM_HANDOFF, HARRIS),
        UNDATED: HARRIS,
    }
    assert contributions[FROM_HANDOFF[0]]["date"] == date(2024, 7, 21)
    assert contributions[UNDATED]["date"] is None
    # One row each still: the dated links never overlap.
    assert len(contributions) == len(BEFORE_HANDOFF) + len(FROM_HANDOFF) + 1
    # A committee's gift before the date is BIDEN's on both its sides.
    assert (
        transfers[HANDOFF_GIFT]["candidate_id"],
        transfers[HANDOFF_RECEIPT]["candidate_id"],
    ) == (
        BIDEN,
        BIDEN,
    )


def test_spending_naming_a_handed_off_candidate_is_split_between_its_candidates_by_date(
    fixture_silver: Path,
) -> None:
    spending = {
        row["source_record_id"]: (row["candidate_id"], row["race_id"], row["support_oppose"])
        for row in local_silver(fixture_silver, "independent_expenditure")
    }

    # Filed for BIDEN all four: his before the handoff, HARRIS's on its date, after it and undated,
    # as the committee's own money is. Its side stays as filed.
    assert [
        spending[s]
        for s in (SPENT_BEFORE_HANDOFF, SPENT_ON_HANDOFF, SPENT_AFTER_HANDOFF, SPENT_UNDATED)
    ] == [
        (BIDEN, "2024-P-US-00", "S"),
        (HARRIS, "2024-P-US-00", "S"),
        (HARRIS, "2024-P-US-00", "S"),
        (HARRIS, "2024-P-US-00", "S"),
    ]


def test_the_handoff_expenditure_check_fails_on_spending_left_with_the_candidate_handed_from() -> (
    None
):
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE handoff AS SELECT"
            f" '{HANDED_OFF}' AS committee_id, '{BIDEN}' AS from_candidate_id,"
            f" '{HARRIS}' AS to_candidate_id, DATE '2024-07-21' AS handoff_date"
        )
        # Right: 1 BIDEN's before the date, 2 and 3 HARRIS's on it and undated. Wrong: 4 BIDEN's on
        # the date, 5 after it, 6 undated.
        con.execute(
            "CREATE TABLE independent_expenditure AS SELECT * FROM (VALUES"
            f" (1, '{BIDEN}', DATE '2024-07-20'),"
            f" (2, '{HARRIS}', DATE '2024-07-21'),"
            f" (3, '{HARRIS}', CAST(NULL AS DATE)),"
            f" (4, '{BIDEN}', DATE '2024-07-21'),"
            f" (5, '{BIDEN}', DATE '2024-10-01'),"
            f" (6, '{BIDEN}', CAST(NULL AS DATE))"
            ") AS t(source_record_id, candidate_id, date)"
        )

        failed = failing_rows(con, "silver_independent_expenditure_handoff.sql")
        assert sorted(str(row[0]) for row in failed) == ["4", "5", "6"]


def test_a_handoff_whose_committee_is_not_linked_to_both_candidates_aborts_the_run(
    store: R2, cli_env: Path
) -> None:
    # `ccl` without HARRIS's link: the vendored handoff names a link the cycle does not have.
    ccl = "".join(
        line
        for line in fec_fixture.bulk_text("ccl").splitlines(keepends=True)
        if not line.startswith(f"{HARRIS}|")
    )
    put_bronze(store, texts={"ccl": ccl})
    seats_report()

    result = transform()

    assert isinstance(result.exception, ChecksFailed)
    assert "silver_handoff_linked.sql" in str(result.exception)
    assert f"('{HANDED_OFF}', '{HARRIS}')" in str(result.exception)
    assert uploaded_silver(store) == []
    assert not markers.exists("transformed", store, cycle=2024, build_id=BUILD)


def test_a_second_id_of_one_person_is_an_alias_only_in_the_same_race_under_the_same_name(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    alias = fec_fixture.bulk_text("cn").splitlines()[-1]
    assert alias.startswith(f"{DRISCOLL_ALIAS}|")
    cn = (
        fec_fixture.bulk_text("cn")
        # The same person filing for MD-04, a race he is not in: no alias.
        + alias.replace(DRISCOLL_ALIAS, "H6MD04114").replace("|MD|H|05|", "|MD|H|04|")
        + "\n"
        # Another person of the same last name, in the same race: no alias.
        + alias.replace(DRISCOLL_ALIAS, "H6MD05115").replace("PETER J.", "PAULA")
        + "\n"
    )
    ccl = (
        fec_fixture.bulk_text("ccl")
        + "H6MD04114|2024|2024|C00800107|H|P|124000000097\n"
        + "H6MD05115|2024|2024|C00800107|H|P|124000000098\n"
    )
    put_bronze(store, texts={"cn": cn, "ccl": ccl})
    seats_report()

    assert transform().exit_code == 0
    aliases = {
        row["candidate_id"]: row["alias_of"]
        for row in read_silver(store, "candidate", tmp_path)
        if row["alias_of"] is not None
    }
    assert aliases == {DRISCOLL_ALIAS: DRISCOLL}


def test_an_id_credited_a_committee_by_either_crediting_rule_is_no_alias(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # DRISCOLL's committee linked principal to an id `cn` lacks, lower than his: contribution's
    # rule credits it that id, committee_transfer's (a candidate of the cycle only) still DRISCOLL.
    # And DRISCOLL under a third, lower id, linked with him to the leadership PAC, which credits it.
    # DRISCOLL holds that committee's transfers, so is no alias of his lower id.
    cn = fec_fixture.bulk_text("cn") + (
        "H2MD05100|DRISCOLL, PETER|REP|2024|MD|H|05|C|C|C00800114|99 OAK LN||LA PLATA|MD|20646\n"
    )
    ccl = fec_fixture.bulk_text("ccl") + (
        "H0MD05001|2024|2024|C00800107|H|P|124000000096\n"
        "H2MD05100|2024|2024|C00800114|H|P|124000000097\n"
        f"{DRISCOLL}|2024|2024|C00800114|H|P|124000000098\n"
    )
    put_bronze(store, texts={"cn": cn, "ccl": ccl})
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    aliases = {
        row["candidate_id"]: row["alias_of"]
        for row in read_silver(store, "candidate", tmp_path)
        if row["alias_of"] is not None
    }
    assert aliases == {DRISCOLL_ALIAS: DRISCOLL}


def test_a_gift_naming_an_alias_is_credited_to_the_id_it_is_an_alias_of(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # The fixture's 24K to the super PAC, which raises for no candidate, with the giver writing
    # DRISCOLL's alias as CAND_ID: it stands, as the id holding his money.
    [line] = [
        line
        for line in fec_fixture.bulk_text("pas2").splitlines()
        if line.endswith(f"|{NO_CANDIDATE_GIFT}")
    ]
    fields = line.split("|")
    fields[16], fields[21] = DRISCOLL_ALIAS, "4240200000000000099"
    # And an independent expenditure against him naming the alias (NEU-2057), with a memo line
    # restating it, which is no expenditure.
    spending = [*fields]
    spending[5], spending[21] = "24A", "4240200000000000098"
    memo = [*spending]
    memo[19], memo[21] = "X", "4240200000000000097"
    rows = "".join("|".join(row) + "\n" for row in (fields, spending, memo))
    put_bronze(store, texts={"pas2": fec_fixture.bulk_text("pas2") + rows})
    seats_report()

    assert transform().exit_code == 0
    gifts = {
        row["source_record_id"]: row["candidate_id"]
        for row in read_silver(store, "committee_transfer", tmp_path)
    }
    assert gifts[4240200000000000099] == DRISCOLL
    expenditures = {
        row["source_record_id"]: (row["candidate_id"], row["race_id"], row["support_oppose"])
        for row in read_silver(store, "independent_expenditure", tmp_path)
    }
    assert expenditures[4240200000000000098] == (DRISCOLL, "2024-H-MD-05", "O")
    assert 4240200000000000097 not in expenditures


def failing_rows(con: duckdb.DuckDBPyConnection, check: str) -> list[tuple[object, ...]]:
    # Rendered as the build renders it, so a regex quantifier is written `{{8}}` in both.
    return con.execute(render(CHECKS / check, {})).fetchall()


def test_the_alias_checks_fail_on_an_alias_with_money_and_on_an_alias_of_an_alias() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE candidate AS SELECT * FROM (VALUES"
            f" ('{DRISCOLL}', CAST(NULL AS VARCHAR)),"
            f" ('{DRISCOLL_ALIAS}', '{DRISCOLL}'),"
            f" ('H8MD05116', '{DRISCOLL_ALIAS}')"
            ") AS t(candidate_id, alias_of)"
        )
        con.execute(
            "CREATE TABLE contribution AS SELECT * FROM (VALUES"
            f" (1, '{DRISCOLL}'), (2, '{DRISCOLL_ALIAS}'), (3, '{DRISCOLL_ALIAS}')"
            ") AS t(source_record_id, candidate_id)"
        )
        con.execute(
            "CREATE TABLE committee_transfer AS SELECT * FROM (VALUES"
            f" (4, '{DRISCOLL}'), (5, 'H8MD05116')"
            ") AS t(source_record_id, candidate_id)"
        )

        assert sorted(failing_rows(con, "silver_candidate_alias_no_money.sql")) == [
            ("committee_transfer", "H8MD05116", 1),
            ("contribution", DRISCOLL_ALIAS, 2),
        ]
        assert failing_rows(con, "silver_candidate_alias_canonical.sql") == [
            ("H8MD05116", DRISCOLL_ALIAS)
        ]


def test_the_expenditure_checks_fail_on_a_misattached_row_or_one_counted_as_money() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE candidate AS SELECT * FROM (VALUES"
            f" ('{DRISCOLL}', CAST(NULL AS VARCHAR), '2024-H-MD-05'),"
            f" ('{DRISCOLL_ALIAS}', '{DRISCOLL}', '2024-H-MD-05')"
            ") AS t(candidate_id, alias_of, race_id)"
        )
        # Right: 1 attached, 2 attached to no one. Wrong: 3 an alias, 4 a race not its
        # candidate's, 5 a race and no candidate, 6 a 24C called an ie, 7 a 24A called support.
        con.execute(
            "CREATE TABLE independent_expenditure AS SELECT * FROM (VALUES"
            f" (1, '{DRISCOLL}', '2024-H-MD-05', '24A', 'ie', 'O'),"
            " (2, NULL, NULL, '24E', 'ie', 'S'),"
            f" (3, '{DRISCOLL_ALIAS}', '2024-H-MD-05', '24E', 'ie', 'S'),"
            f" (4, '{DRISCOLL}', '2024-S-MD-00', '24E', 'ie', 'S'),"
            " (5, NULL, '2024-H-MD-05', '24E', 'ie', 'S'),"
            f" (6, '{DRISCOLL}', '2024-H-MD-05', '24C', 'ie', 'S'),"
            f" (7, '{DRISCOLL}', '2024-H-MD-05', '24A', 'ie', 'S')"
            ") AS t(source_record_id, candidate_id, race_id, transaction_type, kind,"
            " support_oppose)"
        )
        con.execute(
            "CREATE TABLE contribution AS SELECT * FROM (VALUES (1, '15'), (8, '24E'))"
            " AS t(source_record_id, transaction_type)"
        )
        con.execute("CREATE TABLE committee_transfer AS SELECT 2 AS source_record_id")
        con.execute("CREATE TABLE organization_receipt AS SELECT 9 AS source_record_id")

        failed = failing_rows(con, "silver_independent_expenditure_candidate.sql")
        assert sorted(str(row[0]) for row in failed) == ["3", "4", "5", "6", "7"]
        assert sorted(failing_rows(con, "silver_independent_expenditure_not_money.sql")) == [
            (1, "contribution"),
            (2, "committee_transfer"),
            (8, "contribution typed 24E"),
        ]


def test_the_superseded_filing_check_fails_on_a_counted_row_of_one() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE TABLE superseded_filing AS SELECT 1001 AS FILE_NUM")
        # Filing 1001's rows: a contribution, an organization receipt and a committee's gift; and a
        # row of filing 1002, which nothing supersedes.
        con.execute(
            "CREATE TABLE indiv AS SELECT * FROM"
            " (VALUES (1, 1001), (2, 1001), (3, 1001), (4, 1002)) AS t(SUB_ID, FILE_NUM)"
        )
        con.execute(
            "CREATE TABLE contribution AS SELECT * FROM (VALUES (1), (4)) AS t(source_record_id)"
        )
        con.execute("CREATE TABLE organization_receipt AS SELECT 2 AS source_record_id")
        con.execute("CREATE TABLE committee_transfer AS SELECT 3 AS source_record_id")

        assert sorted(failing_rows(con, "silver_superseded_filing.sql")) == [
            ("committee_transfer", 3, 1001),
            ("contribution", 1, 1001),
            ("organization_receipt", 2, 1001),
        ]


def test_the_memo_check_fails_on_a_counted_memo_line_other_than_an_orphaned_attribution() -> None:
    with duckdb.connect() as con:
        # Memo lines 1 to 3, counted as a contribution, an organization receipt and a committee's
        # gift; 4, an orphaned attribution (NEU-2198), counted; and 5, not a memo line.
        con.execute(
            "CREATE TABLE indiv AS SELECT * FROM (VALUES (1, 'C1', 10, 'X'), (2, 'C1', 20, 'X'),"
            " (3, 'C1', 30, 'X'), (4, 'C1', 40, 'X'), (5, 'C1', 50, NULL))"
            " AS t(SUB_ID, CMTE_ID, TRANSACTION_AMT, MEMO_CD)"
        )
        # In `oth`, a candidate's loan memo line 6, counted, and loan 7, not a memo line (NEU-2071).
        con.execute(
            "CREATE TABLE oth AS SELECT * FROM (VALUES (6, 'C2', 60, 'X', '16C'),"
            " (7, 'C2', 70, NULL, '16C'))"
            " AS t(SUB_ID, CMTE_ID, TRANSACTION_AMT, MEMO_CD, TRANSACTION_TP)"
        )
        con.execute("CREATE TABLE orphaned_attribution AS SELECT 4 AS SUB_ID")
        con.execute(
            "CREATE TABLE contribution AS"
            " SELECT * FROM (VALUES (1), (4), (5), (6), (7)) AS t(source_record_id)"
        )
        con.execute("CREATE TABLE organization_receipt AS SELECT 2 AS source_record_id")
        con.execute("CREATE TABLE committee_transfer AS SELECT 3 AS source_record_id")

        assert sorted(failing_rows(con, "silver_contribution_no_memo.sql")) == [
            ("committee_transfer", 3, "C1", 30),
            ("contribution", 1, "C1", 10),
            ("contribution", 6, "C2", 60),
            ("organization_receipt", 2, "C1", 20),
        ]


def test_the_self_funding_checks_fail_on_an_unflagged_15c_and_an_earmark_of_another_type() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE contribution AS SELECT * FROM (VALUES"
            " (1, 'C1', '15C', 'IND', 'DOE, JANE', CAST(NULL AS VARCHAR), false),"
            f" (2, 'C1', '15C', 'CAN', 'DOE, JANE', '{WINRED}', true),"
            f" (3, 'C1', '15E', 'CAN', 'DOE, JANE', '{WINRED}', true),"
            " (4, 'C1', '15', 'CAN', 'DOE, JANE', NULL, true),"
            # A candidate's loan and its repayment (NEU-2071).
            " (5, 'C1', '16C', 'CCM', 'DOE FOR CONGRESS', NULL, false),"
            " (6, 'C1', '20C', 'CAN', 'DOE, JANE', NULL, false),"
            " (7, 'C1', '16C', 'IND', 'DOE, JANE', NULL, true)"
            ") AS t(source_record_id, recipient_committee_id, transaction_type, entity_type,"
            " contributor_name, conduit_committee_id, is_self_funding)"
        )

        assert failing_rows(con, "silver_contribution_15c_self_funding.sql") == [
            (1, "C1", "IND", "DOE, JANE"),
            (5, "C1", "CCM", "DOE FOR CONGRESS"),
            (6, "C1", "CAN", "DOE, JANE"),
        ]
        assert failing_rows(con, "silver_contribution_self_funding.sql") == [(3, "C1", WINRED)]


def test_the_organization_receipt_key_check_fails_on_a_repeated_or_missing_key() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE organization_receipt AS SELECT * FROM (VALUES"
            " (2024, 'fec', 1), (2024, 'fec', 1), (2024, 'fec', NULL), (2024, 'fec', 2)"
            ") AS t(cycle, source, source_record_id)"
        )

        assert sorted(
            failing_rows(con, "silver_organization_receipt_key.sql"), key=lambda r: str(r[2])
        ) == [(2024, "fec", 1, 2), (2024, "fec", None, 1)]


def test_the_organization_receipt_recipient_check_fails_on_a_committee_cm_lacks() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE TABLE committee AS SELECT * FROM (VALUES ('C1')) AS t(committee_id)")
        con.execute(
            "CREATE TABLE organization_receipt AS SELECT * FROM (VALUES"
            " (1, 'C1', 100), (2, 'C9', 200)"
            ") AS t(source_record_id, recipient_committee_id, amount)"
        )

        assert failing_rows(con, "silver_organization_receipt_recipient.sql") == [(2, "C9", 200)]


def test_the_organization_receipt_disjoint_check_fails_on_a_row_another_table_holds() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE organization_receipt AS SELECT * FROM (VALUES (1), (2), (3))"
            " AS t(source_record_id)"
        )
        con.execute(
            "CREATE TABLE contribution AS SELECT * FROM (VALUES (2), (4)) AS t(source_record_id)"
        )
        con.execute(
            "CREATE TABLE committee_transfer AS SELECT * FROM (VALUES (3), (5))"
            " AS t(source_record_id)"
        )

        assert sorted(failing_rows(con, "silver_organization_receipt_disjoint.sql")) == [
            (2, "contribution"),
            (3, "committee_transfer"),
        ]


def test_the_organization_receipt_classified_check_fails_on_a_flag_its_type_contradicts() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE organization_receipt AS SELECT * FROM (VALUES"
            " (1, 'ORG', false), (2, NULL, true), (3, '', true), (4, 'ORG', true), (5, NULL, false)"
            ") AS t(source_record_id, entity_type, classified)"
        )

        assert sorted(failing_rows(con, "silver_organization_receipt_classified.sql")) == [
            (4, "ORG", True),
            (5, None, False),
        ]


def test_the_name_match_twin_check_fails_on_a_receipt_oth_holds_under_the_givers_id() -> None:
    with duckdb.connect() as con:
        # Receipt 1 is an `indiv` row named by name, receipt 7 an `oth` row with a blank OTHER_ID:
        # `oth` holds each gift from the giver's id too (rows 9 and 8). Receipt 9 carries the id
        # on its own row, receipt 3's only twin is a memo line, and receipt 5 is from a JFC named
        # by NAME (NEU-2124's rule, with no twin rule): none of those fails.
        con.execute(
            "CREATE TABLE committee AS SELECT * FROM (VALUES ('C1', 'P'), ('C2', 'U'), ('C3', 'J')"
            ") AS t(committee_id, designation)"
        )
        con.execute(
            "CREATE TABLE committee_transfer AS SELECT * FROM (VALUES"
            " (1, 'C2', 'C1', 100, DATE '2024-01-15', 'receipt'),"
            " (7, 'C2', 'C1', 300, DATE '2024-02-15', 'receipt'),"
            " (9, 'C2', 'C1', 100, DATE '2024-01-15', 'receipt'),"
            " (3, 'C2', 'C1', 500, DATE '2024-03-15', 'receipt'),"
            " (5, 'C3', 'C1', 700, DATE '2024-04-15', 'receipt'),"
            " (4, 'C1', 'C2', 100, DATE '2024-01-15', 'disbursement')"
            ") AS t(source_record_id, from_committee_id, to_committee_id, amount, date, side)"
        )
        con.execute(
            "CREATE TABLE oth AS SELECT * FROM (VALUES"
            " (9, 'C1', 'C2', 100, '01152024', '18K', NULL),"
            " (7, 'C1', '', 300, '02152024', '18K', NULL),"
            " (8, 'C1', 'C2', 300, '02152024', '18K', NULL),"
            " (6, 'C1', 'C2', 500, '03152024', '18K', 'X'),"
            " (5, 'C1', '', 700, '04152024', '18G', NULL),"
            " (2, 'C1', 'C3', 700, '04152024', '18G', NULL)"
            ") AS t(SUB_ID, CMTE_ID, OTHER_ID, TRANSACTION_AMT, TRANSACTION_DT, TRANSACTION_TP,"
            " MEMO_CD)"
        )

        assert sorted(failing_rows(con, "silver_committee_transfer_name_match_twin.sql")) == [
            (1, "C2", "C1", 100, 9),
            (7, "C2", "C1", 300, 8),
        ]


def test_transform_without_bronze_says_to_extract(store: R2, cli_env: Path) -> None:
    result = transform()

    assert result.exit_code == 1
    assert "fundlens extract --cycle 2024" in result.output
    assert not markers.exists("transformed", store, cycle=2024, build_id=BUILD)


def test_an_odd_cycle_is_a_usage_error(store: R2, cli_env: Path) -> None:
    assert transform(2025).exit_code == 2


def test_committee_transfers_hold_each_side_once_and_add_up_to_the_expected_totals(
    fixture_silver: Path,
) -> None:
    rows = local_silver(fixture_silver, "committee_transfer")
    expected = fec_fixture.expected()
    receipts = [row for row in rows if row["side"] == "receipt"]
    disbursements = [row for row in rows if row["side"] == "disbursement"]

    # Every `oth` receipt from a committee is a receipt, and the `indiv` rows a committee's by
    # name (NEU-2131), RESTORATION PAC's ORG-typed one among them (NEU-2195); every 24K `pas2` row
    # a disbursement; nothing else is here. `oth`'s repeat
    # of a pas2 24K and 24A, its 15J memo line, the 16C candidate loan and the union's gift are
    # none of those (NEU-2070); the 31K party-account receipt is one.
    receipt_ids = {row["source_record_id"] for row in receipts}
    assert receipt_ids & OTH_NOT_RECEIPTS == set()
    assert OTH_PARTY_ACCOUNT_RECEIPT in receipt_ids
    assert len(receipts) == expected["rows"]["oth"] - len(OTH_NOT_RECEIPTS) + 2
    assert len(disbursements) == len(rows) - len(receipts)
    assert len(rows) == expected["silver"]["committee_transfer"]
    assert {row["transaction_type"] for row in disbursements} == {"24K"}
    # A conduit's 24K is its side of an earmark, an individual's money (ADR-0004): WinRed's two
    # to DRISCOLL are no committee's gift.
    assert {row["from_committee_id"] for row in disbursements} & {ACTBLUE, WINRED} == set()
    # A receipt's candidate is the one its recipient raises for, by contribution's rule, and none
    # when its recipient raises for no one: the super PAC and the state party (NEU-2124).
    assert {(row["to_committee_id"], row["candidate_id"]) for row in receipts} == {
        ("C00800101", "P40000101"),
        (HANDED_OFF, BIDEN),
        ("C00800103", "S4MD00103"),
        ("C00800104", "S4MD00104"),
        ("C00800106", "H4MD05106"),
        ("C00800107", "H4MD05107"),
        ("C00800109", "H4MD09109"),
        ("C00800201", None),
        ("C00800203", None),
    }
    # A gift is credited to the candidate its recipient is linked to, whatever CAND_ID the giver
    # wrote, and to none when its recipient raises for no candidate of the cycle (NEU-2075).
    by_sub_id = {row["source_record_id"]: row for row in disbursements}
    assert by_sub_id[STALE_CAND_ID_GIFT]["candidate_id"] == "S4MD00104"
    assert [r["source_record_id"] for r in disbursements if r["candidate_id"] is None] == [
        NO_CANDIDATE_GIFT
    ]
    assert {(row["source"], row["jurisdiction"], row["cycle"]) for row in rows} == {
        ("fec", "US", 2024)
    }
    # BRICKLAYERS' gift to OKAFOR: the giver's 24K and the recipient's 18K, one row each.
    by_id = {row["source_record_id"]: row for row in rows}
    given, received = by_id[4240200000000000010], by_id[4240300000000000004]
    assert (given["from_committee_id"], given["to_committee_id"], given["candidate_id"]) == (
        "C00800202",
        "C00800103",
        "S4MD00103",
    )
    assert (
        received["from_committee_id"],
        received["to_committee_id"],
        received["candidate_id"],
    ) == ("C00800202", "C00800103", "S4MD00103")
    assert (given["amount"], received["amount"], given["date"]) == (5000, 5000, date(2024, 4, 10))

    # One side each (expected.yaml's rule): receipts by recipient, disbursements by giver and
    # by candidate.
    committees = expected["committees"]
    assert sum_by(receipts, "to_committee_id") == {
        committee_id: totals["total_from_committees"]
        for committee_id, totals in committees.items()
        if totals["total_from_committees"]
    }
    # A pair of giver and candidate netting below 0 (NEU-2204) is kept here, and gold sets it
    # apart: the void of CALLOWAY's 2022 gift is in its giver's total_returned_by_candidates.
    returned = expected["returned_by_candidates"]
    assert set(returned["disbursements"]) <= set(by_sub_id)
    credited = [row for row in disbursements if row["candidate_id"] is not None]
    gifts = [row for row in credited if row["source_record_id"] not in returned["disbursements"]]
    assert sum_by(gifts, "from_committee_id") == {
        committee_id: totals["total_to_candidates"]
        for committee_id, totals in committees.items()
        if totals["total_to_candidates"]
    }
    assert {
        committee_id: total - committees[str(committee_id)]["total_to_candidates"]
        for committee_id, total in sum_by(credited, "from_committee_id").items()
        if total != committees[str(committee_id)]["total_to_candidates"]
    } == returned["by_committee"]
    candidates = expected["candidates"]
    assert sum_by(gifts, "candidate_id") == {
        candidate_id: totals["total_committee"]
        for candidate_id, totals in candidates.items()
        if totals["total_committee"]
    }
    # A JFC's transfer is a receipt, whatever its type, credited to the candidate its recipient
    # raises for.
    jfc_transfers = [row for row in receipts if row["from_committee_id"] == JFC]
    assert {row["transaction_type"] for row in jfc_transfers} == {"18G", "18J", "15J"}
    assert sum_by(jfc_transfers, "candidate_id") == {
        candidate_id: totals["total_jfc_transfers"]
        for candidate_id, totals in candidates.items()
        if totals["total_jfc_transfers"]
    }


def test_organization_receipts_are_organizations_gifts_grouped_by_name_and_feed_no_total(
    fixture_silver: Path,
) -> None:
    expected = fec_fixture.expected()
    rows = local_silver(fixture_silver, "organization_receipt")
    by_id = {row["source_record_id"]: row for row in rows}

    # Every ORG row of either file that counts, and nothing else: the 15J line of an
    # organization (NOT_ATTRIBUTIONS) is evidence, not a receipt.
    assert by_id.keys() == {int(sub_id) for sub_id in expected["organization_receipts"]["keys"]}
    assert len(rows) == expected["silver"]["organization_receipt"]
    assert {sub_id: row["organization_key"] for sub_id, row in by_id.items()} == {
        int(sub_id): key for sub_id, key in expected["organization_receipts"]["keys"].items()
    }
    assert sum_by(rows, "organization_key") == expected["organization_receipts"]["by_key"]
    assert (
        sum_by(rows, "recipient_committee_id")
        == (expected["organization_receipts"]["by_committee"])
    )
    # Two spellings, a legal form and its punctuation apart, are one key; the refund, written
    # positive, subtracts.
    assert [by_id[sub_id]["organization_name"] for sub_id in (CHESAPEAKE, CHESAPEAKE_AGAIN)] == [
        "CHESAPEAKE STEEL, INC.",
        "CHESAPEAKE STEEL INC",
    ]
    assert (by_id[CHESAPEAKE_REFUND]["amount"], by_id[CHESAPEAKE_REFUND]["date"]) == (
        -2500,
        date(2024, 5, 1),
    )
    # The union's gift is read from `oth`, with its party-account type.
    union = by_id[UNION_RECEIPT]
    assert (union["recipient_committee_id"], union["transaction_type"], union["amount"]) == (
        PARTY,
        "31K",
        4000,
    )
    # Every receipt is typed ORG but the one filed with no type, which the classifier put here.
    assert (
        {sub_id for sub_id, row in by_id.items() if row["classified"]}
        == {ACME_WIDGETS}
        == {int(sub_id) for sub_id in expected["organization_receipts"]["classified"]}
    )
    assert {row["entity_type"] for row in rows if not row["classified"]} == {"ORG"}
    assert by_id[ACME_WIDGETS]["entity_type"] is None
    assert {(row["source"], row["jurisdiction"], row["cycle"]) for row in rows} == {
        ("fec", "US", 2024)
    }
    # No contribution, no transfer and no contributor reads them (ADR-0011).
    contributions = local_silver(fixture_silver, "contribution")
    assert {row["source_record_id"] for row in contributions}.isdisjoint(by_id)
    assert len(contributions) == expected["silver"]["contribution"]
    transfers = local_silver(fixture_silver, "committee_transfer")
    assert {row["source_record_id"] for row in transfers}.isdisjoint(by_id)
    contributors = local_silver(fixture_silver, "contributor")
    assert len(contributors) == expected["silver"]["contributor"]
    assert "CHESAPEAKE STEEL" not in {row["employer_norm"] for row in contributors}


def test_a_hybrid_pacs_type_10_rows_are_kept_and_marked_non_contribution_account_money(
    fixture_silver: Path,
) -> None:
    expected = fec_fixture.expected()["non_contribution_account"]
    contributions = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "contribution")
    }
    receipts = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "organization_receipt")
    }

    # Only the hybrid PAC's 10s, and its 20Y refund, are marked: its 15 is the contribution
    # account, and a 10 to the super PAC is line 11(a)(i) money.
    assert {s for s, row in contributions.items() if row["is_non_contribution_account"]} == set(
        expected["contributions"]
    )
    assert {s for s, row in receipts.items() if row["is_non_contribution_account"]} == set(
        expected["organization_receipts"]
    )
    # A refund is typed by account, whoever its giver gave: a 20Y the non-contribution account's,
    # a 22Y the contribution account's.
    assert [
        (
            contributions[s]["transaction_type"],
            contributions[s]["amount"],
            contributions[s]["is_non_contribution_account"],
        )
        for s in (MARKED_REFUND, UNMARKED_REFUND)
    ] == [("20Y", -5000, True), ("22Y", -250, False)]
    assert [
        (contributions[s]["recipient_committee_id"], contributions[s]["transaction_type"])
        for s in (CONTRIBUTION_ACCOUNT, NON_CONTRIBUTION_ACCOUNT, SUPER_PAC_TYPE_10)
    ] == [(HYBRID_PAC, "15"), (HYBRID_PAC, "10"), (SUPER_PAC, "10")]
    assert not contributions[CONTRIBUTION_ACCOUNT]["is_non_contribution_account"]
    assert not contributions[SUPER_PAC_TYPE_10]["is_non_contribution_account"]
    # The account's money is still the donor's: a contributor key, no candidate.
    assert contributions[NON_CONTRIBUTION_ACCOUNT]["candidate_id"] is None
    assert (
        contributions[NON_CONTRIBUTION_ACCOUNT]["contributor_key"]
        == (contributions[CONTRIBUTION_ACCOUNT]["contributor_key"])
    )
    assert (receipts[PATAPSCO]["recipient_committee_id"], receipts[PATAPSCO]["amount"]) == (
        HYBRID_PAC,
        250000,
    )


def test_rows_off_line_11ai_are_kept_with_their_line_and_marked(fixture_silver: Path) -> None:
    contributions = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "contribution")
    }

    assert {
        s for s, row in contributions.items() if row["is_other_line"] and not row["is_self_funding"]
    } == set(fec_fixture.expected()["other_lines"]["contributions"])
    # The candidate's own loans, in `indiv` and in `oth` (NEU-2071), are on line 13 too, and stay
    # self-funding (gold's self_funding).
    loans = [row for row in contributions.values() if row["transaction_type"] == "16C"]
    assert [(row["fec_line"], row["is_other_line"], row["is_self_funding"]) for row in loans] == [
        ("13 loans", True, True)
    ] * 2
    # The party account's refund goes with its receipt; the loan stays the candidate's committee's.
    assert [
        (
            contributions[s]["transaction_type"],
            contributions[s]["amount"],
            contributions[s]["fec_line"],
            contributions[s]["candidate_id"],
        )
        for s in (HEADQUARTERS_ACCOUNT, HEADQUARTERS_REFUND, INDIVIDUAL_LOAN)
    ] == [
        ("31", 10000, "party account 31", None),
        ("41Y", -2500, "party account 31", None),
        ("16G", 1000, "13 loans", "S4MD00104"),
    ]
    # Line 11(a)(i) money and its refunds are unmarked, as is the non-contribution account, which
    # has its own flag.
    assert contributions[CONTRIBUTION_ACCOUNT]["fec_line"] == "11(a)(i)"
    assert contributions[UNMARKED_REFUND]["fec_line"] == "20 refunds"
    assert contributions[NON_CONTRIBUTION_ACCOUNT]["fec_line"] == "non-contribution account"
    assert not any(
        contributions[s]["is_other_line"]
        for s in (CONTRIBUTION_ACCOUNT, UNMARKED_REFUND, NON_CONTRIBUTION_ACCOUNT)
    )

    # An organization's gift to a party account is marked by the same rule, from either file
    # (NEU-2205); its 15 to the same party is line 11(a)(i) money, unmarked.
    receipts = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "organization_receipt")
    }
    assert {s for s, row in receipts.items() if row["is_other_line"]} == set(
        fec_fixture.expected()["other_lines"]["organization_receipts"]
    )
    assert [
        (
            receipts[s]["recipient_committee_id"],
            receipts[s]["transaction_type"],
            receipts[s]["fec_line"],
            receipts[s]["is_other_line"],
        )
        for s in (TRIBE_ACCOUNT, RECOUNT_RECEIPT, UNION_RECEIPT, PARTY_PILOTS)
    ] == [
        (PARTY, "31T", "party account 31", True),
        (PARTY, "32J", "party account 32", True),
        (PARTY, "31K", "party account 31", True),
        (PARTY, "15", "11(a)(i)", False),
    ]
    assert (receipts[PATAPSCO]["fec_line"], receipts[PATAPSCO]["is_other_line"]) == (
        "non-contribution account",
        False,
    )

    # A line the filer's TRAN_ID names (NEU-2276), in either table; Form 3P's 17(a) is not one.
    assert (
        contributions[PARTY_OFFSET]["transaction_type"],
        contributions[PARTY_OFFSET]["fec_line"],
        contributions[PARTY_OFFSET]["is_other_line"],
    ) == ("15", "15 other receipts", True)
    assert (
        receipts[OTHER_COMMITTEE_GIFT]["recipient_committee_id"],
        receipts[OTHER_COMMITTEE_GIFT]["transaction_type"],
        receipts[OTHER_COMMITTEE_GIFT]["fec_line"],
        receipts[OTHER_COMMITTEE_GIFT]["is_other_line"],
    ) == (SUPER_PAC, "10", "11(c) other committees", True)
    assert {
        (contributions[s]["fec_line"], contributions[s]["is_other_line"])
        for s in (*BEFORE_HANDOFF, *FROM_HANDOFF, UNDATED)
    } == {("11(a)(i)", False)}


def test_an_intermediarys_24i_its_recipient_itemized_is_dropped_and_any_other_24i_counts(
    fixture_silver: Path,
) -> None:
    contributions = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "contribution")
    }

    # The intermediary's side is in no table; the recipient's own row of the gift counts, OKAFOR's.
    assert INTERMEDIARY_24I not in contributions
    for table in ("committee_transfer", "organization_receipt"):
        assert INTERMEDIARY_24I not in {
            row["source_record_id"] for row in local_silver(fixture_silver, table)
        }
    assert [
        (
            contributions[s]["transaction_type"],
            contributions[s]["recipient_committee_id"],
            contributions[s]["candidate_id"],
            contributions[s]["amount"],
            contributions[s]["conduit_committee_id"],
            contributions[s]["fec_line"],
            contributions[s]["is_other_line"],
            contributions[s]["is_non_contribution_account"],
        )
        for s in (
            INTERMEDIARY_TWIN,
            INTERMEDIARY_ONLY,
            RECIPIENT_24I,
            HYBRID_PAC_24I,
            HYBRID_PAC_CONTRIBUTION_24I,
        )
    ] == [
        ("15E", "C00800103", "S4MD00103", 1000, None, "11(a)(i)", False, False),
        # The only record of the gift, the intermediary's.
        ("24I", BRICKLAYERS, None, 500, None, "11(a)(i)", False, False),
        # Filers' own receipts of an earmark, coded 24I: line 11(a)(i), or a hybrid PAC's
        # non-contribution account when its memo names the account, as its 10s are (NEU-2207).
        ("24I", SUPER_PAC, None, 250, ACTBLUE, "11(a)(i)", False, False),
        ("24I", HYBRID_PAC, None, 1000, ACTBLUE, "non-contribution account", False, True),
        ("24I", HYBRID_PAC, None, 500, ACTBLUE, "11(a)(i)", False, False),
    ]


def test_the_conduit_side_check_fails_on_a_24t_a_24i_and_a_refund_of_an_earmark() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE committee AS SELECT * FROM (VALUES ('C1', false), ('C2', false),"
            " ('C3', false), ('A1', true)) AS t(committee_id, is_conduit)"
        )
        con.execute(
            "CREATE TABLE indiv AS SELECT * FROM (VALUES"
            " (1, 'C2', 'C1', 'ADAMS, ANN', 100, '24I', NULL, NULL),"
            " (2, 'C2', 'C1', 'BAKER, BO', 100, '24I', NULL, NULL),"
            " (3, 'C2', 'C1', 'COLE, CY', 100, '24I', NULL, NULL),"
            " (4, 'A1', 'C1', 'ADAMS, ANN', 100, '24I', NULL, NULL),"
            " (5, 'C1', 'C1', 'ADAMS, ANN', 100, '24I', NULL, NULL),"
            " (6, 'C3', 'C1', 'ADAMS, ANN', 100, '24I', NULL, NULL),"
            " (7, 'C2', 'C1', 'DOYLE, DI', 100, '24T', NULL, NULL),"
            # The conduit A1's own gifts: ADAMS's tip, and an organization's, no contribution; and
            # its own line for EVANS's earmark to C2, which is none.
            " (15, NULL, 'A1', 'ADAMS, ANN', 100, '15', NULL, 'CONTRIBUTION TO A1'),"
            " (16, NULL, 'A1', 'FIRM LLC', 75, '15', NULL, NULL),"
            " (17, NULL, 'A1', 'EVANS, EVE', 100, '15', NULL, 'EARMARKED FOR C2 (C00000002)')"
            ") AS t(SUB_ID, OTHER_ID, CMTE_ID, NAME, TRANSACTION_AMT, TRANSACTION_TP, MEMO_CD,"
            " MEMO_TEXT)"
        )
        con.execute(
            "CREATE TABLE contribution AS SELECT * FROM (VALUES"
            # 24Is at C1 passing gifts on: to C2, which itemized ADAMS (10 days on) and BAKER (40
            # days on); through a conduit; to itself; to C3, which itemized none.
            " (1, 'C1', 'ADAMS, ANN', 100, DATE '2024-03-01', '24I'),"
            " (2, 'C1', 'BAKER, BO', 100, DATE '2024-03-01', '24I'),"
            " (3, 'C1', 'COLE, CY', 100, DATE '2024-03-01', '24I'),"
            " (4, 'C1', 'ADAMS, ANN', 100, DATE '2024-03-01', '24I'),"
            " (5, 'C1', 'ADAMS, ANN', 100, DATE '2024-03-01', '24I'),"
            " (6, 'C1', 'ADAMS, ANN', 100, DATE '2024-03-01', '24I'),"
            " (7, 'C1', 'DOYLE, DI', 100, DATE '2024-03-01', '24T'),"
            # C2's rows of ADAMS's gift and BAKER's, and a 22Y to COLE counted positive, as a
            # voided refund is (NEU-2073). ADAMS's gifts to C1 and to the conduit A1: the twins of
            # the 24Is naming them, were those an intermediary's.
            " (11, 'C2', 'ADAMS ANN', 100, DATE '2024-03-11', '15E'),"
            " (12, 'C2', 'BAKER, BO', 100, DATE '2024-04-10', '15E'),"
            " (13, 'C2', 'COLE, CY', 100, DATE '2024-03-02', '22Y'),"
            " (14, 'C1', 'ADAMS, ANN', 100, DATE '2024-03-02', '15'),"
            " (15, 'A1', 'ADAMS, ANN', 100, DATE '2024-03-02', '15'),"
            # Refunds at the conduit A1 (NEU-2199): of ADAMS's own gift there, of 50 she gave
            # nothing of there, to EVANS, whose only row there is her earmark's, and of the
            # organization's gift, which a refund mirrors whoever gave it; and EVANS's at C2.
            " (21, 'A1', 'ADAMS ANN', -100, DATE '2024-03-09', '22Y'),"
            " (22, 'A1', 'ADAMS, ANN', -50, DATE '2024-03-09', '22Y'),"
            " (23, 'A1', 'EVANS, EVE', -100, DATE '2024-03-09', '22Y'),"
            " (24, 'C2', 'EVANS, EVE', -100, DATE '2024-03-09', '22Y'),"
            " (25, 'A1', 'FIRM LLC', 75, DATE '2024-03-09', '22Y')"
            ") AS t(source_record_id, recipient_committee_id, contributor_name, amount, date,"
            " transaction_type)"
        )

        # The 24T, ADAMS's 24I to C2, whose row there is a twin though its name lacks the comma,
        # and the conduit's two refunds that mirror no gift of its own.
        assert sorted(failing_rows(con, "silver_contribution_no_conduit_side.sql")) == [
            ("22Y", 22, "A1", -50, None),
            ("22Y", 23, "A1", -100, None),
            ("24I", 1, "C1", 100, 11),
            ("24T", 7, "C1", 100, None),
        ]


def test_the_non_contribution_account_check_fails_on_a_flag_its_type_contradicts() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE committee AS SELECT * FROM (VALUES ('C1', 'V'), ('C2', 'W'), ('C3', 'O'))"
            " AS t(committee_id, type)"
        )
        con.execute(
            "CREATE TABLE contribution AS SELECT * FROM (VALUES"
            " (1, 'C1', '10', NULL, true), (2, 'C1', '15', NULL, false),"
            " (3, 'C2', '10J', NULL, false), (4, 'C3', '10', NULL, true),"
            " (5, 'C3', '10', NULL, false), (9, 'C1', '20Y', NULL, true),"
            " (10, 'C1', '20Y', NULL, false), (11, 'C1', '22Y', NULL, false),"
            " (12, 'C1', '22Y', NULL, true), (13, 'C3', '20Y', NULL, false),"
            " (15, 'C2', '24I', '* NON-CONTRIBUTION ACCOUNT', true),"
            " (16, 'C1', '24I', '* NON-CONTRIBUTION ACCOUNT', false),"
            " (17, 'C2', '24I', 'EARMARKED', false), (18, 'C1', '24I', NULL, true),"
            " (19, 'C3', '24I', '* NON-CONTRIBUTION ACCOUNT', false)"
            ") AS t(source_record_id, recipient_committee_id, transaction_type, memo_text,"
            " is_non_contribution_account)"
        )
        con.execute(
            "CREATE TABLE organization_receipt AS SELECT * FROM (VALUES"
            " (6, 'C2', '10', NULL, true), (7, 'C2', '10', NULL, false),"
            " (8, 'C1', '22Y', NULL, true), (14, 'C2', '20Y', NULL, true)"
            ") AS t(source_record_id, recipient_committee_id, transaction_type, memo_text,"
            " is_non_contribution_account)"
        )

        # An unmarked 10J to a W, a marked 10 to a super PAC, an unmarked 20Y and a marked 22Y at
        # a V, an unmarked 24I under the account's memo and a marked one without it (NEU-2207);
        # an unmarked 10 to a W, and a marked 22Y at a V.
        assert sorted(failing_rows(con, "silver_non_contribution_account.sql")) == [
            ("contribution", 3, "10J", "W", False),
            ("contribution", 4, "10", "O", True),
            ("contribution", 10, "20Y", "V", False),
            ("contribution", 12, "22Y", "V", True),
            ("contribution", 16, "24I", "V", False),
            ("contribution", 18, "24I", "V", True),
            ("organization_receipt", 7, "10", "W", False),
            ("organization_receipt", 8, "22Y", "V", True),
        ]


def test_a_pac_typed_gift_with_no_id_is_a_receipt_from_the_one_committee_its_name_names(
    fixture_silver: Path,
) -> None:
    expected = fec_fixture.expected()
    transfers = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "committee_transfer")
    }

    # BRICKLAYERS' gift to the super PAC, filed in `indiv` under its name alone, is a receipt from
    # BRICKLAYERS, kept as filed, to no candidate: the super PAC raises for none.
    named = transfers[NAMED_GIFT]
    assert (
        named["from_committee_id"],
        named["to_committee_id"],
        named["candidate_id"],
        named["amount"],
        named["date"],
        named["transaction_type"],
        named["side"],
    ) == (BRICKLAYERS, SUPER_PAC, None, 15000, date(2024, 9, 20), "15", "receipt")
    # `oth`'s 18K from BRICKLAYERS with OTHER_ID blank, to OKAFOR, is one too, credited to her.
    assert (
        transfers[OTH_NAMED_GIFT]["from_committee_id"],
        transfers[OTH_NAMED_GIFT]["candidate_id"],
    ) == (BRICKLAYERS, "S4MD00103")
    # A row naming no committee, or its own recipient, is in no table.
    everywhere = {
        row["source_record_id"]
        for table in ("contribution", "committee_transfer", "organization_receipt")
        for row in local_silver(fixture_silver, cast(SilverTable, table))
    }
    assert {NAMES_NONE, NAMES_SELF}.isdisjoint(everywhere)
    assert {NAMED_GIFT, OTH_NAMED_GIFT} <= everywhere
    assert {
        sub_id: transfers[sub_id]["from_committee_id"] if sub_id in transfers else None
        for sub_id in (NAMED_GIFT, NAMES_NONE, NAMES_SELF, OLD_LINE_BLANK, RESTORATION)
    } == {int(sub_id): c for sub_id, c in expected["name_matched"].items()}
    receipts = [row for row in transfers.values() if row["side"] == "receipt"]
    assert (
        sum_by(receipts, "to_committee_id")[SUPER_PAC]
        == (expected["committees"][SUPER_PAC]["total_from_committees"])
    )


def test_an_org_typed_gift_naming_a_political_committee_is_that_committees_receipt(
    fixture_silver: Path,
) -> None:
    transfers = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "committee_transfer")
    }
    receipts = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "organization_receipt")
    }

    # The super PAC typed RESTORATION PAC's gift ORG, with no OTHER_ID: its NAME names one super
    # PAC, so it is a receipt from it, kept as filed, and no organization receipt (NEU-2195). A
    # Form 9 filer shares the name, but it is no political committee, so it names no second one.
    restoration = transfers[RESTORATION]
    assert (
        restoration["from_committee_id"],
        restoration["to_committee_id"],
        restoration["candidate_id"],
        restoration["amount"],
        restoration["date"],
        restoration["side"],
    ) == (RESTORATION_PAC, SUPER_PAC, None, 90000, date(2024, 9, 5), "receipt")
    assert RESTORATION not in receipts
    # ONE NATION's NAME names a Form 5 filer (type I), no political committee: an organization's
    # gift still, on line 11(a)(i).
    assert ONE_NATION not in transfers
    one_nation = receipts[ONE_NATION]
    assert (
        one_nation["organization_key"],
        one_nation["recipient_committee_id"],
        one_nation["amount"],
        one_nation["fec_line"],
    ) == ("ONE NATION", SUPER_PAC, 40000, "11(a)(i)")


def test_a_blank_entity_type_the_classifier_calls_an_organization_is_no_contribution(
    fixture_silver: Path,
) -> None:
    expected = fec_fixture.expected()
    contributions = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "contribution")
    }
    transfers = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "committee_transfer")
    }
    receipts = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "organization_receipt")
    }

    # ACME WIDGETS INC is an organization receipt, classified, and no contribution or contributor.
    assert ACME_WIDGETS not in contributions and ACME_WIDGETS not in transfers
    assert (receipts[ACME_WIDGETS]["organization_key"], receipts[ACME_WIDGETS]["classified"]) == (
        "ACME WIDGETS",
        True,
    )
    contributors = local_silver(fixture_silver, "contributor")
    assert not any(row["name_raw"] == "ACME WIDGETS INC" for row in contributors)
    # BANKS, JOHN is an individual's contribution, as a blank type was before the classifier.
    banks = contributions[BANKS]
    assert (banks["entity_type"], banks["candidate_id"], banks["contributor_key"]) == (
        None,
        BAD,
        "BANKS, JOHN|21209|BANKS HARDWARE|OWNER",
    )
    assert any(row["contributor_key"] == banks["contributor_key"] for row in contributors)
    # OLD LINE REPUBLICAN COMMITTEE names one committee: a receipt from it, as a PAC-typed row is.
    old_line = transfers[OLD_LINE_BLANK]
    assert (
        old_line["from_committee_id"],
        old_line["to_committee_id"],
        old_line["candidate_id"],
        old_line["amount"],
        old_line["side"],
    ) == (PARTY, DRISCOLL_COMMITTEE, DRISCOLL, 2000, "receipt")
    assert OLD_LINE_BLANK not in contributions and OLD_LINE_BLANK not in receipts
    # The organization's 15J line is in no table.
    attributions = local_silver(fixture_silver, "jfc_attribution")
    assert CLASSIFIED_LINE not in {row["source_record_id"] for row in attributions}
    assert len(attributions) == expected["silver"]["jfc_attribution"]


def test_a_classified_gift_oth_holds_under_the_named_committees_id_is_read_once(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # DRISCOLL's committee also files OLD LINE REPUBLICAN COMMITTEE's blank-type gift as an 18K
    # with the party's id: the `indiv` row is its twin, in neither committee_transfer nor
    # organization_receipt, so the gift is counted once.
    oth = fec_fixture.bulk_text("oth") + (
        f"{DRISCOLL_COMMITTEE}|N|Q3|G2024|1|18K|PTY|OLD LINE REPUBLICAN COMMITTEE|ANNAPOLIS|MD|"
        f"21401|||09102024|2000|{PARTY}|SA12.00497|1900107|||4249999999999999962\n"
    )
    put_bronze(store, texts={"oth": oth})
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    transfers = {
        row["source_record_id"]: row for row in read_silver(store, "committee_transfer", tmp_path)
    }
    assert OLD_LINE_BLANK not in transfers
    assert transfers[4249999999999999962]["from_committee_id"] == PARTY
    receipts = {
        row["source_record_id"] for row in read_silver(store, "organization_receipt", tmp_path)
    }
    assert OLD_LINE_BLANK not in receipts
    contributions = {
        row["source_record_id"] for row in read_silver(store, "contribution", tmp_path)
    }
    assert OLD_LINE_BLANK not in contributions


def test_a_name_matched_gift_oth_holds_under_the_givers_id_is_read_once(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # The super PAC also files BRICKLAYERS' gift as an 18K with BRICKLAYERS' id: the `indiv` row is
    # its twin and is dropped, so the gift is counted once, from the row that names its giver.
    oth = fec_fixture.bulk_text("oth") + (
        f"{SUPER_PAC}|N|Q3|G2024|1|18K|PAC|BRICKLAYERS UNITED PAC|WASHINGTON|DC|20005|||09202024|"
        f"15000|{BRICKLAYERS}|SA12.00499|1900201|||4249999999999999960\n"
    )
    put_bronze(store, texts={"oth": oth})
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    transfers = {
        row["source_record_id"]: row for row in read_silver(store, "committee_transfer", tmp_path)
    }
    assert NAMED_GIFT not in transfers
    assert transfers[4249999999999999960]["from_committee_id"] == BRICKLAYERS
    receipts = [row for row in transfers.values() if row["side"] == "receipt"]
    assert (
        sum_by(receipts, "to_committee_id")[SUPER_PAC]
        == (fec_fixture.expected()["committees"][SUPER_PAC]["total_from_committees"])
    )


def test_an_oth_receipt_mirroring_a_counted_indiv_row_is_read_once_from_indiv(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # The super PAC files CHESAPEAKE STEEL's first gift in `oth` too, as an 18U under another
    # SUB_ID: the same recipient, name, amount and date, so it is the `indiv` row's mirror.
    oth = fec_fixture.bulk_text("oth") + (
        f"{SUPER_PAC}|N|Q2|P2024|1|18U|ORG|CHESAPEAKE STEEL, INC.|SPARROWS POINT|MD|21219|||"
        "04152024|50000||SA12.00498|1900201|||4249999999999999961\n"
    )
    put_bronze(store, texts={"oth": oth})
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    rows = read_silver(store, "organization_receipt", tmp_path)
    by_id = {row["source_record_id"]: row for row in rows}
    assert 4249999999999999961 not in by_id
    assert CHESAPEAKE in by_id
    assert len(rows) == fec_fixture.expected()["silver"]["organization_receipt"]


def test_a_candidates_loan_in_oth_mirroring_one_in_indiv_is_read_once_from_indiv(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # WHITLOCK FOR SENATE files his `indiv` 16C in `oth` too, under another SUB_ID and giver id:
    # the same committee, type, amount and date, so it is the same loan (NEU-2071).
    oth = fec_fixture.bulk_text("oth") + (
        "C00800104|N|Q1|P2024|1|16C|CAN|WHITLOCK, GORDON|POTOMAC|MD|20854|||"
        "01052024|1500000|S4MD00104|SA13.00498|1900104|||4249999999999999962\n"
    )
    put_bronze(store, texts={"oth": oth})
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    rows = read_silver(store, "contribution", tmp_path)
    by_id = {row["source_record_id"]: row for row in rows}
    assert 4249999999999999962 not in by_id
    assert by_id[4240100000000000022]["transaction_type"] == "16C"
    assert len(rows) == fec_fixture.expected()["silver"]["contribution"]


def test_an_organizations_loan_and_attribution_line_are_no_receipts(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # A bank's 16F loan and its 16G repayment, a 16C and a 15J typed ORG, and an ORG row whose
    # OTHER_ID names a committee `cm` lacks (a committee's money, in committee_transfer as today).
    # A 16C is a candidate's loan whatever its entity type: a self-funding contribution (NEU-2071).
    lines = [
        ("16F", "CHESAPEAKE BANK", "", "4249999999999999951"),
        ("16G", "CHESAPEAKE BANK", "", "4249999999999999952"),
        ("16C", "CHESAPEAKE BANK", "", "4249999999999999953"),
        ("15J", "CHESAPEAKE BANK", "", "4249999999999999954"),
        ("18U", "CHESAPEAKE BANK", "C00899998", "4249999999999999955"),
    ]
    oth = fec_fixture.bulk_text("oth") + "".join(
        f"{SUPER_PAC}|N|Q2|P2024|1|{kind}|ORG|{name}|BALTIMORE|MD|21201|||04012024|9000|{other}|"
        f"SA12.{sub_id[-3:]}|1900201|||{sub_id}\n"
        for kind, name, other, sub_id in lines
    )
    put_bronze(store, texts={"oth": oth})
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    receipts = {
        row["source_record_id"] for row in read_silver(store, "organization_receipt", tmp_path)
    }
    assert receipts.isdisjoint(int(sub_id) for _, _, _, sub_id in lines)
    transfers = {
        row["source_record_id"]: row["from_committee_id"]
        for row in read_silver(store, "committee_transfer", tmp_path)
    }
    assert transfers[4249999999999999955] == "C00899998"
    assert 4249999999999999951 not in transfers
    contributions = {
        row["source_record_id"]: row for row in read_silver(store, "contribution", tmp_path)
    }
    assert contributions.keys() & {int(sub_id) for _, _, _, sub_id in lines} == {
        4249999999999999953
    }
    assert contributions[4249999999999999953]["is_self_funding"]


def test_a_duplicated_committee_receipt_aborts_the_run_before_any_upload(
    store: R2, cli_env: Path
) -> None:
    oth = fec_fixture.bulk_text("oth")
    put_bronze(store, texts={"oth": oth + oth.splitlines(keepends=True)[0]})
    seats_report()

    result = transform()

    assert isinstance(result.exception, ChecksFailed)
    assert "silver_committee_transfer_key.sql" in str(result.exception)
    assert "4240300000000000001" in str(result.exception)
    assert uploaded_silver(store) == []
    assert not markers.exists("transformed", store, cycle=2024, build_id=BUILD)


def test_jfc_attributions_are_the_15j_lines_of_individuals_and_carry_no_money(
    fixture_silver: Path,
) -> None:
    expected = fec_fixture.expected()
    rows = {row["source_record_id"]: row for row in local_silver(fixture_silver, "jfc_attribution")}

    # Each line's JFC is the committee its MEMO_TEXT names ('* OKAFOR VICTORY FUND', or after
    # '2024 AGGREGATE; JFC ATTRIB:'), else the one JFC its filing has transfers from, of any type:
    # VANTERPOOL's an 18J, HOLLOWAY's others an 18G and a blank-OTHER_ID 15J (spec §6.11).
    assert {sub_id: row["jfc_committee_id"] for sub_id, row in rows.items()} == (
        expected["attributions"]["jfc_committee"]
    )
    assert rows.keys().isdisjoint(NOT_ATTRIBUTIONS)
    assert len(rows) == expected["silver"]["jfc_attribution"]
    # The filer is the participant, and its candidate the one `ccl` links it to. An amount is
    # kept as filed, a negative one too.
    assert {(r["participant_committee_id"], r["candidate_id"]) for r in rows.values()} == {
        ("C00800103", "S4MD00103")
    }
    assert [r["amount"] for r in rows.values() if cast(Decimal, r["amount"]) < 0] == [-100]
    assert rows[ACHTERBERG]["date"] == date(2024, 10, 20)
    assert {(r["source"], r["jurisdiction"], r["cycle"]) for r in rows.values()} == {
        ("fec", "US", 2024)
    }

    # A person known only from a 15J line is a contributor with no money; VANTERPOOL's line joins
    # her contribution's key, a line more and not a dollar more.
    contributors = {
        row["contributor_key"]: row for row in local_silver(fixture_silver, "contributor")
    }
    only = contributors[cast(str, rows[ACHTERBERG]["contributor_key"])]
    assert (
        only["name_raw"],
        only["contribution_count"],
        only["amount_total"],
        only["attribution_count"],
    ) == ("ACHTERBERG, LIESBETH", 0, 0, 1)
    [gift] = [
        row
        for row in local_silver(fixture_silver, "contribution")
        if row["source_record_id"] == VANTERPOOL
    ]
    assert rows[VANTERPOOL_LINE]["contributor_key"] == gift["contributor_key"]
    vanterpool = contributors[cast(str, gift["contributor_key"])]
    assert (
        vanterpool["contribution_count"],
        vanterpool["amount_total"],
        vanterpool["attribution_count"],
    ) == (1, 250000, 1)

    # The money is the JFC's transfers, receipts like any other; the one with OTHER_ID blank is
    # the JFC's because its NAME is the JFC's, case and punctuation aside.
    transfers = {
        row["source_record_id"]: row for row in local_silver(fixture_silver, "committee_transfer")
    }
    assert {
        sub_id: (
            transfers[sub_id]["from_committee_id"],
            transfers[sub_id]["to_committee_id"],
            transfers[sub_id]["amount"],
            transfers[sub_id]["side"],
        )
        for sub_id in (JFC_TRANSFER, JFC_18G, JFC_NAMED_ONLY)
    } == {
        JFC_TRANSFER: (JFC, "C00800103", 6500, "receipt"),
        JFC_18G: (JFC, "C00800103", 10000, "receipt"),
        JFC_NAMED_ONLY: (JFC, "C00800103", 3000, "receipt"),
    }


def test_a_jfc_named_in_memo_text_is_the_joint_fundraising_committee_of_that_name(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # A committee of a lower id sharing the JFC's name, as FEC's `cm` has: the JFC is the one of
    # designation J.
    cm = fec_fixture.bulk_text("cm") + (
        "C00800099|OKAFOR VICTORY FUND||||ROCKVILLE|MD|20850|U|Q||Q|||\n"
    )
    put_bronze(store, texts={"cm": cm})
    seats_report()

    assert transform().exit_code == 0
    rows = {row["source_record_id"]: row for row in read_silver(store, "jfc_attribution", tmp_path)}
    assert rows[ACHTERBERG]["jfc_committee_id"] == JFC


def test_a_line_in_a_filing_with_transfers_from_two_jfcs_names_neither(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # A second JFC with the same participant, and a filing holding an 18G from each and a 15J line
    # naming neither: either could be its JFC, so it has none (spec §6.11).
    cm = fec_fixture.bulk_text("cm") + (
        "C00800116|CHESAPEAKE UNITY FUND||||BALTIMORE|MD|21202|J|N|DEM|Q|||\n"
    )
    oth = fec_fixture.bulk_text("oth") + (
        "C00800103|N|30G|G2024|1|18G|COM|OKAFOR VICTORY FUND|BALTIMORE|MD|21202|||11252024|4000|"
        "C00800115|SA.1|1900126|||4249999999999999981\n"
        "C00800103|N|30G|G2024|1|18G|COM|CHESAPEAKE UNITY FUND|BALTIMORE|MD|21202|||11252024|2000|"
        "C00800116|SA.2|1900126|||4249999999999999982\n"
        "C00800103|N|30G|G2024|1|15J|IND|HOLLOWAY, DEAN|FREDERICK|MD|21701|HOLLOWAY FARMS|OWNER|"
        "11252024|100||SA.3|1900126|X||4249999999999999983\n"
    )
    put_bronze(store, texts={"cm": cm, "oth": oth})
    seats_report()

    assert transform().exit_code == 0
    transfers = {
        row["source_record_id"]: row["from_committee_id"]
        for row in read_silver(store, "committee_transfer", tmp_path)
    }
    assert (transfers[4249999999999999981], transfers[4249999999999999982]) == (JFC, "C00800116")
    rows = {row["source_record_id"]: row for row in read_silver(store, "jfc_attribution", tmp_path)}
    assert rows[4249999999999999983]["jfc_committee_id"] is None
    # The fixture's own lines are as before: VANTERPOOL's filing has one JFC's 18J.
    assert rows[VANTERPOOL_LINE]["jfc_committee_id"] == JFC


def test_a_key_with_no_contributions_shows_the_variant_most_of_its_attributions_report(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # ACHTERBERG written again twice without the space: one key, which no contribution reports,
    # so the spelling of most of its lines is the key's.
    oth = fec_fixture.bulk_text("oth") + "".join(
        "C00800103|N|12G|G2024|1|15J|IND|ACHTERBERG,LIESBETH|ANNAPOLIS|MD|21402|US NAVAL ACADEMY|"
        f"PROFESSOR|10202024|50||SA.{n}|1900123|X||424999999999999997{n}\n"
        for n in (1, 2)
    )
    put_bronze(store, texts={"oth": oth})
    seats_report()

    assert transform().exit_code == 0
    rows = {row["source_record_id"]: row for row in read_silver(store, "jfc_attribution", tmp_path)}
    key = rows[ACHTERBERG]["contributor_key"]
    assert {rows[4249999999999999970 + n]["contributor_key"] for n in (1, 2)} == {key}
    [contributor] = [
        row for row in read_silver(store, "contributor", tmp_path) if row["contributor_key"] == key
    ]
    assert (contributor["name_raw"], contributor["attribution_count"]) == (
        "ACHTERBERG,LIESBETH",
        3,
    )
