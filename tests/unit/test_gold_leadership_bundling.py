"""Gold's leadership, lobbyist and bundling fields on `committee_cycle` (every-FEC-dollar spec §7.7,
NEU-2176): its two checks failing on hand-made rows the model never writes."""

from decimal import Decimal
from pathlib import Path

import duckdb

from fundlens.transform.runner import render

CHECKS = Path(__file__).resolve().parents[2] / "sql" / "checks"


def failing(con: duckdb.DuckDBPyConnection, check: str) -> list[tuple[object, ...]]:
    return con.execute(render(CHECKS / check, {})).fetchall()


def test_the_bundled_total_check_fails_where_gold_and_silver_differ() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA silver")
        # 2024's and 2008's builds hold the table, 2022's predates it.
        con.execute(
            "CREATE TABLE silver_held AS SELECT * FROM (VALUES"
            " ('bundling_report', 2024), ('bundling_report', 2008), ('committee', 2022)"
            ") AS t(silver_table, cycle)"
        )
        con.execute(
            "CREATE TABLE silver.bundling_report AS"
            " SELECT cycle, committee_id, CAST(amount AS DECIMAL(14, 2)) AS amount FROM (VALUES"
            " (2024, 'C1', 100), (2024, 'C1', 50), (2024, 'C2', 70), (2024, 'C3', 40),"
            " (2024, 'C9', 10), (2022, 'C7', 5)"
            ") AS t(cycle, committee_id, amount)"
        )
        con.execute(
            "CREATE TABLE committee_cycle AS"
            " SELECT committee_id, cycle, CAST(bundled_total AS DECIMAL(16, 2)) AS bundled_total"
            " FROM (VALUES"
            # C1 sums its two reports, C4 has none: 0; NULL before 2010 and where the build
            # lacks the table. All pass.
            " ('C1', 2024, 150), ('C4', 2024, 0), ('C4', 2008, NULL), ('C4', 2022, NULL),"
            # C2 is off by $1, C3 is NULL beside its report, C5 NULL in a cycle holding the table,
            # C6 0 before 2010, and C7 NULL beside a report of a cycle not held.
            " ('C2', 2024, 71), ('C3', 2024, NULL), ('C5', 2024, NULL), ('C6', 2008, 0),"
            " ('C7', 2022, NULL)"
            ") AS t(committee_id, cycle, bundled_total)"
        )

        # And C9's report has no committee_cycle row at all.
        assert sorted(failing(con, "gold_committee_cycle_bundled_total.sql")) == [
            ("C2", 2024, Decimal("71.00"), Decimal("70.00")),
            ("C3", 2024, None, Decimal("40.00")),
            ("C5", 2024, None, None),
            ("C6", 2008, Decimal("0.00"), None),
            ("C7", 2022, None, Decimal("5.00")),
            ("C9", 2024, None, Decimal("10.00")),
        ]


def test_the_sponsor_check_fails_on_a_sponsor_of_no_leadership_pac_or_no_candidate() -> None:
    with duckdb.connect() as con:
        con.execute("CREATE TABLE candidate AS SELECT 'H1' AS candidate_id")
        con.execute(
            "CREATE TABLE candidate_redirect AS"
            " SELECT 'H1ALIAS' AS old_candidate_id, 'H1' AS candidate_id"
        )
        con.execute(
            "CREATE TABLE committee_cycle AS SELECT * FROM (VALUES"
            # A candidate's PAC, an alias's, one with a name and no id, and no sponsor: all pass.
            " ('C1', 2024, true, 'H1', 'ONE, A'), ('C2', 2024, true, 'H1ALIAS', 'ONE, A'),"
            " ('C3', 2024, true, NULL, 'TWO, B'), ('C4', 2024, false, NULL, NULL),"
            # A sponsor on a committee that is no leadership PAC, and an id fundlens never held.
            " ('C5', 2024, false, NULL, 'THREE, C'), ('C6', 2024, true, 'H9', 'FOUR, D')"
            ") AS t(committee_id, cycle, is_leadership_pac, sponsor_candidate_id, sponsor_name)"
        )

        assert sorted(failing(con, "gold_committee_cycle_sponsor.sql")) == [
            ("no such candidate", "C6", 2024, "H9", "FOUR, D"),
            ("not a leadership PAC", "C5", 2024, None, "THREE, C"),
        ]
