"""The synthetic 2024 fixture cycle: its zips match FEC's layout and `expected.yaml` adds up.

The tally here is an independent reading of the fixture CSVs under the spec §4 rules, written
only to keep `expected.yaml` honest: edit a fixture row and this fails until the expected totals
are updated to match. It is not the pipeline, and nothing outside this module uses it.
"""

import csv
import io
import re
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import get_args

import pytest

from fundlens.fec.files import CATALOGUE, FecFile
from fundlens.resolve import normalize
from fundlens.transform.seats import Filing, races_for
from tests import fec_fixture
from tests.fec_fixture import CYCLE, MEMBERS, CandidateTotals, CommitteeTotals, RaceTotals

FILES: tuple[FecFile, ...] = get_args(FecFile)
DIME = fec_fixture.FIXTURES / "dime" / "contribDB_2024.csv"

# The conduits by FEC id (ADR-0004), and the MEMO_TEXT that names one when OTHER_ID does not.
CONDUITS = {"ACTBLUE": "C00401224", "WINRED": "C00694323"}
IE_SUPPORT, IE_OPPOSE = "24E", "24A"
COMMITTEE_CONTRIBUTION = "24K"
JFC = "J"
# A giver's entity type: an organization's, and the ones that are a committee's (NEU-2131).
ORGANIZATION = "ORG"
COMMITTEE_TYPES = ("PAC", "COM", "CCM", "PTY")
# `oth` lines that are no organization receipt: a JFC attribution, and a loan or its repayment.
NOT_GIFTS = ("15J", "16C", "16F", "16G")
# A hybrid PAC's committee types, and the transaction types of its non-contribution account's
# receipts and refunds (NEU-2192).
HYBRID_PACS = ("V", "W")
NON_CONTRIBUTION_ACCOUNT = ("10", "10J", "20Y")
# The vendored handoff list (fec/handoffs.csv) as the tally reads it: a committee handed from one
# candidate to another, the first's before the date and the second's on and after it (NEU-2126).
HANDOFFS = {"C00703975": ("P80000722", "P00009423", date(2024, 7, 21))}

EXPECTED = fec_fixture.expected()


def rows(file: FecFile) -> list[dict[str, str]]:
    return fec_fixture.read_rows(file)


def amount(row: dict[str, str]) -> int:
    value = Decimal(row["TRANSACTION_AMT"])
    # Every fixture amount is whole dollars, so the expected totals can be plain integers.
    assert value == value.to_integral_value(), row["SUB_ID"]
    return int(value)


def is_refund(row: dict[str, str]) -> bool:
    return re.fullmatch(r"[24]\dY", row["TRANSACTION_TP"]) is not None


def signed(row: dict[str, str]) -> int:
    """A contribution's amount as it counts. A refund (22Y, or any 2nY or 4nY type) subtracts
    whichever sign its filer wrote, unless it is negative and mirrors a positive refund to the same
    donor at the same committee: then it voids that refund and adds back."""
    if not is_refund(row):
        return amount(row)
    reverses = amount(row) < 0 and any(
        is_refund(other)
        and other["CMTE_ID"] == row["CMTE_ID"]
        and other["NAME"] == row["NAME"]
        and amount(other) == -amount(row)
        for other in rows("indiv")
    )
    return -amount(row) if reverses else -abs(amount(row))


def linked_candidates() -> dict[str, str]:
    """Committee → candidate, for the principal and authorized committees `ccl` links, and the
    principal campaign committee each `cn` row names whatever `ccl`'s designation (spec §4). A
    committee linked to two candidates is the principal link's, then the lower candidate_id's."""
    principal = {(row["CAND_ID"], row["CAND_PCC"]) for row in rows("cn")}
    links = sorted(
        (
            not (row["CMTE_DSGN"] == "P" or (row["CAND_ID"], row["CMTE_ID"]) in principal),
            row["CAND_ID"],
            row["CMTE_ID"],
        )
        for row in rows("ccl")
        if row["CMTE_DSGN"] in ("P", "A") or (row["CAND_ID"], row["CMTE_ID"]) in principal
    )
    linked: dict[str, str] = {}
    for _, candidate_id, committee_id in links:
        linked.setdefault(committee_id, candidate_id)
    return linked


def candidate_of(committee_id: str, row: dict[str, str]) -> str | None:
    """The candidate `row`'s money to `committee_id` is credited to: the one `ccl` links it to, or,
    for a handed-off committee, the candidate it was handed from before the handoff date and the
    one it was handed to on and after it, and an undated row's the latter's (NEU-2126)."""
    if committee_id in HANDOFFS:
        before, after, handoff = HANDOFFS[committee_id]
        dated = row["TRANSACTION_DT"]
        return before if dated and datetime.strptime(dated, "%m%d%Y").date() < handoff else after
    return linked_candidates().get(committee_id)


def is_conduit_side(row: dict[str, str]) -> bool:
    """A conduit's own line for an earmark it passed on, filed as a 15 naming the recipient."""
    return (
        row["CMTE_ID"] in CONDUITS.values()
        and re.search(r"EARMARKED FOR .*\(C\d{8}\)", row["MEMO_TEXT"]) is not None
    )


def counts(row: dict[str, str]) -> bool:
    """An `indiv` row that counts, whoever gave it: no memo line, no conduit's 24T, no conduit's
    own line for an earmark, to a committee of the cycle."""
    committees = {row["CMTE_ID"] for row in rows("cm")}
    return (
        row["MEMO_CD"] != "X"
        and row["TRANSACTION_TP"] != "24T"
        and not is_conduit_side(row)
        and row["CMTE_ID"] in committees
    )


def non_contribution_account(table: list[dict[str, str]]) -> list[dict[str, str]]:
    """The rows of one table, the counted contributions or the organization receipts, a hybrid PAC
    took into or refunded from its non-contribution account (NEU-2192): a 10, 10J or 20Y to or
    from a committee typed V or W, whoever the giver. At any other committee a 10 is an ordinary
    contribution."""
    types = {committee["CMTE_ID"]: committee["CMTE_TP"] for committee in rows("cm")}
    return [
        row
        for row in table
        if row["TRANSACTION_TP"] in NON_CONTRIBUTION_ACCOUNT
        and types.get(row["CMTE_ID"]) in HYBRID_PACS
    ]


def is_classified(row: dict[str, str]) -> bool:
    """An `indiv` row filed with no entity type whose name the classifier calls an
    organization's (NEU-2132)."""
    return not row["ENTITY_TP"].strip() and normalize.is_organization_name(row["NAME"])


def is_individual(row: dict[str, str]) -> bool:
    """An `indiv` row from an individual or a candidate: typed IND or CAN, or blank and not
    classified (NEU-2132)."""
    return row["ENTITY_TP"] in ("IND", "CAN") or (
        not row["ENTITY_TP"].strip() and not is_classified(row)
    )


def counted() -> list[dict[str, str]]:
    """The `indiv` rows the contribution table keeps: individuals and candidates, earmarks once,
    to committees of the cycle."""
    return [row for row in rows("indiv") if is_individual(row) and counts(row)]


def name_key(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", name.upper())


def person(name: str) -> tuple[str, str]:
    """A `cn` name's last name and first given name, as the self-funding test compares them."""
    last, _, given = name.partition(",")
    return name_key(last), name_key(given.strip().partition(" ")[0])


def aliases() -> dict[str, str]:
    """Candidate alias → the candidate it is an alias of (NEU-2127): a candidate of the same race,
    under the same last and first given name, credited a committee `ccl` links both principal or
    authorized; the alias credited none, and in no handoff."""
    linked = {c: cand for c, cand in linked_candidates().items() if c not in HANDOFFS}
    credited = {
        *linked.values(),
        *(c for before, after, _ in HANDOFFS.values() for c in (before, after)),
    }
    races = race_ids()
    names = {row["CAND_ID"]: person(row["CAND_NAME"]) for row in rows("cn")}
    pa_links = {(r["CAND_ID"], r["CMTE_ID"]) for r in rows("ccl") if r["CMTE_DSGN"] in ("P", "A")}
    found: dict[str, str] = {}
    for alias, committee_id in sorted(pa_links):
        holder = linked.get(committee_id)
        if (
            holder is not None
            and holder != alias
            and alias not in credited
            and (holder, committee_id) in pa_links
            and races[alias] is not None
            and races[alias] == races[holder]
            and names[alias] == names[holder]
        ):
            found[alias] = min(found.get(alias, holder), holder)
    return found


def is_receipt_line(row: dict[str, str]) -> bool:
    """An `oth` row of a receipt type (1x, or 3x for a party's accounts) that is no memo line."""
    return row["TRANSACTION_TP"][:1] in ("1", "3") and row["MEMO_CD"] != "X"


def named_committee(row: dict[str, str], *, classified: bool = False) -> str | None:
    """The one `cm` committee a row typed PAC, COM, CCM or PTY with a blank OTHER_ID names
    (NEU-2131), or a `classified` `indiv` row does (NEU-2132), never its own recipient; None when
    it names several, none, or itself."""
    if (row["ENTITY_TP"] not in COMMITTEE_TYPES and not classified) or row["OTHER_ID"]:
        return None
    named = [r["CMTE_ID"] for r in rows("cm") if name_key(r["CMTE_NM"]) == name_key(row["NAME"])]
    return named[0] if len(named) == 1 and named[0] != row["CMTE_ID"] else None


def has_twin(row: dict[str, str], committee_id: str) -> bool:
    """Whether `oth` already holds `row`'s gift under `committee_id`: a receipt to the same
    recipient from that id, of the same amount on the same date (NEU-2131)."""
    return any(
        is_receipt_line(other)
        and other["SUB_ID"] != row["SUB_ID"]
        and other["CMTE_ID"] == row["CMTE_ID"]
        and other["OTHER_ID"] == committee_id
        and other["TRANSACTION_AMT"] == row["TRANSACTION_AMT"]
        and other["TRANSACTION_DT"] == row["TRANSACTION_DT"]
        for other in rows("oth")
    )


def giver(row: dict[str, str]) -> str | None:
    """The committee an `oth` row is from: OTHER_ID when it is a committee's id, else, when it is
    blank, the joint fundraising committee whose name NAME is (NEU-2124), else the one committee
    a PAC, COM, CCM or PTY row names (NEU-2131), unless `oth` holds the gift under that
    committee's id already."""
    if row["OTHER_ID"].startswith("C"):
        return row["OTHER_ID"]
    if row["OTHER_ID"]:
        return None
    jfcs = {name_key(r["CMTE_NM"]): r["CMTE_ID"] for r in rows("cm") if r["CMTE_DSGN"] == JFC}
    jfc = jfcs.get(name_key(row["NAME"]))
    if jfc is not None:
        return jfc
    named = named_committee(row)
    return named if named is not None and not has_twin(row, named) else None


def committee_receipts() -> list[dict[str, str]]:
    """The `oth` rows that are receipts from another committee: a receipt type (1x, or 3x for a
    party's accounts), not a memo line, from a giver."""
    return [row for row in rows("oth") if is_receipt_line(row) and giver(row) is not None]


def name_matched() -> dict[str, str | None]:
    """Each counted `indiv` row typed PAC, COM, CCM or PTY with a blank OTHER_ID, by SUB_ID, and
    the committee it is a receipt from (NEU-2131): the one its NAME names, unless `oth` holds the
    gift under that id already; None when it is dropped. A classified row (NEU-2132) is here only
    when its NAME names one committee: naming none, it is an organization receipt."""
    found: dict[str, str | None] = {}
    for row in rows("indiv"):
        if row["OTHER_ID"] or not counts(row):
            continue
        if row["ENTITY_TP"] in COMMITTEE_TYPES:
            named = named_committee(row)
        elif is_classified(row):
            named = named_committee(row, classified=True)
            if named is None:
                continue
        else:
            continue
        found[row["SUB_ID"]] = named if named and not has_twin(row, named) else None
    return found


def name_matched_gifts() -> list[dict[str, str]]:
    """The `indiv` rows that are committee_transfer receipts by the name rule."""
    kept = {sub_id for sub_id, committee_id in name_matched().items() if committee_id}
    return [row for row in rows("indiv") if row["SUB_ID"] in kept]


def mirrors_counted_row(row: dict[str, str]) -> bool:
    """Whether a counted `indiv` row is the same gift as `oth`'s `row`: same recipient, name,
    amount and date (NEU-2131), so the receipt is read once, from `indiv`."""
    return any(
        counts(other)
        and other["CMTE_ID"] == row["CMTE_ID"]
        and name_key(other["NAME"]) == name_key(row["NAME"])
        and other["TRANSACTION_AMT"] == row["TRANSACTION_AMT"]
        and other["TRANSACTION_DT"] == row["TRANSACTION_DT"]
        for other in rows("indiv")
    )


def organization_receipts() -> list[dict[str, str]]:
    """The rows of either file that are organization receipts (NEU-2131, ADR-0011): a counted
    `indiv` row typed ORG, or classified and naming no one committee (NEU-2132), or an `oth`
    receipt typed ORG from no committee id, naming no JFC, neither an attribution line nor a
    loan, to a committee of the cycle, mirroring no counted `indiv` row."""
    committees = {row["CMTE_ID"] for row in rows("cm")}
    return [
        row
        for row in rows("indiv")
        if counts(row)
        and (
            row["ENTITY_TP"] == ORGANIZATION
            or (is_classified(row) and named_committee(row, classified=True) is None)
        )
    ] + [
        row
        for row in rows("oth")
        if is_receipt_line(row)
        and row["ENTITY_TP"] == ORGANIZATION
        and not row["OTHER_ID"].startswith("C")
        and giver(row) is None
        and row["TRANSACTION_TP"] not in NOT_GIFTS
        and row["CMTE_ID"] in committees
        and not mirrors_counted_row(row)
    ]


def attributions() -> list[dict[str, str]]:
    """The `oth` rows that are JFC attributions (spec §6.11): 15J memo lines from an individual
    (IND, or blank and not classified, NEU-2132) filed by a committee of the cycle."""
    committees = {row["CMTE_ID"] for row in rows("cm")}
    return [
        row
        for row in rows("oth")
        if row["TRANSACTION_TP"] == "15J"
        and row["MEMO_CD"] == "X"
        and (row["ENTITY_TP"] == "IND" or (not row["ENTITY_TP"] and not is_classified(row)))
        and row["CMTE_ID"] in committees
    ]


def is_self_funding(row: dict[str, str]) -> bool:
    names = {r["CAND_ID"]: r["CAND_NAME"] for r in rows("cn")}
    candidate = candidate_of(row["CMTE_ID"], row)
    return row["ENTITY_TP"] == "CAN" and candidate is not None and names[candidate] == row["NAME"]


def conduit(row: dict[str, str]) -> str | None:
    """The conduit an earmark came through; never the recipient itself (a gift to ActBlue)."""
    found = None
    if row["OTHER_ID"] in CONDUITS.values():
        found = row["OTHER_ID"]
    else:
        for name, committee_id in CONDUITS.items():
            if re.search(rf"\b{name}\b", row["MEMO_TEXT"]):
                found = committee_id
                break
    return None if found == row["CMTE_ID"] else found


def race_ids() -> dict[str, str | None]:
    """Candidate → the regular race its filing's seat names, or None when the seat is no race."""
    seats = {race.seat: race.race_id for race in races_for(CYCLE) if not race.is_special}
    return {
        row["CAND_ID"]: seats.get(
            Filing(
                row["CAND_ID"],
                row["CAND_OFFICE"],
                row["CAND_OFFICE_ST"],
                row["CAND_OFFICE_DISTRICT"],
            ).seat
        )
        for row in rows("cn")
    }


def sum_by[K](pairs: Iterable[tuple[K, int]]) -> dict[K, int]:
    totals: dict[K, int] = defaultdict(int)
    for key, value in pairs:
        totals[key] += value
    return totals


def tally_committees() -> dict[str, CommitteeTotals]:
    contributions = counted()
    account = {r["SUB_ID"] for r in non_contribution_account(contributions)}
    individual = sum_by(
        (r["CMTE_ID"], signed(r))
        for r in contributions
        if not is_self_funding(r) and r["SUB_ID"] not in account
    )
    self_funding = sum_by((r["CMTE_ID"], signed(r)) for r in contributions if is_self_funding(r))
    from_committees = sum_by(
        (r["CMTE_ID"], amount(r)) for r in [*committee_receipts(), *name_matched_gifts()]
    )
    pas2 = rows("pas2")
    to_candidates = sum_by(
        (r["CMTE_ID"], amount(r))
        for r in committee_contributions()
        if gift_candidate(r) is not None
    )
    ie = sum_by(
        (r["CMTE_ID"], amount(r)) for r in pas2 if r["TRANSACTION_TP"] in (IE_SUPPORT, IE_OPPOSE)
    )
    return {
        committee_id: {
            "total_individual": individual.get(committee_id, 0),
            "self_funding": self_funding.get(committee_id, 0),
            "total_from_committees": from_committees.get(committee_id, 0),
            "total_to_candidates": to_candidates.get(committee_id, 0),
            "ie_total": ie.get(committee_id, 0),
        }
        for committee_id in (row["CMTE_ID"] for row in rows("cm"))
    }


def committee_contributions() -> list[dict[str, str]]:
    """The `pas2` 24K rows that are a committee's gift: not a conduit's, whose 24K is its side of
    an earmark it passed on, counted on the recipient's `indiv` row (ADR-0004)."""
    return [
        r
        for r in rows("pas2")
        if r["TRANSACTION_TP"] == COMMITTEE_CONTRIBUTION and r["CMTE_ID"] not in CONDUITS.values()
    ]


def gift_candidate(row: dict[str, str]) -> str | None:
    """The candidate a 24K is credited to: the one its recipient committee is linked to, else the
    giver's CAND_ID when that is a candidate of the cycle (the one it is an alias of, when it is an
    alias), else none."""
    candidates = {r["CAND_ID"] for r in rows("cn")}
    linked = candidate_of(row["OTHER_ID"], row)
    if linked in candidates:
        return linked
    stated = row["CAND_ID"]
    return aliases().get(stated, stated) if stated in candidates else None


def ie_candidate(row: dict[str, str]) -> str | None:
    """The candidate an independent expenditure is for or against: the one it names."""
    return row["CAND_ID"]


def tally_candidates() -> dict[str, CandidateTotals]:
    pas2 = rows("pas2")
    contributions = counted()
    individual = sum_by(
        (c, signed(r))
        for r in contributions
        if not is_self_funding(r) and (c := candidate_of(r["CMTE_ID"], r)) is not None
    )
    self_funding = sum_by(
        (c, signed(r))
        for r in contributions
        if is_self_funding(r) and (c := candidate_of(r["CMTE_ID"], r)) is not None
    )

    def by_type(transaction_type: str) -> dict[str, int]:
        return sum_by(
            (c, amount(r))
            for r in pas2
            if r["TRANSACTION_TP"] == transaction_type and (c := ie_candidate(r)) is not None
        )

    from_committees = sum_by(
        (c, amount(r)) for r in committee_contributions() if (c := gift_candidate(r)) is not None
    )
    # A JFC's transfer, whatever its type, credited to the candidate its recipient raises for.
    jfcs = {r["CMTE_ID"] for r in rows("cm") if r["CMTE_DSGN"] == JFC}
    jfc_transfers = sum_by(
        (c, amount(r))
        for r in committee_receipts()
        if giver(r) in jfcs and (c := candidate_of(r["CMTE_ID"], r)) is not None
    )
    support, oppose = by_type(IE_SUPPORT), by_type(IE_OPPOSE)
    races, alias_ids = race_ids(), aliases()
    return {
        candidate_id: {
            "race_id": races[candidate_id],
            "total_individual": individual.get(candidate_id, 0),
            "total_committee": from_committees.get(candidate_id, 0),
            "total_jfc_transfers": jfc_transfers.get(candidate_id, 0),
            "self_funding": self_funding.get(candidate_id, 0),
            "ie_support": support.get(candidate_id, 0),
            "ie_oppose": oppose.get(candidate_id, 0),
        }
        for candidate_id in races
        if candidate_id not in alias_ids
    }


def tally_races(candidates: dict[str, CandidateTotals]) -> dict[str, RaceTotals]:
    races: dict[str, RaceTotals] = {}
    for race_id in EXPECTED["races"]:
        members = [c for c in candidates.values() if c["race_id"] == race_id]
        races[race_id] = {
            "candidate_count": len(members),
            "total_individual": sum(c["total_individual"] for c in members),
            "total_committee": sum(c["total_committee"] for c in members),
            "total_jfc_transfers": sum(c["total_jfc_transfers"] for c in members),
            "ie_support": sum(c["ie_support"] for c in members),
            "ie_oppose": sum(c["ie_oppose"] for c in members),
        }
    return races


@pytest.mark.parametrize("file", FILES)
def test_each_zip_holds_one_pipe_delimited_member_with_the_vendored_column_count(
    file: FecFile,
) -> None:
    columns = CATALOGUE[file].header()
    with zipfile.ZipFile(io.BytesIO(fec_fixture.zips()[file])) as archive:
        assert archive.namelist() == [MEMBERS[file]]
        lines = archive.read(MEMBERS[file]).decode().splitlines()
    assert lines
    assert len(lines) == EXPECTED["rows"][file]
    assert all(len(line.split("|")) == len(columns) for line in lines)
    # No header row: FEC's bulk files have none.
    assert lines[0].split("|")[0] != columns[0]


def test_a_csv_whose_header_is_not_fecs_is_refused(tmp_path: Path) -> None:
    text = (fec_fixture.fixture_dir() / "cm.csv").read_text()
    (tmp_path / "cm.csv").write_text(text.replace("CMTE_NM", "CMTE_NAME", 1))
    with pytest.raises(ValueError, match="header"):
        fec_fixture.read_rows("cm", tmp_path)


def test_a_row_with_a_value_too_many_is_refused(tmp_path: Path) -> None:
    (tmp_path / "ccl.csv").write_text(
        ",".join(CATALOGUE["ccl"].header()) + "\nH4MD05106,2024,2024,C00800106,H,P,1,extra\n"
    )
    with pytest.raises(ValueError, match="row 1"):
        fec_fixture.read_rows("ccl", tmp_path)


def test_each_race_total_is_the_sum_of_its_candidates() -> None:
    for race_id, race in EXPECTED["races"].items():
        members = [c for c in EXPECTED["candidates"].values() if c["race_id"] == race_id]
        assert race["candidate_count"] == len(members), race_id
        for field in (
            "total_individual",
            "total_committee",
            "total_jfc_transfers",
            "ie_support",
            "ie_oppose",
        ):
            assert race[field] == sum(c[field] for c in members), (race_id, field)


def test_each_candidate_total_is_the_sum_of_their_principal_and_authorized_committees() -> None:
    links = {c: cand for c, cand in linked_candidates().items() if c not in HANDOFFS}
    handed = {cand for before, after, _ in HANDOFFS.values() for cand in (before, after)}
    for candidate_id, candidate in EXPECTED["candidates"].items():
        if candidate_id in handed:
            continue
        committees = [
            EXPECTED["committees"][c] for c, cand in links.items() if cand == candidate_id
        ]
        for field in ("total_individual", "self_funding"):
            assert candidate[field] == sum(c[field] for c in committees), (candidate_id, field)


def test_a_handed_off_committee_is_split_between_its_candidates_and_its_money_kept_whole() -> None:
    # The fixture's two candidates of the handed-off committee have no other: each holds a share
    # of it, together all of it, so the split moves money within the race and adds none.
    for committee_id, (before, after, _) in HANDOFFS.items():
        committee = EXPECTED["committees"][committee_id]
        shares = (EXPECTED["candidates"][before], EXPECTED["candidates"][after])
        assert all(share["total_individual"] for share in shares), committee_id
        for field in ("total_individual", "self_funding"):
            assert sum(share[field] for share in shares) == committee[field], (committee_id, field)


def test_every_candidate_with_a_race_is_in_a_listed_race() -> None:
    listed = set(EXPECTED["races"])
    for candidate_id, candidate in EXPECTED["candidates"].items():
        assert candidate["race_id"] is None or candidate["race_id"] in listed, candidate_id


def test_the_expected_totals_match_a_tally_of_the_fixture() -> None:
    candidates = tally_candidates()
    assert EXPECTED["committees"] == tally_committees()
    assert EXPECTED["candidates"] == candidates
    assert EXPECTED["races"] == tally_races(candidates)
    assert EXPECTED["unmatched_filings"] == [c for c, r in race_ids().items() if r is None]
    assert EXPECTED["aliases"] == aliases()


def contributor_key(row: dict[str, str]) -> str:
    """The contributor key of an `indiv` or `oth` row (spec §6.1), from the normalizers it is
    built from."""
    return normalize.contributor_key(
        normalize.normalize_name(row["NAME"]).norm,
        normalize.zip5(row["ZIP_CODE"]),
        normalize.normalize_employer(row["EMPLOYER"]),
        normalize.normalize_occupation(row["OCCUPATION"]),
    )


def test_the_expected_counts_match_the_fixture() -> None:
    indiv, pas2 = rows("indiv"), rows("pas2")
    contributions = counted()
    assert EXPECTED["rows"] == {file: len(rows(file)) for file in FILES}
    assert EXPECTED["silver"] == {
        "committee": len(rows("cm")),
        "candidate": len(rows("cn")),
        "candidate_committee_link": len(rows("ccl")),
        "contribution": len(contributions),
        "independent_expenditure": sum(r["TRANSACTION_TP"] != COMMITTEE_CONTRIBUTION for r in pas2),
        "committee_transfer": len(committee_receipts())
        + len(name_matched_gifts())
        + len(committee_contributions()),
        "organization_receipt": len(organization_receipts()),
        "jfc_attribution": len(attributions()),
        "contributor": len({contributor_key(r) for r in [*contributions, *attributions()]}),
    }
    conduits = sum_by((c, 1) for r in contributions if (c := conduit(r)) is not None)
    committees = {row["CMTE_ID"] for row in rows("cm")}
    assert EXPECTED["contributions"] == {
        "dropped_memo": sum(r["MEMO_CD"] == "X" for r in indiv),
        "dropped_conduit_24t": sum(r["TRANSACTION_TP"] == "24T" for r in indiv),
        "dropped_conduit_side": sum(
            is_conduit_side(r) and r["TRANSACTION_TP"] != "24T" for r in indiv
        ),
        "dropped_unknown_recipient": sum(r["CMTE_ID"] not in committees for r in indiv),
        "dropped_not_individual": sum(not is_individual(r) for r in indiv),
        "self_funding": sum(is_self_funding(r) for r in contributions),
        "earmarked": dict(sorted(conduits.items())),
        "total_amount": sum(signed(r) for r in contributions),
    }


def test_the_expected_organization_receipts_match_the_fixture_and_feed_no_other_total() -> None:
    receipts = organization_receipts()
    expected = EXPECTED["organization_receipts"]
    keys = {
        int(r["SUB_ID"]): key for r in receipts if (key := normalize.organization_key(r["NAME"]))
    }
    assert len(keys) == len(receipts)
    assert expected["keys"] == keys
    assert expected["by_key"] == sum_by((keys[int(r["SUB_ID"])], signed(r)) for r in receipts)
    assert expected["by_committee"] == sum_by((r["CMTE_ID"], signed(r)) for r in receipts)
    assert expected["total_amount"] == sum(signed(r) for r in receipts)
    # Classified exactly when filed with no entity type (NEU-2132).
    assert expected["classified"] == [int(r["SUB_ID"]) for r in receipts if is_classified(r)]
    assert expected["classified"] == [int(r["SUB_ID"]) for r in receipts if not r["ENTITY_TP"]]
    # Two spellings of one organization share a key; a refund nets its organization's total.
    assert len(set(keys.values())) < len(keys)
    assert any(is_refund(r) for r in receipts)
    assert any(r["SUB_ID"].startswith("42403") for r in receipts)
    # Organization money is no contribution and no contributor: not a row of `counted`, and
    # every SUB_ID here is in no donor's grouping.
    counted_ids = {r["SUB_ID"] for r in counted()}
    assert counted_ids.isdisjoint(r["SUB_ID"] for r in receipts)
    assert all(
        sub_id not in {int(s) for s in keys} and sub_id not in {int(s) for s in name_matched()}
        for donor in EXPECTED["donors"].values()
        for sub_id in donor["sub_ids"]
    )


def test_the_expected_non_contribution_account_is_the_hybrid_pacs_type_10_rows() -> None:
    contributions = non_contribution_account(counted())
    receipts = non_contribution_account(organization_receipts())
    expected = EXPECTED["non_contribution_account"]
    assert expected["contributions"] == [int(r["SUB_ID"]) for r in contributions]
    assert expected["organization_receipts"] == [int(r["SUB_ID"]) for r in receipts]
    assert expected["by_committee"] == sum_by(
        (r["CMTE_ID"], signed(r)) for r in [*contributions, *receipts]
    )
    assert expected["organizations_by_committee"] == sum_by(
        (r["CMTE_ID"], signed(r)) for r in receipts
    )
    # A 10 to a super PAC is line 11(a)(i) money, an ordinary contribution, in its total_individual.
    # A hybrid PAC's refund is typed by account: a 20Y is the non-contribution account's though its
    # giver gave no 10, a 22Y the contribution account's though its giver gave both.
    marked = {r["SUB_ID"] for r in contributions}
    unmarked = [r for r in counted() if r["SUB_ID"] not in marked]
    givers = {r["NAME"] for r in contributions if r["TRANSACTION_TP"] == "10"}
    assert any(r["TRANSACTION_TP"] == "10" for r in unmarked)
    assert any(
        r["TRANSACTION_TP"] == "22Y" and r["CMTE_ID"] == "C00800204" and r["NAME"] in givers
        for r in unmarked
    )
    assert any(r["TRANSACTION_TP"] == "20Y" and r["NAME"] not in givers for r in contributions)


def test_the_expected_top_organizations_follow_the_net_money_by_key() -> None:
    receipts = organization_receipts()
    key_of = {r["SUB_ID"]: normalize.organization_key(r["NAME"]) or "" for r in receipts}
    # The spelling with the most money, then the most receipts, names the key, as
    # donor.display_name is chosen (spec §6.7).
    spellings = sum_by(((key_of[r["SUB_ID"]], r["NAME"]), signed(r)) for r in receipts)
    receipts_of = sum_by(((key_of[r["SUB_ID"]], r["NAME"]), 1) for r in receipts)
    name_of: dict[str, str] = {}
    for (key, name), _ in sorted(
        spellings.items(), key=lambda item: (-item[1], -receipts_of[item[0]], item[0][1])
    ):
        name_of.setdefault(key, name)
    given = sum_by(((r["CMTE_ID"], key_of[r["SUB_ID"]]), signed(r)) for r in receipts)
    top: dict[str, list[list[str | int]]] = defaultdict(list)
    for (committee, key), net in sorted(given.items(), key=lambda item: (-item[1], item[0][1])):
        if net > 0:
            top[committee].append([key, name_of[key], net])
    assert EXPECTED["organization_receipts"]["top_by_committee"] == top
    # One organization under two spellings is listed once.
    assert len({r["NAME"] for r in receipts if key_of[r["SUB_ID"]] == "CHESAPEAKE STEEL"}) == 2


def test_the_expected_name_matches_are_the_fixtures_pac_rows_without_an_id() -> None:
    assert EXPECTED["name_matched"] == {int(s): c for s, c in name_matched().items()}
    # Two join committee_transfer, one of them a classified blank-type row (NEU-2132); one names
    # no committee; one names its own recipient.
    kept = [c for c in EXPECTED["name_matched"].values() if c]
    assert len(kept) == 2 and len(EXPECTED["name_matched"]) == 4
    by_sub_id = {int(r["SUB_ID"]): r for r in rows("indiv")}
    assert any(is_classified(by_sub_id[s]) for s, c in EXPECTED["name_matched"].items() if c)
    by_id = {r["SUB_ID"]: r for r in rows("indiv")}
    names = {r["CMTE_ID"]: name_key(r["CMTE_NM"]) for r in rows("cm")}
    dropped = [by_id[str(s)] for s, c in EXPECTED["name_matched"].items() if c is None]
    assert sorted(name_key(r["NAME"]) == names[r["CMTE_ID"]] for r in dropped) == [False, True]


def test_the_expected_attributions_are_the_fixtures_and_one_is_of_no_contributor() -> None:
    lines = attributions()
    assert sorted(EXPECTED["attributions"]["jfc_committee"]) == sorted(
        int(r["SUB_ID"]) for r in lines
    )
    counted_keys = {contributor_key(r) for r in counted()}
    assert EXPECTED["attributions"]["attribution_only"] == [
        int(r["SUB_ID"]) for r in lines if contributor_key(r) not in counted_keys
    ]


def test_a_conduit_is_a_counted_recipient_only_of_gifts_to_itself() -> None:
    to_conduits = [r for r in counted() if r["CMTE_ID"] in CONDUITS.values()]
    assert to_conduits
    assert all(conduit(r) is None and "EARMARK" not in r["MEMO_TEXT"] for r in to_conduits)


def dime_rows() -> list[dict[str, str]]:
    with DIME.open(newline="") as f:
        return list(csv.DictReader(f))


def dime_cids() -> dict[int, str]:
    """Each counted contribution's DIME `bonica.cid`, joined as the validator joins them: on the
    filer's committee and transaction ids (ADR-0009)."""
    labels: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in dime_rows():
        labels[row["efec.comid.orig"], row["efec.transaction.id.orig"]].add(row["bonica.cid"])
    cids: dict[int, str] = {}
    for row in counted():
        [cids[int(row["SUB_ID"])]] = labels[row["CMTE_ID"], row["TRAN_ID"]]
    return cids


def test_every_counted_contribution_has_exactly_one_dime_label() -> None:
    assert len(dime_rows()) == len(counted())
    cids = dime_cids()
    assert len(cids) == len(counted())
    assert EXPECTED["distinct_donors"] == len(set(cids.values()))


def test_each_donor_grouping_is_its_contributions_and_one_dime_donor() -> None:
    by_sub_id = {int(r["SUB_ID"]): r for r in counted()}
    cids = dime_cids()
    for label, donor in EXPECTED["donors"].items():
        assert set(donor["sub_ids"]) <= by_sub_id.keys(), label
        assert donor["amount"] == sum(signed(by_sub_id[s]) for s in donor["sub_ids"]), label
        assert {cids[s] for s in donor["sub_ids"]} == {str(donor["bonica_cid"])}, label
        # A grouping is all of that donor's counted contributions, not a sample of them.
        assert sorted(donor["sub_ids"]) == sorted(
            s for s, cid in cids.items() if cid == str(donor["bonica_cid"])
        ), label
    cids_listed = [donor["bonica_cid"] for donor in EXPECTED["donors"].values()]
    assert len(cids_listed) == len(set(cids_listed))


def test_the_expected_validation_labels_every_dated_counted_contribution_and_its_keys() -> None:
    validation = EXPECTED["validation"]
    # The DIME import drops a label with no date, and the validator matches on the date: a counted
    # contribution with none (VOSS's, NEU-2126) is labelled in the file but never matched.
    dated = [r for r in counted() if r["TRANSACTION_DT"]]
    assert len(dated) < len(counted()) == len(dime_cids())
    assert validation["matched_rows"] == len(dated)
    cids = dime_cids()
    assert validation["labelled_keys"] == len(
        {(contributor_key(r), cids[int(r["SUB_ID"])]) for r in dated}
    )
