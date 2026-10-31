-- No MEMO_CD = 'X' memo line is counted (ADR-0004). contribution keeps no memo code, so the memo
-- lines are taken from `indiv` and looked for among its rows by SUB_ID. contribution is on the
-- left: the transform builds each join on its right side (`transform.runner.connect`), here the
-- few memo lines rather than every contribution.
SELECT memo.SUB_ID, memo.CMTE_ID, memo.TRANSACTION_AMT
FROM contribution
JOIN (SELECT SUB_ID, CMTE_ID, TRANSACTION_AMT FROM indiv WHERE MEMO_CD = 'X') AS memo
    ON memo.SUB_ID = contribution.source_record_id;
