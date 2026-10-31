-- No independent expenditure (24A against, 24E for) is a committee transfer: those are
-- independent_expenditure's (NEU-2057), and would otherwise count as money given to a candidate.
SELECT source_record_id, from_committee_id, candidate_id, transaction_type, amount
FROM committee_transfer
WHERE transaction_type IN ('24A', '24E');
