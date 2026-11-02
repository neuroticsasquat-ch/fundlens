"""`fundlens transform` on the fixture cycle, against MinIO bronze and a migrated Postgres
(spec §5.3)."""

import io
import zipfile
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import duckdb
from typer.testing import CliRunner, Result

from fundlens import cli, markers, paths
from fundlens.fec.files import FecFile, files_for
from fundlens.paths import SilverTable
from fundlens.r2 import R2
from fundlens.resolve import normalize
from fundlens.transform.runner import ChecksFailed
from tests import fec_fixture
from tests.fake_fec import zipped

BUILD = "20261030T030000Z"
TABLES: tuple[SilverTable, ...] = (
    "committee",
    "candidate",
    "candidate_committee_link",
    "contribution",
    "committee_transfer",
    "jfc_attribution",
    "contributor",
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
OTH_NOT_RECEIPTS = {
    4240200000000000010,  # pas2's 24K, repeated in oth
    4240200000000000003,  # pas2's 24A, repeated in oth
    4240300000000000011,  # a 15J memo line
    4240300000000000012,  # WHITLOCK's 16C loan to his campaign
    # More 15J memo lines (spec §6.11): JFC attributions, an organization's, one to no committee.
    *range(4240300000000000015, 4240300000000000020),
}
OTH_PARTY_ACCOUNT_RECEIPT = 4240300000000000013
# OKAFOR VICTORY FUND's 18J transfer to OKAFOR, and the 15J lines of the people behind it: one known
# from no contribution, and VANTERPOOL, who gave to the super PAC. An organization's 15J line and
# one to a committee missing from `cm` are no attribution.
JFC, JFC_TRANSFER = "C00800115", 4240300000000000014
ACHTERBERG, VANTERPOOL_LINE = 4240300000000000015, 4240300000000000016
VANTERPOOL = 4240100000000000030
NOT_ATTRIBUTIONS = {4240300000000000018, 4240300000000000019}
# The Musk case's first contribution, and the same contributor written again with a comma and a JR.
MUSK, MUSK_AGAIN = 4240100000000000007, 4240100000000000011
# 24K gifts whose giver wrote a stale candidate id, and whose recipient raises for no candidate.
STALE_CAND_ID_GIFT, NO_CANDIDATE_GIFT = 4240200000000000017, 4240200000000000018


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
    local = store.download_to(key, tmp_path / "fetched" / f"{table}.parquet")
    with duckdb.connect() as con:
        # The file's own columns: DuckDB would otherwise add `build` from a hive-style path.
        cursor = con.execute(f"SELECT * FROM read_parquet('{local}', hive_partitioning = false)")
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


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
    ]
    assert {row["candidate_id"]: row["race_id"] for row in candidates} == {
        candidate_id: totals["race_id"] for candidate_id, totals in expected["candidates"].items()
    }

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


def sum_by(rows: list[dict[str, object]], key: str) -> dict[object, int]:
    """Whole-dollar amount totals of `rows` by `key`, rows without one left out."""
    totals: dict[object, int] = {}
    for row in rows:
        if row[key] is not None:
            totals[row[key]] = totals.get(row[key], 0) + int(cast(Decimal, row["amount"]))
    return totals


def test_contributions_count_each_earmark_once_and_add_up_to_the_expected_totals(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    put_bronze(store)
    seats_report()

    assert transform().exit_code == 0
    rows = read_silver(store, "contribution", tmp_path)
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
    # A conduit is a recipient only of gifts to itself (PARK's tip to ActBlue), with no conduit;
    # ActBlue's own line for an earmark, filed as a 15, is dropped like its 24T (NEU-2070).
    to_conduits = [row for row in rows if row["recipient_committee_id"] in (ACTBLUE, WINRED)]
    assert [(row["source_record_id"], row["conduit_committee_id"]) for row in to_conduits] == [
        (PARK_TIP, None)
    ]
    assert PARK_EARMARK_CONDUIT_SIDE not in by_id

    individual = [row for row in rows if not row["is_self_funding"]]
    self_funding = [row for row in rows if row["is_self_funding"]]
    assert len(self_funding) == expected["contributions"]["self_funding"]
    committees = expected["committees"]
    assert sum_by(individual, "recipient_committee_id") == {
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
        row["candidate_id"]: row["race_id"] for row in read_silver(store, "candidate", tmp_path)
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
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    put_bronze(store)
    seats_report()

    assert transform().exit_code == 0
    by_id = {row["source_record_id"]: row for row in read_silver(store, "contribution", tmp_path)}
    donors = fec_fixture.expected()["donors"]

    gift, loan = (by_id[sub_id] for sub_id in donors["self_funder"]["sub_ids"])
    assert (loan["transaction_type"], loan["amount"], loan["is_self_funding"]) == (
        "16C",
        1500000,
        True,
    )
    assert gift["is_self_funding"] and gift["conduit_committee_id"] is None
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
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # The fixture's OSEI and LINDQVIST rows (NEU-2073): a gift and its refund written negative;
    # a gift, its refund written positive, and the refund check voided by a mirroring negative.
    put_bronze(store)
    seats_report()

    assert transform().exit_code == 0
    by_id = {row["source_record_id"]: row for row in read_silver(store, "contribution", tmp_path)}
    osei, osei_refund, lindqvist, lindqvist_refund, lindqvist_void = (
        by_id[4240100000000000300 + n]["amount"] for n in (4, 5, 6, 7, 8)
    )
    assert (osei, osei_refund) == (300, -300)
    assert (lindqvist, lindqvist_refund, lindqvist_void) == (500, -200, 200)


def test_a_gift_to_a_committee_missing_from_the_committee_file_is_dropped(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # The fixture's NORRIS row: a few fringe filers report gifts to a committee FEC's `cm` lacks,
    # which would belong to no committee (NEU-2070).
    put_bronze(store)
    seats_report()

    assert transform().exit_code == 0
    rows = read_silver(store, "contribution", tmp_path)
    assert NORRIS_UNKNOWN_RECIPIENT not in {row["source_record_id"] for row in rows}
    assert "C00899999" not in {row["recipient_committee_id"] for row in rows}


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
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    put_bronze(store)
    seats_report()

    assert transform().exit_code == 0
    contributions = read_silver(store, "contribution", tmp_path)
    contributors = {
        row["contributor_key"]: row for row in read_silver(store, "contributor", tmp_path)
    }
    attributions = read_silver(store, "jfc_attribution", tmp_path)
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


def test_transform_without_bronze_says_to_extract(store: R2, cli_env: Path) -> None:
    result = transform()

    assert result.exit_code == 1
    assert "fundlens extract --cycle 2024" in result.output
    assert not markers.exists("transformed", store, cycle=2024, build_id=BUILD)


def test_an_odd_cycle_is_a_usage_error(store: R2, cli_env: Path) -> None:
    assert transform(2025).exit_code == 2


def test_committee_transfers_hold_each_side_once_and_add_up_to_the_expected_totals(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    put_bronze(store)
    seats_report()

    assert transform().exit_code == 0
    rows = read_silver(store, "committee_transfer", tmp_path)
    expected = fec_fixture.expected()
    receipts = [row for row in rows if row["side"] == "receipt"]
    disbursements = [row for row in rows if row["side"] == "disbursement"]

    # Every `oth` receipt from a committee is a receipt; every 24K `pas2` row a disbursement;
    # nothing else is here. `oth`'s repeat of a pas2 24K and 24A, its 15J memo line and the 16C
    # candidate loan are none of those (NEU-2070); the 31K party-account receipt is one.
    receipt_ids = {row["source_record_id"] for row in receipts}
    assert receipt_ids & OTH_NOT_RECEIPTS == set()
    assert OTH_PARTY_ACCOUNT_RECEIPT in receipt_ids
    assert len(receipts) == expected["rows"]["oth"] - len(OTH_NOT_RECEIPTS)
    assert len(disbursements) == len(rows) - len(receipts)
    assert len(rows) == expected["silver"]["committee_transfer"]
    assert {row["transaction_type"] for row in disbursements} == {"24K"}
    # A conduit's 24K is its side of an earmark, an individual's money (ADR-0004): WinRed's two
    # to DRISCOLL are no committee's gift.
    assert {row["from_committee_id"] for row in disbursements} & {ACTBLUE, WINRED} == set()
    assert {row["candidate_id"] for row in receipts} == {None}
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
    assert (received["from_committee_id"], received["to_committee_id"]) == (
        "C00800202",
        "C00800103",
    )
    assert (given["amount"], received["amount"], given["date"]) == (5000, 5000, date(2024, 4, 10))

    # One side each (expected.yaml's rule): receipts by recipient, disbursements by giver and
    # by candidate.
    committees = expected["committees"]
    assert sum_by(receipts, "to_committee_id") == {
        committee_id: totals["total_from_committees"]
        for committee_id, totals in committees.items()
        if totals["total_from_committees"]
    }
    credited = [row for row in disbursements if row["candidate_id"] is not None]
    assert sum_by(credited, "from_committee_id") == {
        committee_id: totals["total_to_candidates"]
        for committee_id, totals in committees.items()
        if totals["total_to_candidates"]
    }
    candidates = expected["candidates"]
    assert sum_by(disbursements, "candidate_id") == {
        candidate_id: totals["total_committee"]
        for candidate_id, totals in candidates.items()
        if totals["total_committee"]
    }


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
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    put_bronze(store)
    seats_report()

    assert transform().exit_code == 0
    expected = fec_fixture.expected()
    rows = {row["source_record_id"]: row for row in read_silver(store, "jfc_attribution", tmp_path)}

    # Each line's JFC is the committee its MEMO_TEXT names ('* OKAFOR VICTORY FUND', or after
    # '2024 AGGREGATE; JFC ATTRIB:'), else its filing's only 18J sender, else none (spec §6.11).
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
        row["contributor_key"]: row for row in read_silver(store, "contributor", tmp_path)
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
        for row in read_silver(store, "contribution", tmp_path)
        if row["source_record_id"] == VANTERPOOL
    ]
    assert rows[VANTERPOOL_LINE]["contributor_key"] == gift["contributor_key"]
    vanterpool = contributors[cast(str, gift["contributor_key"])]
    assert (
        vanterpool["contribution_count"],
        vanterpool["amount_total"],
        vanterpool["attribution_count"],
    ) == (1, 250000, 1)

    # The money is the JFC's 18J transfer, a receipt like any other.
    transfers = {
        row["source_record_id"]: row for row in read_silver(store, "committee_transfer", tmp_path)
    }
    transfer = transfers[JFC_TRANSFER]
    assert (
        transfer["from_committee_id"],
        transfer["to_committee_id"],
        transfer["amount"],
        transfer["side"],
    ) == (JFC, "C00800103", 6500, "receipt")


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
