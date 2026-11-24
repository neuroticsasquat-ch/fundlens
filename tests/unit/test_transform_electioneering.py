"""Silver `electioneering_communication` (every-FEC-dollar spec §6.4, NEU-2166) on hand-made rows:
the cases the fixture cycle does not plant (a disbursement with no candidate count), and its
candidate and copies checks failing on rows the model never writes."""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from fundlens.transform.runner import render

SQL = Path(__file__).resolve().parents[2] / "sql"
MODEL = SQL / "silver" / "13_electioneering_communication.sql"
CHECKS = SQL / "checks"

SPENDER = "C90800207"
DRISCOLL, DRISCOLL_ALIAS = "H4MD05107", "H6MD05113"
BIDEN, HARRIS = "P80000722", "P00009423"


def build(con: duckdb.DuckDBPyConnection) -> None:
    """The model's inputs, hand-made, and the model run over them."""
    con.execute(f"CREATE TABLE committee AS SELECT '{SPENDER}' AS committee_id")
    con.execute(
        "CREATE TABLE candidate AS SELECT * FROM (VALUES"
        f" ('{DRISCOLL}', CAST(NULL AS VARCHAR), '2024-H-MD-05'),"
        f" ('{DRISCOLL_ALIAS}', '{DRISCOLL}', '2024-H-MD-05'),"
        f" ('{BIDEN}', NULL, '2024-P-US-00'),"
        f" ('{HARRIS}', NULL, '2024-P-US-00')"
        ") AS t(candidate_id, alias_of, race_id)"
    )
    con.execute(
        f"CREATE TABLE handoff AS SELECT '{BIDEN}' AS from_candidate_id,"
        f" '{HARRIS}' AS to_candidate_id, DATE '2024-07-21' AS handoff_date"
    )
    con.execute(
        "CREATE TABLE ElectioneeringComm AS SELECT"
        " CANDIDATE_ID, 'A CANDIDATE' AS CANDIDATE_NAME, 'H' AS CANDIDATE_OFFICE,"
        " 'MD' AS CANDIDATE_STATE, '05' AS CANDIDATE_DISTRICT,"
        f" '{SPENDER}' AS COMMITTEE_ID, 'Restoration PAC' AS COMMITTEE_NAME, SB_IMAGE_NUM,"
        " 'Harbor Light Media' AS PAYEE_NAME, '410 Key Hwy' AS PAYEE_STREET,"
        " 'Baltimore' AS PAYEE_CITY, 'MD' AS PAYEE_STATE,"
        " 'TV AD PLACEMENT' AS DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE,"
        " COMMUNICATION_DATE, COMMUNICATION_DATE AS PUBLIC_DISBURSEMENT_DATE,"
        " CAST(amount AS DECIMAL(14, 2)) AS REPORTED_DISBURSEMENT_AMOUNT,"
        " CAST(candidates AS SMALLINT) AS NUMBER_OF_CANDIDATES,"
        " CAST(share AS DECIMAL(14, 2)) AS CALCULATED_CANDIDATE_SHARE"
        " FROM (VALUES"
        # A disbursement with no candidate count, and one with a count of 0: no copy is known,
        # so every row is kept.
        f" ('{DRISCOLL}', '1', '03-OCT-24', '05-OCT-24', 8000, NULL, 4000),"
        f" ('{DRISCOLL}', '1', '03-OCT-24', '06-OCT-24', 8000, NULL, 4000),"
        f" ('{DRISCOLL}', '4', '04-OCT-24', '05-OCT-24', 1000, 0, 500),"
        f" ('{DRISCOLL}', '4', '04-OCT-24', '06-OCT-24', 1000, 0, 500),"
        # A two-candidate disbursement on three rows: the third, by CANDIDATE_ID, is a copy.
        f" ('{DRISCOLL_ALIAS}', '2', '20-JUL-24', '22-JUL-24', 10000, 2, 5000),"
        f" ('{BIDEN}', '2', '20-JUL-24', '22-JUL-24', 10000, 2, 5000),"
        f" ('{BIDEN}', '2', '20-JUL-24', '23-JUL-24', 10000, 2, 5000),"
        # Naming BIDEN with no date: HARRIS's, as an undated row past a handoff is.
        f" ('{BIDEN}', '3', NULL, NULL, 2500, 1, 2500)"
        ") AS t(CANDIDATE_ID, SB_IMAGE_NUM, DISBURSEMENT_DATE, COMMUNICATION_DATE, amount,"
        " candidates, share)"
    )
    con.execute(render(MODEL, {"cycle": 2024}))


@pytest.fixture(scope="module")
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    """The model built once for the tests that only read it."""
    with duckdb.connect() as con:
        build(con)
        yield con


def failing(con: duckdb.DuckDBPyConnection, check: str) -> list[tuple[object, ...]]:
    return con.execute(render(CHECKS / check, {})).fetchall()


def test_a_disbursement_keeps_as_many_rows_as_its_candidates_and_all_with_no_count_above_0(
    con: duckdb.DuckDBPyConnection,
) -> None:
    rows = con.execute(
        "SELECT source_record_id, candidate_id, race_id, amount, date, communication_date"
        " FROM electioneering_communication ORDER BY source_record_id"
    ).fetchall()

    assert rows == [
        ("1:1", DRISCOLL, "2024-H-MD-05", Decimal("4000.00"), date(2024, 10, 3), date(2024, 10, 5)),
        ("1:2", DRISCOLL, "2024-H-MD-05", Decimal("4000.00"), date(2024, 10, 3), date(2024, 10, 6)),
        # The alias is DRISCOLL's.
        ("2:1", DRISCOLL, "2024-H-MD-05", Decimal("5000.00"), date(2024, 7, 20), date(2024, 7, 22)),
        # Dated the day before the handoff: BIDEN's. The copy, dated 23 July, is dropped.
        ("2:2", BIDEN, "2024-P-US-00", Decimal("5000.00"), date(2024, 7, 20), date(2024, 7, 22)),
        ("3:1", HARRIS, "2024-P-US-00", Decimal("2500.00"), None, None),
        ("4:1", DRISCOLL, "2024-H-MD-05", Decimal("500.00"), date(2024, 10, 4), date(2024, 10, 5)),
        ("4:2", DRISCOLL, "2024-H-MD-05", Decimal("500.00"), date(2024, 10, 4), date(2024, 10, 6)),
    ]


def test_the_checks_pass_on_the_models_rows(con: duckdb.DuckDBPyConnection) -> None:
    for check in sorted(CHECKS.glob("silver_electioneering_communication_*.sql")):
        assert failing(con, check.name) == [], check.name


def test_the_copies_check_fails_on_a_hand_added_copy() -> None:
    # A row is added by hand here, so on a connection of its own.
    with duckdb.connect() as con:
        build(con)

        con.execute(
            "INSERT INTO electioneering_communication"
            " SELECT * REPLACE ('2:3' AS source_record_id)"
            " FROM electioneering_communication WHERE source_record_id = '2:1'"
        )

        assert failing(con, "silver_electioneering_communication_copies.sql") == [
            (SPENDER, "2", "Harbor Light Media", date(2024, 7, 20), Decimal("10000.00"), 3, 2)
        ]


def test_the_candidate_check_fails_on_a_misattached_row() -> None:
    with duckdb.connect() as con:
        build(con)

        # An alias, a race not the candidate's, a race with no candidate, an id `cn` lacks, and
        # the candidate handed from, on the handoff and undated.
        con.execute(
            "INSERT INTO electioneering_communication (source_record_id, candidate_id, race_id,"
            " date) VALUES"
            f" ('bad:1', '{DRISCOLL_ALIAS}', '2024-H-MD-05', DATE '2024-10-28'),"
            f" ('bad:2', '{DRISCOLL}', '2024-S-MD-00', DATE '2024-10-21'),"
            " ('bad:3', NULL, '2024-H-MD-05', DATE '2024-10-17'),"
            " ('bad:4', 'H4MD03120', NULL, DATE '2024-10-22'),"
            f" ('bad:5', '{BIDEN}', '2024-P-US-00', DATE '2024-07-21'),"
            f" ('bad:6', '{BIDEN}', '2024-P-US-00', NULL)"
        )

        failed = failing(con, "silver_electioneering_communication_candidate.sql")

        assert sorted(str(row[0]) for row in failed) == [f"bad:{n}" for n in range(1, 7)]
