-- Every 15C, FEC's "contribution from the candidate", is self-funding whatever its entity type,
-- name or route (NEU-2194), and so is every 16C and 20C, the candidate's loan and its repayment
-- (NEU-2071).
SELECT source_record_id, recipient_committee_id, entity_type, contributor_name
FROM contribution
WHERE transaction_type IN ('15C', '16C', '20C') AND NOT is_self_funding;
