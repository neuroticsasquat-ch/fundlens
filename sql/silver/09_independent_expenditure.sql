-- independent_expenditure (spec §4, NEU-2057): one row per `pas2` row that is a committee's spending
-- for or against a candidate rather than a gift to one. `pas2`'s 24Ks, committees' contributions
-- to candidates, are committee_transfer's disbursements (05_committee_transfer.sql).
--
-- kind tells the rows apart, and only kind 'ie' is an independent expenditure: 24E for the
-- candidate (support_oppose 'S') and 24A against (support_oppose 'O'). The rest are kept for the
-- outside-spending tickets (NEU-2167), in no total yet: a party's coordinated expenditure (24C,
-- 'coordinated', for its candidate) and a Form 7 filer's communication cost (24F for, 24N against,
-- 'communication_cost').
--
-- A memo line (MEMO_CD 'X') is no expenditure: it notes an unpaid invoice or debt (Schedule D),
-- itemizes a credit card's or vendor's payment, or restates an in-kind gift, and is dropped as
-- every other file's memo lines are. 2024's are 8,478 IE lines, $74,904,053, against 73,825 counted
-- IEs, $4,422,471,620. A row whose filer `cm` lacks is dropped as a contribution to one is (none
-- in 2024).
--
-- The candidate is CAND_ID's, or the id it is an alias of (NEU-2127), when it is a candidate of the
-- cycle; else none. The race is the candidate's race in the seat calendar, or none. A candidate a
-- spender targets is not always one of the cycle: in 2024, 1,282 IE rows ($54,429,826, memo lines
-- among them) name an id `cn` lacks or none, and others a candidate whose seat is not up (a
-- 2026 senator, a 2028 hopeful). Such a row is kept, its candidate or race null: the money is the
-- spender's ie_total all the same, and in no candidate's or race's figure.
-- Each amount is kept as filed, a negative one included (a correction), so it nets out.
CREATE TABLE independent_expenditure AS
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    spending.SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    spending.CMTE_ID AS committee_id,
    coalesce(candidate.alias_of, candidate.candidate_id) AS candidate_id,
    -- An alias is of a candidate of the same race, so its race is the canonical id's.
    candidate.race_id,
    CASE WHEN spending.TRANSACTION_TP IN ('24A', '24N') THEN 'O' ELSE 'S' END AS support_oppose,
    spending.TRANSACTION_AMT AS amount,
    -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
    CAST(try_strptime(spending.TRANSACTION_DT, '%m%d%Y') AS DATE) AS date,
    spending.TRANSACTION_TP AS transaction_type,
    CASE spending.TRANSACTION_TP
        WHEN '24C' THEN 'coordinated'
        WHEN '24F' THEN 'communication_cost'
        WHEN '24N' THEN 'communication_cost'
        ELSE 'ie'
    END AS kind
FROM pas2 AS spending
LEFT JOIN candidate ON candidate.candidate_id = nullif(trim(spending.CAND_ID), '')
WHERE spending.TRANSACTION_TP IN ('24A', '24E', '24C', '24F', '24N')
    AND coalesce(spending.MEMO_CD, '') <> 'X'
    AND spending.CMTE_ID IN (SELECT committee_id FROM committee);
