"""An itemized file's view reads each transaction of a filing once: a row FEC's file repeats, the
same in every column but SUB_ID, is left out (`transform.runner._drop_fec_repeats`, NEU-2401)."""

from pathlib import Path

import duckdb
import pytest

from fundlens.fec.files import CATALOGUE, FecFile
from fundlens.transform.runner import register_bulk, register_unpublished
from tests import fec_fixture

# A loan from the candidate on Williamson's YE 2023 amendment, as FEC's 2024 `oth` holds it: once
# per copy. The fields a case changes are filled in by `row`.
LOAN = {
    "CMTE_ID": "C00834424",
    "AMNDT_IND": "A",
    "RPT_TP": "YE",
    "TRANSACTION_PGI": "P2024",
    "IMAGE_NUM": "202403199622525001",
    "TRANSACTION_TP": "16C",
    "ENTITY_TP": "CAN",
    "NAME": "WILLIAMSON, MARIANNE",
    "CITY": "WASHINGTON",
    "STATE": "DC",
    "ZIP_CODE": "20033",
    "EMPLOYER": "",
    "OCCUPATION": "",
    "TRANSACTION_DT": "12152023",
    "TRANSACTION_AMT": "125000",
    "OTHER_ID": "",
    "CAND_ID": "",
    "TRAN_ID": "SA19A.4001",
    "FILE_NUM": "1764677",
    "MEMO_CD": "",
    "MEMO_TEXT": "",
}


def row(sub_id: int, **changed: str) -> dict[str, str]:
    return {**LOAN, **changed, "SUB_ID": str(sub_id)}


# By SUB_ID: the transaction's copies (1 to 3, 2 and 3 repeats), a second transaction under its
# own TRAN_ID with the same values (4, counted), two rows under one TRAN_ID that differ in their
# amount (5, 6: nothing says which is the transaction), a paper filing's twins (7, 8: FILE_NUM
# below 0, no TRAN_ID), an electronic filing's twins with no TRAN_ID (9, 10), and a row copied
# under its own SUB_ID (11, twice), and the transaction again with no SUB_ID (NULL): each read, for
# the key checks to stop the build on.
ROWS = (
    row(3),
    row(1),
    row(2),
    row(4, TRAN_ID="SA19A.4002"),
    row(5, TRAN_ID="SA19A.4003"),
    row(6, TRAN_ID="SA19A.4003", TRANSACTION_AMT="12500"),
    row(7, TRAN_ID="", FILE_NUM="-1764677"),
    row(8, TRAN_ID="", FILE_NUM="-1764677"),
    row(9, TRAN_ID=""),
    row(10, TRAN_ID=""),
    row(11, TRAN_ID="SA19A.4004"),
    row(11, TRAN_ID="SA19A.4004"),
    {**row(0), "SUB_ID": ""},
)


def registered(tmp_path: Path, file: FecFile) -> duckdb.DuckDBPyConnection:
    """A connection holding `file`'s view of `ROWS`, as the transform registers it."""
    bulk = CATALOGUE[file]
    text = tmp_path / f"{file}.txt"
    text.write_text(
        fec_fixture.pipe_text(bulk, tuple({c: r[c] for c in bulk.columns} for r in ROWS))
    )
    con = duckdb.connect()
    register_bulk(con, bulk, text)
    return con


@pytest.mark.parametrize("file", ["indiv", "oth", "pas2"])
def test_a_transaction_fec_repeats_is_read_once_from_its_lowest_sub_id(
    tmp_path: Path, file: FecFile
) -> None:
    with registered(tmp_path, file) as con:
        read = [
            sub_id for (sub_id,) in con.execute(f"SELECT SUB_ID FROM {file} ORDER BY 1").fetchall()
        ]
        repeats = [
            s for (s,) in con.execute(f"SELECT SUB_ID FROM {file}_repeat ORDER BY 1").fetchall()
        ]
        [(published,)] = con.execute(f"SELECT count(*) FROM {file}_published").fetchall()

    assert read == [1, 4, 5, 6, 7, 8, 9, 10, 11, 11, None]
    assert repeats == [2, 3]
    assert published == len(ROWS)


def test_a_file_with_no_transaction_id_is_read_as_published(tmp_path: Path) -> None:
    text = tmp_path / "cm.txt"
    text.write_text(fec_fixture.pipe_text(CATALOGUE["cm"], fec_fixture.read_rows("cm")))
    with duckdb.connect() as con:
        register_bulk(con, CATALOGUE["cm"], text)
        [(rows,)] = con.execute("SELECT count(*) FROM cm").fetchall()
        tables = {name for (name,) in con.execute("SHOW TABLES").fetchall()}

    assert rows == len(fec_fixture.read_rows("cm"))
    assert {"cm_published", "cm_repeat"}.isdisjoint(tables)


def test_an_unpublished_itemized_file_has_no_repeats() -> None:
    with duckdb.connect() as con:
        register_unpublished(con, CATALOGUE["oth"])

        assert con.execute("SELECT count(*) FROM oth_repeat").fetchall() == [(0,)]
