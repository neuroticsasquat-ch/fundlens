-- No MEMO_CD = 'X' memo line is counted (ADR-0004) but an orphaned attribution, the only record
-- of an LLC's or trust's gift (`orphaned_attribution`, 04_contribution.sql, NEU-2198): not as a
-- contribution, an organization receipt or a committee's gift. The silver tables keep no memo code,
-- so the memo lines are taken from `indiv`, and `oth`'s loan memo lines (NEU-2071), and looked for
-- among their rows by SUB_ID. Each table is on the left: the transform builds each join on its
-- right side (`transform.runner.connect`), here the few memo lines rather than every row.
WITH memo AS (
    SELECT SUB_ID, CMTE_ID, TRANSACTION_AMT
    FROM indiv
    WHERE MEMO_CD = 'X' AND SUB_ID NOT IN (SELECT SUB_ID FROM orphaned_attribution)
    UNION ALL
    -- A candidate's loan or repayment memo line in `oth` (NEU-2071): never counted either.
    SELECT SUB_ID, CMTE_ID, TRANSACTION_AMT
    FROM oth
    WHERE MEMO_CD = 'X' AND TRANSACTION_TP IN ('16C', '20C')
)
SELECT 'contribution' AS silver_table, memo.SUB_ID, memo.CMTE_ID, memo.TRANSACTION_AMT
FROM contribution
JOIN memo ON memo.SUB_ID = contribution.source_record_id
UNION ALL
SELECT 'organization_receipt', memo.SUB_ID, memo.CMTE_ID, memo.TRANSACTION_AMT
FROM organization_receipt
JOIN memo ON memo.SUB_ID = organization_receipt.source_record_id
UNION ALL
SELECT 'committee_transfer', memo.SUB_ID, memo.CMTE_ID, memo.TRANSACTION_AMT
FROM committee_transfer
JOIN memo ON memo.SUB_ID = committee_transfer.source_record_id;
