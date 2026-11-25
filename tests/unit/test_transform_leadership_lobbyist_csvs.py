"""The leadership and lobbyist CSVs read through the transform's reader as FEC serves them
(NEU-2174): `leadership`, `lobbyist` and `lobbyist_bundle`, each copied with `copy_as_utf8` and
registered with `register_bulk`, as `fetch_bulk` and the runner do.

The models that read their views (NEU-2175) are tested on their own; this holds the catalogue's
types to the fixture's cells, so a type that refused a real cell's shape fails here first.
"""

import io
from collections.abc import Iterator
from decimal import Decimal

import duckdb
import pytest

from fundlens.fec.files import CATALOGUE, FecFile
from fundlens.transform.runner import copy_as_utf8, register_bulk
from tests import fec_fixture

FILES: tuple[FecFile, ...] = ("leadership", "lobbyist", "lobbyist_bundle")
EXPECTED_ROWS = fec_fixture.expected()["rows"]


@pytest.fixture(scope="module")
def con(tmp_path_factory: pytest.TempPathFactory) -> Iterator[duckdb.DuckDBPyConnection]:
    directory = tmp_path_factory.mktemp("leadership_lobbyist")
    with duckdb.connect() as con:
        for name in FILES:
            path = directory / f"{name}.csv"
            with path.open("wb") as out:
                copy_as_utf8(io.BytesIO(fec_fixture.body(name)), out)
            register_bulk(con, CATALOGUE[name], path)
        yield con


def column(con: duckdb.DuckDBPyConnection, query: str) -> list[object]:
    return [value for (value,) in con.execute(query).fetchall()]


@pytest.mark.parametrize("name", FILES)
def test_each_file_reads_its_fixture_rows(con: duckdb.DuckDBPyConnection, name: FecFile) -> None:
    assert column(con, f"SELECT count(*) FROM {name}") == [EXPECTED_ROWS[name]]


@pytest.mark.parametrize("name", FILES)
def test_every_cell_reads_under_its_catalogued_type(
    con: duckdb.DuckDBPyConnection, name: FecFile
) -> None:
    columns = CATALOGUE[name].columns
    con.execute(f"SELECT * FROM {name}").fetchall()
    [types] = con.execute(
        f"SELECT {', '.join(f'typeof("{c}")' for c in columns)} FROM {name} LIMIT 1"
    ).fetchall()

    assert dict(zip(columns, types, strict=True)) == columns


@pytest.mark.parametrize("name", FILES)
def test_every_date_parses_as_dd_mon_yy(con: duckdb.DuckDBPyConnection, name: FecFile) -> None:
    # Dates stay VARCHAR for `sql/silver/` to parse; each filled one is DD-MON-YY (Q1, Q12).
    dates = [c for c in CATALOGUE[name].columns if c.endswith(("_Date", "Date_Filed"))]
    filled = " + ".join(f'count("{c}")' for c in dates)
    parsed = " + ".join(f"""count(try_strptime("{c}", '%d-%b-%y'))""" for c in dates)
    [(filled_count, parsed_count)] = con.execute(
        f"SELECT {filled}, {parsed} FROM {name}"
    ).fetchall()

    assert filled_count > 0
    assert parsed_count == filled_count


@pytest.mark.parametrize(
    "query",
    [
        # leadership.csv's case 2, the blank sponsor.
        "SELECT count(*) FROM leadership WHERE Sponsor_Name IS NULL",
        # lobbyist.csv's unticked Form 1s.
        "SELECT count(*) FROM lobbyist WHERE Is_Lobbyist IS NULL",
        # lobbyist_bundle.csv's case 4, no Coverage_End_Date; a party's blank election state.
        "SELECT count(*) FROM lobbyist_bundle WHERE Coverage_End_Date IS NULL",
        "SELECT count(*) FROM lobbyist_bundle WHERE Committee_Election_State IS NULL",
    ],
)
def test_a_blank_cell_reads_null(con: duckdb.DuckDBPyConnection, query: str) -> None:
    [count] = column(con, query)

    assert isinstance(count, int) and count > 0


def test_a_sponsor_holding_a_comma_reads_whole(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute(
        "SELECT Committee_Id, Sponsor_Name FROM leadership WHERE Sponsor_Name IS NOT NULL"
    ).fetchall()

    assert rows == [("C00800114", "CALLOWAY, RUTH")]


def test_amounts_read_as_filed(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute(
        "SELECT Quarterly_Contribution, Semi_Annual_Contribution FROM lobbyist_bundle"
        " WHERE Report_Type = 'JULY MONTHLY / SEMI-ANNUAL'"
    ).fetchall()

    assert rows == [(Decimal("15000"), Decimal("82000"))]


def test_image_numbers_of_both_lengths_are_in_link_image(con: duckdb.DuckDBPyConnection) -> None:
    # The digits after `?_` NEU-2175's rules break ties by, 18 or 11 of them (§7.2, §7.5).
    pattern = r"'[?]_([0-9]+)[+]'"
    for name in ("lobbyist", "lobbyist_bundle"):
        lengths = con.execute(
            f"SELECT DISTINCT length(regexp_extract(Link_Image, {pattern}, 1)) FROM {name}"
        ).fetchall()

        assert sorted(length for (length,) in lengths) == [11, 18]
