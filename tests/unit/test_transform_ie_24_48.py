"""The 24/48-hour file's rows in silver `independent_expenditure` (every-FEC-dollar spec §6.3,
NEU-2165), on hand-made rows: the cases the fixture cycle does not plant, the tenfold boundary and a
track record that is a reported figure alone, and the no-double check failing on a row the rules
would never add."""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from fundlens.transform.runner import render

SQL = Path(__file__).resolve().parents[2] / "sql"
MODEL = SQL / "silver" / "10_independent_expenditure.sql"
NO_DOUBLE = SQL / "checks" / "silver_independent_expenditure_no_double.sql"

# Spenders: each reports independent expenditures as `reported_total` gives them, and none but
# IN_PAS2 has a `pas2` independent expenditure. Every period ends 2024-09-30.
AT_TENFOLD = "C90000001"  # reports $100; its rows add up to $1,000.00
PAST_TENFOLD = "C90000002"  # reports $100; its rows add up to $1,000.01
REPORTED_ONLY = "C90000003"  # reports $50: a track record by its figure alone
REPORTS_NONE = "C90000004"  # reports $0
IN_PAS2 = "C00000005"  # a `pas2` 24E, and reports $0


def build(con: duckdb.DuckDBPyConnection) -> None:
    """The model's inputs, hand-made, and the model run over them."""
    spenders = (AT_TENFOLD, PAST_TENFOLD, REPORTED_ONLY, REPORTS_NONE, IN_PAS2)
    con.execute("CREATE TABLE committee AS SELECT unnest($ids) AS committee_id", {"ids": spenders})
    con.execute(
        "CREATE TABLE candidate AS SELECT 'S4MD00103' AS candidate_id,"
        " CAST(NULL AS VARCHAR) AS alias_of, '2024-S-MD-00' AS race_id"
    )
    con.execute(
        "CREATE TABLE handoff (from_candidate_id VARCHAR, to_candidate_id VARCHAR,"
        " handoff_date DATE)"
    )
    con.execute(
        "CREATE TABLE ie_candidate_correction (sub_id UBIGINT, pas2_candidate_id VARCHAR,"
        " candidate_id VARCHAR)"
    )
    con.execute(
        "CREATE TABLE pas2 AS SELECT CAST(1 AS UBIGINT) AS SUB_ID,"
        f" '{IN_PAS2}' AS CMTE_ID, 'S4MD00103' AS CAND_ID, '24E' AS TRANSACTION_TP,"
        " CAST(900 AS DECIMAL(14, 2)) AS TRANSACTION_AMT, '09012024' AS TRANSACTION_DT,"
        " CAST(NULL AS VARCHAR) AS MEMO_CD, 'HARBOR LIGHT MEDIA' AS NAME"
    )
    con.execute(
        "CREATE TABLE CommunicationCosts (SUB_ID UBIGINT, COMMUNICATION_TP VARCHAR,"
        " COMMUNICATION_CLASS VARCHAR)"
    )
    con.execute(
        "CREATE TABLE reported_total AS SELECT committee_id, DATE '2024-09-30' AS period_end,"
        " CAST(figure AS DECIMAL(14, 2)) AS independent_expenditures FROM (VALUES"
        f" ('{AT_TENFOLD}', 100), ('{PAST_TENFOLD}', 100), ('{REPORTED_ONLY}', 50),"
        f" ('{REPORTS_NONE}', 0), ('{IN_PAS2}', 0)"
        ") AS t(committee_id, figure)"
    )
    con.execute(
        "CREATE TABLE ie_24_48 AS SELECT"
        " 'S4MD00103' AS cand_id, spe_id, CAST(exp_amo AS DECIMAL(14, 2)) AS exp_amo,"
        " nullif(exp_date, '') AS exp_date, 'S' AS sup_opp, 'TV advertising' AS pur,"
        " 'Harbor Light Media' AS pay, CAST(file_num AS BIGINT) AS file_num, tran_id,"
        " CAST(NULL AS BIGINT) AS prev_file_num, nullif(dissem_dt, '') AS dissem_dt"
        " FROM (VALUES"
        # The tenfold boundary: exactly ten times what the spender reports is added.
        f" (1001, 'A', '{AT_TENFOLD}', 600.00, '02-SEP-24', ''),"
        f" (1001, 'B', '{AT_TENFOLD}', 400.00, '', '03-SEP-24'),"
        f" (1002, 'A', '{PAST_TENFOLD}', 600.00, '02-SEP-24', ''),"
        f" (1002, 'B', '{PAST_TENFOLD}', 400.01, '02-SEP-24', ''),"
        # Its figure is a track record: a row after its period end is added, unscreened, and
        # its row before it, ten times over, is not.
        f" (1003, 'A', '{REPORTED_ONLY}', 5000.00, '15-OCT-24', ''),"
        f" (1003, 'B', '{REPORTED_ONLY}', 5000.00, '15-SEP-24', ''),"
        # No track record: nothing, after its period end or before.
        f" (1004, 'A', '{REPORTS_NONE}', 70.00, '15-OCT-24', ''),"
        f" (1004, 'B', '{REPORTS_NONE}', 70.00, '15-SEP-24', ''),"
        # A `pas2` spender: after its period end only, by its dissemination date here.
        f" (1005, 'A', '{IN_PAS2}', 1200.00, '', '01-OCT-24'),"
        f" (1005, 'B', '{IN_PAS2}', 900.00, '30-SEP-24', '')"
        ") AS t(file_num, tran_id, spe_id, exp_amo, exp_date, dissem_dt)"
    )
    con.execute(render(MODEL, {"cycle": 2024}))


@pytest.fixture(scope="module")
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    """The model built once for the tests that only read it."""
    with duckdb.connect() as con:
        build(con)
        yield con


def added(con: duckdb.DuckDBPyConnection) -> dict[str, tuple[str, Decimal]]:
    return {
        key: (spender, amount)
        for key, spender, amount in con.execute(
            "SELECT source_record_id, committee_id, amount FROM independent_expenditure"
            " WHERE source_file = 'ie_24_48'"
        ).fetchall()
    }


def test_a_spenders_rows_are_added_up_to_ten_times_what_it_reports_and_not_a_cent_more(
    con: duckdb.DuckDBPyConnection,
) -> None:
    rows = added(con)

    assert {key for key, (spender, _) in rows.items() if spender == AT_TENFOLD} == {
        "1001:A",
        "1001:B",
    }
    assert not any(spender == PAST_TENFOLD for spender, _ in rows.values())


def test_a_reported_figure_alone_is_a_track_record_for_rows_after_the_period_end(
    con: duckdb.DuckDBPyConnection,
) -> None:
    rows = added(con)

    assert rows["1003:A"] == (REPORTED_ONLY, Decimal("5000.00"))
    assert "1003:B" not in rows
    assert not any(spender == REPORTS_NONE for spender, _ in rows.values())
    assert [key for key, (spender, _) in rows.items() if spender == IN_PAS2] == ["1005:A"]
    assert con.execute(
        "SELECT rule, count(*) FROM ie_24_48_added GROUP BY rule ORDER BY rule"
    ).fetchall() == [("by_spender", 2), ("timeliness", 2)]


def test_a_24_48_hour_row_is_an_independent_expenditure_keyed_by_its_filing_and_tran_id(
    con: duckdb.DuckDBPyConnection,
) -> None:
    [row] = con.execute(
        "SELECT * FROM independent_expenditure WHERE source_record_id = '1005:A'"
    ).fetchall()
    [pas2] = con.execute(
        "SELECT source_record_id, source_file, payee_name, purpose, dissemination_date"
        " FROM independent_expenditure WHERE source_file = 'pas2'"
    ).fetchall()
    columns = [c[0] for c in con.execute("DESCRIBE independent_expenditure").fetchall()]

    assert dict(zip(columns, row, strict=True)) == {
        "cycle": 2024,
        "source": "fec",
        "source_record_id": "1005:A",
        "jurisdiction": "US",
        "committee_id": IN_PAS2,
        "candidate_id": "S4MD00103",
        "race_id": "2024-S-MD-00",
        "support_oppose": "S",
        "amount": Decimal("1200.00"),
        # exp_date is blank: its date is dissem_dt.
        "date": date(2024, 10, 1),
        "transaction_type": None,
        "kind": "ie",
        "source_file": "ie_24_48",
        "payee_name": "Harbor Light Media",
        "purpose": "TV advertising",
        "dissemination_date": date(2024, 10, 1),
        # Only a communication cost has a type and class (NEU-2167).
        "communication_type": None,
        "communication_class": None,
    }
    assert pas2 == ("1", "pas2", "HARBOR LIGHT MEDIA", None, None)


def failing(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str]]:
    return sorted(
        (str(key), reason) for key, _, reason in con.execute(render(NO_DOUBLE, {})).fetchall()
    )


def test_the_no_double_check_passes_on_the_rules_rows_and_fails_on_one_they_never_add() -> None:
    # Rows are added by hand here, so on a connection of its own.
    with duckdb.connect() as con:
        build(con)
        assert failing(con) == []

        # By hand: a `pas2` spender's row by its period end, a row with no track record, and a row
        # on a filing an amendment in the file replaced.
        con.execute(
            "INSERT INTO independent_expenditure (source_record_id, committee_id, date, kind,"
            " source_file) VALUES"
            f" ('1005:B', '{IN_PAS2}', DATE '2024-09-30', 'ie', 'ie_24_48'),"
            f" ('1004:A', '{REPORTS_NONE}', DATE '2024-10-15', 'ie', 'ie_24_48'),"
            f" ('1009:A', '{AT_TENFOLD}', DATE '2024-09-02', 'ie', 'ie_24_48')"
        )
        con.execute(
            f"INSERT INTO ie_24_48 (spe_id, file_num, tran_id, prev_file_num) VALUES"
            f" ('{AT_TENFOLD}', 1010, 'A', 1009)"
        )

        assert failing(con) == [
            ("1004:A", "no track record"),
            ("1005:B", "in pas2 by its period end"),
            ("1009:A", "replaced by an amendment"),
        ]
