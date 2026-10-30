-- No conduit's 24T row for an earmark is counted: the recipient's own row is (ADR-0004).
SELECT source_record_id, recipient_committee_id, amount
FROM contribution
WHERE transaction_type = '24T';
