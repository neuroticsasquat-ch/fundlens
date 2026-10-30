-- A candidate's own money never came through a conduit: self-funding is never an earmark.
SELECT source_record_id, recipient_committee_id, conduit_committee_id
FROM contribution
WHERE is_self_funding AND conduit_committee_id IS NOT NULL;
