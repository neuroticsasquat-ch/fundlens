"""The Form 3/3X line FEC files each `indiv` transaction type on (NEU-2193).

`fec_line(transaction_type, committee_type, memo_text, tran_id)` is a DuckDB macro: the line a
receipt or refund of that type goes on at a recipient of that `cm.CMTE_TP`, as FEC's summary files
total it, unless its `TRAN_ID` names another (below). The type's line is `type_line`, the
`fec_line` CASE of `docs/measurements/summary-files-2024.md` Q6, with two additions so that an
account's refunds go with its receipts: a hybrid PAC's 20Y is its non-contribution
account's (NEU-2192), and a national party's 40Y, 41Y and 42Y are its convention, headquarters and
recount accounts' (FEC: "Convention Account refund to an individual", and so on). The committee type
matters only there and for type 10, a hybrid PAC's (V, W) non-contribution account and line
11(a)(i) money anywhere else, and for type 24I, whose memo text decides it at a hybrid PAC
(below). A type it does not place, a blank one among them, is NULL.

A 24I is FEC's earmarked-intermediary-out code, which Q6 called an earmark's conduit side. Filers
write it on line 11(a)(i), mostly on their own receipts of earmarks through ActBlue, a hybrid
PAC's among them, except where a hybrid PAC writes it on line 17 for its non-contribution
account. Neither committee type tells the two apart: in 2024 two W committees filed their 151
($22,920) on line 17 and four V committees their 21 ($5,740) on 11(a)(i), but in 2026 three W
committees filed all 166 of theirs ($37,794) on 11(a)(i). The memo does: every line-17 24I's
`MEMO_TEXT` begins `* NON-CONTRIBUTION ACCOUNT`, and no other hybrid PAC's does
(`docs/measurements/summary-files-2024.md` Q10j, NEU-2207). So a hybrid PAC's 24I with that memo
goes where its 10 does, and every other 24I on line 11(a)(i).
An intermediary's 24I that its recipient itemized too is no contribution at all
(`sql/silver/04_contribution.sql`).

Where the type puts a row on a line a total counts, or on none, the filer's `TRAN_ID` can
place it elsewhere (NEU-2276). `indiv` types a super PAC's receipts 10 on every line and a
party's offsets 15, but many filers' software writes the Schedule A line into the ID
(`SA11C001`, `SA17.4313`). A `TRAN_ID` naming 11(b), 11(c), 12, 13, 14, 15, 16, 17 or Schedule L
puts the row on that line: lines 11(b) to 16 are other committees', transfers, loans and other
receipts on Form 3 and 3X alike, and 17 is other federal receipts on Form 3X. Not 17(a): Form 3P
files individuals' contributions on it, and its `TRAN_ID`s say `SA17A`. Measured on the 2024
build's `indiv` rows, the rule moves 71 committees toward FEC's itemized figure ($52.1M) and 39
away ($2.5M) (`docs/measurements/summary-files-2024.md` Q15g2); `oth` rows were not measured.
Every other line a type names stands whatever the `TRAN_ID` says: a party account, a hybrid PAC's
non-contribution account (whose 24Is are on line 17), a loan, a transfer. The match is
case-sensitive, as Q15 measured it.

Only the 11(a)(i) lines, a candidate's 15C and the refunds of either are in a `total_individual`
or a `total_from_organizations`; `sql/silver/04_contribution.sql` and
`sql/silver/08_organization_receipt.sql` mark the rest `is_other_line` (NEU-2205).
"""

import duckdb

TYPE_LINE = r"""
CREATE MACRO type_line(transaction_type, committee_type, memo_text) AS CASE
    WHEN transaction_type IN ('15', '15E', '15I', '15T', '11', '11J', '15Z') THEN '11(a)(i)'
    WHEN transaction_type IN ('10', '10J') THEN
        CASE WHEN committee_type IN ('V', 'W') THEN 'non-contribution account' ELSE '11(a)(i)' END
    WHEN transaction_type = '24I' THEN
        CASE
            WHEN committee_type IN ('V', 'W')
                AND starts_with(upper(memo_text), '* NON-CONTRIBUTION ACCOUNT')
                THEN 'non-contribution account'
            ELSE '11(a)(i)'
        END
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


# The line a `TRAN_ID` names, by Q15g's `named_line2`; NULL where it names 11(a)(i), 11(d), 17(a)
# or none.
TRAN_ID_LINE = r"""
CREATE MACRO tran_id_line(tran_id) AS CASE
    regexp_extract(tran_id, '^SA(11AI|11A1|11B|11C|11D|12|13|14|15|16|17A|17|SL)', 1)
    WHEN '11B' THEN '11(b) party committees'
    WHEN '11C' THEN '11(c) other committees'
    WHEN '12' THEN '12 transfers'
    WHEN '13' THEN '13 loans'
    WHEN '14' THEN '14 other receipts'
    WHEN '15' THEN '15 other receipts'
    WHEN '16' THEN '16 other receipts'
    WHEN '17' THEN '17 other receipts'
    WHEN 'SL' THEN 'Schedule L Levin funds'
END
"""

FEC_LINE = r"""
CREATE MACRO fec_line(transaction_type, committee_type, memo_text, tran_id) AS CASE
    -- A type the type rule does not place (NULL) counts, so its TRAN_ID may place it too.
    WHEN tran_id_line(tran_id) IS NOT NULL
        AND coalesce(type_line(transaction_type, committee_type, memo_text), '11(a)(i)')
            IN ('11(a)(i)', '11(d) candidate', '20 refunds')
        THEN tran_id_line(tran_id)
    ELSE type_line(transaction_type, committee_type, memo_text)
END
"""


def register(con: duckdb.DuckDBPyConnection) -> None:
    """Make `fec_line`, and the `type_line` and `tran_id_line` it reads, macros on `con`."""
    for macro in (TYPE_LINE, TRAN_ID_LINE, FEC_LINE):
        con.execute(macro)
