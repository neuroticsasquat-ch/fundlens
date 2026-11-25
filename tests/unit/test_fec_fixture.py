"""The synthetic 2024 fixture cycle: its files match FEC's layout and `expected.yaml` adds up.

The tally here is an independent reading of the fixture CSVs under the spec §4 rules, written
only to keep `expected.yaml` honest: edit a fixture row and this fails until the expected totals
are updated to match. It is not the pipeline, and nothing outside this module uses it.
"""

import csv
import functools
import io
import re
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal
from importlib.resources import files as package_files
from pathlib import Path
from types import MappingProxyType
from typing import Any, get_args

import pytest

from fundlens.fec.files import CATALOGUE, FecFile
from fundlens.load import gold
from fundlens.resolve import normalize
from fundlens.transform.seats import Filing, races_for
from tests import fec_fixture
from tests.fec_fixture import (
    CYCLE,
    CandidateTotals,
    CommitteeTotals,
    RaceTotals,
    Row,
)

FILES: tuple[FecFile, ...] = get_args(FecFile)
ZIPS = tuple(name for name in FILES if CATALOGUE[name].format == "zip")
CSVS = tuple(name for name in FILES if CATALOGUE[name].format == "csv")
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
# A 10 or 10J under a memo beginning with the account's name, in any filed spelling, is the
# account's at any committee: the filer's mark, which the cycle's `cm` type can miss (NEU-2400).
ACCOUNT_RECEIPTS = ("10", "10J")
NAMES_THE_ACCOUNT = r"[^A-Z]*NON[- ]?CONTRIBUTION ACCOUNT"
# The transaction types FEC files on a line no total_individual counts (NEU-2193): loans, transfers
# and other non-contribution receipts, Form 9 donations, and a national party's convention,
# headquarters and recount accounts (30, 31, 32 and variants) and their refunds.
OTHER_LINES = r"16[CFGHJKLR]|18[GHJKLU]|19J?|3[012][A-Z]?|4[012]Y"
# The Schedule A line a filer's TRAN_ID names (NEU-2276), and the ones no total counts: 11(b),
# 11(c), 12 to 17 and Schedule L, not 11(a)(i), 11(d) or Form 3P's individuals' line 17(a).
NAMED_LINE = r"SA(11AI|11A1|11B|11C|11D|12|13|14|15|16|17A|17|SL)"
OTHER_NAMED_LINES = frozenset({"11B", "11C", "12", "13", "14", "15", "16", "17", "SL"})
# A memo naming a cost coming back to the committee, not a gift (NEU-2402, `fec.lines`): on line 15
# when its type puts it on 11(a)(i), and on no top-organization list.
RETURNED_COST = (
    r"(TAX|VENDOR|MEDIA|EXPENSE|FEES?) (REFUND|REBATE|REIMBURSEMENT)|REFUNDED (EXPENSE|FEES)"
    r"|(REFUND|REBATE|REIMBURSEMENT)S? (OF|FOR) [^;.,]{0,40}(EXPENSE|FEES|PURCHASE|DISBURSEMENT)"
)
# The vendored handoff list (fec/handoffs.csv) as the tally reads it: a committee handed from one
# candidate to another, the first's before the date and the second's on and after it (NEU-2126).
HANDOFFS = {"C00703975": ("P80000722", "P00009423", date(2024, 7, 21))}
# The fixture's rows of the vendored correction list (fec/ie_candidate_corrections.csv) as the tally
# reads it: SUB_ID → (the candidate `pas2` codes, the one the filing names) (NEU-2279).
IE_CORRECTIONS = {
    "4111920241070657390": ("P80000722", "P00009423"),
    "4060220251204384159": ("P80000722", "P80001571"),
}

EXPECTED = fec_fixture.expected()


@functools.cache
def rows(file: FecFile) -> tuple[Row, ...]:
    """`file`'s rows as the transform reads them: an itemized file's without FEC's repeats."""
    published, repeats = fec_fixture.read_rows(file), fec_repeats(file)
    return tuple(row for row in published if not repeats or row["SUB_ID"] not in repeats)


@functools.cache
def fec_repeats(file: FecFile) -> frozenset[str]:
    """The SUB_IDs of the rows FEC's file repeats (NEU-2401): of an itemized file's rows on one
    electronic filing (FILE_NUM above 0) under one TRAN_ID, the same in every column but SUB_ID,
    every one but the lowest SUB_ID. Rows with no TRAN_ID repeat none."""
    if "TRAN_ID" not in CATALOGUE[file].columns:
        return frozenset()
    first: set[tuple[str, ...]] = set()
    repeats: set[str] = set()
    for row in sorted(fec_fixture.read_rows(file), key=lambda r: int(r["SUB_ID"])):
        if int(row["FILE_NUM"] or 0) <= 0 or not row["TRAN_ID"].strip():
            continue
        transaction = tuple(value for column, value in row.items() if column != "SUB_ID")
        if transaction in first:
            repeats.add(row["SUB_ID"])
        first.add(transaction)
    return frozenset(repeats)


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
    once (NEU-2269): among the refunds to one giver at one committee of one type and size, the
    negatives in order of date, then SUB_ID, void as many as there are positive ones. A further
    negative is a refund like any other, and so is a negative of another type: a void is filed as
    the type of the refund it voids (NEU-2320)."""
    groups: defaultdict[tuple[str, str, str, int], list[Row]] = defaultdict(list)
    for row in rows("indiv"):
        if is_refund(row) and row["MEMO_CD"] != "X" and row["NAME"] and not is_superseded(row):
            groups[row["CMTE_ID"], row["NAME"], row["TRANSACTION_TP"], abs(amount(row))].append(row)
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
    whichever sign its filer wrote, unless it is negative and voids a positive refund of its type to
    the same giver at the same committee (`reversals`): then it adds back. A loan repaid to the
    candidate (20C) subtracts as filed, so a negative one, a correction, adds back (NEU-2071)."""
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
    the giver; or a 10 or 10J at any committee whose memo begins with the account's name
    (NEU-2400). At any other committee a 10 is an ordinary contribution."""
    types = {committee["CMTE_ID"]: committee["CMTE_TP"] for committee in rows("cm")}
    return [
        row
        for row in table
        if (
            types.get(row["CMTE_ID"]) in HYBRID_PACS
            and (
                row["TRANSACTION_TP"] in NON_CONTRIBUTION_ACCOUNT
                or (
                    row["TRANSACTION_TP"] == "24I"
                    and row["MEMO_TEXT"].upper().startswith(NON_CONTRIBUTION_MEMO)
                )
            )
        )
        or (
            row["TRANSACTION_TP"] in ACCOUNT_RECEIPTS
            and re.match(NAMES_THE_ACCOUNT, row["MEMO_TEXT"].upper()) is not None
        )
    ]


def is_other_line(row: Row) -> bool:
    """A counted row or organization receipt whose type FEC files on a line no total_individual
    or total_from_organizations counts (NEU-2193, NEU-2205), or whose TRAN_ID names one, outside a
    hybrid PAC's non-contribution account (NEU-2276), or whose memo names a cost coming back
    there (NEU-2402); a candidate's own money is self-funding whatever its line."""
    if re.fullmatch(OTHER_LINES, row["TRANSACTION_TP"]) is not None:
        return True
    if non_contribution_account([row]):
        return False
    named = re.match(NAMED_LINE, row["TRAN_ID"])
    if named is not None and named.group(1) in OTHER_NAMED_LINES:
        return True
    return row["TRANSACTION_TP"] not in CANDIDATE_TYPES and is_returned_cost(row)


def is_returned_cost(row: Row) -> bool:
    """An organization receipt or counted row, no refund, whose memo names a cost coming back to
    the committee: a tax, vendor or expense refund (NEU-2402)."""
    return (
        not is_refund(row)
        and row["TRANSACTION_TP"] != "22Z"
        and re.search(RETURNED_COST, row["MEMO_TEXT"].upper()) is not None
    )


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
    party's accounts), not a memo line, from a giver, filed by a committee in `cm`: the filer is
    the recipient (NEU-2281)."""
    return [
        row
        for row in rows("oth")
        if is_receipt_line(row) and giver(row) is not None and row["CMTE_ID"] in committee_ids()
    ]


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


def sum_dollars[K](pairs: Iterable[tuple[K, Decimal]]) -> dict[K, Decimal]:
    """`sum_by` for amounts with cents: the 24/48-hour file's (NEU-2165)."""
    totals: dict[K, Decimal] = defaultdict(Decimal)
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
    ie = sum_dollars(
        [
            *(
                (r["CMTE_ID"], Decimal(amount(r)))
                for r in pas2
                if r["TRANSACTION_TP"] in (IE_SUPPORT, IE_OPPOSE)
            ),
            *((r["spe_id"], Decimal(r["exp_amo"])) for r, _ in ie_24_48_added()),
        ]
    )
    return {
        committee_id: {
            "total_individual": individual.get(committee_id, 0),
            "self_funding": self_funding.get(committee_id, 0),
            "total_from_committees": from_committees.get(committee_id, 0),
            "total_to_candidates": to_candidates.get(committee_id, 0),
            "ie_total": float(ie.get(committee_id, 0)),
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
    """The candidate an independent expenditure is for or against: the one it names, or its filing
    names where `pas2` still codes it as the correction list says (NEU-2279), unless a committee was
    handed from them, and then the one it was handed to when the row is dated on or after the
    handoff date or undated (NEU-2277)."""
    named, dated = row["CAND_ID"], row["TRANSACTION_DT"]
    correction = IE_CORRECTIONS.get(row["SUB_ID"])
    if correction is not None and named == correction[0]:
        named = correction[1]
    for before, after, handoff in HANDOFFS.values():
        if named == before and not (dated and datetime.strptime(dated, "%m%d%Y").date() < handoff):
            return after
    return named


def ie_24_48_date(row: Row) -> date | None:
    """A 24/48-hour row's date: exp_date, or dissem_dt where that is blank (DD-MON-YY)."""
    filed = row["exp_date"] or row["dissem_dt"]
    return datetime.strptime(filed, "%d-%b-%y").date() if filed else None


@functools.cache
def ie_24_48_added() -> tuple[tuple[Row, str], ...]:
    """The 24/48-hour file's rows silver independent_expenditure adds, each with the rule that adds
    it (project spec §6.3, NEU-2165): no row on a filing an amendment replaced, nor of a spender
    `cm` lacks; a row dated after the period end of a spender with a track record (a counted `pas2`
    independent expenditure, or a reported figure above $0); and the other rows of a spender with
    no `pas2` independent expenditure that reports one above $0, when they add up to no more than
    ten times it."""
    ies = fec_fixture.read_rows("ie_24_48")
    replaced = {r["prev_file_num"] for r in ies if r["prev_file_num"]}
    kept = [r for r in ies if r["file_num"] not in replaced and r["spe_id"] in committee_ids()]
    in_pas2 = {
        r["CMTE_ID"]
        for r in rows("pas2")
        if r["TRANSACTION_TP"] in (IE_SUPPORT, IE_OPPOSE) and r["MEMO_CD"] != "X"
    }
    summary = cycle_to_date(rows("committee_summary"))

    def period_end(spender: str) -> date | None:
        row = summary.get(spender)
        return None if row is None or not row["CVG_END_DT"] else summary_day(row["CVG_END_DT"])

    def figure_reported(spender: str) -> Decimal:
        row = summary.get(spender)
        return Decimal(row["INDT_EXP"]) if row is not None and row["INDT_EXP"] else Decimal(0)

    def is_timely(row: Row) -> bool:
        spender, end, day = row["spe_id"], period_end(row["spe_id"]), ie_24_48_date(row)
        has_record = spender in in_pas2 or figure_reported(spender) > 0
        return end is not None and day is not None and day > end and has_record

    by_spender: dict[str, list[Row]] = defaultdict(list)
    for row in kept:
        if not is_timely(row) and row["spe_id"] not in in_pas2:
            by_spender[row["spe_id"]].append(row)
    screened = {
        spender
        for spender, spent in by_spender.items()
        if 0 < figure_reported(spender)
        and sum(Decimal(r["exp_amo"]) for r in spent) <= 10 * figure_reported(spender)
    }
    return tuple(
        (row, "timeliness" if is_timely(row) else "by_spender")
        for row in kept
        if is_timely(row) or row["spe_id"] in screened
    )


def summary_day(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def ie_24_48_candidate(row: Row) -> str | None:
    """The candidate a 24/48-hour row is for or against: the one it names, or the one that id is
    an alias of, unless a committee was handed from them, and then the one it was handed to when
    the row is dated on or after the handoff or undated. No correction applies: the list is keyed
    by `pas2`'s SUB_ID."""
    named = aliases().get(row["cand_id"], row["cand_id"])
    day = ie_24_48_date(row)
    for before, after, handoff in HANDOFFS.values():
        if named == before and not (day is not None and day < handoff):
            return after
    return named or None


def test_the_expected_24_48_hour_rows_are_the_rules_on_the_fixture() -> None:
    added = defaultdict[str, list[str]](list)
    amounts = defaultdict[str, Decimal](Decimal)
    for row, rule in ie_24_48_added():
        added[rule].append(f"{row['file_num']}:{row['tran_id']}")
        amounts[rule] += Decimal(row["exp_amo"])
    assert EXPECTED["ie_24_48"] == {
        rule: {"amount": float(amounts[rule]), "source_record_ids": sorted(added[rule])}
        for rule in ("by_spender", "timeliness")
    }


def test_the_tallys_ie_corrections_are_the_vendored_lists() -> None:
    text = package_files("fundlens.fec").joinpath("ie_candidate_corrections.csv").read_text()
    vendored = {
        row["sub_id"]: (row["pas2_candidate_id"], row["candidate_id"])
        for row in csv.DictReader(io.StringIO(text))
    }

    assert {s: vendored.get(s) for s in IE_CORRECTIONS} == IE_CORRECTIONS


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

    def by_side(side: str) -> dict[str, Decimal]:
        transaction_type = {"S": IE_SUPPORT, "O": IE_OPPOSE}[side]
        return sum_dollars(
            [
                *(
                    (c, Decimal(amount(r)))
                    for r in pas2
                    if r["TRANSACTION_TP"] == transaction_type
                    and (c := ie_candidate(r)) is not None
                ),
                *(
                    (c, Decimal(r["exp_amo"]))
                    for r, _ in ie_24_48_added()
                    if r["sup_opp"] == side and (c := ie_24_48_candidate(r)) is not None
                ),
            ]
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
    support, oppose = by_side("S"), by_side("O")
    races, alias_ids = race_ids(), aliases()
    return {
        candidate_id: {
            "race_id": races[candidate_id],
            "total_individual": individual.get(candidate_id, 0),
            "total_committee": from_committees.get(candidate_id, 0),
            "total_jfc_transfers": jfc_transfers.get(candidate_id, 0),
            "self_funding": self_funding.get(candidate_id, 0),
            "ie_support": float(support.get(candidate_id, 0)),
            "ie_oppose": float(oppose.get(candidate_id, 0)),
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
            "ie_support": float(sum(Decimal(str(c["ie_support"])) for c in members)),
            "ie_oppose": float(sum(Decimal(str(c["ie_oppose"])) for c in members)),
        }
    return races


@pytest.mark.parametrize("file", ZIPS)
def test_each_zip_holds_one_pipe_delimited_member_with_the_vendored_column_count(
    file: FecFile,
) -> None:
    bulk = CATALOGUE[file]
    columns = bulk.header()
    member = bulk.member_for(CYCLE)
    with zipfile.ZipFile(io.BytesIO(fec_fixture.bodies()[file])) as archive:
        assert archive.namelist() == [member]
        lines = archive.read(member).decode().splitlines()
    assert lines
    assert len(lines) == EXPECTED["rows"][file]
    if bulk.trailing_delimiter:
        # FEC's layout: a `|` after the last column, so one field more, the last empty.
        assert all(line.endswith("|") for line in lines)
        assert all(len(line.split("|")) == len(columns) + 1 for line in lines)
        assert all(line.split("|")[-1] == "" for line in lines)
    else:
        # A line may still end in `|`: its last column is empty (a `cm` row with no CAND_ID).
        assert all(len(line.split("|")) == len(columns) for line in lines)
    # No header row: FEC's bulk files have none.
    assert lines[0].split("|")[0] != columns[0]


@pytest.mark.parametrize("file", CSVS)
def test_each_csv_has_the_catalogued_header_row_then_every_field_quoted(file: FecFile) -> None:
    columns = list(CATALOGUE[file].columns)
    header, *lines = fec_fixture.bodies()[file].decode().split("\n")[:-1]

    assert header == ",".join(columns)
    assert len(lines) == EXPECTED["rows"][file]
    for line in lines:
        assert line.startswith('"') and line.endswith('"')
        assert len(next(csv.reader([line]))) == len(columns)


def test_oppexps_sub_ids_are_its_own() -> None:
    # NEU-2152's no_contribution check needs no operating expenditure to share a receipt's SUB_ID.
    sub_ids = [row["SUB_ID"] for row in fec_fixture.read_rows("oppexp")]
    receipts = {row["SUB_ID"] for file in ("indiv", "pas2", "oth") for row in rows(file)}

    assert len(sub_ids) == len(set(sub_ids))
    assert not receipts & set(sub_ids)


def test_oppexp_repeats_one_row() -> None:
    assert fec_repeats("oppexp") == {"4240400000000000026"}


def test_oppexp_has_one_row_on_a_superseded_filing() -> None:
    superseded = [r for r in fec_fixture.read_rows("oppexp") if is_superseded(r)]

    assert [(r["CMTE_ID"], r["FILE_NUM"]) for r in superseded] == [("C00800201", "1900211")]


@functools.cache
def operating_expenditures() -> tuple[Row, ...]:
    """The `oppexp` rows silver keeps (every-FEC-dollar spec §5.1): read once, filed by a committee
    of the cycle, on no filing a later amendment supersedes by the receipt side's rule."""
    return tuple(
        row
        for row in rows("oppexp")
        if row["CMTE_ID"] in committee_ids() and not is_superseded(row)
    )


def named_tran_id(row: Row) -> str | None:
    """The TRAN_ID `row` names as its parent's: BACK_REF_TRAN_ID, unless blank or its own."""
    named = row["BACK_REF_TRAN_ID"].strip()
    return named if named and named != row["TRAN_ID"].strip() else None


@functools.cache
def spending_parents() -> Mapping[str, str]:
    """Sub-item SUB_ID → its parent's (spec §5.1): the row on the sub-item's committee and filing
    whose TRAN_ID it names, the lowest SUB_ID of them. A row with no FILE_NUM is on no filing."""
    holders: dict[tuple[str, str, str], int] = {}
    for row in operating_expenditures():
        if not row["FILE_NUM"]:
            continue
        held = (row["CMTE_ID"], row["FILE_NUM"], row["TRAN_ID"].strip())
        holders[held] = min(holders.get(held, int(row["SUB_ID"])), int(row["SUB_ID"]))
    return MappingProxyType(
        {
            row["SUB_ID"]: str(holders[named])
            for row in operating_expenditures()
            if (tran_id := named_tran_id(row))
            and (named := (row["CMTE_ID"], row["FILE_NUM"], tran_id)) in holders
        }
    )


def spending_counts(row: Row) -> bool:
    """Spec §5.2: a sub-item never counts, a parent always does, any other row unless a memo."""
    if row["SUB_ID"] in spending_parents():
        return False
    return row["SUB_ID"] in spending_parents().values() or row["MEMO_CD"] != "X"


def spending_candidate(row: Row) -> str | None:
    """The candidate an operating expenditure is credited to: its committee's, by contribution's
    rule; on a handed-off committee by the row's date, an undated one the later candidate's."""
    committee_id = row["CMTE_ID"]
    if committee_id not in HANDOFFS:
        return linked_candidates().get(committee_id)
    before, after, handoff = HANDOFFS[committee_id]
    try:
        spent_on = datetime.strptime(row["TRANSACTION_DT"], "%m/%d/%Y").date()
    except ValueError:
        return after
    return before if spent_on < handoff else after


def spending_in_kind(row: Row) -> bool:
    """Spec §5.4's in-kind outlay: a reference to a TRAN_ID no row of its filing holds, or a purpose
    naming a gift received: IN-KIND, but no in-kind contribution the committee made or pays ahead
    for, or crypto received (NEU-2464)."""
    purpose = row["PURPOSE"].upper()
    gift = bool(re.search(r"IN[- ]?KIND", purpose)) and not re.search(
        r"IN[- ]?KIND CONTRIBUTIONS? MADE|\bFOR\b.*\bIN[- ]?KIND CONTRIBUTIONS\b", purpose
    )
    crypto = re.search(
        r"\b(BITCOINS?|ETHER(EUM)?|USDC|RIPPLE|CRYPTO\w*)\b.*\bRECEIVED\b"
        r"|\bRECEIVED,? (NOT )?LIQUIDATED\b|\bNOT LIQUIDATED\b",
        purpose,
    )
    return (
        bool(named_tran_id(row) and row["SUB_ID"] not in spending_parents()) or gift or bool(crypto)
    )


def payee_is_person(row: Row) -> bool:
    """Spec §5.4: typed IND or CAN, or untyped with a name the classifier calls no
    organization's."""
    return row["ENTITY_TP"] in ("IND", "CAN") or bool(
        not row["ENTITY_TP"] and row["NAME"] and not normalize.is_organization_name(row["NAME"])
    )


# The outside-spending fixture files (NEU-2164; project spec §6). They plant the cases NEU-2165,
# NEU-2166 and NEU-2167 test their silver models on; these tests hold the rows to what each case
# needs, not to what silver makes of them.
ONE_NATION, GUNPOWDER, NANTICOKE = "C90800206", "C90800209", "C00800210"
STEAMFITTERS = "C70800208"
# ie_24_48.csv's two spenders `cm` lacks: a hoax filing's web-form filer, and a real Form 5 filer.
ABSENT_SPENDERS = frozenset({"C90899916", "C90899917"})
# Case 11's amendment names a filing the file lacks.
UNKNOWN_FILING = "1909999"
# CommunicationCosts.csv's case 4: a row `pas2` lacks.
UNPAIRED_COST = "4240200000000000090"
# The one row each of CommunicationCosts.csv and pas2.csv repeats: case 6's higher SUB_ID.
REPEATED_COST = "4240200000000000035"


def reported_independent_expenditures(committee_id: str) -> Decimal:
    (row,) = (r for r in rows("committee_summary") if r["CMTE_ID"] == committee_id)
    return Decimal(row["INDT_EXP"])


def test_the_24_48_hour_file_has_each_transaction_on_one_row_and_a_date() -> None:
    ies = fec_fixture.read_rows("ie_24_48")
    keys = [(r["file_num"], r["tran_id"]) for r in ies]

    assert len(keys) == len(set(keys))
    assert all(r["exp_date"] or r["dissem_dt"] for r in ies)
    assert all(r["fec_election_yr"] == "2024" for r in ies)


def test_the_24_48_hour_files_filings_are_in_no_other_fixture_file() -> None:
    # A 24/48-hour report's file_num is its own filing, never a periodic report's (Q4f).
    others = {r["FILE_NUM"] for file in ("pas2", "indiv", "oth", "oppexp") for r in rows(file)}

    assert not {r["file_num"] for r in fec_fixture.read_rows("ie_24_48")} & others


def test_every_amendment_in_the_24_48_hour_file_names_a_filing_of_its_own_spender() -> None:
    ies = fec_fixture.read_rows("ie_24_48")
    filings = {(r["spe_id"], r["file_num"]) for r in ies}
    named = [(r["spe_id"], r["prev_file_num"]) for r in ies if r["prev_file_num"]]

    assert [filing for filing in named if filing not in filings] == [(ONE_NATION, UNKNOWN_FILING)]


def test_the_24_48_hour_file_names_two_spenders_cm_lacks() -> None:
    spenders = {r["spe_id"] for r in fec_fixture.read_rows("ie_24_48")}

    assert spenders - committee_ids() == ABSENT_SPENDERS


def test_the_24_48_hour_files_screen_adds_one_form_5_filer_and_not_the_other() -> None:
    ies = fec_fixture.read_rows("ie_24_48")
    replaced = {r["prev_file_num"] for r in ies if r["prev_file_num"]}

    def filed(spender: str) -> Decimal:
        return sum(
            (
                Decimal(r["exp_amo"])
                for r in ies
                if r["spe_id"] == spender and r["file_num"] not in replaced
            ),
            Decimal(0),
        )

    assert 0 < filed(ONE_NATION) <= 10 * reported_independent_expenditures(ONE_NATION)
    assert filed(GUNPOWDER) > 10 * reported_independent_expenditures(GUNPOWDER)
    assert not any(r["CMTE_ID"] in (ONE_NATION, GUNPOWDER) for r in rows("pas2"))


def test_a_timely_spenders_pas2_spending_is_all_by_its_period_end() -> None:
    (summary,) = (r for r in rows("committee_summary") if r["CMTE_ID"] == NANTICOKE)
    period_end = datetime.strptime(summary["CVG_END_DT"], "%Y%m%d").date()
    spent = [
        datetime.strptime(r["TRANSACTION_DT"], "%m%d%Y").date()
        for r in rows("pas2")
        if r["CMTE_ID"] == NANTICOKE and r["TRANSACTION_TP"] in (IE_SUPPORT, IE_OPPOSE)
    ]

    assert period_end == date(2024, 9, 30)
    assert len(spent) == 2
    assert all(day <= period_end for day in spent)


def test_one_electioneering_disbursement_has_more_rows_than_candidates() -> None:
    by_disbursement: dict[tuple[str, ...], list[Row]] = defaultdict(list)
    for r in fec_fixture.read_rows("ElectioneeringComm"):
        disbursement = (
            r["COMMITTEE_ID"],
            r["SB_IMAGE_NUM"],
            r["PAYEE_NAME"],
            r["DISBURSEMENT_DATE"],
            r["REPORTED_DISBURSEMENT_AMOUNT"],
        )
        by_disbursement[disbursement].append(r)

    over = [rs for rs in by_disbursement.values() if len(rs) > int(rs[0]["NUMBER_OF_CANDIDATES"])]
    assert len(over) == 1
    (copies,) = over
    assert {r["CANDIDATE_ID"] for r in copies} == {"H4MD05106"}
    assert len({r["COMMUNICATION_DATE"] for r in copies}) == len(copies)


def electioneering_candidate(row: Row) -> str | None:
    """The candidate an electioneering row names (project spec §6.1): its CANDIDATE_ID, or the id
    it is an alias of, when a candidate of the cycle; past the handoff, on a row dated on or after
    it or undated, the candidate the committee was handed to."""
    named = aliases().get(row["CANDIDATE_ID"], row["CANDIDATE_ID"])
    if named not in race_ids():
        return None
    filed = row["DISBURSEMENT_DATE"]
    day = datetime.strptime(filed, "%d-%b-%y").date() if filed else None
    for before, after, handoff in HANDOFFS.values():
        if named == before and not (day is not None and day < handoff):
            return after
    return named


@functools.cache
def electioneering_communications() -> Mapping[str, list[str | float | None]]:
    """Silver electioneering_communication's rows by key, [committee_id, candidate_id, race_id,
    amount]: every row of a spender in `cm` but a disbursement's rows beyond its candidate count, in
    order of CANDIDATE_ID and then every column; each keyed by its place among its image number's
    kept rows, in the same order (project spec §6.4)."""
    by_disbursement: dict[tuple[str, ...], list[Row]] = defaultdict(list)
    for r in fec_fixture.read_rows("ElectioneeringComm"):
        if r["COMMITTEE_ID"] in committee_ids():
            disbursement = (
                r["COMMITTEE_ID"],
                r["SB_IMAGE_NUM"],
                r["PAYEE_NAME"],
                r["DISBURSEMENT_DATE"],
                r["REPORTED_DISBURSEMENT_AMOUNT"],
            )
            by_disbursement[disbursement].append(r)
    columns = list(CATALOGUE["ElectioneeringComm"].columns)

    def order(r: Row) -> tuple[tuple[bool, str], ...]:
        # Blanks last, as DuckDB orders a NULL.
        return tuple((not r[c], r[c]) for c in columns)

    by_image: dict[str, list[Row]] = defaultdict(list)
    for rs in by_disbursement.values():
        for r in sorted(rs, key=order)[: int(rs[0]["NUMBER_OF_CANDIDATES"])]:
            by_image[r["SB_IMAGE_NUM"]].append(r)
    tallied: dict[str, list[str | float | None]] = {}
    for image, rs in by_image.items():
        for place, r in enumerate(sorted(rs, key=order), start=1):
            candidate = electioneering_candidate(r)
            tallied[f"{image}:{place}"] = [
                r["COMMITTEE_ID"],
                candidate,
                None if candidate is None else race_ids()[candidate],
                float(Decimal(r["CALCULATED_CANDIDATE_SHARE"])),
            ]
    return MappingProxyType(tallied)


def test_the_expected_electioneering_rows_are_the_rules_on_the_fixture() -> None:
    assert EXPECTED["electioneering_communications"] == electioneering_communications()


def test_each_communication_cost_is_a_pas2_row_under_its_sub_id_but_one() -> None:
    costs = fec_fixture.read_rows("CommunicationCosts")
    sub_ids = [r["SUB_ID"] for r in costs]
    pas2 = {r["SUB_ID"]: r for r in fec_fixture.read_rows("pas2")}

    assert len(sub_ids) == len(set(sub_ids))
    assert [s for s in sub_ids if s not in pas2] == [UNPAIRED_COST]
    for cost in costs:
        if cost["SUB_ID"] == UNPAIRED_COST:
            continue
        twin = pas2[cost["SUB_ID"]]
        assert twin["CMTE_ID"] == cost["CMTE_ID"] == STEAMFITTERS
        assert twin["TRANSACTION_TP"] == cost["TRANSACTION_TP"] in ("24F", "24N")
        assert twin["CAND_ID"] == cost["CAND_ID"]
        assert twin["FILE_NUM"] == cost["FILE_NUM"]
        assert twin["TRAN_ID"] == cost["TRAN_ID"]
        # FEC's pas2 drops a communication cost's cents.
        assert Decimal(twin["TRANSACTION_AMT"]) == int(Decimal(cost["TRANSACTION_AMT"]))
    paired = set(sub_ids)
    unpaired = [
        r for r in rows("pas2") if r["CMTE_ID"] == STEAMFITTERS and r["SUB_ID"] not in paired
    ]
    assert [r["CAND_ID"] for r in unpaired] == [""]


def test_communication_costs_and_pas2_each_repeat_the_same_one_row() -> None:
    assert fec_repeats("CommunicationCosts") == {REPEATED_COST}
    assert REPEATED_COST in fec_repeats("pas2")


def pas2_kind(transaction_types: tuple[str, ...]) -> dict[str, tuple[Row, str | None, str | None]]:
    """`pas2`'s counted rows of `transaction_types` by SUB_ID, each with the candidate it names
    (when one of the cycle) and that candidate's race, as silver attaches them."""
    races = race_ids()
    kept: dict[str, tuple[Row, str | None, str | None]] = {}
    for r in rows("pas2"):
        if r["TRANSACTION_TP"] in transaction_types and r["MEMO_CD"] != "X":
            candidate = ie_candidate(r)
            candidate = candidate if candidate in races else None
            kept[r["SUB_ID"]] = (r, candidate, races[candidate] if candidate else None)
    return kept


def test_the_expected_communication_costs_are_pas2s_with_the_csvs_type_and_class() -> None:
    # Counted from pas2 alone (project spec §6.2, NEU-2167): its amount and side by type; the CSV
    # gives the type and class of the row under the same SUB_ID, and adds no row of its own.
    described = {r["SUB_ID"]: r for r in rows("CommunicationCosts")}
    assert EXPECTED["communication_costs"] == {
        sub_id: [
            r["CMTE_ID"],
            candidate,
            race,
            "O" if r["TRANSACTION_TP"] == "24N" else "S",
            amount(r),
            (cost := described.get(sub_id, {})).get("COMMUNICATION_TP") or None,
            cost.get("COMMUNICATION_CLASS") or None,
        ]
        for sub_id, (r, candidate, race) in sorted(pas2_kind(("24F", "24N")).items())
    }


def test_the_expected_party_coordinated_expenditures_are_pas2s_24cs() -> None:
    assert EXPECTED["party_coordinated"] == {
        sub_id: [r["CMTE_ID"], candidate, race, "S", amount(r)]
        for sub_id, (r, candidate, race) in sorted(pas2_kind(("24C",)).items())
    }


def test_the_expected_operating_expenditures_match_the_fixture() -> None:
    expected = EXPECTED["operating_expenditures"]
    kept = operating_expenditures()
    counted_rows = [row for row in kept if spending_counts(row)]

    def dollars(pairs: Iterable[tuple[str, Decimal]]) -> dict[str, str]:
        totals: defaultdict[str, Decimal] = defaultdict(Decimal)
        for key, value in pairs:
            totals[key] += value
        return {key: f"{total:.2f}" for key, total in sorted(totals.items())}

    assert EXPECTED["silver"]["operating_expenditure"] == len(kept)
    kept_ids = {row["SUB_ID"] for row in kept}
    assert expected["dropped"] == sorted(
        int(row["SUB_ID"])
        for row in fec_fixture.read_rows("oppexp")
        if row["SUB_ID"] not in kept_ids
    )
    assert expected["parents"] == {int(k): int(v) for k, v in spending_parents().items()}
    assert expected["not_counted"] == sorted(
        int(r["SUB_ID"]) for r in kept if not spending_counts(r)
    )
    amounts = [(row, Decimal(row["TRANSACTION_AMT"])) for row in counted_rows]
    assert expected["by_committee"] == dollars((row["CMTE_ID"], value) for row, value in amounts)
    assert expected["by_candidate"] == dollars(
        (candidate, value) for row, value in amounts if (candidate := spending_candidate(row))
    )
    assert expected["total"] == f"{sum(value for _, value in amounts):.2f}"
    assert expected["in_kind"] == sorted(
        int(row["SUB_ID"]) for row in kept if spending_in_kind(row)
    )
    for sub_id, key in expected["payee_keys"].items():
        [row] = [r for r in kept if r["SUB_ID"] == str(sub_id)]
        assert normalize.organization_key(row["NAME"] or None) == key
    assert expected["persons"] == sorted(int(row["SUB_ID"]) for row in kept if payee_is_person(row))
    assert expected["fec_categories"] == {
        int(row["SUB_ID"]): row["CATEGORY"].zfill(3) for row in kept if row["CATEGORY"]
    }
    # The cases the rules are for are planted: a memo parent counted, a chain's middle row not, a
    # parentless reference counted, refunds netting, two spellings sharing a key.
    parents = set(spending_parents().values())
    assert any(r["MEMO_CD"] == "X" and r["SUB_ID"] in parents for r in counted_rows)
    assert any(r["SUB_ID"] in parents and r["SUB_ID"] in spending_parents() for r in kept)
    assert any(named_tran_id(r) and r["SUB_ID"] not in spending_parents() for r in counted_rows)
    assert any(value < 0 for _, value in amounts)
    keys = [key for key in expected["payee_keys"].values() if key]
    assert len(set(keys)) < len(keys)


# The hand-kept list of payee keys with no page (spec §5.4), read once.
NO_PAGE = frozenset(gold.payee_no_page())


@functools.cache
def payee_rows() -> tuple[tuple[Row, str, Decimal], ...]:
    """Spec §5.4's payee rows of the fixture, each with its payee key and amount: counted, named,
    no in-kind outlay."""
    rows_: list[tuple[Row, str, Decimal]] = []
    for row in operating_expenditures():
        if not spending_counts(row) or not row["NAME"] or spending_in_kind(row):
            continue
        key = normalize.organization_key(row["NAME"])
        assert key is not None
        rows_.append((row, key, Decimal(row["TRANSACTION_AMT"])))
    return tuple(rows_)


@functools.cache
def has_page(key: str) -> bool:
    """Spec §5.4: a key has a page unless more than half its payee dollars are a person's, or the
    hand-kept list names it."""
    keyed = [(row, amount) for row, k, amount in payee_rows() if k == key]
    person = sum((amount for row, amount in keyed if payee_is_person(row)), Decimal(0))
    total = sum((amount for _, amount in keyed), Decimal(0))
    return key not in NO_PAGE and not (person > total / 2 and person > 0)


def most(amounts: Mapping[str, Decimal], rows_: Mapping[str, int]) -> str:
    """The value with the most payee dollars, then the most rows, then the first in order."""
    return min(amounts, key=lambda value: (-amounts[value], -rows_[value], value))


def test_the_expected_gold_spending_tables_match_the_fixture() -> None:
    """committee_spending_category and committee_top_payee (spec §5.5), derived from oppexp.csv:
    each committee's counted dollars by the category expected.yaml gives each row, and its payee
    rows (counted, named, no in-kind outlay) by key."""
    expected = EXPECTED["operating_expenditures"]
    counted = [row for row in operating_expenditures() if spending_counts(row)]

    by_category: defaultdict[str, defaultdict[str, Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )
    for row in counted:
        [category, _] = expected["categories"][int(row["SUB_ID"])]
        by_category[row["CMTE_ID"]][category] += Decimal(row["TRANSACTION_AMT"])
    assert expected["by_committee_category"] == {
        committee_id: {category: f"{amount:.2f}" for category, amount in sorted(amounts.items())}
        for committee_id, amounts in sorted(by_category.items())
    }
    for committee_id, amounts in expected["by_committee_category"].items():
        assert sum(map(Decimal, amounts.values())) == Decimal(
            expected["by_committee"][committee_id]
        ), committee_id

    paid: defaultdict[str, defaultdict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    spellings: defaultdict[str, defaultdict[str, Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )
    for row, key, amount in payee_rows():
        paid[row["CMTE_ID"]][key] += amount
        spellings[key][row["NAME"]] += amount
    assert expected["top_payees"] == {
        committee_id: [
            [
                key,
                max(spellings[key], key=spellings[key].__getitem__),
                f"{amount:.2f}",
                has_page(key),
            ]
            for key, amount in sorted(keys.items(), key=lambda item: (-item[1], item[0]))
            if amount > 0
        ]
        for committee_id, keys in sorted(paid.items())
    }
    # The planted cases: a key in two spellings, a tie broken by key, a person's key with no page,
    # and one the hand-kept list gives none.
    assert any(len(names) > 1 for names in spellings.values())
    okafor = [row[2] for row in expected["top_payees"]["C00800103"]]
    assert len(set(okafor)) < len(okafor)
    assert not all(row[3] for rows_ in expected["top_payees"].values() for row in rows_)
    assert "PETTY CASH" in NO_PAGE and not has_page("PETTY CASH")


def test_the_expected_gold_payee_tables_match_the_fixture() -> None:
    """payee and payee_top_payer (spec §5.5), derived from oppexp.csv: every key with a page, each
    display column its value with the most payee dollars, and the committees that paid it, ranked,
    each with the candidate its rows are credited to."""
    keyed: defaultdict[str, list[tuple[Row, Decimal]]] = defaultdict(list)
    for row, key, amount in payee_rows():
        keyed[key].append((row, amount))

    def display(rows_: list[tuple[Row, Decimal]], column: str) -> str | None:
        amounts: defaultdict[str, Decimal] = defaultdict(Decimal)
        counts: Counter[str] = Counter()
        for row, amount in rows_:
            if row[column]:
                amounts[row[column]] += amount
                counts[row[column]] += 1
        return most(amounts, counts) if amounts else None

    def payers(rows_: list[tuple[Row, Decimal]]) -> list[list[str | None]]:
        by_committee: defaultdict[str, Decimal] = defaultdict(Decimal)
        credited: defaultdict[str, defaultdict[str, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal)
        )
        for row, amount in rows_:
            by_committee[row["CMTE_ID"]] += amount
            if candidate := spending_candidate(row):
                credited[row["CMTE_ID"]][candidate] += amount
        return [
            [
                committee_id,
                min(credited[committee_id], key=lambda c: (-credited[committee_id][c], c))
                if credited[committee_id]
                else None,
                f"{amount:.2f}",
            ]
            for committee_id, amount in sorted(by_committee.items(), key=lambda i: (-i[1], i[0]))
            if amount > 0
        ]

    assert EXPECTED["operating_expenditures"]["payees"] == {
        key: {
            "name": display(rows_, "NAME"),
            "city": display(rows_, "CITY"),
            "state": display(rows_, "STATE"),
            "total": f"{sum(amount for _, amount in rows_):.2f}",
            "committees": len({row["CMTE_ID"] for row, _ in rows_}),
            "payers": payers(rows_),
        }
        for key, rows_ in sorted(keyed.items())
        if has_page(key)
    }
    # The planted case: one payee under two spellings, paid by two committees.
    blue_harbor = EXPECTED["operating_expenditures"]["payees"]["BLUE HARBOR STRATEGIES"]
    assert len({row["NAME"] for row, _ in keyed["BLUE HARBOR STRATEGIES"]}) == 2
    assert len(blue_harbor["payers"]) == 2


def test_every_key_the_no_page_list_names_is_a_payee_key_with_a_reason() -> None:
    """`fec/payee_no_page.csv` (spec §5.4) lists keys as organization_key writes them, each once,
    each with why it names nobody."""
    text = package_files("fundlens.fec").joinpath("payee_no_page.csv").read_text()
    listed = list(csv.DictReader(io.StringIO(text)))

    assert listed
    assert all(row["reason"] for row in listed)
    keys = [row["payee_key"] for row in listed]
    assert len(set(keys)) == len(keys)
    assert all(normalize.organization_key(key) == key for key in keys)


def test_the_1998_cycle_publishes_its_summary_zips_and_no_committee_summary() -> None:
    files = fec_fixture.bodies(1998)

    assert "committee_summary" not in files
    summaries: tuple[tuple[FecFile, str], ...] = (
        ("weball", "weball98.txt"),
        ("webk", "webk98.txt"),
    )
    for name, member in summaries:
        with zipfile.ZipFile(io.BytesIO(files[name])) as archive:
            assert archive.namelist() == [member]


def test_committee_summary_repeats_a_committee_per_linked_candidate_or_period() -> None:
    by_committee: dict[str, list[Row]] = defaultdict(list)
    for r in rows("committee_summary"):
        by_committee[r["CMTE_ID"]].append(r)

    assert committee_ids() <= set(by_committee)
    repeated = {c: rs for c, rs in by_committee.items() if len(rs) > 1}
    assert {c: sorted(r["CAND_ID"] for r in rs) for c, rs in repeated.items()} == {
        "C00703975": ["P00009423", "P80000722"],
        "C00800107": ["H4MD05107", "H6MD05113"],
        "C00800101": ["P40000101", "P40000101"],
    }
    # A committee repeated per linked candidate: every field but CAND_ID alike.
    for committee_id in ("C00703975", "C00800107"):
        rs = repeated[committee_id]
        assert len({tuple(v for k, v in r.items() if k != "CAND_ID") for r in rs}) == 1
    # HARGROVE FOR AMERICA over two periods, the narrower first (NEU-2454): its cycle-to-date row
    # is the second.
    hargrove = repeated["C00800101"]
    assert [(r["CVG_START_DT"], r["CVG_END_DT"]) for r in hargrove] == [
        ("20240701", "20241231"),
        ("20230101", "20241231"),
    ]
    assert cycle_to_date(hargrove)["C00800101"] is hargrove[1]


def test_a_weball_row_adds_up_its_candidates_principal_and_authorized_committees() -> None:
    receipts = {
        committee_id: int(r["TTL_RECEIPTS"] or 0)
        for committee_id, r in cycle_to_date(rows("committee_summary")).items()
    }
    weball = {r["CAND_ID"]: int(r["TTL_RECEIPTS"]) for r in rows("weball")}

    assert weball == {
        candidate_id: sum(
            receipts[r["CMTE_ID"]]
            for r in rows("ccl")
            if r["CAND_ID"] == candidate_id and r["CMTE_DSGN"] in ("P", "A")
        )
        for candidate_id in weball
    }
    # Every candidate `ccl` gives a principal or authorized committee, and no other.
    assert set(weball) == {r["CAND_ID"] for r in rows("ccl") if r["CMTE_DSGN"] in ("P", "A")}


# Silver reported_total's measures in column order (every-FEC-dollar spec §4.1, §4.2), each with the
# column it is read from in committee_summary, webk and weball, None where the file has none. Two
# are derived from two columns where a file has them (`summary_figures`): other_loans in
# committee_summary (where OTH_LOANS is blank) and webk, and operating_expenditures.
SUMMARY_FILES = ("committee_summary", "webk", "weball")
MEASURES: dict[str, tuple[str | None, str | None, str | None]] = {
    "receipts": ("TTL_RECEIPTS", "TTL_RECEIPTS", "TTL_RECEIPTS"),
    "disbursements": ("TTL_DISB", "TTL_DISB", "TTL_DISB"),
    "cash_on_hand_start": ("COH_BOP", "COH_BOP", "COH_BOP"),
    "cash_on_hand_end": ("COH_COP", "COH_COP", "COH_COP"),
    "debts_owed_by": ("DEBTS_OWED_BY_CMTE", "DEBTS_OWED_BY", "DEBTS_OWED_BY"),
    "debts_owed_to": ("DEBTS_OWED_TO_CMTE", None, None),
    "individual_itemized": ("INDV_ITEM_CONTB", None, None),
    "individual_unitemized": ("INDV_UNITEM_CONTB", None, None),
    "individual_total": ("INDV_CONTB", "INDV_CONTRIB", "TTL_INDIV_CONTRIB"),
    "individual_refunds": ("INDV_REF", "INDV_REFUNDS", "INDIV_REFUNDS"),
    "party_contributions": ("PTY_CMTE_CONTB", None, "POL_PTY_CONTRIB"),
    "other_committee_contributions": (
        "OTH_CMTE_CONTB",
        "OTHER_POL_CMTE_CONTRIB",
        "OTHER_POL_CMTE_CONTRIB",
    ),
    "candidate_contributions": ("CAND_CNTB", "CAND_CONTRIB", "CAND_CONTRIB"),
    "candidate_loans": ("CAND_LOAN", "CAND_LOANS", "CAND_LOANS"),
    "other_loans": ("OTH_LOANS", None, "OTHER_LOANS"),
    "candidate_loan_repayments": ("CAND_LOAN_REPYMNT", "CAND_LOAN_REPAY", "CAND_LOAN_REPAY"),
    "other_loan_repayments": ("OTH_LOAN_REPYMTS", "LOAN_REPAY", "OTHER_LOAN_REPAY"),
    "transfers_in": ("TRANF_FROM_OTHER_AUTH_CMTE", "TRANS_FROM_AFF", "TRANS_FROM_AUTH"),
    "transfers_out": ("TRANF_TO_OTHER_AUTH_CMTE", "TRANF_TO_AFF", "TRANS_TO_AUTH"),
    "independent_expenditures": ("INDT_EXP", "IND_EXP", None),
    "party_coordinated": ("COORD_EXP_BY_PTY_CMTE", "PTY_COORD_EXP", None),
    "operating_expenditures": (None, None, None),
    "federal_funds": ("FED_FUNDS", None, None),
}
REPORTED_COLUMNS = ("source_file", "period_start", "period_end", *MEASURES)
# The committee types whose blank committee_summary measures are webk's (spec §4.1): Form 5 and
# Form 7 filers.
FILLED_FROM_WEBK = ("I", "C")
# The cycles the fixture plants summary files for: one before 2008, one after.
SUMMARY_CYCLES = (2024, 1998)


def figure(row: Row, column: str) -> int | None:
    """A summary file's figure as filed: a blank is None."""
    if not row[column]:
        return None
    value = Decimal(row[column])
    # Every fixture figure is whole dollars, as every fixture amount is.
    assert value == value.to_integral_value(), (column, row[column])
    return int(value)


def cycle_to_date(summary: Iterable[Row]) -> dict[str, Row]:
    """Each committee's `committee_summary` row covering the cycle to date, as silver keeps it
    (spec §4.1): the earliest CVG_START_DT, then the latest CVG_END_DT, then the lowest CAND_ID;
    a blank date last."""

    def order(row: Row) -> tuple[bool, int, bool, int, str]:
        start, end = row["CVG_START_DT"], row["CVG_END_DT"]
        return (not start, int(start or 0), not end, -int(end or 0), row["CAND_ID"])

    kept: dict[str, Row] = {}
    for row in sorted(summary, key=order):
        kept.setdefault(row["CMTE_ID"], row)
    return kept


def summary_figures(row: Row, file: str) -> dict[str, date | int | None]:
    """One summary-file row's reporting period and measures, by silver column name."""
    index = SUMMARY_FILES.index(file)
    date_format = "%Y%m%d" if file == "committee_summary" else "%m/%d/%Y"

    def day(column: str) -> date | None:
        return datetime.strptime(row[column], date_format).date() if row[column] else None

    figures: dict[str, date | int | None] = {
        "period_start": day("CVG_START_DT") if file == "committee_summary" else None,
        "period_end": day("CVG_END_DT"),
    }
    for measure, columns in MEASURES.items():
        column = columns[index]
        figures[measure] = None if column is None else figure(row, column)
    if file == "committee_summary":
        if figures["other_loans"] is None and (loans := figure(row, "TTL_LOANS")) is not None:
            figures["other_loans"] = loans - (figure(row, "CAND_LOAN") or 0)
        parts = [figure(row, "OP_EXP"), figure(row, "TTL_OP_EXP")]
        if parts != [None, None]:
            figures["operating_expenditures"] = sum(part or 0 for part in parts)
    if file == "webk" and (loans := figure(row, "TTL_LOANS_RECEIVED")) is not None:
        figures["other_loans"] = loans - (figure(row, "CAND_LOANS") or 0)
    return figures


def reported_totals(cycle: int) -> dict[str, list[object]]:
    """Silver reported_total's rows for `cycle` by committee: `REPORTED_COLUMNS`' values."""
    directory = fec_fixture.fixture_dir(cycle)
    committees = {r["CMTE_ID"] for r in fec_fixture.read_rows("cm", directory)}
    webk = {r["CMTE_ID"]: r for r in fec_fixture.read_rows("webk", directory)}
    if cycle < 2008:
        return {
            committee_id: ["webk", *summary_figures(row, "webk").values()]
            for committee_id, row in webk.items()
            if committee_id in committees
        }
    totals: dict[str, list[object]] = {}
    for committee_id, row in cycle_to_date(
        fec_fixture.read_rows("committee_summary", directory)
    ).items():
        if committee_id not in committees:
            continue
        figures, source_file = summary_figures(row, "committee_summary"), "committee_summary"
        if row["CMTE_TP"] in FILLED_FROM_WEBK and committee_id in webk:
            fill = summary_figures(webk[committee_id], "webk")
            # The measures only: the reporting period stays committee_summary's.
            for column, value in figures.items():
                if column in MEASURES and value is None and fill[column] is not None:
                    figures[column], source_file = fill[column], "committee_summary+webk"
        totals[committee_id] = [source_file, *figures.values()]
    return totals


def candidate_reported_totals(cycle: int) -> dict[str, list[object]]:
    """Silver candidate_reported_total's rows for `cycle` by candidate: none from 2008."""
    if cycle >= 2008:
        return {}
    directory = fec_fixture.fixture_dir(cycle)
    candidates = {r["CAND_ID"] for r in fec_fixture.read_rows("cn", directory)}
    return {
        row["CAND_ID"]: ["weball", *summary_figures(row, "weball").values()]
        for row in fec_fixture.read_rows("weball", directory)
        if row["CAND_ID"] in candidates
    }


def test_the_expected_reported_totals_are_the_summary_files_rows_by_precedence() -> None:
    assert EXPECTED["reported_totals"] == {
        "columns": list(REPORTED_COLUMNS),
        "reported_total": {cycle: reported_totals(cycle) for cycle in SUMMARY_CYCLES},
        "candidate_reported_total": {
            cycle: candidate_reported_totals(cycle) for cycle in SUMMARY_CYCLES
        },
    }


def test_the_summary_fixtures_plant_each_precedence_case() -> None:
    committees = EXPECTED["reported_totals"]["reported_total"]
    sources = {
        cycle: Counter(row[0] for row in rows_by_id.values())
        for cycle, rows_by_id in committees.items()
    }
    # Every 2024 committee's row is committee_summary's, the Form 5 filer's filled from webk; 1998
    # has no committee_summary, so webk's.
    assert sources == {
        2024: {"committee_summary": len(committee_ids()) - 1, "committee_summary+webk": 1},
        1998: {"webk": 2},
    }
    assert committees[2024]["C90800206"][0] == "committee_summary+webk"
    # A pre-2008 row has none of the columns only committee_summary has.
    only_2008 = ("period_start", "debts_owed_to", "individual_itemized", "individual_unitemized")
    for row in committees[1998].values():
        assert all(row[REPORTED_COLUMNS.index(column)] is None for column in only_2008)
    assert set(EXPECTED["reported_totals"]["candidate_reported_total"][1998]) == {
        "H8MD05201",
        "H8MD05202",
    }


def reported(committee_id: str, column: str) -> Any:
    """A 2024 committee's silver reported_total figure, as `expected.yaml` lists it."""
    row = EXPECTED["reported_totals"]["reported_total"][CYCLE].get(committee_id)
    return None if row is None else row[REPORTED_COLUMNS.index(column)]


def itemized_totals() -> dict[str, int]:
    """Each committee's itemized_total (every-FEC-dollar spec §4.4): total_individual +
    total_from_organizations - total_refunds, the organizations' money on line 11(a)(i) only."""
    organizations = EXPECTED["organization_receipts"]["by_committee"]
    outside = (
        EXPECTED["non_contribution_account"]["organizations_by_committee"],
        EXPECTED["other_lines"]["organizations_by_committee"],
    )
    refunds = EXPECTED["refunds"]["by_committee"]
    return {
        committee_id: totals["total_individual"]
        + organizations.get(committee_id, 0)
        - sum(each.get(committee_id, 0) for each in outside)
        - refunds.get(committee_id, 0)
        for committee_id, totals in EXPECTED["committees"].items()
    }


def coverage(itemized: int | None, reported_itemized: int | None) -> float | None:
    """The ratio to four places, as `gold_reported` lists it; None where there is none."""
    return (
        None
        if itemized is None or not reported_itemized
        else round(itemized / reported_itemized, 4)
    )


def test_the_expected_committee_coverage_is_itemized_over_reported_null_at_a_conduit() -> None:
    itemized = itemized_totals()

    assert EXPECTED["gold_reported"]["committees"] == {
        committee_id: [
            itemized[committee_id],
            reported(committee_id, "individual_itemized"),
            reported(committee_id, "cash_on_hand_end"),
            None
            if committee_id in CONDUITS.values()
            else coverage(itemized[committee_id], reported(committee_id, "individual_itemized")),
        ]
        for committee_id in EXPECTED["committees"]
    }
    # A conduit's INDV_ITEM_CONTB is every earmark it took, which fundlens counts at the recipient.
    for conduit_id in CONDUITS.values():
        assert reported(conduit_id, "individual_itemized") == sum(
            amount(r)
            for r in rows("indiv")
            if r["CMTE_ID"] == conduit_id and not r["TRANSACTION_TP"].endswith("Y")
        )
    # Every other committee filed its itemized_total but the two planted to differ: FENWICK FOR
    # CONGRESS by more than 1%, YANG FOR MARYLAND by less.
    differ = {
        committee_id: figures[3]
        for committee_id, figures in EXPECTED["gold_reported"]["committees"].items()
        if figures[3] not in (None, 1.0)
    }
    assert differ == {"C00800109": 1.027, "C00800108": 1.0079}


def credited_committees() -> dict[str, list[tuple[str, bool]]]:
    """Each candidate's credited committees for reported figures (every-FEC-dollar spec §4.3),
    each with whether only its CAND_PCC credits it (a campaign turned PAC): `linked_candidates`,
    but a handed-off committee is the second candidate's whole."""
    designated = {(r["CAND_ID"], r["CMTE_ID"]) for r in rows("ccl") if r["CMTE_DSGN"] in ("P", "A")}
    credited: dict[str, list[tuple[str, bool]]] = defaultdict(list)
    for committee_id, candidate_id in linked_candidates().items():
        if committee_id in HANDOFFS:
            candidate_id = HANDOFFS[committee_id][1]
        credited[candidate_id].append(
            (committee_id, (candidate_id, committee_id) not in designated)
        )
    return credited


def test_the_expected_candidate_figures_sum_their_credited_committees() -> None:
    itemized, credited = itemized_totals(), credited_committees()

    def summed(committee_ids: list[str], column: str) -> int | None:
        figures = [f for c in committee_ids if (f := reported(c, column)) is not None]
        return sum(figures) if figures else None

    expected: dict[str, list[Any]] = {}
    for candidate_id in EXPECTED["candidates"]:
        ids = [committee_id for committee_id, _ in credited.get(candidate_id, [])]
        expected[candidate_id] = [
            summed(ids, "receipts"),
            summed(ids, "cash_on_hand_end"),
            sum(itemized[c] for c in ids) if ids else None,
            coverage(
                sum(itemized[c] for c in ids if reported(c, "individual_itemized") is not None),
                summed(ids, "individual_itemized"),
            ),
            any(
                converted and reported(c, "receipts") is not None
                for c, converted in credited.get(candidate_id, [])
            ),
        ]
    assert EXPECTED["gold_reported"]["candidates"] == expected
    # HARRIS holds C00703975 whole; BIDEN, who has itemized money from it, has no reported figure.
    assert expected["P00009423"][0] == reported("C00703975", "receipts")
    assert expected["P80000722"][0] is None
    assert EXPECTED["candidates"]["P80000722"]["total_individual"] > 0

    races = defaultdict[str, list[int]](list)
    for candidate_id, totals in EXPECTED["candidates"].items():
        if totals["race_id"] is not None and (cash := expected[candidate_id][1]) is not None:
            races[totals["race_id"]].append(cash)
    assert EXPECTED["gold_reported"]["races"] == {
        race_id: sum(races[race_id]) if race_id in races else None for race_id in EXPECTED["races"]
    }


def test_the_expected_reconciliation_lists_each_committee_over_its_reported_figure_by_1pct() -> (
    None
):
    itemized = {
        committee_id: [fundlens, reported_itemized, coverage(fundlens, reported_itemized)]
        for committee_id, (fundlens, reported_itemized, _, _) in EXPECTED["gold_reported"][
            "committees"
        ].items()
        if reported_itemized is not None
        and committee_id not in CONDUITS.values()
        and fundlens - reported_itemized > Decimal("0.01") * reported_itemized
    }
    # Operating expenditures (spec §5.6): counted spending against the reported figure, conduits
    # included.
    column = EXPECTED["reported_totals"]["columns"].index("operating_expenditures")
    reported_totals = EXPECTED["reported_totals"]["reported_total"][2024]
    spending: dict[str, list[Any]] = {}
    for committee_id, spent in EXPECTED["operating_expenditures"]["by_committee"].items():
        reported = reported_totals.get(committee_id, [None] * (column + 1))[column]
        fundlens = Decimal(spent)
        if reported is not None and fundlens - reported > Decimal("0.01") * reported:
            ratio = round(float(fundlens) / reported, 4) if reported else None
            spending[committee_id] = [int(fundlens), reported, ratio]

    assert EXPECTED["gold_reported"]["reconciliation"] == {
        "individual_itemized": itemized,
        "operating_expenditures": spending,
    }


GIFT_SIZE_BUCKETS = ("200_or_less", "under_500", "under_1000", "under_2000", "2000_or_more")


def gift_size_bucket(gift_size: int) -> str:
    """Every-FEC-dollar spec §4.6's bucket for a donor's net gifts to one candidate."""
    if gift_size <= 200:
        return "200_or_less"
    if gift_size < 500:
        return "under_500"
    if gift_size < 1000:
        return "under_1000"
    if gift_size < 2000:
        return "under_2000"
    return "2000_or_more"


def test_the_expected_gift_sizes_bucket_each_donors_net_gifts_to_the_candidate() -> None:
    cids, credited = donor_cids(), credited_committees()
    gift_sizes: defaultdict[tuple[str, str], int] = defaultdict(int)
    for r in counted():
        candidate_id = candidate_of(r["CMTE_ID"], r)
        if candidate_id is not None and not is_self_funding(r) and not is_other_line(r):
            gift_sizes[candidate_id, cids[int(r["SUB_ID"])]] += signed(r)
    for candidate_id, buckets in EXPECTED["gold_reported"]["gift_sizes"].items():
        tallied = {bucket: [0, 0] for bucket in GIFT_SIZE_BUCKETS}
        for (each, _), gift_size in gift_sizes.items():
            if each == candidate_id:
                tallied[gift_size_bucket(gift_size)][0] += gift_size
                tallied[gift_size_bucket(gift_size)][1] += 1
        unitemized = sum(
            reported(committee_id, "individual_unitemized")
            for committee_id, _ in credited[candidate_id]
        )

        assert buckets == {"unitemized": [unitemized, None], **tallied}, candidate_id
        assert (
            sum(tallied[b][0] for b in GIFT_SIZE_BUCKETS)
            == (EXPECTED["candidates"][candidate_id]["total_individual"])
        )
    # THACKERAY's twenty $50 gifts are one $1,000 donor, not twenty in 200_or_less.
    thackeray = EXPECTED["donors"]["twenty_small_gifts"]
    assert len(thackeray["sub_ids"]) == 20
    assert gift_size_bucket(thackeray["amount"]) == "under_2000"


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


def test_the_csv_sample_renders_in_fecs_csv_layout() -> None:
    body = fec_fixture.bulk_body(fec_fixture.SAMPLE, fec_fixture.SAMPLE_FILE)

    assert body == (
        b"CMTE_ID,CMTE_NM,TTL_RECEIPTS,COVERAGE_END_DT\n"
        b'"C00000001","SMITH, JONES & ""FRIENDS"" | PAC","","20241016"\n'
        b'"C00000002"," GO AMERICA PAC","1234.56","31-OCT-24"\n'
    )


def test_a_csv_fixture_whose_header_is_not_the_entrys_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text("CMTE_ID,CMTE_NAME,TTL_RECEIPTS,COVERAGE_END_DT\nC1,N,1,D\n")
    with pytest.raises(ValueError, match="header"):
        fec_fixture.read_file(fec_fixture.SAMPLE, path)


def test_a_csv_fixture_row_short_of_a_value_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text("CMTE_ID,CMTE_NM,TTL_RECEIPTS,COVERAGE_END_DT\nC1,N,1\n")
    with pytest.raises(ValueError, match="row 1"):
        fec_fixture.read_file(fec_fixture.SAMPLE, path)


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
    assert EXPECTED["rows"] == {file: len(fec_fixture.read_rows(file)) for file in FILES}
    assert EXPECTED["silver"] == {
        "committee": len(rows("cm")),
        "candidate": len(rows("cn")),
        "candidate_committee_link": len(rows("ccl")),
        "contribution": len(contributions),
        "independent_expenditure": sum(r["TRANSACTION_TP"] != COMMITTEE_CONTRIBUTION for r in pas2)
        + len(ie_24_48_added()),
        "committee_transfer": len(committee_receipts())
        + len(name_matched_gifts())
        + len(committee_contributions()),
        "organization_receipt": len(organization_receipts()),
        "jfc_attribution": len(attributions()),
        "contributor": len({contributor_key(r) for r in [*contributions, *attributions()]}),
        "reported_total": len(reported_totals(CYCLE)),
        "candidate_reported_total": len(candidate_reported_totals(CYCLE)),
        "operating_expenditure": len(operating_expenditures()),
        "electioneering_communication": len(electioneering_communications()),
        "leadership_pac": len(leadership_pacs()),
        "lobbyist_pac": len(lobbyist_pacs()),
        "bundling_report": len(bundling_reports()),
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
        "dropped_fec_repeat": len(fec_repeats("indiv")),
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


def test_the_expected_recipients_count_a_gift_its_giver_and_recipient_both_filed_once() -> None:
    # Each giver's 24Ks, by recipient and amount: a receipt mirroring one of them is its twin, and
    # each 24K stands for one receipt at most (NEU-2057).
    gifts = Counter((r["CMTE_ID"], r["OTHER_ID"], amount(r)) for r in committee_contributions())
    matched = name_matched()
    receipts = [
        (giver(r), r["CMTE_ID"], amount(r), candidate_of(r["CMTE_ID"], r))
        for r in committee_receipts()
    ] + [
        (matched[r["SUB_ID"]], r["CMTE_ID"], amount(r), candidate_of(r["CMTE_ID"], r))
        for r in name_matched_gifts()
    ]
    # A receipt credited to a candidate the giver credited a 24K to is a twin, whatever its amount.
    credited = {(r["CMTE_ID"], c) for r in committee_contributions() if (c := gift_candidate(r))}
    to_committees: dict[tuple[str, str], int] = defaultdict(int)
    for from_id, to_id, given, candidate in receipts:
        assert from_id is not None
        if (from_id, candidate) in credited:
            continue
        if gifts[from_id, to_id, given]:
            gifts[from_id, to_id, given] -= 1
        else:
            to_committees[from_id, to_id] += given
    for r in committee_contributions():
        if gift_candidate(r) is None and r["OTHER_ID"]:
            to_committees[r["CMTE_ID"], r["OTHER_ID"]] += amount(r)
    entries = [
        (from_id, "candidate", candidate, net)
        for (from_id, candidate), net in gift_pairs().items()
        if net >= 0
    ] + [
        (from_id, "committee", to_id, net)
        for (from_id, to_id), net in to_committees.items()
        if net >= 0 and to_id in committee_ids()
    ]
    # Ranked by amount, then kind, then id.
    lists: dict[str, list[list[str | int]]] = defaultdict(list)
    for from_id, kind, recipient_id, net in sorted(entries, key=lambda e: (-e[3], e[1], e[2])):
        lists[from_id].append([kind, recipient_id, net])
    assert EXPECTED["top_recipients"] == lists
    # BRICKLAYERS' 18K to OKAFOR naming no committee id mirrors no 24K, but is her row's.
    assert ("C00800202", "C00800103") not in to_committees


def test_the_expected_race_committees_are_the_givers_and_the_spenders_on_its_candidates() -> None:
    races = race_ids()
    given = sum_by(
        ((race, from_id), net)
        for (from_id, candidate), net in gift_pairs().items()
        if net >= 0 and (race := races.get(candidate)) is not None
    )
    # A 24/48-hour row with no side is in no race's figure, so in no row here (NEU-2165).
    spent = sum_dollars(
        [
            *(
                ((race, r["CMTE_ID"]), Decimal(amount(r)))
                for r in rows("pas2")
                if r["TRANSACTION_TP"] in (IE_SUPPORT, IE_OPPOSE)
                and (race := races.get(ie_candidate(r) or "")) is not None
            ),
            *(
                ((race, r["spe_id"]), Decimal(r["exp_amo"]))
                for r, _ in ie_24_48_added()
                if r["sup_opp"] in ("S", "O")
                and (race := races.get(ie_24_48_candidate(r) or "")) is not None
            ),
        ]
    )
    entries = [(race, "contribution", c, Decimal(net)) for (race, c), net in given.items()] + [
        (race, "ie", c, net) for (race, c), net in spent.items() if net >= 0
    ]
    # Ranked by amount, then committee id, then kind.
    lists: dict[str, list[list[str | float]]] = defaultdict(list)
    for race, kind, committee_id, net in sorted(entries, key=lambda e: (-e[3], e[2], e[1])):
        lists[race].append([kind, committee_id, float(net)])
    assert EXPECTED["race_top_committees"] == lists


# One row of outside spending as gold reads it (every-FEC-dollar spec §6.5): spender, the candidate
# of the cycle it names (None when none), the contract's kind, side (None where there is none) and
# amount.
type OutsideLine = tuple[str, str | None, str, str | None, Decimal]

KIND_TOTALS = ("communication_cost", "party_coordinated", "electioneering_communication")


@functools.cache
def outside_spending() -> tuple[OutsideLine, ...]:
    """Every row of every kind of outside spending silver holds: `pas2`'s independent expenditures
    and the 24/48-hour rows silver adds, `pas2`'s communication costs and party coordinated
    expenditures, and the electioneering communications' shares."""
    races = race_ids()
    sides = {IE_SUPPORT: "S", IE_OPPOSE: "O"}

    def of_cycle(candidate: str | None) -> str | None:
        return candidate if candidate in races else None

    lines: list[OutsideLine] = [
        (
            r["CMTE_ID"],
            of_cycle(ie_candidate(r)),
            "independent_expenditure",
            sides[r["TRANSACTION_TP"]],
            Decimal(amount(r)),
        )
        for r in rows("pas2")
        if r["TRANSACTION_TP"] in sides
    ]
    lines += [
        (
            r["spe_id"],
            of_cycle(ie_24_48_candidate(r)),
            "independent_expenditure",
            r["sup_opp"] if r["sup_opp"] in ("S", "O") else None,
            Decimal(r["exp_amo"]),
        )
        for r, _ in ie_24_48_added()
    ]
    for kind, types in (("communication_cost", ("24F", "24N")), ("party_coordinated", ("24C",))):
        lines += [
            (
                r["CMTE_ID"],
                candidate,
                kind,
                "O" if r["TRANSACTION_TP"] == "24N" else "S",
                Decimal(amount(r)),
            )
            for r, candidate, _ in pas2_kind(types).values()
        ]
    lines += [
        (
            str(spender),
            None if candidate is None else str(candidate),
            "electioneering_communication",
            None,
            Decimal(str(share)),
        )
        for spender, candidate, _, share in electioneering_communications().values()
    ]
    return tuple(lines)


def figures(
    lines: list[OutsideLine], kinds: Iterable[tuple[str, str | None]]
) -> list[float | None]:
    """The lines' amounts added up by (kind, side), a side of None taking both; an electioneering
    figure None where there is no line, every other 0."""
    totals: list[float | None] = []
    for kind, side in kinds:
        mine = [line[4] for line in lines if line[2] == kind and side in (None, line[3])]
        none = not mine and kind == "electioneering_communication"
        totals.append(None if none else float(sum(mine, Decimal(0))))
    return totals


def test_the_expected_outside_spending_is_every_kind_on_the_fixture() -> None:
    # Gold's other kinds beside v1's independent expenditures (every-FEC-dollar spec §6.5): on a
    # candidate by side, a row with no side in none; on a race its candidates' added up; on a
    # spender every row, those naming no candidate too. A total adds the kinds, a NULL as 0.
    lines = outside_spending()
    races = race_ids()
    sided = [
        line
        for line in lines
        if line[1] is not None
        and (line[3] is not None or line[2] == "electioneering_communication")
    ]
    candidate_kinds = (
        ("communication_cost", "S"),
        ("communication_cost", "O"),
        ("party_coordinated", None),
        ("electioneering_communication", None),
    )
    other = {line[1] for line in sided if line[2] in KIND_TOTALS}
    by_candidate = {
        candidate_id: figures([line for line in sided if line[1] == candidate_id], candidate_kinds)
        for candidate_id in sorted(c for c in other if c is not None)
    }
    by_race: dict[str, list[float | None]] = {}
    for race_id, totals in EXPECTED["races"].items():
        members = [line for line in sided if races.get(line[1] or "") == race_id]
        kinds = figures(members, candidate_kinds)
        ie = Decimal(str(totals["ie_support"])) + Decimal(str(totals["ie_oppose"]))
        added = sum((Decimal(str(f)) for f in kinds if f is not None), ie)
        by_race[race_id] = [*kinds, float(added)]
    spenders = {line[0] for line in lines if line[2] in KIND_TOTALS}
    by_committee: dict[str, list[float | None]] = {}
    for committee_id in sorted(spenders):
        mine = [line for line in lines if line[0] == committee_id]
        kinds = figures(mine, [(kind, None) for kind in KIND_TOTALS])
        ie = Decimal(str(EXPECTED["committees"][committee_id]["ie_total"]))
        by_committee[committee_id] = [
            *kinds,
            float(sum((Decimal(str(f)) for f in kinds if f is not None), ie)),
        ]

    assert EXPECTED["outside_spending"] == {
        "by_candidate": by_candidate,
        "by_race": by_race,
        "by_committee": by_committee,
    }


def test_the_expected_race_top_spenders_are_every_kinds_lines_on_its_candidates() -> None:
    # One line per spender, candidate, kind and side on the race, a row with no side in none, a
    # line netting to $0 or less left out; ranked by amount, then committee, candidate, kind and
    # side (every-FEC-dollar spec §6.5).
    races = race_ids()
    net: dict[tuple[str, str, str, str, str | None], Decimal] = defaultdict(Decimal)
    for spender, candidate, kind, side, value in outside_spending():
        race = races[candidate] if candidate is not None else None
        if race is not None and (side is not None or kind == "electioneering_communication"):
            net[(race, spender, candidate or "", kind, side)] += value
    lists: dict[str, list[list[str | float | None]]] = defaultdict(list)
    for (race, spender, candidate, kind, side), value in sorted(
        ((key, value) for key, value in net.items() if value > 0),
        key=lambda e: (e[0][0], -e[1], e[0][1], e[0][2], e[0][3], e[0][4] or ""),
    ):
        lists[race].append([spender, candidate, kind, side, float(value)])

    assert EXPECTED["race_top_spenders"] == lists
    # The Form 5 filer, the Form 9 filer and the union (CMTE_TP I, E, C) each have a line.
    types = {r["CMTE_ID"]: r["CMTE_TP"] for r in rows("cm")}
    listed = {types[row[0]] for lines in lists.values() for row in lines if isinstance(row[0], str)}
    assert listed >= {"I", "E", "C"}


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


def test_the_expected_returned_costs_are_the_receipts_whose_memo_names_one() -> None:
    receipts = [r for r in organization_receipts() if is_returned_cost(r)]
    assert EXPECTED["returned_costs"]["organization_receipts"] == [
        int(r["SUB_ID"]) for r in receipts
    ]
    # Off line 11(a)(i), so in total_other_lines; a refund of a contribution is none.
    assert all(is_other_line(r) for r in receipts)
    assert any(
        "REFUND" in r["MEMO_TEXT"].upper() and not is_returned_cost(r)
        for r in [*counted(), *organization_receipts()]
    )


def test_the_expected_top_organizations_follow_the_net_money_by_key() -> None:
    # A cost coming back to the committee is no organization's gift (NEU-2402).
    receipts = [r for r in organization_receipts() if not is_returned_cost(r)]
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


def test_the_leadership_files_pacs_are_cms_leadership_pacs() -> None:
    # Every PAC of FEC's leadership file is a committee `cm` holds (leadership-lobbyist
    # measurement Q2), here each designated D; one sponsor is named as `cn` names the incumbent,
    # and one is blank on a PAC whose `cm` row names no candidate either, so nothing but a list row
    # can link it (NEU-2174). STRATTON 2024 is designated D and not listed (§7.3).
    cm = {r["CMTE_ID"]: r for r in rows("cm")}
    incumbents = {r["CAND_NAME"] for r in rows("cn") if r["CAND_ICI"] == "I"}
    named, blank = rows("leadership")

    assert {cm[r["Committee_Id"]]["CMTE_DSGN"] for r in (named, blank)} == {"D"}
    assert named["Sponsor_Name"] in incumbents
    assert blank["Sponsor_Name"] == cm[blank["Committee_Id"]]["CAND_ID"] == ""
    assert cm["C00800102"]["CMTE_DSGN"] == "D"
    assert "C00800102" not in {named["Committee_Id"], blank["Committee_Id"]}


@pytest.mark.parametrize("file", ["lobbyist", "lobbyist_bundle"])
def test_each_lobbyist_rows_image_number_is_its_own(file: FecFile) -> None:
    # NEU-2175 keys `bundling_report` by the image number in Link_Image and breaks a Form 1 tie by
    # it (every-FEC-dollar spec §7.2, §7.5): unique in FEC's file, so in the fixture's.
    images = [r["Link_Image"] for r in rows(file)]

    assert len(set(images)) == len(images)


def test_the_bundling_reports_recipients_are_the_cycles_committees() -> None:
    # A recipient no committee of its cycle is dropped (§7.5); the fixture plants none of those.
    assert {r["Committee_Id"] for r in rows("lobbyist_bundle")} <= committee_ids()


def image_number(row: Row) -> str:
    """The image number a leadership or lobbyist file's Link_Image ends in: the digits after `?_`
    (or `?`)."""
    found = re.search(r"\?_?(\d+)", row["Link_Image"])
    assert found is not None, row["Link_Image"]
    return found.group(1)


def dmy(value: str) -> date | None:
    """A DD-MON-YY date, as the leadership and lobbyist files write them; None when blank."""
    return datetime.strptime(value, "%d-%b-%y").date() if value else None


SPONSORS = Path(__file__).resolve().parents[1] / "fixtures" / "fec" / "leadership_sponsors.csv"


@functools.cache
def leadership_pacs() -> Mapping[str, list[str | None]]:
    """Silver leadership_pac's rows by committee, [sponsor_name, sponsor_candidate_id,
    sponsor_source] (project spec §7.4): the fixture's sponsor list row for the cycle where there is
    one; else the one person of the cycle, through their alias, whose last name and first given
    name are the sponsor's."""
    with SPONSORS.open() as src:
        listed = {r["committee_id"]: r for r in csv.DictReader(src) if int(r["cycle"]) == CYCLE}
    people: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in rows("cn"):
        people[person(r["CAND_NAME"])].add(aliases().get(r["CAND_ID"], r["CAND_ID"]))
    tallied: dict[str, list[str | None]] = {}
    for r in rows("leadership"):
        sponsor = r["Sponsor_Name"].strip() or None
        entry = listed.get(r["Committee_Id"])
        if entry is not None:
            tallied[r["Committee_Id"]] = [
                sponsor or entry["sponsor_name"],
                entry["candidate_id"],
                "list",
            ]
            continue
        key = person(sponsor) if sponsor else ("", "")
        matched: set[str] = people.get(key, set()) if key[1] else set()
        rule = next(iter(matched)) if len(matched) == 1 else None
        tallied[r["Committee_Id"]] = [sponsor, rule, None if rule is None else "rule"]
    return MappingProxyType(tallied)


@functools.cache
def lobbyist_pacs() -> Mapping[str, list[date | str]]:
    """Silver lobbyist_pac's rows by committee, [filed_date, image_num] (project spec §7.2): each
    committee of the cycle whose latest Form 1 filed by the cycle's last day, then the higher image
    number, has the box ticked."""
    latest: dict[str, tuple[date, int, Row]] = {}
    for r in rows("lobbyist"):
        filed = dmy(r["Date_Filed"])
        assert filed is not None
        if filed > date(CYCLE, 12, 31):
            continue
        order = (filed, int(image_number(r)), r)
        best = latest.get(r["Committee_Id"])
        if best is None or order[:2] > best[:2]:
            latest[r["Committee_Id"]] = order
    return MappingProxyType(
        {
            committee: [filed, image_number(r)]
            for committee, (filed, _, r) in latest.items()
            if r["Is_Lobbyist"] == "Y" and committee in committee_ids()
        }
    )


def half_year(day: date) -> str:
    return f"{day.year}-{1 if day.month <= 6 else 2}"


@functools.cache
def bundling_reports() -> Mapping[str, list[str | bool | float | None]]:
    """Silver bundling_report's rows by image number, [committee_id, half_year, is_superseded,
    amount] (project spec §7.5, §7.6): the cycle's reports, amendments resolved by the latest
    receipt date, then the higher image number; each kept report adding its period amount unless
    its covered period holds another kept report, and the one carrying the half-year figure adding
    what it exceeds those by."""
    reports = rows("lobbyist_bundle")
    superseded: set[str] = set()
    by_period: dict[tuple[str, date, date], list[Row]] = defaultdict(list)
    for r in reports:
        start, end = dmy(r["Coverage_Start_Date"]), dmy(r["Coverage_End_Date"])
        if start is not None and end is not None:
            by_period[(r["Committee_Id"], start, end)].append(r)
    for same in by_period.values():
        same.sort(key=lambda r: (dmy(r["Receipt_Date"]), int(image_number(r))))
        superseded.update(image_number(r) for r in same[:-1])
    kept = [r for r in reports if image_number(r) not in superseded and r["Coverage_End_Date"]]

    def period(r: Row) -> tuple[date | None, date]:
        end = dmy(r["Coverage_End_Date"])
        assert end is not None
        return dmy(r["Coverage_Start_Date"]), end

    def holds_another(r: Row) -> bool:
        start, end = period(r)
        return start is not None and any(
            o["Committee_Id"] == r["Committee_Id"]
            and (inner := period(o))[0] is not None
            and start <= inner[0] <= inner[1] <= end
            and inner != (start, end)
            for o in kept
        )

    own = {
        image_number(r): 0 if holds_another(r) else float(Decimal(r["Quarterly_Contribution"]))
        for r in kept
    }
    halves: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for r in kept:
        halves[(r["Committee_Id"], half_year(period(r)[1]))].append(r)
    for half in halves.values():
        carriers = [r for r in half if Decimal(r["Semi_Annual_Contribution"]) > 0]
        if carriers:
            carrier = max(
                carriers,
                key=lambda r: (period(r)[1], period(r)[0] or date.min, int(image_number(r))),
            )
            figure = float(Decimal(carrier["Semi_Annual_Contribution"]))
            innermost = sum(own[image_number(r)] for r in half)
            own[image_number(carrier)] += max(figure - innermost, 0)
    tallied: dict[str, list[str | bool | float | None]] = {}
    for r in reports:
        end, received = dmy(r["Coverage_End_Date"]), dmy(r["Receipt_Date"])
        year = (end or received or date.min).year
        if year + year % 2 != CYCLE or r["Committee_Id"] not in committee_ids():
            continue
        image = image_number(r)
        tallied[image] = [
            r["Committee_Id"],
            None if end is None else half_year(end),
            image in superseded,
            own.get(image, 0),
        ]
    return MappingProxyType(tallied)


def test_the_expected_leadership_and_lobbyist_rows_are_the_rules_on_the_fixture() -> None:
    assert EXPECTED["leadership_pacs"] == leadership_pacs()
    assert EXPECTED["lobbyist_pacs"] == lobbyist_pacs()
    assert EXPECTED["bundling_reports"] == bundling_reports()
