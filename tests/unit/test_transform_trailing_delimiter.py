"""A `trailing_delimiter` file reads as FEC serves it: every `oppexp` line ends in a `|` after its
last column, which `register_bulk`'s unchanged `read_csv` call takes as nothing (NEU-2151).

This holds DuckDB to what it does with that `|`: an upgrade that read it as a 26th column, or
shifted the columns, would otherwise pass every other test and stop the transform.
"""

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from fundlens.fec.files import CATALOGUE
from fundlens.transform.runner import register_bulk
from tests import fec_fixture

OPPEXP = CATALOGUE["oppexp"]
ROWS = fec_fixture.read_rows("oppexp")
# The fixture's one repeated row (NEU-2151 spec §3, case 12): the higher SUB_ID of the two.
REPEAT = 4240400000000000026


def registered(path: Path, text: str) -> duckdb.DuckDBPyConnection:
    path.write_text(text)
    con = duckdb.connect()
    register_bulk(con, OPPEXP, path)
    return con


@pytest.fixture(scope="module")
def con(tmp_path_factory: pytest.TempPathFactory) -> Iterator[duckdb.DuckDBPyConnection]:
    text = fec_fixture.bulk_text("oppexp")
    with registered(tmp_path_factory.mktemp("oppexp") / "oppexp.txt", text) as con:
        yield con


def test_the_fixture_is_served_with_a_trailing_delimiter() -> None:
    lines = fec_fixture.bulk_text("oppexp").splitlines()

    assert all(line.endswith("|") for line in lines)


def test_the_fixture_reads_with_its_repeat_dropped(con: duckdb.DuckDBPyConnection) -> None:
    [(published,)] = con.execute("SELECT count(*) FROM oppexp_published").fetchall()
    [(read,)] = con.execute("SELECT count(*) FROM oppexp").fetchall()
    repeats = con.execute("SELECT SUB_ID FROM oppexp_repeat").fetchall()

    assert published == fec_fixture.expected()["rows"]["oppexp"] == len(ROWS)
    assert read == published - 1
    assert repeats == [(REPEAT,)]


def test_every_column_reads_under_its_catalogued_type(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("SELECT * FROM oppexp_published").fetchall()
    [types] = con.execute(
        "SELECT typeof(RPT_YR), typeof(TRANSACTION_AMT), typeof(SUB_ID), typeof(FILE_NUM)"
        " FROM oppexp_published LIMIT 1"
    ).fetchall()

    assert types == ("SMALLINT", "DECIMAL(14,2)", "UBIGINT", "BIGINT")


def test_the_last_column_is_not_shifted(con: duckdb.DuckDBPyConnection) -> None:
    read = dict(con.execute("SELECT SUB_ID, BACK_REF_TRAN_ID FROM oppexp_published").fetchall())

    assert read == {int(r["SUB_ID"]): r["BACK_REF_TRAN_ID"] or None for r in ROWS}
    # A sub-item names its parent's TRAN_ID, and most rows name nothing.
    assert any(r["BACK_REF_TRAN_ID"] for r in ROWS)
    assert any(not r["BACK_REF_TRAN_ID"] for r in ROWS)


def test_amounts_read_as_filed(con: duckdb.DuckDBPyConnection) -> None:
    read = dict(con.execute("SELECT SUB_ID, TRANSACTION_AMT FROM oppexp_published").fetchall())

    assert read == {int(r["SUB_ID"]): Decimal(r["TRANSACTION_AMT"]) for r in ROWS}
    assert any(amount < 0 for amount in read.values())
    assert any(amount != amount.to_integral_value() for amount in read.values())


def test_a_26th_field_that_is_not_empty_is_refused(tmp_path: Path) -> None:
    first, *rest = fec_fixture.bulk_text("oppexp").splitlines(keepends=True)
    text = "".join([first.replace("|\n", "|SURPLUS\n"), *rest])

    # The read is lazy: registering or selecting may raise.
    with pytest.raises(duckdb.InvalidInputException):
        with registered(tmp_path / "oppexp.txt", text) as con:
            con.execute("SELECT * FROM oppexp_published").fetchall()


def test_a_line_with_no_trailing_delimiter_reads_the_same(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    # FEC has never served one; the flag records what FEC writes, and the reader accepts both.
    text = fec_fixture.bulk_text("oppexp").replace("|\n", "\n")
    query = "SELECT * FROM oppexp_published ORDER BY SUB_ID"

    with registered(tmp_path / "oppexp.txt", text) as bare:
        assert bare.execute(query).fetchall() == con.execute(query).fetchall()
