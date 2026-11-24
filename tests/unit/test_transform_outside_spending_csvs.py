"""The three outside-spending CSVs read through the transform's reader as FEC serves them
(NEU-2164): `ie_24_48`, `ElectioneeringComm` and `CommunicationCosts`, each copied with
`copy_as_utf8` and registered with `register_bulk`, as `fetch_bulk` and the runner do.

The models that read their views (NEU-2165, NEU-2166, NEU-2167) are tested on their own; this
holds the catalogue's types to the fixture's cells, so a type that refused a real cell's shape
fails here first.
"""

import io
from collections.abc import Iterator
from decimal import Decimal

import duckdb
import pytest

from fundlens.fec.files import CATALOGUE, VARCHAR, FecFile
from fundlens.transform.runner import copy_as_utf8, register_bulk
from tests import fec_fixture

FILES: tuple[FecFile, ...] = ("ie_24_48", "ElectioneeringComm", "CommunicationCosts")
EXPECTED_ROWS = fec_fixture.expected()["rows"]
# ie_24_48.csv's case 16, a hoax filing: 2024's largest row's amount.
HOAX = Decimal("9978412568.00")
# CommunicationCosts.csv's case 6: the higher SUB_ID of the row it repeats; case 5's row, of no
# electronic filing.
REPEAT = 4240200000000000035
NO_FILING = 1091820230265311901


@pytest.fixture(scope="module")
def con(tmp_path_factory: pytest.TempPathFactory) -> Iterator[duckdb.DuckDBPyConnection]:
    directory = tmp_path_factory.mktemp("outside_spending")
    with duckdb.connect() as con:
        for name in FILES:
            path = directory / f"{name}.csv"
            with path.open("wb") as out:
                copy_as_utf8(io.BytesIO(fec_fixture.body(name)), out)
            register_bulk(con, CATALOGUE[name], path)
        yield con


def column(con: duckdb.DuckDBPyConnection, query: str) -> list[object]:
    return [value for (value,) in con.execute(query).fetchall()]


def test_each_file_reads_its_fixture_rows(con: duckdb.DuckDBPyConnection) -> None:
    for name in ("ie_24_48", "ElectioneeringComm"):
        assert column(con, f"SELECT count(*) FROM {name}") == [EXPECTED_ROWS[name]]
    published = EXPECTED_ROWS["CommunicationCosts"]

    assert column(con, "SELECT count(*) FROM CommunicationCosts_published") == [published]
    assert column(con, "SELECT count(*) FROM CommunicationCosts") == [published - 1]
    assert column(con, "SELECT SUB_ID FROM CommunicationCosts_repeat") == [REPEAT]


@pytest.mark.parametrize("name", FILES)
def test_every_cell_reads_under_its_catalogued_type(
    con: duckdb.DuckDBPyConnection, name: FecFile
) -> None:
    columns = CATALOGUE[name].columns
    source = f"{name}_published" if name == "CommunicationCosts" else name
    con.execute(f"SELECT * FROM {source}").fetchall()
    typed = [c for c, kind in columns.items() if kind != VARCHAR]
    [types] = con.execute(
        f"SELECT {', '.join(f'typeof("{c}")' for c in typed)} FROM {source} LIMIT 1"
    ).fetchall()

    assert dict(zip(typed, types, strict=True)) == {c: columns[c] for c in typed}


def test_the_24_48_hour_files_lower_case_names_resolve(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute("SELECT spe_id, exp_amo FROM ie_24_48 WHERE tran_id = 'SE.4128'").fetchall()

    assert rows == [("C90800206", Decimal("4250.50"))]


@pytest.mark.parametrize(
    "query",
    [
        "SELECT count(*) FROM ie_24_48 WHERE exp_date IS NULL AND dissem_dt IS NOT NULL",
        "SELECT count(*) FROM ie_24_48 WHERE cand_id IS NULL AND cand_name IS NOT NULL",
        "SELECT count(*) FROM ie_24_48 WHERE sup_opp IS NULL",
        "SELECT count(*) FROM ie_24_48 WHERE agg_amo IS NULL",
        "SELECT count(*) FROM ie_24_48 WHERE amndt_ind = 'A1' AND prev_file_num IS NULL",
        "SELECT count(*) FROM ElectioneeringComm WHERE CANDIDATE_ID IS NULL",
        "SELECT count(*) FROM ElectioneeringComm WHERE PUBLIC_DISBURSEMENT_DATE IS NULL",
        "SELECT count(*) FROM CommunicationCosts WHERE TRAN_ID IS NULL",
    ],
)
def test_a_blank_cell_reads_null(con: duckdb.DuckDBPyConnection, query: str) -> None:
    [count] = column(con, query)

    assert isinstance(count, int) and count > 0


def test_amounts_read_as_filed(con: duckdb.DuckDBPyConnection) -> None:
    ie = column(con, "SELECT exp_amo FROM ie_24_48")
    shares = column(con, "SELECT CALCULATED_CANDIDATE_SHARE FROM ElectioneeringComm")
    costs = column(con, "SELECT TRANSACTION_AMT FROM CommunicationCosts")

    assert HOAX in ie
    assert Decimal("-500") in ie
    assert Decimal("0") in ie
    assert Decimal("4250.50") in ie
    assert Decimal("26409.50") in shares
    assert Decimal("1250.40") in costs


def test_a_negative_file_num_reads_and_is_no_repeat(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute(
        f"SELECT FILE_NUM, TRAN_ID FROM CommunicationCosts WHERE SUB_ID = {NO_FILING}"
    ).fetchall()

    assert rows == [(-1104901, None)]


def test_a_value_holding_a_comma_reads_whole(con: duckdb.DuckDBPyConnection) -> None:
    names = column(con, "SELECT DISTINCT CANDIDATE_NAME FROM ElectioneeringComm")

    assert "OKAFOR, DIANA" in names


def test_a_value_beginning_with_a_space_keeps_it(con: duckdb.DuckDBPyConnection) -> None:
    names = column(con, "SELECT DISTINCT spe_nam FROM ie_24_48")

    assert " Hollowell Family Farms" in names
