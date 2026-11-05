-- Every top-organization row's amount is its organization's net receipts to that committee in
-- silver (ADR-0011), and its name one the organization reported.
SELECT listed.committee_id, listed.organization_key, listed.name, listed.amount, received.amount AS silver_amount
FROM committee_top_organization AS listed
LEFT JOIN (
    SELECT recipient_committee_id AS committee_id, organization_key, sum(amount) AS amount
    FROM silver.organization_receipt
    GROUP BY recipient_committee_id, organization_key
) AS received USING (committee_id, organization_key)
WHERE received.amount IS DISTINCT FROM listed.amount
    OR NOT EXISTS (
        SELECT 1
        FROM silver.organization_receipt AS receipt
        WHERE receipt.organization_key = listed.organization_key
            AND receipt.organization_name = listed.name
    );
