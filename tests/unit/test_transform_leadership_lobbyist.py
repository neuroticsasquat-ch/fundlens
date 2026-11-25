"""Silver `leadership_pac`, `lobbyist_pac` and `bundling_report` (every-FEC-dollar spec §7.3–7.6,
NEU-2175) on hand-made rows: the cases the fixture cycle does not plant (a sponsor name matching
several people or several ids, an alias, the half-year figure's tie, a report with no coverage
start, one spanning two cycles), and each check failing on a row the models never write."""

import csv
import io
import re
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from fundlens.transform import runner
from fundlens.transform.runner import render

SQL = Path(__file__).resolve().parents[2] / "sql"
MODELS = ("14_leadership_pac.sql", "15_lobbyist_pac.sql", "16_bundling_report.sql")
CHECKS = SQL / "checks"
CYCLE = 2024
PARAMS = {"cycle": CYCLE}

# Candidates: one person under two ids, an alias and the id it names; two people of one name; two
# ids under one name that are no alias of each other (Dan Sullivan's case, Q14b).
REYES, REYES_ALIAS = "H4TX01001", "H4TX01002"
MORA_TX, MORA_NM = "H4TX02001", "H4NM01001"
SULLIVAN_AK, SULLIVAN_MA = "S4AK00001", "H4MA01001"
RETIRED = "S8OR00001"  # a candidate of another cycle, named by the list
# Committees.
REYES_PAC, MORA_PAC, SULLIVAN_PAC, NO_GIVEN_PAC, LISTED_PAC, BLANK_PAC, NAMED_LISTED_PAC = (
    "C00900001",
    "C00900002",
    "C00900003",
    "C00900004",
    "C00900005",
    "C00900006",
    "C00900007",
)
RECIPIENT, OTHER_RECIPIENT = "C00900101", "C00900102"


def build(con: duckdb.DuckDBPyConnection) -> None:
    """The models' inputs, hand-made, and the three models run over them."""
    committees = [
        REYES_PAC,
        MORA_PAC,
        SULLIVAN_PAC,
        NO_GIVEN_PAC,
        LISTED_PAC,
        BLANK_PAC,
        NAMED_LISTED_PAC,
        RECIPIENT,
        OTHER_RECIPIENT,
    ]
    con.execute(
        "CREATE TABLE committee AS SELECT unnest(?) AS committee_id, 'Q' AS designation",
        [committees],
    )
    con.execute(
        "CREATE TABLE candidate AS SELECT * FROM (VALUES"
        f" ('{REYES}', CAST(NULL AS VARCHAR), 'REYES, ANA M'),"
        f" ('{REYES_ALIAS}', '{REYES}', 'REYES, ANA'),"
        f" ('{MORA_TX}', NULL, 'MORA, LUIS'),"
        f" ('{MORA_NM}', NULL, 'MORA, LUIS ALBERTO'),"
        f" ('{SULLIVAN_AK}', NULL, 'SULLIVAN, DAN'),"
        f" ('{SULLIVAN_MA}', NULL, 'SULLIVAN, DAN'),"
        # A candidate whose name has no first given name: matched by no sponsor.
        " ('H4CA01001', NULL, 'PRINCE')"
        ") AS t(candidate_id, alias_of, name)"
    )
    con.execute(
        "CREATE TABLE leadership AS SELECT * FROM (VALUES"
        # Matches the alias and the id it names: one person, the id alias_of points to.
        f" ('{REYES_PAC}', 'Reyes, Ana  '),"
        # Two people of one last and first given name: none.
        f" ('{MORA_PAC}', 'MORA, LUIS'),"
        # One name under two ids, no alias: none.
        f" ('{SULLIVAN_PAC}', 'SULLIVAN, DAN'),"
        # Nothing after the comma: matches nobody, PRINCE included.
        f" ('{NO_GIVEN_PAC}', 'PRINCE,'),"
        # The rule would link REYES; the list overrides it.
        f" ('{LISTED_PAC}', 'REYES, ANA'),"
        # Blank: the list names the sponsor and their id.
        f" ('{BLANK_PAC}', ''),"
        # Named, unmatched, and listed: the file's name stands, the list's id is taken.
        f" ('{NAMED_LISTED_PAC}', 'WYDEN, RON')"
        ") AS t(Committee_Id, Sponsor_Name)"
    )
    con.execute(
        "CREATE TABLE leadership_sponsor AS SELECT * FROM (VALUES"
        f" ('{LISTED_PAC}', 'MORA, LUIS', '{MORA_TX}'),"
        f" ('{BLANK_PAC}', 'SULLIVAN, DAN', '{SULLIVAN_AK}'),"
        f" ('{NAMED_LISTED_PAC}', 'WYDEN, RONALD', '{RETIRED}')"
        ") AS t(committee_id, sponsor_name, candidate_id)"
    )
    con.execute(
        "CREATE TABLE lobbyist AS SELECT * FROM (VALUES"
        # Ticked on the cycle's last day: flagged.
        f" ('http://docquery.fec.gov/cgi-bin/fecimg/?_202412319000000001+0', '{REYES_PAC}',"
        "  '31-DEC-24', 'Y'),"
        # Ticked the day after the cycle: not read, and an earlier blank decides.
        f" ('http://docquery.fec.gov/cgi-bin/fecimg/?_202501019000000002+0', '{MORA_PAC}',"
        "  '01-JAN-25', 'Y'),"
        f" ('http://docquery.fec.gov/cgi-bin/fecimg/?_202003019000000003+0', '{MORA_PAC}',"
        "  '01-MAR-20', NULL),"
        # An 11-digit image number, ticked, beside nothing later: flagged.
        f" ('http://docquery.fec.gov/cgi-bin/fecimg/?13940234567', '{SULLIVAN_PAC}',"
        "  '10-JUN-13', 'Y')"
        ") AS t(Link_Image, Committee_Id, Date_Filed, Is_Lobbyist)"
    )
    con.execute(
        "CREATE TABLE lobbyist_bundle AS SELECT Committee_Id,"
        " 'http://docquery.fec.gov/cgi-bin/fecimg/?_' || image || '+0' AS Link_Image,"
        " 'QUARTERLY' AS Report_Type, Receipt_Date, Coverage_Start_Date, Coverage_End_Date,"
        " CAST(q AS DECIMAL(14, 2)) AS Quarterly_Contribution,"
        " CAST(s AS DECIMAL(14, 2)) AS Semi_Annual_Contribution"
        " FROM (VALUES"
        # The second half of 2023: the July quarter; the October quarter, filed twice, the later
        # receipt kept, with a half-year figure; and a six-month report from 1 July, holding both
        # quarters, with a figure of its own. The two figures end on one day: the later coverage
        # start's, $9,000, is the half's.
        f" ('{RECIPIENT}', '1001', '15-OCT-23', '01-JUL-23', '30-SEP-23', 3000, 0),"
        f" ('{RECIPIENT}', '1002', '15-JAN-24', '01-OCT-23', '31-DEC-23', 2500, 0),"
        f" ('{RECIPIENT}', '1003', '20-JAN-24', '01-OCT-23', '31-DEC-23', 4000, 9000),"
        f" ('{RECIPIENT}', '1004', '31-JAN-24', '01-JUL-23', '31-DEC-23', 7000, 8000),"
        # The first half of 2024: a report with no coverage start, counted in its end's half,
        # never superseded, holding nothing; and its half-year figure is below the periods.
        f" ('{RECIPIENT}', '1005', '15-APR-24', NULL, '31-MAR-24', 6000, 0),"
        f" ('{RECIPIENT}', '1006', '15-JUL-24', '01-APR-24', '30-JUN-24', 5000, 10000),"
        f" ('{RECIPIENT}', '1007', '16-JUL-24', NULL, '31-MAR-24', 1000, 0),"
        # A report spanning two cycles, 2024's by its end, holds 2022's last quarter: that
        # quarter adds its amount in 2022, and the spanning report adds nothing in 2024.
        f" ('{OTHER_RECIPIENT}', '2001', '15-JAN-23', '01-OCT-22', '31-DEC-22', 4000, 0),"
        f" ('{OTHER_RECIPIENT}', '2002', '15-APR-23', '01-OCT-22', '31-MAR-23', 6000, 0),"
        # A report with no coverage end: 2024's by its receipt date, adding nothing.
        f" ('{OTHER_RECIPIENT}', '2003', '15-MAY-24', NULL, NULL, 500, 500),"
        # A recipient no committee of the cycle: dropped.
        " ('C00999999', '3001', '15-APR-24', '01-JAN-24', '31-MAR-24', 0, 0)"
        ") AS t(Committee_Id, image, Receipt_Date, Coverage_Start_Date, Coverage_End_Date, q, s)"
    )
    for model in MODELS:
        con.execute(render(SQL / "silver" / model, PARAMS))


@pytest.fixture(scope="module")
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    """The models built once for the tests that only read them."""
    with duckdb.connect() as con:
        build(con)
        yield con


def failing(con: duckdb.DuckDBPyConnection, check: str) -> list[tuple[object, ...]]:
    return con.execute(render(CHECKS / check, PARAMS)).fetchall()


def test_a_sponsor_takes_an_id_by_the_rule_only_for_one_person_and_the_list_overrides_it(
    con: duckdb.DuckDBPyConnection,
) -> None:
    rows = con.execute(
        "SELECT committee_id, sponsor_name, sponsor_candidate_id, sponsor_source"
        " FROM leadership_pac ORDER BY committee_id"
    ).fetchall()

    assert rows == [
        # The alias's match is the person's id.
        (REYES_PAC, "Reyes, Ana", REYES, "rule"),
        (MORA_PAC, "MORA, LUIS", None, None),
        (SULLIVAN_PAC, "SULLIVAN, DAN", None, None),
        (NO_GIVEN_PAC, "PRINCE,", None, None),
        (LISTED_PAC, "REYES, ANA", MORA_TX, "list"),
        (BLANK_PAC, "SULLIVAN, DAN", SULLIVAN_AK, "list"),
        (NAMED_LISTED_PAC, "WYDEN, RON", RETIRED, "list"),
    ]


def test_a_committee_is_flagged_by_its_latest_form_1_by_the_cycles_last_day(
    con: duckdb.DuckDBPyConnection,
) -> None:
    rows = con.execute(
        "SELECT committee_id, filed_date, image_num FROM lobbyist_pac ORDER BY committee_id"
    ).fetchall()

    assert rows == [
        (REYES_PAC, date(2024, 12, 31), "202412319000000001"),
        (SULLIVAN_PAC, date(2013, 6, 10), "13940234567"),
    ]


def test_bundling_amounts_add_up_to_the_greater_of_each_halfs_two_figures(
    con: duckdb.DuckDBPyConnection,
) -> None:
    rows = con.execute(
        "SELECT source_record_id, half_year, is_superseded, amount FROM bundling_report"
        " ORDER BY source_record_id"
    ).fetchall()

    assert rows == [
        # 2023-2: the quarters' $3,000 and $4,000 (1002 superseded by 1003) are innermost; the
        # half-year figure is 1003's $9,000, its start later than 1004's, so 1003 adds $2,000 more.
        ("1001", "2023-2", False, Decimal("3000.00")),
        ("1002", "2023-2", True, Decimal("0.00")),
        ("1003", "2023-2", False, Decimal("6000.00")),
        ("1004", "2023-2", False, Decimal("0.00")),
        # 2024-1: both no-start reports count, and the half-year figure, $10,000, is below the
        # periods' $12,000, so nothing more is added.
        ("1005", "2024-1", False, Decimal("6000.00")),
        ("1006", "2024-1", False, Decimal("5000.00")),
        ("1007", "2024-1", False, Decimal("1000.00")),
        # 2023-1: the spanning report holds 2022's quarter.
        ("2002", "2023-1", False, Decimal("0.00")),
        ("2003", None, False, Decimal("0.00")),
    ]


def test_a_reports_cycle_is_its_coverage_ends_rounded_up_to_even() -> None:
    with duckdb.connect() as con:
        build(con)
        con.execute("DROP TABLE bundling_report")
        con.execute(render(SQL / "silver" / "16_bundling_report.sql", {"cycle": 2022}))

        rows = con.execute(
            "SELECT source_record_id, cycle, half_year, amount FROM bundling_report"
        ).fetchall()

    assert rows == [("2001", 2022, "2022-2", Decimal("4000.00"))]


def test_the_checks_pass_on_the_models_rows(con: duckdb.DuckDBPyConnection) -> None:
    for table in ("leadership_pac", "lobbyist_pac", "bundling_report"):
        for check in sorted(CHECKS.glob(f"silver_{table}_*.sql")):
            assert failing(con, check.name) == [], check.name


@pytest.mark.parametrize(
    ("check", "violation"),
    [
        (
            "silver_leadership_pac_key.sql",
            "INSERT INTO leadership_pac SELECT * FROM leadership_pac"
            f" WHERE committee_id = '{REYES_PAC}'",
        ),
        (
            "silver_leadership_pac_committee.sql",
            "UPDATE leadership_pac SET committee_id = 'C00999999'"
            f" WHERE committee_id = '{MORA_PAC}'",
        ),
        (
            "silver_leadership_pac_sponsor.sql",
            f"UPDATE leadership_pac SET sponsor_source = NULL WHERE committee_id = '{REYES_PAC}'",
        ),
        (
            "silver_leadership_pac_sponsor.sql",
            f"UPDATE leadership_pac SET sponsor_source = 'rule' WHERE committee_id = '{MORA_PAC}'",
        ),
        (
            "silver_leadership_pac_sponsor.sql",
            # The rule never gives an alias's id.
            f"UPDATE leadership_pac SET sponsor_candidate_id = '{REYES_ALIAS}'"
            f" WHERE committee_id = '{REYES_PAC}'",
        ),
        (
            "silver_lobbyist_pac_key.sql",
            "INSERT INTO lobbyist_pac SELECT * FROM lobbyist_pac"
            f" WHERE committee_id = '{REYES_PAC}'",
        ),
        (
            "silver_lobbyist_pac_committee.sql",
            "UPDATE lobbyist_pac SET committee_id = 'C00999999'"
            f" WHERE committee_id = '{REYES_PAC}'",
        ),
        (
            "silver_bundling_report_key.sql",
            "UPDATE bundling_report SET source_record_id = '1001' WHERE source_record_id = '1002'",
        ),
        (
            "silver_bundling_report_committee.sql",
            "UPDATE bundling_report SET committee_id = 'C00999999' WHERE source_record_id = '2003'",
        ),
        (
            "silver_bundling_report_not_counted.sql",
            "UPDATE bundling_report SET amount = 2500 WHERE source_record_id = '1002'",
        ),
        (
            "silver_bundling_report_not_counted.sql",
            "UPDATE bundling_report SET amount = 500 WHERE source_record_id = '2003'",
        ),
        (
            # The six-month report adding its own period amount beside its quarters.
            "silver_bundling_report_total.sql",
            "UPDATE bundling_report SET amount = 7000 WHERE source_record_id = '1004'",
        ),
        (
            # A half left out.
            "silver_bundling_report_total.sql",
            "DELETE FROM bundling_report WHERE half_year = '2024-1'",
        ),
    ],
)
def test_each_check_fails_on_a_hand_made_violation(check: str, violation: str) -> None:
    # A row is changed by hand here, so on a connection of its own.
    with duckdb.connect() as con:
        build(con)
        assert failing(con, check) == []

        con.execute(violation)

        assert failing(con, check) != []


def test_the_vendored_sponsor_list_is_one_row_per_cycle_and_committee_naming_a_candidate() -> None:
    # The list overrides the rule (§7.4.2), and the transform cannot check its ids against a
    # candidate of another cycle, so its shape is held here: committed by NEU-2173 (Q16).
    rows = list(csv.DictReader(io.StringIO(runner.LEADERSHIP_SPONSORS.read_text())))

    assert len(rows) == 2582
    assert len({(r["cycle"], r["committee_id"]) for r in rows}) == len(rows)
    assert {int(r["cycle"]) for r in rows} == set(range(2010, 2028, 2))
    assert all(re.fullmatch(r"C\d{8}", r["committee_id"]) for r in rows)
    assert all(re.fullmatch(r"[HSP][0-9][0-9A-Z]{2}\d{5}", r["candidate_id"]) for r in rows)
    assert all(
        r["source"].startswith(f"https://www.fec.gov/data/committee/{r['committee_id']}/")
        for r in rows
    )
