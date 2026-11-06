"""The Form 3/3X line FEC files each `indiv` transaction type on (NEU-2193).

`fec_line(transaction_type, committee_type)` is a DuckDB macro: the line a receipt or refund of
that type goes on at a recipient of that `cm.CMTE_TP`, as FEC's summary files total it. It is
the `fec_line` CASE of `docs/measurements/summary-files-2024.md` Q6, with two additions so that
an account's refunds go with its receipts: a hybrid PAC's 20Y is its non-contribution account's
(NEU-2192), and a national party's 40Y, 41Y and 42Y are its convention, headquarters and recount
accounts' (FEC: "Convention Account refund to an individual", and so on). The committee type
matters only there and for types 10 and 24I, a hybrid PAC's (V, W) non-contribution account and
line 11(a)(i) money anywhere else. A type it does not place, a blank one among them, is NULL.

A 24I is FEC's earmarked-intermediary-out code, which Q6 called an earmark's conduit side. Filers
write it on line 11(a)(i), mostly on their own receipts of earmarks through ActBlue, except at a
hybrid PAC, which writes it on line 17 for its non-contribution account. Of 2024's counted 24Is,
two W committees' 151 ($22,920) are on line 17 and every other one is on 11(a)(i), a V
committee's single 24I among them (`docs/measurements/summary-files-2024.md` Q10, NEU-2203). So
a 24I goes where a 10 does, which misplaces that one ($1,000) for the other 151.
An intermediary's 24I that its recipient itemized too is no contribution at all
(`sql/silver/04_contribution.sql`).

Only the 11(a)(i) lines, a candidate's 15C and the refunds of either are in a `total_individual`;
`sql/silver/04_contribution.sql` marks the rest `is_other_line`.
"""

import duckdb

FEC_LINE = r"""
CREATE MACRO fec_line(transaction_type, committee_type) AS CASE
    WHEN transaction_type IN ('15', '15E', '15I', '15T', '11', '11J', '15Z') THEN '11(a)(i)'
    WHEN transaction_type IN ('10', '10J', '24I') THEN
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
END
"""


def register(con: duckdb.DuckDBPyConnection) -> None:
    """Make `fec_line` a macro on `con`."""
    con.execute(FEC_LINE)
