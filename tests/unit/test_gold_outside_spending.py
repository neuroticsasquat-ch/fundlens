"""Gold's outside spending by kind (every-FEC-dollar spec §6.5, NEU-2168) on hand-made rows:
`race_top_spender` over cases the fixture cycle does not plant (a line netting to $0, a tie), and
its amount check and the kind-sum check failing on rows the models never write."""

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from fundlens.transform.runner import render

SQL = Path(__file__).resolve().parents[2] / "sql"
TOP_SPENDER = SQL / "gold" / "07_race_top_spender.sql"
CHECKS = SQL / "checks"

RACE = "2024-S-MD-00"
OKAFOR, WHITLOCK = "S4MD00103", "S4MD00104"
SUPER_PAC, FORM_5, UNION, PARTY, FORM_9 = (
    "C00800201",
    "C90800206",
    "C70800208",
    "C00800203",
    "C90800207",
)


def failing(con: duckdb.DuckDBPyConnection, check: str) -> list[tuple[object, ...]]:
    return con.execute(render(CHECKS / check, {})).fetchall()


def build(con: duckdb.DuckDBPyConnection) -> None:
    """The model's inputs, hand-made, and the model run over them."""
    con.execute("CREATE SCHEMA silver")
    con.execute(
        "CREATE TABLE silver.committee AS SELECT * FROM (VALUES"
        f" (2024, '{SUPER_PAC}', 'MARYLAND FORWARD PAC'), (2024, '{FORM_5}', 'ONE NATION'),"
        f" (2024, '{UNION}', 'STEAMFITTERS LOCAL 486'),"
        f" (2024, '{PARTY}', 'OLD LINE REPUBLICAN COMMITTEE'),"
        f" (2024, '{FORM_9}', 'RESTORATION PAC')"
        ") AS t(cycle, committee_id, name)"
    )
    con.execute(f"CREATE TABLE race AS SELECT '{RACE}' AS race_id, 2024 AS cycle")
    con.execute(
        "CREATE TABLE silver.independent_expenditure AS"
        " SELECT cycle, committee_id, candidate_id, race_id, support_oppose,"
        " CAST(amount AS DECIMAL(14, 2)) AS amount, kind FROM (VALUES"
        # The super PAC for OKAFOR in two rows, one line; against WHITLOCK in one.
        f" (2024, '{SUPER_PAC}', '{OKAFOR}', '{RACE}', 'S', 100, 'ie'),"
        f" (2024, '{SUPER_PAC}', '{OKAFOR}', '{RACE}', 'S', 50, 'ie'),"
        f" (2024, '{SUPER_PAC}', '{WHITLOCK}', '{RACE}', 'O', 80, 'ie'),"
        # The Form 5 filer's line nets to $0, and its row with no side is in no line.
        f" (2024, '{FORM_5}', '{OKAFOR}', '{RACE}', 'S', 40, 'ie'),"
        f" (2024, '{FORM_5}', '{OKAFOR}', '{RACE}', 'S', -40, 'ie'),"
        f" (2024, '{FORM_5}', '{OKAFOR}', '{RACE}', NULL, 85, 'ie'),"
        # The union's communication costs, for one and against the other; one naming no candidate.
        f" (2024, '{UNION}', '{OKAFOR}', '{RACE}', 'S', 80, 'communication_cost'),"
        f" (2024, '{UNION}', '{WHITLOCK}', '{RACE}', 'O', 30, 'communication_cost'),"
        f" (2024, '{UNION}', NULL, NULL, 'S', 800, 'communication_cost'),"
        f" (2024, '{PARTY}', '{WHITLOCK}', '{RACE}', 'S', 200, 'coordinated')"
        ") AS t(cycle, committee_id, candidate_id, race_id, support_oppose, amount, kind)"
    )
    con.execute(
        "CREATE TABLE silver.electioneering_communication AS"
        " SELECT cycle, committee_id, candidate_id, race_id,"
        " CAST(amount AS DECIMAL(14, 2)) AS amount FROM (VALUES"
        # Two halves of one disbursement and a row naming no candidate.
        f" (2024, '{FORM_9}', '{OKAFOR}', '{RACE}', 80.00),"
        f" (2024, '{FORM_9}', '{WHITLOCK}', '{RACE}', 30.50),"
        f" (2024, '{FORM_9}', NULL, NULL, 15000.00)"
        ") AS t(cycle, committee_id, candidate_id, race_id, amount)"
    )
    con.execute(render(TOP_SPENDER, {}))


@pytest.fixture(scope="module")
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    with duckdb.connect() as con:
        build(con)
        yield con


def test_each_line_is_a_spenders_kind_on_a_candidate_by_side(
    con: duckdb.DuckDBPyConnection,
) -> None:
    assert con.execute(
        "SELECT rank, committee_id, name, candidate_id, kind, support_oppose, amount"
        " FROM race_top_spender ORDER BY rank"
    ).fetchall() == [
        (1, PARTY, "OLD LINE REPUBLICAN COMMITTEE", WHITLOCK, "party_coordinated", "S", 200),
        (2, SUPER_PAC, "MARYLAND FORWARD PAC", OKAFOR, "independent_expenditure", "S", 150),
        # $80 three ways, ranked by committee.
        (3, SUPER_PAC, "MARYLAND FORWARD PAC", WHITLOCK, "independent_expenditure", "O", 80),
        (4, UNION, "STEAMFITTERS LOCAL 486", OKAFOR, "communication_cost", "S", 80),
        (5, FORM_9, "RESTORATION PAC", OKAFOR, "electioneering_communication", None, 80),
        (
            6,
            FORM_9,
            "RESTORATION PAC",
            WHITLOCK,
            "electioneering_communication",
            None,
            Decimal("30.50"),
        ),
        (7, UNION, "STEAMFITTERS LOCAL 486", WHITLOCK, "communication_cost", "O", 30),
    ]


def test_the_checks_pass_on_the_models_rows(con: duckdb.DuckDBPyConnection) -> None:
    assert failing(con, "gold_race_top_spender_amount.sql") == []


def test_the_amount_check_fails_on_a_line_silver_does_not_give() -> None:
    # Rows are changed by hand here, so on a connection of its own.
    with duckdb.connect() as con:
        build(con)

        con.execute("UPDATE race_top_spender SET amount = 151 WHERE rank = 2")
        con.execute("UPDATE race_top_spender SET support_oppose = 'S' WHERE rank = 5")
        con.execute("UPDATE race_top_spender SET committee_id = 'C99999999' WHERE rank = 7")

        assert sorted(failing(con, "gold_race_top_spender_amount.sql")) == [
            (RACE, 2, SUPER_PAC, OKAFOR, "independent_expenditure", "S", 151, 150),
            (RACE, 5, FORM_9, OKAFOR, "electioneering_communication", "S", 80, None),
            (RACE, 7, "C99999999", WHITLOCK, "communication_cost", "O", 30, None),
        ]


def test_the_kind_sum_check_fails_on_a_hand_broken_row() -> None:
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE race AS SELECT race_id, CAST(ie_support AS DECIMAL(16, 2)) AS ie_support,"
            " CAST(ie_oppose AS DECIMAL(16, 2)) AS ie_oppose,"
            " CAST(cc_s AS DECIMAL(16, 2)) AS communication_cost_support,"
            " CAST(cc_o AS DECIMAL(16, 2)) AS communication_cost_oppose,"
            " CAST(pc AS DECIMAL(16, 2)) AS party_coordinated,"
            " CAST(ec AS DECIMAL(16, 2)) AS electioneering,"
            " CAST(total AS DECIMAL(16, 2)) AS outside_spending_total FROM (VALUES"
            # Adds up; adds up with no electioneering row; $1 short; no total at all.
            " ('R1', 100, 50, 10, 5, 20, 30.50, 215.50),"
            " ('R2', 100, 0, 0, 0, 0, NULL, 100),"
            " ('R3', 100, 50, 10, 5, 20, 30.50, 214.50),"
            " ('R4', 0, 0, 0, 0, 0, NULL, NULL)"
            ") AS t(race_id, ie_support, ie_oppose, cc_s, cc_o, pc, ec, total)"
        )
        con.execute(
            "CREATE TABLE committee_cycle AS SELECT committee_id, cycle,"
            " CAST(ie AS DECIMAL(16, 2)) AS ie_total,"
            " CAST(cc AS DECIMAL(16, 2)) AS communication_cost_total,"
            " CAST(pc AS DECIMAL(16, 2)) AS party_coordinated_total,"
            " CAST(ec AS DECIMAL(16, 2)) AS electioneering_total,"
            " CAST(total AS DECIMAL(16, 2)) AS outside_spending_total FROM (VALUES"
            # Adds up; adds up with no electioneering row; counts electioneering twice.
            " ('C1', 2024, 100, 800, 0, 15000, 15900),"
            " ('C2', 2024, 45, 0, 20, NULL, 65),"
            " ('C3', 2024, 0, 0, 0, 250, 500)"
            ") AS t(committee_id, cycle, ie, cc, pc, ec, total)"
        )

        assert sorted(failing(con, "gold_outside_spending_total.sql"), key=str) == sorted(
            [
                ("race", "R3", Decimal("214.50"), Decimal("215.50")),
                ("race", "R4", None, Decimal("0.00")),
                ("committee_cycle", "C3/2024", Decimal("500.00"), Decimal("250.00")),
            ],
            key=str,
        )
