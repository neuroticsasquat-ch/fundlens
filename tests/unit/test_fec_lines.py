"""`fec_line`: the Form 3/3X line FEC files each transaction type on (NEU-2193)."""

import duckdb
import pytest

from fundlens.fec import lines

NON_CONTRIBUTION_MEMO = "* NON-CONTRIBUTION ACCOUNT; EARMARKED CONTRIBUTION: SEE BELOW"


def fec_line(
    transaction_type: str | None, committee_type: str | None, memo_text: str | None = None
) -> str | None:
    with duckdb.connect() as con:
        lines.register(con)
        [(line,)] = con.execute(
            "SELECT fec_line(?::VARCHAR, ?::VARCHAR, ?::VARCHAR)",
            [transaction_type, committee_type, memo_text],
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
        # A 24I, which most filers write on their own receipt of an earmark (NEU-2203), at a
        # hybrid PAC too unless its memo says otherwise (below).
        ("24I", "O", "11(a)(i)"),
        ("24I", "W", "11(a)(i)"),
        ("24I", "V", "11(a)(i)"),
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


@pytest.mark.parametrize(
    ("committee_type", "memo_text", "line"),
    [
        # A hybrid PAC files a 24I on line 17 for its non-contribution account under this memo,
        # and on 11(a)(i) without it, whatever its type: 2024's W committees did the first and
        # 2026's the second (NEU-2207).
        ("W", NON_CONTRIBUTION_MEMO, "non-contribution account"),
        ("V", NON_CONTRIBUTION_MEMO.lower(), "non-contribution account"),
        ("W", "* EARMARKED CONTRIBUTION: SEE BELOW", "11(a)(i)"),
        ("V", None, "11(a)(i)"),
        # The account is a hybrid PAC's alone.
        ("O", NON_CONTRIBUTION_MEMO, "11(a)(i)"),
    ],
)
def test_a_hybrid_pacs_24i_is_its_non_contribution_accounts_when_its_memo_says_so(
    committee_type: str, memo_text: str | None, line: str
) -> None:
    assert fec_line("24I", committee_type, memo_text) == line


def test_the_memo_matters_only_for_a_24i() -> None:
    assert fec_line("15", "W", NON_CONTRIBUTION_MEMO) == "11(a)(i)"
