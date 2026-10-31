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
    """Committee → candidate, for the principal and authorized committees `ccl` links (spec §4)."""
    return {row["CMTE_ID"]: row["CAND_ID"] for row in rows("ccl") if row["CMTE_DSGN"] in ("P", "A")}


def is_conduit_side(row: dict[str, str]) -> bool:
    """A conduit's own line for an earmark it passed on, filed as a 15 naming the recipient."""
    return (
        row["CMTE_ID"] in CONDUITS.values()
        and re.search(r"EARMARKED FOR .*\(C\d{8}\)", row["MEMO_TEXT"]) is not None
    )


def counted() -> list[dict[str, str]]:
    """The `indiv` rows the contribution table keeps: individuals and candidates, earmarks once,
    to committees of the cycle."""
    committees = {row["CMTE_ID"] for row in rows("cm")}
    return [
        row
        for row in rows("indiv")
        if row["ENTITY_TP"] in ("IND", "CAN")
        and row["MEMO_CD"] != "X"
        and row["TRANSACTION_TP"] != "24T"
        and not is_conduit_side(row)
        and row["CMTE_ID"] in committees
    ]


def committee_receipts() -> list[dict[str, str]]:
    """The `oth` rows that are receipts from another committee: a receipt type (1x, or 3x for a
    party's accounts), not a memo line, from a giver whose id is a committee's."""
    return [
        row
        for row in rows("oth")
        if row["TRANSACTION_TP"][:1] in ("1", "3")
        and row["MEMO_CD"] != "X"
        and row["OTHER_ID"].startswith("C")
    ]


def attributions() -> list[dict[str, str]]:
    """The `oth` rows that are JFC attributions (spec §6.11): 15J memo lines from an individual
    (IND, or blank) filed by a committee of the cycle."""
    committees = {row["CMTE_ID"] for row in rows("cm")}
    return [
        row
        for row in rows("oth")
        if row["TRANSACTION_TP"] == "15J"
        and row["MEMO_CD"] == "X"
        and row["ENTITY_TP"] in ("IND", "")
        and row["CMTE_ID"] in committees
    ]


def is_self_funding(row: dict[str, str]) -> bool:
    names = {r["CAND_ID"]: r["CAND_NAME"] for r in rows("cn")}
    candidate = linked_candidates().get(row["CMTE_ID"])
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


def sum_by(pairs: Iterable[tuple[str, int]]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for key, value in pairs:
        totals[key] += value
    return totals


def tally_committees() -> dict[str, CommitteeTotals]:
    contributions = counted()
    individual = sum_by((r["CMTE_ID"], signed(r)) for r in contributions if not is_self_funding(r))
    self_funding = sum_by((r["CMTE_ID"], signed(r)) for r in contributions if is_self_funding(r))
    from_committees = sum_by((r["CMTE_ID"], amount(r)) for r in committee_receipts())
    pas2 = rows("pas2")
    to_candidates = sum_by(
        (r["CMTE_ID"], amount(r))
        for r in pas2
        if r["TRANSACTION_TP"] == COMMITTEE_CONTRIBUTION and gift_candidate(r) is not None
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


def gift_candidate(row: dict[str, str]) -> str | None:
    """The candidate a 24K is credited to: the one its recipient committee is linked to, else the
    giver's CAND_ID when that is a candidate of the cycle, else none."""
    candidates = {r["CAND_ID"] for r in rows("cn")}
    linked = linked_candidates().get(row["OTHER_ID"])
    if linked in candidates:
        return linked
    return row["CAND_ID"] if row["CAND_ID"] in candidates else None


def ie_candidate(row: dict[str, str]) -> str | None:
    """The candidate an independent expenditure is for or against: the one it names."""
    return row["CAND_ID"]


def tally_candidates() -> dict[str, CandidateTotals]:
    links = linked_candidates()
    committees = tally_committees()
    pas2 = rows("pas2")

    def by_type(transaction_type: str) -> dict[str, int]:
        candidate = gift_candidate if transaction_type == COMMITTEE_CONTRIBUTION else ie_candidate
        return sum_by(
            (c, amount(r))
            for r in pas2
            if r["TRANSACTION_TP"] == transaction_type and (c := candidate(r)) is not None
        )

    from_committees, support, oppose = (
        by_type(COMMITTEE_CONTRIBUTION),
        by_type(IE_SUPPORT),
        by_type(IE_OPPOSE),
    )
    races = race_ids()
    return {
        candidate_id: {
            "race_id": races[candidate_id],
            "total_individual": sum(
                committees[c]["total_individual"]
                for c, cand in links.items()
                if cand == candidate_id
            ),
            "total_committee": from_committees.get(candidate_id, 0),
            "self_funding": sum(
                committees[c]["self_funding"] for c, cand in links.items() if cand == candidate_id
            ),
            "ie_support": support.get(candidate_id, 0),
            "ie_oppose": oppose.get(candidate_id, 0),
        }
        for candidate_id in races
    }


def tally_races(candidates: dict[str, CandidateTotals]) -> dict[str, RaceTotals]:
    races: dict[str, RaceTotals] = {}
    for race_id in EXPECTED["races"]:
        members = [c for c in candidates.values() if c["race_id"] == race_id]
        races[race_id] = {
            "candidate_count": len(members),
            "total_individual": sum(c["total_individual"] for c in members),
            "total_committee": sum(c["total_committee"] for c in members),
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
        for field in ("total_individual", "total_committee", "ie_support", "ie_oppose"):
            assert race[field] == sum(c[field] for c in members), (race_id, field)


def test_each_candidate_total_is_the_sum_of_their_principal_and_authorized_committees() -> None:
    links = linked_candidates()
    for candidate_id, candidate in EXPECTED["candidates"].items():
        committees = [
            EXPECTED["committees"][c] for c, cand in links.items() if cand == candidate_id
        ]
        for field in ("total_individual", "self_funding"):
            assert candidate[field] == sum(c[field] for c in committees), (candidate_id, field)


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
        + sum(r["TRANSACTION_TP"] == COMMITTEE_CONTRIBUTION for r in pas2),
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
        "dropped_not_individual": sum(r["ENTITY_TP"] not in ("IND", "CAN") for r in indiv),
        "self_funding": sum(is_self_funding(r) for r in contributions),
        "earmarked": dict(sorted(conduits.items())),
        "total_amount": sum(signed(r) for r in contributions),
    }


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
    """Each counted contribution's DIME `bonica.cid`, joined as the validator will join them:
    on date, amount, recipient committee and name (spec §6.9)."""
    labels: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for row in dime_rows():
        key = (row["date"], row["amount"], row["bonica.rid"], row["contributor.name"])
        labels[key].add(row["bonica.cid"])
    cids: dict[int, str] = {}
    for row in counted():
        d = row["TRANSACTION_DT"]
        key = (
            f"{d[4:]}-{d[:2]}-{d[2:4]}",
            str(signed(row)),
            row["CMTE_ID"],
            row["NAME"].lower(),
        )
        [cids[int(row["SUB_ID"])]] = labels[key]
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
