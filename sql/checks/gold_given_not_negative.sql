-- No committee's gifts to candidates, nor any candidate's from committees, are below 0: a
-- giver->candidate pair netting negative is returned gifts, in the giver's
-- total_returned_by_candidates alone (NEU-2204).
SELECT 'committee_cycle.total_to_candidates' AS figure, committee_id AS id, total_to_candidates
    AS amount
FROM committee_cycle
WHERE total_to_candidates < 0
UNION ALL
SELECT 'committee_cycle.total_returned_by_candidates', committee_id, total_returned_by_candidates
FROM committee_cycle
WHERE total_returned_by_candidates > 0
UNION ALL
SELECT 'committee_top_recipient.amount', committee_id || ' ' || recipient_id, amount
FROM committee_top_recipient
WHERE amount < 0
UNION ALL
SELECT 'race_top_committee.amount', race_id || ' ' || committee_id, amount
FROM race_top_committee
WHERE amount < 0
UNION ALL
SELECT 'candidate_cycle.total_committee', candidate_id, total_committee
FROM candidate_cycle
WHERE total_committee < 0;
