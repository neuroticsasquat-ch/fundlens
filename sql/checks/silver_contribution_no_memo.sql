-- No MEMO_CD = 'X' memo line is counted (ADR-0004). contribution keeps no memo code, so the memo
-- lines are taken from `indiv` and looked for among its rows by SUB_ID.
SELECT SUB_ID, CMTE_ID, TRANSACTION_AMT
FROM indiv
WHERE MEMO_CD = 'X' AND SUB_ID IN (SELECT source_record_id FROM contribution);
