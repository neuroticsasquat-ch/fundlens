"""Silver `independent_expenditure`'s communication check (every-FEC-dollar spec §6.2, NEU-2167)
failing on rows the model never writes: a communication's type or class on another kind's row."""

from pathlib import Path

import duckdb

from fundlens.transform.runner import render

CHECK = (
    Path(__file__).resolve().parents[2]
    / "sql"
    / "checks"
    / "silver_independent_expenditure_communication.sql"
)


def test_the_communication_check_fails_on_a_type_or_class_on_another_kind() -> None:
    with duckdb.connect() as con:
        # Right: 1 a communication cost with both, 2 one the CSV lacks, 3 an ie with neither.
        # Wrong: 4 an ie with a type, 5 a coordinated row with a class.
        con.execute(
            "CREATE TABLE independent_expenditure AS SELECT * FROM (VALUES"
            " ('1', 'communication_cost', 'DM', 'M'),"
            " ('2', 'communication_cost', NULL, NULL),"
            " ('3', 'ie', NULL, NULL),"
            " ('4', 'ie', 'DM', NULL),"
            " ('5', 'coordinated', NULL, 'M')"
            ") AS t(source_record_id, kind, communication_type, communication_class)"
        )

        assert sorted(con.execute(render(CHECK, {})).fetchall()) == [
            ("4", "ie", "DM", None),
            ("5", "coordinated", None, "M"),
        ]
