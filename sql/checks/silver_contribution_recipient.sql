-- Every contribution's recipient is a committee of the cycle, and never the conduit its earmark
-- went through: an earmark is counted on the recipient side (ADR-0004).
SELECT source_record_id, recipient_committee_id, conduit_committee_id
FROM contribution
WHERE recipient_committee_id = conduit_committee_id
    OR NOT EXISTS (
        SELECT 1 FROM committee WHERE committee.committee_id = contribution.recipient_committee_id
    );
