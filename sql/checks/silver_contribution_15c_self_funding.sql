-- Every 15C, FEC's "contribution from the candidate", is self-funding whatever its entity type,
-- name or route (NEU-2194).
SELECT source_record_id, recipient_committee_id, entity_type, contributor_name
FROM contribution
WHERE transaction_type = '15C' AND NOT is_self_funding;
