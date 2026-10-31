-- Every candidate in a committee's top 100 recipients is a candidate of the cycle.
SELECT committee_id, rank, recipient_id
FROM committee_top_recipient
WHERE recipient_kind = 'candidate'
    AND NOT EXISTS (SELECT 1 FROM candidate WHERE candidate.candidate_id = committee_top_recipient.recipient_id);
