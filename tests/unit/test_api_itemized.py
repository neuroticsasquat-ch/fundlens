"""The `/contributions` cursor: opaque to the client, and refused when it is not ours."""

from datetime import date

import pytest

from fundlens.api.itemized import BadCursor, Cursor

BUILD = "20261030T030000Z"


@pytest.mark.parametrize("day", [date(2024, 3, 1), None])
def test_a_cursor_round_trips(day: date | None) -> None:
    cursor = Cursor(BUILD, day, 4240100000000000001)

    assert Cursor.decode(cursor.encode()) == cursor


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
        # A build id that is not YYYYMMDDTHHMMSSZ: it would name a path outside silver.
        Cursor("../../etc", None, 1).encode(),
    ],
)
def test_a_cursor_we_did_not_issue_is_refused(token: str) -> None:
    with pytest.raises(BadCursor):
        Cursor.decode(token)
