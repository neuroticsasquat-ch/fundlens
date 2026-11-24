"""The itemized routes' cursor: opaque to the client, and refused when it is not ours; a build's
`donor_id`, NULL until donors are resolved; and a backfill-pending table a live build lacks."""

import base64
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from fundlens import paths
from fundlens.api.itemized import COLUMNS, BadCursor, Cursor, ItemizedReader

BUILD = "20261030T030000Z"


@pytest.mark.parametrize("day", [date(2024, 3, 1), None])
def test_a_cursor_round_trips(day: date | None) -> None:
    cursor = Cursor(BUILD, day, 4240100000000000001, 2024)

    assert Cursor.decode(cursor.encode()) == cursor


@pytest.mark.parametrize("amount", [Decimal("-15000.00"), None])
def test_an_amount_cursor_round_trips(amount: Decimal | None) -> None:
    cursor = Cursor(BUILD, date(2024, 3, 1), 4240400000000000001, 2024, "amount", amount)

    assert Cursor.decode(cursor.encode()) == cursor


def test_a_cursor_issued_before_it_carried_a_cycle_still_reads() -> None:
    token = base64.urlsafe_b64encode(b'["20261030T030000Z","2024-03-01","7"]').decode()

    assert Cursor.decode(token) == Cursor(BUILD, date(2024, 3, 1), 7, None)


def test_a_cursor_is_url_safe() -> None:
    token = Cursor(BUILD, date(2024, 3, 1), 2**64 - 1).encode()

    assert token.replace("-", "").replace("_", "").isalnum()


@pytest.mark.parametrize(
    "token",
    [
        "",
        "not base64!",
        "W10",  # []
        Cursor(BUILD, None, 1).encode()[:-3],
        # One element too many.
        base64.urlsafe_b64encode(b'["20261030T030000Z",null,"1",2024,0]').decode(),
        # An amount cursor with another sort, or an amount that is no number.
        base64.urlsafe_b64encode(b'["20261030T030000Z",null,"1",2024,"payee","1"]').decode(),
        base64.urlsafe_b64encode(b'["20261030T030000Z",null,"1",2024,"amount","x"]').decode(),
        base64.urlsafe_b64encode(b'["20261030T030000Z",null,"1",2024,"amount",1]').decode(),
        base64.urlsafe_b64encode(b'["20261030T030000Z",null,"1",null,"amount","1"]').decode(),
        # Amounts no DECIMAL(14, 2) holds.
        *(
            base64.urlsafe_b64encode(
                f'["20261030T030000Z",null,"1",2024,"amount","{amount}"]'.encode()
            ).decode()
            for amount in ["NaN", "Infinity", "-Infinity", "1E+999"]
        ),
        # A build id that is not YYYYMMDDTHHMMSSZ: it would name a path outside silver.
        Cursor("../../etc", None, 1).encode(),
    ],
)
def test_a_cursor_we_did_not_issue_is_refused(token: str) -> None:
    with pytest.raises(BadCursor):
        Cursor.decode(token)


def write_partition(data_dir: Path, *, donor_id: bool) -> None:
    """One contribution to C00800103 in the 2024 build, with a `donor_id` column or none."""
    partition = paths.local_path(data_dir, paths.silver_partition("contribution", 2024, BUILD))
    partition.mkdir(parents=True, exist_ok=True)
    values = {
        "cycle": "2024",
        "source_record_id": "1",
        "date": "DATE '2024-03-01'",
        "amount": "100.0",
        "recipient_committee_id": "'C00800103'",
        "donor_id": "42",
        "is_self_funding": "false",
    }
    columns = [column for column in COLUMNS if donor_id or column != "donor_id"]
    select = ", ".join(f"{values.get(column, 'NULL')} AS {column}" for column in columns)
    duckdb.execute(f"COPY (SELECT {select}) TO '{partition / paths.part(0)}' (FORMAT parquet)")


def test_a_build_resolved_in_place_is_read_with_its_donor_ids(tmp_path: Path) -> None:
    reader = ItemizedReader(tmp_path, lambda: {2024: BUILD})
    write_partition(tmp_path, donor_id=False)

    before = reader.contributions(2024, "recipient_committee_id", "C00800103", cursor=None)
    # `resolve` rewrites the live build under the same build id.
    write_partition(tmp_path, donor_id=True)
    after = reader.contributions(2024, "recipient_committee_id", "C00800103", cursor=None)

    assert [row["donor_id"] for row in before.rows] == [None]
    assert [row["donor_id"] for row in after.rows] == [42]
    reader.close()


def test_a_live_build_that_lacks_a_backfill_pending_table_has_no_rows_of_it(
    tmp_path: Path,
) -> None:
    # Transformed before `operating_expenditure` existed (every-FEC-dollar spec §2): its other
    # tables' partitions, and none of that one.
    reader = ItemizedReader(tmp_path, lambda: {2024: BUILD})
    write_partition(tmp_path, donor_id=True)

    page = reader.operating_expenditures(2024, "C00800103", category=None, sort="date", cursor=None)

    assert (page.rows, page.next_cursor) == ([], None)
    reader.close()


def test_a_live_build_missing_from_the_volume_is_no_empty_page(tmp_path: Path) -> None:
    # Not a build that predates the table: gold names a build the volume does not hold at all.
    reader = ItemizedReader(tmp_path, lambda: {2024: BUILD})
    (tmp_path / "silver").mkdir()

    with pytest.raises(FileNotFoundError):
        reader.operating_expenditures(2024, "C00800103", category=None, sort="date", cursor=None)
    reader.close()


def test_a_text_keyed_cursor_round_trips_and_is_refused_where_keys_are_sub_ids(
    tmp_path: Path,
) -> None:
    # A 24/48-hour row's key (NEU-2165); a `pas2` row's, all digits, decodes as a SUB_ID still.
    cursor = Cursor(BUILD, date(2024, 10, 1), "1910001:SE.4128", 2024)
    reader = ItemizedReader(tmp_path, lambda: {2024: BUILD})
    write_partition(tmp_path, donor_id=True)

    assert Cursor.decode(cursor.encode()) == cursor
    with pytest.raises(BadCursor):
        reader.contributions(2024, "recipient_committee_id", "C00800103", cursor=cursor.encode())
    with pytest.raises(BadCursor):
        reader.donor_contributions(42, cycle=2024, cursor=cursor.encode())
    reader.close()


@pytest.mark.parametrize(
    "keys",
    [
        # A build transformed before the key was text: SUB_IDs.
        ["4240200000000000001", "4240200000000000002", "4240200000000000003"],
        # Since: a `pas2` row's digits beside 24/48-hour rows' keys, all text.
        ["'4240200000000000001'", "'1910001:SE.4128'", "'1910001:SE.4129'"],
    ],
)
def test_independent_expenditures_page_by_their_key_whether_text_or_sub_id(
    tmp_path: Path, keys: list[str]
) -> None:
    partition = paths.local_path(
        tmp_path, paths.silver_partition("independent_expenditure", 2024, BUILD)
    )
    partition.mkdir(parents=True)
    rows = " UNION ALL ".join(
        f"SELECT 2024 AS cycle, {key} AS source_record_id, DATE '2024-10-01' AS date,"
        " 100.0 AS amount, 'C90800206' AS committee_id, NULL AS candidate_id, NULL AS race_id,"
        " 'S' AS support_oppose, NULL AS transaction_type, 'ie' AS kind"
        for key in keys
    )
    duckdb.execute(f"COPY ({rows}) TO '{partition / paths.part(0)}' (FORMAT parquet)")
    reader = ItemizedReader(tmp_path, lambda: {2024: BUILD})

    walked: list[object] = []
    cursor = None
    while True:
        page = reader.independent_expenditures(2024, "C90800206", cursor=cursor, limit=1)
        walked += [row["source_record_id"] for row in page.rows]
        if (cursor := page.next_cursor) is None:
            break

    assert sorted(str(key) for key in walked) == sorted(key.strip("'") for key in keys)
    reader.close()


@pytest.mark.parametrize(
    ("added", "expected"),
    [
        # A build transformed before NEU-2165 appended them: `pas2` rows alone, no payee kept.
        ("", ("pas2", None, None)),
        (
            ", 'ie_24_48' AS source_file, 'Tidewater Digital LLC' AS payee_name,"
            " 'Digital advertising' AS purpose",
            ("ie_24_48", "Tidewater Digital LLC", "Digital advertising"),
        ),
    ],
    ids=["before NEU-2165", "since"],
)
def test_an_independent_expenditure_has_its_source_file_payee_and_purpose(
    tmp_path: Path, added: str, expected: tuple[str, str | None, str | None]
) -> None:
    partition = paths.local_path(
        tmp_path, paths.silver_partition("independent_expenditure", 2024, BUILD)
    )
    partition.mkdir(parents=True)
    row = (
        "SELECT 2024 AS cycle, '1910001:SE.4128' AS source_record_id, DATE '2024-10-02' AS date,"
        " 4250.50 AS amount, 'C90800206' AS committee_id, NULL AS candidate_id, NULL AS race_id,"
        f" 'S' AS support_oppose, NULL AS transaction_type, 'ie' AS kind{added}"
    )
    duckdb.execute(f"COPY ({row}) TO '{partition / paths.part(0)}' (FORMAT parquet)")
    reader = ItemizedReader(tmp_path, lambda: {2024: BUILD})

    [page_row] = reader.independent_expenditures(2024, "C90800206", cursor=None).rows

    assert (page_row["source_file"], page_row["payee_name"], page_row["purpose"]) == expected
    reader.close()
