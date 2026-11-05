-- Every organization receipt's recipient is a committee of the cycle: organization money is the
-- receiving committee's only (ADR-0011, NEU-2131), so a receipt no committee can hold belongs
-- nowhere.
SELECT source_record_id, recipient_committee_id, amount
FROM organization_receipt
WHERE NOT EXISTS (
    SELECT 1 FROM committee
    WHERE committee.committee_id = organization_receipt.recipient_committee_id
);
