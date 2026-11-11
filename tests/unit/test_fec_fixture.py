"""The synthetic 2024 fixture cycle: its zips match FEC's layout and `expected.yaml` adds up.

The tally here is an independent reading of the fixture CSVs under the spec §4 rules, written
only to keep `expected.yaml` honest: edit a fixture row and this fails until the expected totals
are updated to match. It is not the pipeline, and nothing outside this module uses it.
"""

import csv
import functools
import io
import re
import zipfile
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import get_args

import pytest

from fundlens.fec.files import CATALOGUE, FecFile
from fundlens.resolve import normalize
from fundlens.transform.seats import Filing, races_for
from tests import fec_fixture
from tests.fec_fixture import (
    CYCLE,
    MEMBERS,
    CandidateTotals,
    CommitteeTotals,
    RaceTotals,
    Row,
)

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
# The `cm` types that are no political committee: persons and organizations filing Forms 5, 7 and 9.
# An ORG row naming one is an organization receipt still (NEU-2195).
NOT_POLITICAL = ("I", "C", "E")
# `oth` lines that are no organization receipt: a JFC attribution, and a loan or its repayment.
NOT_GIFTS = ("15J", "16C", "16F", "16G")
# A candidate's loan to their campaign and its repayment (NEU-2071), contributions from `oth`; with
# a 15C, the types that are the candidate's own money whoever the row names (NEU-2194).
LOAN_REPAYMENT = "20C"
CANDIDATE_LOANS = ("16C", LOAN_REPAYMENT)
CANDIDATE_TYPES = ("15C", *CANDIDATE_LOANS)
# A hybrid PAC's committee types, and the transaction types of its non-contribution account's
# receipts and refunds (NEU-2192). A 24I, an earmark through a conduit, is one of them when its
# memo begins with the account's name (NEU-2203, NEU-2207); a hybrid PAC files its other 24Is on
# line 11(a)(i).
HYBRID_PACS = ("V", "W")
NON_CONTRIBUTION_ACCOUNT = ("10", "10J", "20Y")
NON_CONTRIBUTION_MEMO = "* NON-CONTRIBUTION ACCOUNT"
# The transaction types FEC files on a line no total_individual counts (NEU-2193): loans, transfers
# and other non-contribution receipts, Form 9 donations, and a national party's convention,
# headquarters and recount accounts (30, 31, 32 and variants) and their refunds.
OTHER_LINES = r"16[CFGHJKLR]|18[GHJKLU]|19J?|3[012][A-Z]?|4[012]Y"
# The vendored handoff list (fec/handoffs.csv) as the tally reads it: a committee handed from one
# candidate to another, the first's before the date and the second's on and after it (NEU-2126).
HANDOFFS = {"C00703975": ("P80000722", "P00009423", date(2024, 7, 21))}

EXPECTED = fec_fixture.expected()


def rows(file: FecFile) -> tuple[Row, ...]:
    return fec_fixture.read_rows(file)


@functools.cache
def committee_ids() -> frozenset[str]:
    """The committees of the cycle: `cm`'s."""
    return frozenset(row["CMTE_ID"] for row in rows("cm"))


def amount(row: Row) -> int:
    value = Decimal(row["TRANSACTION_AMT"])
    # Every fixture amount is whole dollars, so the expected totals can be plain integers.
    assert value == value.to_integral_value(), row["SUB_ID"]
    return int(value)


def is_refund(row: Row) -> bool:
    return re.fullmatch(r"[24]\dY", row["TRANSACTION_TP"]) is not None


def gift(row: Row) -> tuple[str, ...]:
    """A gift as two filings are compared on it (NEU-2196): its committee, its giver's name key,
    ZIP5, employer and occupation, and its amount and date."""
    return (
        row["CMTE_ID"],
        name_key(row["NAME"]),
        row["ZIP_CODE"][:5],
        row["EMPLOYER"].upper(),
        row["OCCUPATION"].upper(),
        str(Decimal(row["TRANSACTION_AMT"])),
        row["TRANSACTION_DT"],
    )


def is_dated(row: Row) -> bool:
    """Whether `row`'s TRANSACTION_DT is a date, MMDDYYYY."""
    try:
        datetime.strptime(row["TRANSACTION_DT"], "%m%d%Y")
    except ValueError:
        return False
    return True


@functools.cache
def superseded_filings() -> frozenset[str]:
    """The filings a later amendment supersedes, by FILE_NUM (NEU-2196): an electronic filing
    (FILE_NUM above 0) when a later-numbered one at the same committee, itself an amendment
    (AMNDT_IND A), holds the gift of at least half its rows, no memo line or 24T. A row with no
    date that parses repeats none."""
    filings: defaultdict[str, list[Row]] = defaultdict(list)
    for row in rows("indiv"):
        if (
            row["MEMO_CD"] != "X"
            and row["TRANSACTION_TP"] != "24T"
            and int(row["FILE_NUM"] or 0) > 0
        ):
            filings[row["FILE_NUM"]].append(row)
    superseded: set[str] = set()
    for earlier, filed in filings.items():
        for later, amended in filings.items():
            if (
                int(later) > int(earlier)
                and amended[0]["CMTE_ID"] == filed[0]["CMTE_ID"]
                and any(r["AMNDT_IND"] == "A" for r in amended)
            ):
                gifts = {gift(r) for r in amended if is_dated(r)}
                repeated = sum(is_dated(r) and gift(r) in gifts for r in filed)
                if 2 * repeated >= len(filed):
                    superseded.add(earlier)
    return frozenset(superseded)


def is_superseded(row: Row) -> bool:
    """An `indiv` row on a filing a later amendment supersedes (NEU-2196)."""
    return row["FILE_NUM"] in superseded_filings()


def says_attribution(memo_text: str) -> bool:
    """A memo that calls its line an attribution, and not a reattribution (NEU-2198)."""
    text = memo_text.upper()
    return re.search(r"(^|[^E])ATTRIBUTION", text) is not None and "REATTRIBUT" not in text


@functools.cache
def orphaned_attributions() -> frozenset[str]:
    """The memo lines that are the only record of a gift, by SUB_ID (NEU-2198): a gift typed 10
    or 15 from an individual, organization or candidate, of more than $0, whose memo says it is an
    attribution, or which has none, is typed 10 and is one of two or more names sharing its filing,
    date and employer, not blank; and that attributes nothing either file holds. It attributes a
    row, not a memo line, on its filing, dated the same or within a page of it, whose amount is its
    own or its group's (its filing's memo lines of its date, an organization's apart from anyone
    else's), within $1 a line; or such an organization's memo line, unless it is an organization's
    itself; or it restates a counted-shape row of its committee with its name and amount."""
    indiv, oth = rows("indiv"), rows("oth")
    memo = [r for r in indiv if r["MEMO_CD"] == "X" and r["FILE_NUM"]]

    def is_org(row: Row) -> bool:
        return row["ENTITY_TP"].strip() == ORGANIZATION

    lines = [
        r
        for r in memo
        if r["TRANSACTION_TP"] in ("10", "15")
        and (r["ENTITY_TP"].strip() or "IND") in ("IND", ORGANIZATION, "CAN")
    ]
    groups: defaultdict[tuple[str, str, str, bool], list[Row]] = defaultdict(list)
    names: defaultdict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for r in lines:
        groups[r["CMTE_ID"], r["FILE_NUM"], r["TRANSACTION_DT"], is_org(r)].append(r)
        names[r["CMTE_ID"], r["FILE_NUM"], r["TRANSACTION_DT"], r["EMPLOYER"].strip().upper()].add(
            name_key(r["NAME"])
        )
    parents = [(r, False) for f in (indiv, oth) for r in f if r["MEMO_CD"] != "X"] + [
        (r, True) for r in memo if is_org(r)
    ]
    orphaned: set[str] = set()
    for r in lines:
        group = groups[r["CMTE_ID"], r["FILE_NUM"], r["TRANSACTION_DT"], is_org(r)]
        total = sum(amount(g) for g in group)
        shaped = says_attribution(r["MEMO_TEXT"]) or (
            not r["MEMO_TEXT"].strip()
            and r["TRANSACTION_TP"] == "10"
            and r["EMPLOYER"].strip()
            and len(
                names[
                    r["CMTE_ID"], r["FILE_NUM"], r["TRANSACTION_DT"], r["EMPLOYER"].strip().upper()
                ]
            )
            >= 2
        )
        attributes = any(
            p["CMTE_ID"] == r["CMTE_ID"]
            and p["FILE_NUM"] == r["FILE_NUM"]
            and not (is_memo and is_org(r))
            and (
                abs(int(p["IMAGE_NUM"]) - int(r["IMAGE_NUM"])) <= 1
                or p["TRANSACTION_DT"] == r["TRANSACTION_DT"]
            )
            and (amount(p) == amount(r) or abs(amount(p) - total) <= len(group))
            for p, is_memo in parents
        )
        restates = any(
            o["CMTE_ID"] == r["CMTE_ID"]
            and o["MEMO_CD"] != "X"
            and o["TRANSACTION_TP"] != "24T"
            and amount(o) == amount(r)
            and name_key(o["NAME"]) == name_key(r["NAME"])
            for o in indiv
        )
        if amount(r) > 0 and shaped and not attributes and not restates:
            orphaned.add(r["SUB_ID"])
    return frozenset(orphaned)


@functools.cache
def reversals() -> frozenset[str]:
    """The negative refunds that void a positive one, by SUB_ID. Each positive refund is voided
    once (NEU-2269): among the refunds to one giver at one committee of one size, the negatives in
    order of date, then SUB_ID, void as many as there are positive ones. A further negative is a
    refund like any other."""
    groups: defaultdict[tuple[str, str, int], list[Row]] = defaultdict(list)
    for row in rows("indiv"):
        if is_refund(row) and row["MEMO_CD"] != "X" and row["NAME"] and not is_superseded(row):
            groups[row["CMTE_ID"], row["NAME"], abs(amount(row))].append(row)
    voids: set[str] = set()
    for group in groups.values():
        negatives = sorted(
            (r for r in group if amount(r) < 0),
            key=lambda r: (datetime.strptime(r["TRANSACTION_DT"], "%m%d%Y"), int(r["SUB_ID"])),
        )
        voids.update(r["SUB_ID"] for r in negatives[: sum(amount(r) > 0 for r in group)])
    return frozenset(voids)


def signed(row: Row) -> int:
    """A contribution's amount as it counts. A refund (22Y, or any 2nY or 4nY type) subtracts
    whichever sign its filer wrote, unless it is negative and voids a positive refund to the same
    giver at the same committee (`reversals`): then it adds back. A loan repaid to the candidate
    (20C) subtracts as filed, so a negative one, a correction, adds back (NEU-2071)."""
    if row["TRANSACTION_TP"] == LOAN_REPAYMENT:
        return -amount(row)
    if not is_refund(row):
        return amount(row)
    return -amount(row) if row["SUB_ID"] in reversals() else -abs(amount(row))


@functools.cache
def linked_candidates() -> Mapping[str, str]:
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
    return MappingProxyType(linked)


def candidate_of(committee_id: str, row: Row) -> str | None:
    """The candidate `row`'s money to `committee_id` is credited to: the one `ccl` links it to, or,
    for a handed-off committee, the candidate it was handed from before the handoff date and the
    one it was handed to on and after it, and an undated row's the latter's (NEU-2126)."""
    if committee_id in HANDOFFS:
        before, after, handoff = HANDOFFS[committee_id]
        dated = row["TRANSACTION_DT"]
        return before if dated and datetime.strptime(dated, "%m%d%Y").date() < handoff else after
    return linked_candidates().get(committee_id)


def is_conduit_side(row: Row) -> bool:
    """A conduit's own line for an earmark it passed on, filed as a 15 naming the recipient."""
    return (
        row["CMTE_ID"] in CONDUITS.values()
        and re.search(r"EARMARKED FOR .*\(C\d{8}\)", row["MEMO_TEXT"]) is not None
    )


def is_intermediary_earmark(row: Row) -> bool:
    """An intermediary's 24I that its recipient itemized too (NEU-2203): OTHER_ID a committee of
    the cycle, no conduit and not the filer, holding a row of the same name and amount, no memo
    line, refund, 24T or 24I, dated within 30 days of it."""
    others = committee_ids() - set(CONDUITS.values()) - {row["CMTE_ID"]}
    if row["TRANSACTION_TP"] != "24I" or row["MEMO_CD"] == "X" or row["OTHER_ID"] not in others:
        return False
    dated = datetime.strptime(row["TRANSACTION_DT"], "%m%d%Y").date()
    return any(
        twin["CMTE_ID"] == row["OTHER_ID"]
        and twin["MEMO_CD"] != "X"
        and twin["TRANSACTION_TP"] not in ("24T", "24I")
        and not is_refund(twin)
        and name_key(twin["NAME"]) == name_key(row["NAME"])
        and amount(twin) == amount(row)
        and twin["TRANSACTION_DT"] != ""
        and abs((datetime.strptime(twin["TRANSACTION_DT"], "%m%d%Y").date() - dated).days) <= 30
        for twin in rows("indiv")
    )


def is_conduit_earmark_refund(row: Row) -> bool:
    """A conduit's refund of an earmark (NEU-2199): a refund at a conduit mirroring no gift of the
    conduit's own there (no memo line, 24T or line for an earmark) by name key and amount."""
    if row["CMTE_ID"] not in CONDUITS.values() or not is_refund(row) or row["MEMO_CD"] == "X":
        return False
    return not any(
        own["CMTE_ID"] == row["CMTE_ID"]
        and own["MEMO_CD"] != "X"
        and own["TRANSACTION_TP"] != "24T"
        and abs(amount(own)) == abs(amount(row))
        and not is_refund(own)
        and not is_conduit_side(own)
        and name_key(own["NAME"]) == name_key(row["NAME"])
        for own in rows("indiv")
    )


def counts(row: Row) -> bool:
    """An `indiv` row that counts, whoever gave it: no memo line but an orphaned attribution, no
    conduit's 24T, no intermediary's 24I its recipient itemized too, no conduit's own line for an
    earmark or refund of one, on no superseded filing, to a committee of the cycle."""
    return (
        (row["MEMO_CD"] != "X" or row["SUB_ID"] in orphaned_attributions())
        and row["TRANSACTION_TP"] != "24T"
        and row["CMTE_ID"] in committee_ids()
        and not is_conduit_side(row)
        and not is_intermediary_earmark(row)
        and not is_conduit_earmark_refund(row)
        and not is_superseded(row)
    )


def non_contribution_account(table: Iterable[Row]) -> list[Row]:
    """The rows of one table, the counted contributions or the organization receipts, a hybrid PAC
    took into or refunded from its non-contribution account (NEU-2192): a 10, 10J or 20Y to or
    from a committee typed V or W, or a 24I there whose memo names the account (NEU-2207), whoever
    the giver. At any other committee a 10 is an ordinary contribution."""
    types = {committee["CMTE_ID"]: committee["CMTE_TP"] for committee in rows("cm")}
    return [
        row
        for row in table
        if types.get(row["CMTE_ID"]) in HYBRID_PACS
        and (
            row["TRANSACTION_TP"] in NON_CONTRIBUTION_ACCOUNT
            or (
                row["TRANSACTION_TP"] == "24I"
                and row["MEMO_TEXT"].upper().startswith(NON_CONTRIBUTION_MEMO)
            )
        )
    ]


def is_other_line(row: Row) -> bool:
    """A counted row or organization receipt whose type FEC files on a line no total_individual
    or total_from_organizations counts (NEU-2193, NEU-2205); a candidate's own money is
    self-funding whatever its line."""
    return re.fullmatch(OTHER_LINES, row["TRANSACTION_TP"]) is not None


def is_classified(row: Row) -> bool:
    """An `indiv` row filed with no entity type whose name the classifier calls an
    organization's (NEU-2132)."""
    return not row["ENTITY_TP"].strip() and normalize.is_organization_name(row["NAME"])


def is_individual(row: Row) -> bool:
    """An `indiv` row from an individual or a candidate: typed IND or CAN, or blank and not
    classified (NEU-2132)."""
    return row["ENTITY_TP"] in ("IND", "CAN") or (
        not row["ENTITY_TP"].strip() and not is_classified(row)
    )


@functools.cache
def candidate_loans() -> tuple[Row, ...]:
    """The `oth` rows that are a candidate's loan to their campaign or its repayment (NEU-2071):
    typed 16C or 20C, whoever the row names as giver, no memo line, to a committee of the cycle,
    and mirroring no `indiv` row of the same type (same committee, amount and date)."""
    mirrored = {
        (r["CMTE_ID"], r["TRANSACTION_TP"], amount(r), r["TRANSACTION_DT"])
        for r in rows("indiv")
        if r["TRANSACTION_TP"] in CANDIDATE_LOANS and r["MEMO_CD"] != "X"
    }
    return tuple(
        row
        for row in rows("oth")
        if row["TRANSACTION_TP"] in CANDIDATE_LOANS
        and row["MEMO_CD"] != "X"
        and row["CMTE_ID"] in committee_ids()
        and (row["CMTE_ID"], row["TRANSACTION_TP"], amount(row), row["TRANSACTION_DT"])
        not in mirrored
    )


@functools.cache
def counted_indiv() -> tuple[Row, ...]:
    """The `indiv` rows the contribution table keeps: individuals and candidates, earmarks once,
    to committees of the cycle. DIME labels these, and no `oth` row."""
    return tuple(row for row in rows("indiv") if is_individual(row) and counts(row))


@functools.cache
def counted() -> tuple[Row, ...]:
    """The rows the contribution table keeps: `counted_indiv`, and the candidates' loans and
    repayments in `oth` (NEU-2071)."""
    return (*counted_indiv(), *candidate_loans())


def name_key(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", name.upper())


def person(name: str) -> tuple[str, str]:
    """A `cn` name's last name and first given name, as the self-funding test compares them."""
    last, _, given = name.partition(",")
    return name_key(last), name_key(given.strip().partition(" ")[0])


@functools.cache
def aliases() -> Mapping[str, str]:
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
    return MappingProxyType(found)


def is_receipt_line(row: Row) -> bool:
    """An `oth` row of a receipt type (1x, or 3x for a party's accounts) that is no memo line."""
    return row["TRANSACTION_TP"][:1] in ("1", "3") and row["MEMO_CD"] != "X"


def named_committee(
    row: Row, *, classified: bool = False, organization: bool = False
) -> str | None:
    """The one `cm` committee a row typed PAC, COM, CCM or PTY with a blank OTHER_ID names
    (NEU-2131), or a `classified` `indiv` row does (NEU-2132), never its own recipient; None when
    it names several, none, or itself. An `organization` `indiv` row, typed ORG with no committee
    id (OTHER_ID blank or not C-prefixed), is read against the political committees alone
    (NEU-2195): typed, and of no type in NOT_POLITICAL."""
    if organization:
        if row["OTHER_ID"].startswith("C"):
            return None
    elif (row["ENTITY_TP"] not in COMMITTEE_TYPES and not classified) or row["OTHER_ID"]:
        return None
    named = [
        r["CMTE_ID"]
        for r in rows("cm")
        if name_key(r["CMTE_NM"]) == name_key(row["NAME"])
        and (not organization or r["CMTE_TP"].strip() not in ("", *NOT_POLITICAL))
    ]
    return named[0] if len(named) == 1 and named[0] != row["CMTE_ID"] else None


def has_twin(row: Row, committee_id: str) -> bool:
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


def giver(row: Row) -> str | None:
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


def committee_receipts() -> list[Row]:
    """The `oth` rows that are receipts from another committee: a receipt type (1x, or 3x for a
    party's accounts), not a memo line, from a giver."""
    return [row for row in rows("oth") if is_receipt_line(row) and giver(row) is not None]


@functools.cache
def name_matched() -> Mapping[str, str | None]:
    """Each counted `indiv` row typed PAC, COM, CCM or PTY with a blank OTHER_ID, by SUB_ID, and
    the committee it is a receipt from (NEU-2131): the one its NAME names, unless `oth` holds the
    gift under that id already; None when it is dropped. A classified row (NEU-2132), or one typed
    ORG (NEU-2195), is here only when its NAME names one committee: naming none, it is an
    organization receipt."""
    found: dict[str, str | None] = {}
    for row in rows("indiv"):
        if not counts(row):
            continue
        if row["ENTITY_TP"] == ORGANIZATION:
            named = named_committee(row, organization=True)
            if named is None:
                continue
        elif row["OTHER_ID"]:
            continue
        elif row["ENTITY_TP"] in COMMITTEE_TYPES:
            named = named_committee(row)
        elif is_classified(row):
            named = named_committee(row, classified=True)
            if named is None:
                continue
        else:
            continue
        found[row["SUB_ID"]] = named if named and not has_twin(row, named) else None
    return MappingProxyType(found)


def name_matched_gifts() -> list[Row]:
    """The `indiv` rows that are committee_transfer receipts by the name rule."""
    kept = {sub_id for sub_id, committee_id in name_matched().items() if committee_id}
    return [row for row in rows("indiv") if row["SUB_ID"] in kept]


def mirrors_counted_row(row: Row) -> bool:
    """Whether a counted `indiv` row is the same gift as `oth`'s `row`: same recipient, name,
    amount and date (NEU-2131), so the receipt is read once, from `indiv`."""
    return any(
        other["CMTE_ID"] == row["CMTE_ID"]
        and other["TRANSACTION_AMT"] == row["TRANSACTION_AMT"]
        and other["TRANSACTION_DT"] == row["TRANSACTION_DT"]
        and name_key(other["NAME"]) == name_key(row["NAME"])
        and counts(other)
        for other in rows("indiv")
    )


@functools.cache
def organization_receipts() -> tuple[Row, ...]:
    """The rows of either file that are organization receipts (NEU-2131, ADR-0011): a counted
    `indiv` row typed ORG and naming no one political committee (NEU-2195), or classified and
    naming no one committee (NEU-2132), or an `oth`
    receipt typed ORG from no committee id, naming no JFC, neither an attribution line nor a
    loan, to a committee of the cycle, mirroring no counted `indiv` row."""
    return tuple(
        row
        for row in rows("indiv")
        if counts(row)
        and (
            (row["ENTITY_TP"] == ORGANIZATION and named_committee(row, organization=True) is None)
            or (is_classified(row) and named_committee(row, classified=True) is None)
        )
    ) + tuple(
        row
        for row in rows("oth")
        if is_receipt_line(row)
        and row["ENTITY_TP"] == ORGANIZATION
        and not row["OTHER_ID"].startswith("C")
        and giver(row) is None
        and row["TRANSACTION_TP"] not in NOT_GIFTS
        and row["CMTE_ID"] in committee_ids()
        and not mirrors_counted_row(row)
    )


def attributions() -> list[Row]:
    """The `oth` rows that are JFC attributions (spec §6.11): 15J memo lines from an individual
    (IND, or blank and not classified, NEU-2132) filed by a committee of the cycle."""
    return [
        row
        for row in rows("oth")
        if row["TRANSACTION_TP"] == "15J"
        and row["MEMO_CD"] == "X"
        and (row["ENTITY_TP"] == "IND" or (not row["ENTITY_TP"] and not is_classified(row)))
        and row["CMTE_ID"] in committee_ids()
    ]


def is_self_funding(row: Row) -> bool:
    """A candidate's own money: a 15C, a 16C loan or its 20C repayment whoever it names (NEU-2194,
    NEU-2071), or a CAN row under the name of the candidate its recipient raises for."""
    if row["TRANSACTION_TP"] in CANDIDATE_TYPES:
        return True
    names = {r["CAND_ID"]: r["CAND_NAME"] for r in rows("cn")}
    candidate = candidate_of(row["CMTE_ID"], row)
    return row["ENTITY_TP"] == "CAN" and candidate is not None and names[candidate] == row["NAME"]


def conduit(row: Row) -> str | None:
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


@functools.cache
def race_ids() -> Mapping[str, str | None]:
    """Candidate → the regular race its filing's seat names, or None when the seat is no race."""
    seats = {race.seat: race.race_id for race in races_for(CYCLE) if not race.is_special}
    return MappingProxyType(
        {
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
    )


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
        if not is_self_funding(r) and r["SUB_ID"] not in account and not is_other_line(r)
    )
    self_funding = sum_by((r["CMTE_ID"], signed(r)) for r in contributions if is_self_funding(r))
    from_committees = sum_by(
        (r["CMTE_ID"], amount(r)) for r in [*committee_receipts(), *name_matched_gifts()]
    )
    pas2 = rows("pas2")
    to_candidates = sum_by((giver, net) for (giver, _), net in gift_pairs().items() if net >= 0)
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


def committee_contributions() -> list[Row]:
    """The `pas2` 24K rows that are a committee's gift: not a conduit's, whose 24K is its side of
    an earmark it passed on, counted on the recipient's `indiv` row (ADR-0004)."""
    return [
        r
        for r in rows("pas2")
        if r["TRANSACTION_TP"] == COMMITTEE_CONTRIBUTION and r["CMTE_ID"] not in CONDUITS.values()
    ]


def gift_candidate(row: Row) -> str | None:
    """The candidate a 24K is credited to: the one its recipient committee is linked to, else the
    giver's CAND_ID when that is a candidate of the cycle (the one it is an alias of, when it is an
    alias), else none."""
    candidates = {r["CAND_ID"] for r in rows("cn")}
    linked = candidate_of(row["OTHER_ID"], row)
    if linked in candidates:
        return linked
    stated = row["CAND_ID"]
    return aliases().get(stated, stated) if stated in candidates else None


def gift_pairs() -> dict[tuple[str, str], int]:
    """Each giver's 24Ks to each candidate, net for the cycle. A pair below 0 is returns of an
    earlier cycle's gifts, not gifts (NEU-2204)."""
    return sum_by(
        ((r["CMTE_ID"], c), amount(r))
        for r in committee_contributions()
        if (c := gift_candidate(r)) is not None
    )


def ie_candidate(row: Row) -> str | None:
    """The candidate an independent expenditure is for or against: the one it names."""
    return row["CAND_ID"]


def tally_candidates() -> dict[str, CandidateTotals]:
    pas2 = rows("pas2")
    contributions = counted()
    individual = sum_by(
        (c, signed(r))
        for r in contributions
        if not is_self_funding(r)
        and not is_other_line(r)
        and (c := candidate_of(r["CMTE_ID"], r)) is not None
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
        (candidate, net) for (_, candidate), net in gift_pairs().items() if net >= 0
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


def contributor_key(row: Row) -> str:
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
        "dropped_memo": sum(
            r["MEMO_CD"] == "X" and r["SUB_ID"] not in orphaned_attributions() for r in indiv
        ),
        "orphaned_attribution": len(orphaned_attributions()),
        "dropped_conduit_24t": sum(r["TRANSACTION_TP"] == "24T" for r in indiv),
        "dropped_intermediary_24i": sum(is_intermediary_earmark(r) for r in indiv),
        "dropped_conduit_side": sum(
            is_conduit_side(r) and r["TRANSACTION_TP"] != "24T" for r in indiv
        ),
        "dropped_conduit_refund": sum(is_conduit_earmark_refund(r) for r in indiv),
        "dropped_superseded": sum(is_superseded(r) for r in indiv),
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


def test_the_expected_other_lines_are_the_counted_rows_off_line_11ai() -> None:
    other = [r for r in counted() if is_other_line(r) and not is_self_funding(r)]
    receipts = [r for r in organization_receipts() if is_other_line(r)]
    expected = EXPECTED["other_lines"]
    assert expected["contributions"] == [int(r["SUB_ID"]) for r in other]
    assert expected["organization_receipts"] == [int(r["SUB_ID"]) for r in receipts]
    assert expected["by_committee"] == sum_by(
        (r["CMTE_ID"], signed(r)) for r in [*other, *receipts]
    )
    assert expected["organizations_by_committee"] == sum_by(
        (r["CMTE_ID"], signed(r)) for r in receipts
    )
    # An organization's gift to a party account is off line 11(a)(i) from either file, whatever
    # its variant; its 15 to the same party is on it, in total_from_organizations (NEU-2205).
    assert {(r["TRANSACTION_TP"], r["SUB_ID"][:5]) for r in receipts} >= {
        ("31T", "42401"),
        ("32J", "42403"),
    }
    assert any(
        r["TRANSACTION_TP"] == "15" and r["CMTE_ID"] in expected["organizations_by_committee"]
        for r in organization_receipts()
        if not is_other_line(r)
    )
    # A party account's refund goes with its receipts, and a loan with the candidate's committee:
    # both are the donor's money all the same, in no total_individual.
    assert {r["TRANSACTION_TP"] for r in other} >= {"31", "41Y", "16G"}
    assert any(linked_candidates().get(r["CMTE_ID"]) for r in other)


def test_the_expected_returns_are_the_24ks_of_pairs_netting_below_0() -> None:
    pairs = gift_pairs()
    returned = [
        r
        for r in committee_contributions()
        if (c := gift_candidate(r)) is not None and pairs[r["CMTE_ID"], c] < 0
    ]
    expected = EXPECTED["returned_by_candidates"]
    assert expected["disbursements"] == [int(r["SUB_ID"]) for r in returned]
    assert expected["by_committee"] == sum_by((r["CMTE_ID"], amount(r)) for r in returned)
    # A same-cycle refund nets inside its pair: BRICKLAYERS' to YANG is no return.
    assert pairs["C00800202", "H4MD05108"] == 2000
    assert any(amount(r) < 0 for r in committee_contributions() if r not in returned)


def test_the_expected_refunds_are_the_counted_refunds_on_line_20() -> None:
    contributions = counted()
    receipts = organization_receipts()
    account = {r["SUB_ID"] for r in non_contribution_account([*contributions, *receipts])}

    def in_totals(row: Row) -> bool:
        return row["SUB_ID"] not in account and not is_other_line(row)

    refunds = [r for r in contributions if is_refund(r) and not is_self_funding(r) and in_totals(r)]
    organization_refunds = [r for r in receipts if is_refund(r) and in_totals(r)]
    expected = EXPECTED["refunds"]
    assert expected["contributions"] == [int(r["SUB_ID"]) for r in refunds]
    assert expected["organization_receipts"] == [int(r["SUB_ID"]) for r in organization_refunds]
    assert expected["by_committee"] == sum_by(
        (r["CMTE_ID"], signed(r)) for r in [*refunds, *organization_refunds]
    )
    # The non-contribution account's 20Y and a party account's 41Y are refunds too, in neither
    # total, so in no total_refunds.
    assert {
        r["TRANSACTION_TP"]
        for r in [*contributions, *receipts]
        if is_refund(r) and not in_totals(r)
    } >= {"20Y", "41Y"}


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
    # Three join committee_transfer, one of them a classified blank-type row (NEU-2132) and one an
    # ORG row (NEU-2195); one names no committee; one names its own recipient.
    kept = [c for c in EXPECTED["name_matched"].values() if c]
    assert len(kept) == 3 and len(EXPECTED["name_matched"]) == 5
    by_sub_id = {int(r["SUB_ID"]): r for r in rows("indiv")}
    assert any(is_classified(by_sub_id[s]) for s, c in EXPECTED["name_matched"].items() if c)
    by_id = {r["SUB_ID"]: r for r in rows("indiv")}
    names = {r["CMTE_ID"]: name_key(r["CMTE_NM"]) for r in rows("cm")}
    dropped = [by_id[str(s)] for s, c in EXPECTED["name_matched"].items() if c is None]
    assert sorted(name_key(r["NAME"]) == names[r["CMTE_ID"]] for r in dropped) == [False, True]


def test_an_org_row_is_a_committees_gift_only_when_it_names_a_political_committee() -> None:
    # NEU-2195: both rows are typed ORG with no OTHER_ID, and each NAME names exactly one `cm`
    # committee. RESTORATION PAC is a super PAC: its gift is a committee_transfer receipt.
    # ONE NATION files Form 5 (type I), no political committee: an organization receipt still.
    # A Form 9 filer (type E) shares RESTORATION PAC's name: read against the political
    # committees alone, the name names the super PAC.
    by_name = {r["NAME"]: r for r in rows("indiv") if r["ENTITY_TP"] == ORGANIZATION}
    types: defaultdict[str, list[str]] = defaultdict(list)
    for r in rows("cm"):
        types[r["CMTE_NM"]].append(r["CMTE_TP"])
    restoration, one_nation = by_name["RESTORATION PAC"], by_name["ONE NATION"]
    assert (types["RESTORATION PAC"], types["ONE NATION"]) == (["O", "E"], ["I"])
    assert not restoration["OTHER_ID"] and not one_nation["OTHER_ID"]

    assert EXPECTED["name_matched"][int(restoration["SUB_ID"])] == "C00800205"
    assert int(restoration["SUB_ID"]) not in EXPECTED["organization_receipts"]["keys"]
    assert int(one_nation["SUB_ID"]) not in EXPECTED["name_matched"]
    assert int(one_nation["SUB_ID"]) in EXPECTED["organization_receipts"]["keys"]


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
    for row in counted_indiv():
        [cids[int(row["SUB_ID"])]] = labels[row["CMTE_ID"], row["TRAN_ID"]]
    return cids


def donor_cids() -> dict[int, str]:
    """Each counted contribution's DIME donor: its label (`dime_cids`), or, for a candidate's loan
    or repayment from `oth`, which DIME does not label, the one donor the labelled rows of its
    contributor key are."""
    cids = dime_cids()
    by_key: defaultdict[str, set[str]] = defaultdict(set)
    for row in counted_indiv():
        by_key[contributor_key(row)].add(cids[int(row["SUB_ID"])])
    for row in candidate_loans():
        [cids[int(row["SUB_ID"])]] = by_key[contributor_key(row)]
    return cids


def test_every_counted_indiv_contribution_has_exactly_one_dime_label() -> None:
    assert len(dime_rows()) == len(counted_indiv())
    cids = dime_cids()
    assert len(cids) == len(counted_indiv())
    assert EXPECTED["distinct_donors"] == len(set(cids.values()))


def test_each_donor_grouping_is_its_contributions_and_one_dime_donor() -> None:
    by_sub_id = {int(r["SUB_ID"]): r for r in counted()}
    cids = donor_cids()
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
    dated = [r for r in counted_indiv() if r["TRANSACTION_DT"]]
    assert len(dated) < len(counted_indiv()) == len(dime_cids())
    assert validation["matched_rows"] == len(dated)
    cids = dime_cids()
    assert validation["labelled_keys"] == len(
        {(contributor_key(r), cids[int(r["SUB_ID"])]) for r in dated}
    )
