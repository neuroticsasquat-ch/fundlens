"""`fec_line`: the Form 3/3X line FEC files each transaction type on (NEU-2193)."""

import duckdb
import pytest

from fundlens.fec import lines


def fec_line(transaction_type: str | None, committee_type: str | None) -> str | None:
    with duckdb.connect() as con:
        lines.register(con)
        [(line,)] = con.execute(
            "SELECT fec_line(?::VARCHAR, ?::VARCHAR)", [transaction_type, committee_type]
        ).fetchall()
    return line


@pytest.mark.parametrize(
    ("transaction_type", "committee_type", "line"),
    [
        # A national party's convention, headquarters and recount accounts, and their refunds.
        ("30", "Y", "party account 30"),
        ("31T", "Y", "party account 31"),
        ("32E", "Y", "party account 32"),
        ("40Y", "Y", "party account 30"),
        ("41Y", "Y", "party account 31"),
        ("42Y", "Y", "party account 32"),
        # Receipts that are no individual's contribution on line 11(a)(i).
        ("18U", "X", "11(c) unregistered committee"),
        ("18G", "W", "12 transfers"),
        ("16G", "H", "13 loans"),
        ("19", "I", "electioneering"),
        # Line 11(a)(i), a candidate's own gift, and their refunds.
        ("15", "H", "11(a)(i)"),
        ("15E", "Q", "11(a)(i)"),
        # A 24I, which most filers write on their own receipt of an earmark, goes where a 10 does
        # (NEU-2203).
        ("24I", "O", "11(a)(i)"),
        ("24I", "W", "non-contribution account"),
        ("15C", "S", "11(d) candidate"),
        ("22Y", "Y", "20 refunds"),
        # A hybrid PAC's non-contribution account (NEU-2192); a 10 or 20Y anywhere else is not one.
        ("10", "V", "non-contribution account"),
        ("10J", "W", "non-contribution account"),
        ("20Y", "W", "non-contribution account"),
        ("10", "O", "11(a)(i)"),
        ("20Y", "O", "20 refunds"),
        # A type the rule does not place.
        ("15J", "Q", None),
        (None, "Q", None),
    ],
)
def test_each_transaction_type_is_on_the_line_fec_files_it_on(
    transaction_type: str | None, committee_type: str | None, line: str | None
) -> None:
    assert fec_line(transaction_type, committee_type) == line


def test_a_10_to_a_committee_of_no_known_type_is_line_11ai() -> None:
    assert fec_line("10", None) == "11(a)(i)"
