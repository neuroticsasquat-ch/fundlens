"""`fec_line`: the Form 3/3X line FEC files each transaction type on (NEU-2193), or the line the
filer's `TRAN_ID` names (NEU-2276)."""

from collections.abc import Callable, Iterator

import duckdb
import pytest

from fundlens.fec import lines

type FecLine = Callable[..., str | None]

NON_CONTRIBUTION_MEMO = "* NON-CONTRIBUTION ACCOUNT; EARMARKED CONTRIBUTION: SEE BELOW"


@pytest.fixture(scope="module")
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    with duckdb.connect() as connection:
        lines.register(connection)
        yield connection


@pytest.fixture
def fec_line(con: duckdb.DuckDBPyConnection) -> FecLine:
    def line(
        transaction_type: str | None,
        committee_type: str | None,
        memo_text: str | None = None,
        tran_id: str | None = None,
    ) -> str | None:
        [(placed,)] = con.execute(
            "SELECT fec_line(?::VARCHAR, ?::VARCHAR, ?::VARCHAR, ?::VARCHAR)",
            [transaction_type, committee_type, memo_text, tran_id],
        ).fetchall()
        return placed

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
    fec_line: FecLine, transaction_type: str | None, committee_type: str | None, line: str | None
) -> None:
    assert fec_line(transaction_type, committee_type) == line


def test_a_10_to_a_committee_of_no_known_type_is_line_11ai(fec_line: FecLine) -> None:
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
    fec_line: FecLine, committee_type: str, memo_text: str | None, line: str
) -> None:
    assert fec_line("24I", committee_type, memo_text) == line


def test_the_memo_matters_only_for_a_24i(fec_line: FecLine) -> None:
    assert fec_line("15", "W", NON_CONTRIBUTION_MEMO) == "11(a)(i)"


@pytest.mark.parametrize(
    ("tran_id", "line"),
    [
        # A super PAC's 10 or a party's 15 on another line, as the filer's software names it in the
        # ID (NEU-2276): RSLC PAC's gifts from the Republican State Leadership Committee are SA11C.
        ("SA11B.0042", "11(b) party committees"),
        ("SA11C001", "11(c) other committees"),
        ("SA12.7", "12 transfers"),
        ("SA13.1", "13 loans"),
        ("SA14.1", "14 other receipts"),
        ("SA15.1", "15 other receipts"),
        ("SA16.1", "16 other receipts"),
        ("SA17.4313", "17 other receipts"),
        ("SASL.001", "Schedule L Levin funds"),
        # Line 11(a)(i), in either spelling; Form 3P's individuals' line 17(a); 11(d), a candidate's
        # own; an ID naming no line; none at all. Each leaves the type's line.
        ("SA11AI.00030", "11(a)(i)"),
        ("SA11A1.00030", "11(a)(i)"),
        ("SA17A.00312", "11(a)(i)"),
        ("SA11D.001", "11(a)(i)"),
        ("A1B2C3", "11(a)(i)"),
        ("sa17.4313", "11(a)(i)"),
        (None, "11(a)(i)"),
    ],
)
def test_a_tran_id_naming_another_line_puts_the_row_on_it(
    fec_line: FecLine, tran_id: str | None, line: str
) -> None:
    assert fec_line("10", "O", None, tran_id) == line
    assert fec_line("15", "Y", None, tran_id) == line


@pytest.mark.parametrize(
    ("transaction_type", "committee_type", "memo_text", "line"),
    [
        # A candidate's own gift, a refund and a type the type rule does not place: the ID's line.
        ("15C", "H", None, "17 other receipts"),
        ("22Y", "O", None, "17 other receipts"),
        ("15J", "Q", None, "17 other receipts"),
        # Every other line a type names stands: a party account's, a hybrid PAC's non-contribution
        # account (whose 24Is are on line 17), a loan's.
        ("31", "Y", None, "party account 31"),
        ("10", "V", None, "non-contribution account"),
        ("24I", "W", NON_CONTRIBUTION_MEMO, "non-contribution account"),
        ("16G", "H", None, "13 loans"),
    ],
)
def test_the_tran_id_places_only_rows_the_type_puts_on_a_counted_line_or_none(
    fec_line: FecLine,
    transaction_type: str,
    committee_type: str,
    memo_text: str | None,
    line: str,
) -> None:
    assert fec_line(transaction_type, committee_type, memo_text, "SA17.4313") == line
