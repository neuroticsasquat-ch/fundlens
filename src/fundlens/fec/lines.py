"""The Form 3/3X line FEC files each `indiv` transaction type on (NEU-2193).

`fec_line(transaction_type, committee_type)` is a DuckDB macro: the line a receipt or refund of
that type goes on at a recipient of that `cm.CMTE_TP`, as FEC's summary files total it. It is
the `fec_line` CASE of `docs/measurements/summary-files-2024.md` Q6, with two additions so that
an account's refunds go with its receipts: a hybrid PAC's 20Y is its non-contribution account's
(NEU-2192), and a national party's 40Y, 41Y and 42Y are its convention, headquarters and recount
accounts' (FEC: "Convention Account refund to an individual", and so on). The committee type
matters only there and for type 10, a hybrid PAC's (V, W) non-contribution account and line
11(a)(i) money anywhere else. A type it does not place, a blank one among them, is NULL.

Only the 11(a)(i) lines, a candidate's 15C and the refunds of either are in a `total_individual`;
`sql/silver/04_contribution.sql` marks the rest `is_other_line`.
"""

import duckdb

FEC_LINE = r"""
CREATE MACRO fec_line(transaction_type, committee_type) AS CASE
    WHEN transaction_type IN ('15', '15E', '15I', '15T', '11', '11J', '15Z') THEN '11(a)(i)'
    WHEN transaction_type IN ('10', '10J') THEN
        CASE WHEN committee_type IN ('V', 'W') THEN 'non-contribution account' ELSE '11(a)(i)' END
    WHEN transaction_type = '20Y' AND committee_type IN ('V', 'W') THEN 'non-contribution account'
    WHEN transaction_type = '15C' THEN '11(d) candidate'
    WHEN transaction_type IN ('16C', '16F', '16G', '16H', '16J', '16K', '16L', '16R')
        THEN '13 loans'
    WHEN transaction_type IN ('18G', '18J', '18K', '18L') THEN '12 transfers'
    WHEN transaction_type = '18U' THEN '11(c) unregistered committee'
    WHEN transaction_type = '18H' THEN '15 other receipts'
    WHEN transaction_type IN ('19', '19J') THEN 'electioneering'
    WHEN regexp_matches(transaction_type, '^3[012][A-Z]?$')
        THEN 'party account ' || left(transaction_type, 2)
    WHEN transaction_type IN ('40Y', '41Y', '42Y')
        THEN 'party account 3' || substr(transaction_type, 2, 1)
    WHEN regexp_matches(transaction_type, '^[24][0-9]Y$') OR transaction_type = '22Z'
        THEN '20 refunds'
    WHEN transaction_type = '24I' THEN 'earmark, conduit side (24I)'
END
"""


def register(con: duckdb.DuckDBPyConnection) -> None:
    """Make `fec_line` a macro on `con`."""
    con.execute(FEC_LINE)
