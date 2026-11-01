"""The `/contributions` cursor: opaque to the client, and refused when it is not ours; and a
build's `donor_id`, NULL until donors are resolved."""

import base64
from datetime import date
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
