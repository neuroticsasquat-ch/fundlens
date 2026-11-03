-- committee_transfer (spec §4, NEU-2039 §1.3): one row per `oth` receipt from another committee
-- and per `pas2` 24K committee-to-candidate contribution, told apart by `side`.
--
-- A committee's gift to a candidate's committee is reported twice: the giver files it in `pas2`
-- as a 24K (side = 'disbursement'), the recipient in `oth` as an 18K (side = 'receipt'). Both are
-- kept, and a gold aggregate sums one side only: receipts by to_committee_id or candidate_id,
-- disbursements by from_committee_id or candidate_id. Adding the two sides would count the gift
-- twice (expected.yaml's rule). The other `pas2` types (24A/24E independent expenditures, 24C
-- coordinated) are NEU-2057's independent_expenditure.
-- A negative amount is a correction, kept so it nets out. A conduit's 24K is no gift: it is the
-- conduit's side of an earmark it passed on (WinRed filed 348,042 in 2024, $10.2M net, most of them
-- refunds), an individual's money counted once on the recipient's `indiv` row (ADR-0004), so it
-- is dropped as the conduit's 24T is in 04_contribution.sql.
--
-- `oth` is not only receipts (NEU-2070). It also repeats every `pas2` row under the same SUB_ID,
-- holds the filer's own disbursements (24G, 22Z), the memo lines itemizing individuals' gifts
-- through a joint fundraising committee (15J, MEMO_CD = 'X') and candidates' loans to their
-- campaigns (16C). A receipt here is a receipt type (TRANSACTION_TP 1x, or 3x for a party's
-- convention, headquarters and recount accounts), not a memo line, from a giver whose id is a
-- committee's. A JFC's transfer is filed under any of several receipt types (18G mostly, some 18J,
-- a few 15J) and now and then with OTHER_ID blank: Trump's campaign filed $32.3M of its 2024 JFC
-- transfers so (NEU-2124). A blank OTHER_ID's giver is the joint fundraising committee (designation
-- J) its NAME names, compared as names are in 04_contribution.sql; naming any other committee, or
-- none, it names no giver and the row is no receipt.
--
-- A receipt's candidate is the one its recipient committee raises for, by contribution's rule
-- (NEU-2124), so a JFC's transfer to a campaign is that candidate's (gold's
-- total_jfc_transfers). A receipt to a committee raising for no candidate (a party, a PAC, a JFC)
-- has none: the giver's CAND_ID a 24K may fall back on is not on the receipt.
--
-- A 24K's candidate is the one its recipient committee is linked to (NEU-2075), the rule
-- contribution follows: givers often write a stale or wrong CAND_ID (a senator's old House id, an
-- id from an earlier race). Only when the recipient has no principal or authorized link to a
-- candidate of the cycle does the giver's CAND_ID stand, and only if it is one; otherwise the gift is
-- credited to no candidate, and is in neither a candidate's total_committee nor the giver's
-- total_to_candidates.
CREATE TABLE committee_transfer AS
WITH linked AS (
    -- As in 04_contribution.sql: a P or A link, or the candidate's `cn` principal committee; the
    -- principal link, then the lower candidate_id, so one each. Only to a candidate of the cycle:
    -- `ccl` also links a few committees to candidates `cn` lacks.
    SELECT link.committee_id, link.candidate_id
    FROM candidate_committee_link AS link
    JOIN candidate USING (candidate_id)
    WHERE link.designation IN ('P', 'A') OR link.committee_id = candidate.principal_committee_id
    QUALIFY row_number() OVER (
        PARTITION BY link.committee_id
        ORDER BY
            (link.designation = 'P' OR link.committee_id = candidate.principal_committee_id) DESC,
            link.candidate_id
    ) = 1
),
jfc_named AS (
    -- Each JFC by name; a name two JFCs share names neither.
    SELECT
        regexp_replace(upper(name), '[^A-Z0-9]', '', 'g') AS name_key,
        min(committee_id) AS committee_id
    FROM committee
    WHERE designation = 'J'
    GROUP BY name_key
    HAVING count(*) = 1
),
receipt AS (
    SELECT
        oth.*,
        coalesce(
            CASE WHEN trim(oth.OTHER_ID) LIKE 'C%' THEN trim(oth.OTHER_ID) END,
            jfc_named.committee_id
        ) AS giver
    FROM oth
    LEFT JOIN jfc_named
        ON coalesce(trim(oth.OTHER_ID), '') = ''
        AND jfc_named.name_key = regexp_replace(upper(oth.NAME), '[^A-Z0-9]', '', 'g')
    WHERE left(oth.TRANSACTION_TP, 1) IN ('1', '3') AND oth.MEMO_CD IS DISTINCT FROM 'X'
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    receipt.SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    receipt.giver AS from_committee_id,
    receipt.CMTE_ID AS to_committee_id,
    linked.candidate_id,
    receipt.TRANSACTION_AMT AS amount,
    -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
    CAST(try_strptime(receipt.TRANSACTION_DT, '%m%d%Y') AS DATE) AS date,
    receipt.TRANSACTION_TP AS transaction_type,
    'receipt' AS side
FROM receipt
LEFT JOIN linked ON linked.committee_id = receipt.CMTE_ID
WHERE receipt.giver IS NOT NULL
UNION ALL
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    pas2.CMTE_ID AS from_committee_id,
    nullif(trim(pas2.OTHER_ID), '') AS to_committee_id,
    coalesce(
        linked.candidate_id,
        CASE WHEN pas2.CAND_ID IN (SELECT candidate_id FROM candidate) THEN pas2.CAND_ID END
    ) AS candidate_id,
    pas2.TRANSACTION_AMT AS amount,
    CAST(try_strptime(pas2.TRANSACTION_DT, '%m%d%Y') AS DATE) AS date,
    pas2.TRANSACTION_TP AS transaction_type,
    'disbursement' AS side
FROM pas2
LEFT JOIN linked ON linked.committee_id = nullif(trim(pas2.OTHER_ID), '')
WHERE pas2.TRANSACTION_TP = '24K'
    AND pas2.CMTE_ID NOT IN (SELECT committee_id FROM committee WHERE is_conduit);
