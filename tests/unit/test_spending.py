"""The spending category (every-FEC-dollar spec §5.3, NEU-2153)."""

import csv
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import TypedDict

import duckdb
import pytest

from fundlens.transform import spending
from fundlens.transform.spending import CATEGORIES, TRUSTED_CODES, spending_category

LABELS = Path(__file__).parents[1] / "fixtures" / "spending" / "purpose_labels_2024.csv"

# The share of the labelled set's dollars the rule must classify as the labels do (NEU-2153).
TARGET = Decimal("0.90")

# The labelled purposes the rule classifies otherwise, purpose: (label, what the rule gives). Empty:
# the rules were written against this set, which scores what they were tuned on. The share of a
# real cycle's counted dollars left unclassified, logged by every transform, is the check on the
# purposes nobody labelled.
KNOWN_MISSES: dict[str, tuple[str, str]] = {}


class Label(TypedDict):
    purpose: str
    dollars: Decimal
    fec_category: str | None
    spending_category: str


@cache
def labels() -> tuple[Label, ...]:
    """The measurement's 200 labelled purposes (oppexp-2024.md Q8)."""
    with LABELS.open(newline="") as file:
        return tuple(
            Label(
                purpose=row["purpose"],
                dollars=Decimal(row["dollars"]),
                fec_category=row["fec_category"] or None,
                spending_category=row["spending_category"],
            )
            for row in csv.DictReader(file)
        )


def test_the_rule_classifies_the_labelled_sets_dollars_as_labelled() -> None:
    misses: dict[str, tuple[str, str]] = {}
    right = Decimal(0)
    for label in labels():
        category, _ = spending_category(label["fec_category"], label["purpose"])
        if category == label["spending_category"]:
            right += label["dollars"]
        else:
            misses[label["purpose"]] = (label["spending_category"], category)
    score = right / sum(label["dollars"] for label in labels())

    assert len(labels()) == 200
    assert score >= TARGET
    assert misses == KNOWN_MISSES


def test_the_labels_are_the_fixed_list() -> None:
    assert {label["spending_category"] for label in labels()} == set(CATEGORIES)
    assert set(TRUSTED_CODES.values()) <= set(CATEGORIES)


@pytest.mark.parametrize(
    ("fec_category", "purpose", "expected"),
    [
        # The purpose first, a trusted code beside it or not: 004 cannot tell digital from media.
        ("004", "DIGITAL ADVERTISING", ("digital", "purpose_rule")),
        ("004", "MEDIA BUY", ("media", "purpose_rule")),
        # An untrusted code is never read: 001 on pay, and on a purpose no rule matches.
        ("001", "SALARY", ("payroll", "purpose_rule")),
        ("001", "ARTWORK", ("other", "unclassified")),
        ("003", "REIMBURSEMENT", ("other", "unclassified")),
        # A trusted code decides a purpose that names nothing bought, or none.
        ("004", "SEE BELOW", ("media", "fec")),
        ("002", None, ("travel", "fec")),
        ("011", "IN-KIND CONTRIBUTION", ("transfers_fees", "fec")),
        # Else other: no code, or an in-kind outlay, whatever else its purpose names (T11).
        (None, None, ("other", "unclassified")),
        (None, "SEE MEMO", ("other", "unclassified")),
        (None, "IN-KIND CONTRIBUTION: CATERING", ("other", "unclassified")),
        (None, "IN-KIND CONTRIBUTION", ("other", "unclassified")),
        # The purpose upper-cased, trimmed and its whitespace made one space.
        (None, "  media \t  buy ", ("media", "purpose_rule")),
        # E-mail is digital's, not mail's; card-processing fees are no card bill (T4, T9).
        (None, "E-MAIL SERVICES", ("digital", "purpose_rule")),
        (None, "CREDIT CARD PROCESSING FEES", ("transfers_fees", "purpose_rule")),
        (None, "CREDIT CARD CHARGES", ("credit_card", "purpose_rule")),
        # The activity wins over the channel (T2), and X consulting is X's (T3).
        (None, "FUNDRAISING DIGITAL AD BUY", ("fundraising", "purpose_rule")),
        (None, "MEDIA STRATEGY CONSULTING", ("media", "purpose_rule")),
        (None, "GENERAL CONSULTING", ("consulting", "purpose_rule")),
        # A named service's fees are its own (T3); a bare service fee is a conduit's (T4).
        (None, "LEGAL SERVICE FEES", ("legal_compliance", "purpose_rule")),
        (None, "SERVICE FEE", ("transfers_fees", "purpose_rule")),
        # A fundraiser's commission is fundraising's, a card's refund a refund, a fundraising
        # benefit no payroll, an online survey a survey.
        (None, "FUNDRAISING COMMISSIONS ON CONTRIBUTIONS", ("fundraising", "purpose_rule")),
        (None, "REFUND OF CREDIT CARD CONTRIBUTION", ("transfers_fees", "purpose_rule")),
        (None, "FUNDRAISING BENEFIT", ("fundraising", "purpose_rule")),
        (None, "ONLINE SURVEY", ("polling_research", "purpose_rule")),
    ],
)
def test_the_purpose_rule_comes_first_then_a_trusted_code_then_other(
    fec_category: str | None, purpose: str | None, expected: tuple[str, str]
) -> None:
    assert spending_category(fec_category, purpose) == expected


def test_the_category_is_a_duckdb_function_once_registered() -> None:
    with duckdb.connect() as con:
        spending.register(con)
        rows = con.execute(
            "SELECT spending_category(NULL, 'MEDIA BUY'), spending_category('005', NULL),"
            " spending_category(NULL, NULL)"
        ).fetchone()
    assert rows == (
        {"category": "media", "source": "purpose_rule"},
        {"category": "polling_research", "source": "fec"},
        {"category": "other", "source": "unclassified"},
    )
