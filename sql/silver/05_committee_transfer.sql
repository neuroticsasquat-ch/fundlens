-- committee_transfer (spec §4, NEU-2039 §1.3): one row per `oth` receipt from another committee
-- and per `pas2` 24K committee-to-candidate contribution, told apart by `side`.
--
-- A committee's gift to a candidate's committee is reported twice: the giver files it in `pas2`
-- as a 24K (side = 'disbursement', with the candidate it is for), the recipient in `oth` as an
-- 18K (side = 'receipt', with no candidate). Both are kept, and a gold aggregate sums one side
-- only: receipts by to_committee_id, disbursements by from_committee_id or candidate_id. Adding
-- the two sides would count the gift twice (expected.yaml's rule). The other `pas2` types
-- (24A/24E independent expenditures, 24C coordinated) are NEU-2057's independent_expenditure.
-- Refunds are negative amounts, kept so they net out.
--
-- `oth` is not only receipts (NEU-2070). It also repeats every `pas2` row under the same SUB_ID,
-- holds the filer's own disbursements (24G, 22Z), the memo lines itemizing individuals' gifts
-- through a joint fundraising committee (15J, MEMO_CD = 'X') and candidates' loans to their
-- campaigns (16C). A receipt here is a receipt type (TRANSACTION_TP 1x, or 3x for a party's
-- convention, headquarters and recount accounts), not a memo line, from a giver whose id is a
-- committee's.
CREATE TABLE committee_transfer AS
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    trim(OTHER_ID) AS from_committee_id,
    CMTE_ID AS to_committee_id,
    CAST(NULL AS VARCHAR) AS candidate_id,
    TRANSACTION_AMT AS amount,
    -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
    CAST(try_strptime(TRANSACTION_DT, '%m%d%Y') AS DATE) AS date,
    TRANSACTION_TP AS transaction_type,
    'receipt' AS side
FROM oth
WHERE left(TRANSACTION_TP, 1) IN ('1', '3')
    AND MEMO_CD IS DISTINCT FROM 'X'
    AND trim(OTHER_ID) LIKE 'C%'
UNION ALL
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    CMTE_ID AS from_committee_id,
    nullif(trim(OTHER_ID), '') AS to_committee_id,
    CAND_ID AS candidate_id,
    TRANSACTION_AMT AS amount,
    CAST(try_strptime(TRANSACTION_DT, '%m%d%Y') AS DATE) AS date,
    TRANSACTION_TP AS transaction_type,
    'disbursement' AS side
FROM pas2
WHERE TRANSACTION_TP = '24K';
