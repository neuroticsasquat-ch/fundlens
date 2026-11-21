-- A payee page's address and key are each one payee's, its payee_id the key's (the first 16
-- hexadecimal characters of its SHA-256), and no key `fec/payee_no_page.csv` lists has a page
-- (every-FEC-dollar spec §5.4, §5.5). A committee's top payee links to a page exactly when its key
-- has one, and to that page.
SELECT 'payee' AS "table", payee_id, NULL AS payee_key, 'payee_id not unique' AS problem
FROM payee
GROUP BY payee_id
HAVING count(*) > 1
UNION ALL
SELECT 'payee', NULL, payee_key, 'payee_key not unique'
FROM payee
GROUP BY payee_key
HAVING count(*) > 1
UNION ALL
SELECT 'payee', payee_id, payee_key, 'payee_id is not the key''s'
FROM payee
WHERE payee_id <> left(sha256(payee_key), 16)
UNION ALL
SELECT 'payee', payee_id, payee_key, 'listed in payee_no_page'
FROM payee
WHERE payee_key IN (SELECT payee_key FROM payee_no_page)
UNION ALL
SELECT DISTINCT 'committee_top_payee', listed.payee_id, listed.payee_key, 'not its key''s page'
FROM committee_top_payee AS listed
LEFT JOIN payee USING (payee_key)
WHERE listed.payee_id IS DISTINCT FROM payee.payee_id;
