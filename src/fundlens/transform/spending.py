"""The spending category of an operating expenditure (every-FEC-dollar spec §5.3, NEU-2153).

`spending_category(fec_category, purpose)` is one of `CATEGORIES`, with where it came from:

1. `purpose_rule`: the first of `PURPOSE_RULES` whose pattern is in the purpose, upper-cased,
   trimmed and with runs of whitespace made one space;
2. `fec`: else FEC's code, where it is one of `TRUSTED_CODES`, the six filers use reliably;
3. `unclassified`: else `other`.

The rules are ordered so the first match follows the measurement's tie-breaks
(`docs/measurements/oppexp-2024.md` Q8, T1 to T11): a purpose naming what the money was for and
the channel it went through takes the activity (T2), so fundraising is tried before digital and
media; "X consulting" is X's (T3), so consulting is tried last; payroll, per-payment fees and
card bills are tried first, since each is named outright when it is the purpose. An order is not
T5's "first named" for every pair: `TRAVEL & EVENT EXPENSES` is events, as the labelled
`AUDIO VISUAL SERVICES, EVENT STAGING EXPENSE, & TRAVEL EXPENSES` is. A purpose that
names nothing bought (`SEE MEMO`, an in-kind outlay's `IN-KIND CONTRIBUTION`, crypto received
and not liquidated) stops the rules unmatched, so FEC's code decides it, else it is `other`.

The rules are scored on `tests/fixtures/spending/purpose_labels_2024.csv`, the measurement's 200
labelled purposes; `tests/unit/test_spending.py` asserts the score and lists the misses. A rule
added or reordered is a measured change: the test says what it moved.

The function is pure; `register` makes it a DuckDB function, which the silver SQL asks once per
distinct (code, purpose) pair, not once per row.
"""

import re
from typing import Final, Literal

import duckdb
from duckdb.func import FunctionNullHandling

type Category = Literal[
    "media",
    "digital",
    "mail",
    "fundraising",
    "payroll",
    "consulting",
    "field",
    "polling_research",
    "travel",
    "events",
    "administrative",
    "legal_compliance",
    "transfers_fees",
    "credit_card",
    "other",
]
type CategorySource = Literal["purpose_rule", "fec", "unclassified"]

# The fixed list (spec §5.3), in the spec's order.
CATEGORIES: Final[tuple[Category, ...]] = (
    "media",
    "digital",
    "mail",
    "fundraising",
    "payroll",
    "consulting",
    "field",
    "polling_research",
    "travel",
    "events",
    "administrative",
    "legal_compliance",
    "transfers_fees",
    "credit_card",
    "other",
)

# FEC's codes that agree with the labels on 84.98% to 100% of their dollars (spec §5.3, Q8g).
# Every other code is read by purpose alone: trusting one is a measured change.
TRUSTED_CODES: Final[dict[str, Category]] = {
    "002": "travel",
    "004": "media",
    "005": "polling_research",
    "011": "transfers_fees",
    "102": "media",
    "106": "polling_research",
}

# (category, pattern), first match wins. A None category names nothing bought: it stops the rules
# and leaves the row to FEC's code.
_RULES: Final[list[tuple[Category | None, str]]] = [
    # Names nothing bought (T11; spec §5.3's `other`): an in-kind outlay, crypto received and held,
    # a pointer to memo lines or another schedule, the form's own heading.
    (None, r"\bIN[- ]?KIND\b"),
    (None, r"\bNOT LIQUIDATED\b"),
    (None, r"^SEE\b"),
    (None, r"^OPERATING (EXPENDITURES?|EXPENSES?)$"),
    # Pay to staff, before fees and taxes: a payroll processor's fee and payroll taxes are pay's.
    ("payroll", r"\bPAYROLL\b|\bSALAR(Y|IES)\b|\bWAGES?\b|\bSTIPENDS?\b"),
    ("payroll", r"\bBENEFITS\b|\b(EMPLOYEE|STAFF) BENEFIT|\bHEALTH INSURANCE\b"),
    ("payroll", r"\bMEDICAL\b|\bDENTAL\b|\bRETIREMENT\b"),
    ("payroll", r"\bPERSONNEL\b|\bWITHHOLDING\b|\bFICA\b|\b401 ?\(?K\b"),
    # A fee per payment processed (T4), before card bills: a card-processing fee is no card bill.
    ("transfers_fees", r"\bMERCHANT\b|\bPROCESSING FEES?\b|\bCREDIT CARD PROCESSING\b"),
    ("transfers_fees", r"\b(BANK|CARD|TRANSACTION|CONDUIT|MERCHANDISE|WIRE) FEES?\b"),
    ("transfers_fees", r"\b(BANK|WIRE) CHARGES?\b"),
    ("transfers_fees", r"\bACTBLUE\b|\bWINRED\b|\bEARMARK (FEES?|PROCESSING)\b"),
    # A refund is money passed back, a card's refund among them.
    ("transfers_fees", r"\bREFUNDS?\b"),
    # A card bill (T9): what it bought is in its sub-items, if anywhere.
    ("credit_card", r"\bCREDIT CARD\b|\bAMEX\b|\bAMERICAN EXPRESS\b|\bCARD PAYMENT\b"),
    # An independent expenditure paid ahead, its medium unnamed, is media (T10); print advertising
    # is media's, before mail takes PRINT.
    ("media", r"\bINDEPENDENT EXPENDITURES?\b|\bIES?\b"),
    ("media", r"\bPRINT (AD|ADS|ADVERTISING|ADVERTISEMENTS?)\b|\bNEWSPAPER\b"),
    # Direct mail and printed material, fundraising mail among it (§5.3's `mail`), before
    # fundraising.
    ("mail", r"(?<!E-)\bMAIL(ING|INGS|ER|ERS)?\b|\bPOSTAGE\b|\bPRINT(ING|ED|ER|S)?\b"),
    ("mail", r"\bLETTERSHOP\b|\bMAILSHOP\b|\bSIGNS?\b"),
    # The cost of raising money: the activity wins over the channel (T2).
    ("fundraising", r"\bFUND ?RAIS(ING|ER|ERS|E)\b|\bFINANCE CONSULT|\bTELEMARKETING\b"),
    ("fundraising", r"\bSOLICIT"),
    ("fundraising", r"\bMERCHANDISE\b|\bDONOR\b|\bACQUISITION\b|\bCAGING\b|\bLIST PURCHASE\b"),
    # Money passed on, named outright, after fundraising: a fundraiser's commission on
    # contributions is fundraising's.
    ("transfers_fees", r"\bCONTRIBUTIONS?\b|\bDONATIONS?\b|\bTRANSFERS?\b|\bDISGORGEMENT\b"),
    ("transfers_fees", r"\bLOAN (RE)?PAYMENTS?\b|\bREPAYMENT OF LOAN\b"),
    # Polling and research, before digital: an online survey is a survey (T2).
    ("polling_research", r"\bPOLL(ING|S)?\b|\bSURVEYS?\b|\bFOCUS GROUPS?\b|\bRESEARCH\b"),
    # Data processing for contributions is compliance work, not data services.
    ("legal_compliance", r"\bDATA PROCESSING\b"),
    # Online advertising and messaging, websites, digital organizing, data (T1: only advertising
    # named digital, online, SMS or social is digital's).
    ("digital", r"\bDIGITAL\b|\bON ?LINE\b|\bINTERNET (AD|ADS|ADVERTISING)\b|\bSOCIAL MEDIA\b"),
    ("digital", r"\bSMS\b|\bTEXT(S|ING)?\b|\bE-?MAIL(S|ING)?\b|\bWEB ?(SITE|SITES|HOSTING)?\b"),
    ("digital", r"\bHOSTING\b|\bDATA(BASE)?\b|\bVOTER FILE\b"),
    ("digital", r"^DIRECT MARKETING\b|\bWIRE SERVICES\b"),
    ("fundraising", r"\bLIST (RENTAL|RENT|ACQUISITION)\b"),
    # Paid advertising whose channel is broadcast, print or unnamed (T1).
    ("media", r"\bMEDIA\b|\bADVERTIS(ING|EMENTS?|E)\b|\bADS?\b|\bAD BUYS?\b"),
    ("media", r"\bTV\b|\bTELEVISION\b|\bRADIO\b|\bCABLE\b|\bBROADCAST\b|\bBILLBOARDS?\b"),
    ("media", r"\bVIDEO(GRAPHY)?\b|\bCOMMERCIALS?\b|\bAIR ?TIME\b"),
    # Voter contact in person and by phone (T8).
    ("field", r"\bCANVASS|\bFIELD\b|\bORGANIZ(ING|ERS?)\b|\bVOTER (REGISTRATION|CONTACT)\b"),
    ("field", r"\bGOTV\b|\bGET OUT THE VOTE\b|\bPHONE ?BANK|\bPHONE CALLS?\b"),
    ("field", r"\bDOOR (TO DOOR|KNOCK)"),
    # Putting on an event, before travel (T5: the first named of an event's costs and travel).
    ("events", r"\bEVENTS?\b|\bCATER(ING|ER)\b|\bVENUE\b|\b(SITE|FACILITY) RENTALS?\b"),
    ("events", r"\bAUDIO ?-?VISUAL\b|\bSTAGING\b|\bADVANCE\b|\bMEETINGS?\b"),
    ("travel", r"\bTRAVEL|\bAIR ?FARES?\b|\bAIR\b|\bFLIGHTS?\b|\bLODGING\b|\bHOTELS?\b"),
    ("travel", r"\bMILEAGE\b|\bTAXI|\bUBER\b|\bLYFT\b|\b(CAR|AUTO) RENTAL\b|\bRENTAL CAR\b"),
    ("travel", r"\bFUEL\b|\bGASOLINE\b|\bPARKING\b|\bTOLLS?\b|\bTRANSPORTATION\b|\bPER DIEM\b"),
    ("legal_compliance", r"\bLEGAL\b|\bATTORNEYS?\b|\bCOMPLIANCE\b|\bACCOUNTING\b|\bACCOUNTANT\b"),
    ("legal_compliance", r"\bBOOKKEEPING\b|\bAUDIT\b|\bFEC REPORT"),
    # Running an office: rent, utilities, software, supplies, insurance and taxes not staff's.
    ("administrative", r"\bRENT\b|\bUTILIT(Y|IES)\b|\bSOFTWARE\b|\bCOMPUTERS?\b|\bEQUIPMENT\b"),
    ("administrative", r"\bOFFICE\b|\bSUPPLIES\b|\bINSURANCE\b|\bTAX(ES)?\b|\bSECURITY\b"),
    ("administrative", r"\bSUBSCRIPTIONS?\b|\bTELEPHONE\b|\bPHONES?\b|\bINTERNET\b|\bOVERHEAD\b"),
    # Money passed on, named only by the account it went between.
    ("transfers_fees", r"\bACCT\b|\bACCOUNT\b|\bALLOCABLE\b|\bNON-?FEDERAL\b"),
    # A service fee whose purpose names no service (T4: most are a conduit's, per contribution).
    ("transfers_fees", r"\bSERVICE (FEES?|CHARGES?)\b"),
    # Consulting that names no other category, last (T3).
    ("consulting", r"\bCONSULT(ING|ANTS?|ATION)?\b|\bSTRATEG(Y|IC|IST)\b|\bSPOKESPERSON\b"),
]

# Each rule compiled, in order.
PURPOSE_RULES: Final[list[tuple[Category | None, re.Pattern[str]]]] = [
    (category, re.compile(pattern)) for category, pattern in _RULES
]


def normalize_purpose(purpose: str) -> str:
    """`purpose` upper-cased, trimmed and with runs of whitespace made one space."""
    return " ".join(purpose.upper().split())


def purpose_category(purpose: str | None) -> Category | None:
    """The first matching rule's category, or None: no rule matched, or the first that did says the
    purpose names nothing bought."""
    if purpose is None:
        return None
    normalized = normalize_purpose(purpose)
    for category, pattern in PURPOSE_RULES:
        if pattern.search(normalized):
            return category
    return None


def spending_category(
    fec_category: str | None, purpose: str | None
) -> tuple[Category, CategorySource]:
    """The row's spending category and its `category_source` (spec §5.3): the purpose rule's, else
    a trusted FEC code's, else `other`. `fec_category` is the padded three-digit code silver
    holds."""
    if (category := purpose_category(purpose)) is not None:
        return category, "purpose_rule"
    if fec_category is not None and (category := TRUSTED_CODES.get(fec_category.strip())):
        return category, "fec"
    return "other", "unclassified"


CATEGORY_TYPE = "STRUCT(category VARCHAR, source VARCHAR)"


def _category_struct(fec_category: str | None, purpose: str | None) -> dict[str, str]:
    category, source = spending_category(fec_category, purpose)
    return {"category": category, "source": source}


def register(con: duckdb.DuckDBPyConnection) -> None:
    """Make `spending_category(fec_category, purpose)` a DuckDB function on `con`, a struct of the
    `category` and its `source`. A NULL argument is seen as None."""
    # DuckDB's stub leaves one overload's return type unknown.
    con.create_function(  # pyright: ignore[reportUnknownMemberType]
        "spending_category",
        _category_struct,
        ["VARCHAR", "VARCHAR"],
        CATEGORY_TYPE,
        null_handling=FunctionNullHandling.SPECIAL,
    )
