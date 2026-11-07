"""The transform's DuckDB connection builds each join on its right side (NEU-2076)."""

from pathlib import Path

from fundlens.transform.runner import Limits, connect


def test_a_bulk_file_left_joined_to_a_small_table_builds_on_the_small_table(
    tmp_path: Path,
) -> None:
    # DuckDB guesses a read_csv view holds a few dozen rows, and would otherwise build the hash
    # table on the bulk file: a RIGHT join with `committee` as the probe side.
    bulk = tmp_path / "indiv.txt"
    bulk.write_text("".join(f"C{i:08d}|{i}\n" for i in range(10_000)))
    with connect(Limits(None, "1GB", None), tmp_path / "spill") as con:
        con.execute(
            f"CREATE VIEW indiv AS SELECT * FROM read_csv('{bulk}', delim = '|',"
            " header = false, auto_detect = false,"
            " columns = {'CMTE_ID': 'VARCHAR', 'SUB_ID': 'VARCHAR'})"
        )
        # A cycle's `cm` is thousands of committees: more than DuckDB guesses the bulk file holds.
        con.execute(
            "CREATE TABLE committee AS"
            " SELECT 'C' || lpad(CAST(i AS VARCHAR), 8, '0') AS committee_id FROM range(2000) t(i)"
        )
        [(_, plan)] = con.execute(
            "EXPLAIN SELECT indiv.SUB_ID, committee.committee_id FROM indiv"
            " LEFT JOIN committee ON committee.committee_id = indiv.CMTE_ID"
        ).fetchall()
    assert "Join Type: LEFT" in plan
    assert "Join Type: RIGHT" not in plan
