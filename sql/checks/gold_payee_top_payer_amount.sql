-- Every top-payer row's amount is its committee's net payee rows to that payee's key in silver in
-- that cycle (every-FEC-dollar spec §5.4, §5.5: counted, with a key, no in-kind outlay), its payee
-- a payee with a page, and its candidate_id, where it has one, a candidate those rows are credited
-- to: NULL only when none is.
SELECT listed.payee_id, listed.cycle, listed.committee_id, listed.candidate_id, listed.amount, paid.amount AS silver_amount
FROM payee_top_payer AS listed
LEFT JOIN payee USING (payee_id)
LEFT JOIN (
    SELECT cycle, committee_id, payee_key, sum(amount) AS amount,
        list(DISTINCT candidate_id) FILTER (WHERE candidate_id IS NOT NULL) AS candidates
    FROM silver.operating_expenditure
    WHERE counted AND NOT is_in_kind
    GROUP BY cycle, committee_id, payee_key
) AS paid ON paid.cycle = listed.cycle
    AND paid.committee_id = listed.committee_id
    AND paid.payee_key = payee.payee_key
WHERE payee.payee_id IS NULL
    OR paid.amount IS DISTINCT FROM listed.amount
    OR (listed.candidate_id IS NULL AND len(coalesce(paid.candidates, [])) > 0)
    OR (
        listed.candidate_id IS NOT NULL
        AND NOT list_contains(coalesce(paid.candidates, []), listed.candidate_id)
    );
