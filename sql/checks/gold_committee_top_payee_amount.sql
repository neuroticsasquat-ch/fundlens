-- Every top-payee row's amount is its payee's net payee rows from that committee in silver in that
-- cycle (every-FEC-dollar spec §5.4, §5.5: counted, with a key, no in-kind outlay), its name a
-- spelling of the key on those rows that cycle, and its payee_id, where it has one, the key's
-- (the first 16 hexadecimal characters of its SHA-256).
SELECT listed.cycle, listed.committee_id, listed.payee_key, listed.name, listed.payee_id, listed.amount, paid.amount AS silver_amount
FROM committee_top_payee AS listed
LEFT JOIN (
    SELECT cycle, committee_id, payee_key, sum(amount) AS amount
    FROM silver.operating_expenditure
    WHERE counted AND NOT is_in_kind
    GROUP BY cycle, committee_id, payee_key
) AS paid USING (cycle, committee_id, payee_key)
WHERE paid.amount IS DISTINCT FROM listed.amount
    OR listed.payee_id <> left(sha256(listed.payee_key), 16)
    OR NOT EXISTS (
        SELECT 1
        FROM silver.operating_expenditure AS spending
        WHERE spending.cycle = listed.cycle
            AND spending.payee_key = listed.payee_key
            AND spending.payee_name = listed.name
            AND spending.counted
            AND NOT spending.is_in_kind
    );
