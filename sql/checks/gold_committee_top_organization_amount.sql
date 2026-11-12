-- Every top-organization row's amount is its organization's net receipts to that committee in
-- silver in that cycle (ADR-0011), and its name one the organization reported that cycle.
SELECT listed.cycle, listed.committee_id, listed.organization_key, listed.name, listed.amount, received.amount AS silver_amount
FROM committee_top_organization AS listed
LEFT JOIN (
    SELECT cycle, recipient_committee_id AS committee_id, organization_key, sum(amount) AS amount
    FROM silver.organization_receipt
    GROUP BY cycle, recipient_committee_id, organization_key
) AS received USING (cycle, committee_id, organization_key)
WHERE received.amount IS DISTINCT FROM listed.amount
    OR NOT EXISTS (
        SELECT 1
        FROM silver.organization_receipt AS receipt
        WHERE receipt.cycle = listed.cycle
            AND receipt.organization_key = listed.organization_key
            AND receipt.organization_name = listed.name
    );
