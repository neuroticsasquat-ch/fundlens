-- A candidate's own money is never a top donor (spec §2): every top-donor row's amount is exactly
-- the donor's gifts to its race, candidate or committee net of refunds, the recipient candidate's
-- own money left out. A row of own money alone has no such gifts; one with own money added is
-- larger than them.
WITH gift AS (
    SELECT donor_id, candidate_id, recipient_committee_id, amount
    FROM silver.contribution
    WHERE NOT is_self_funding AND donor_id IS NOT NULL
)
SELECT 'race_top_donor' AS "table", top.race_id AS group_id, top.donor_id, top.amount
FROM race_top_donor AS top
WHERE top.amount IS DISTINCT FROM (
    SELECT sum(gift.amount)
    FROM gift
    JOIN race_candidate USING (candidate_id)
    WHERE race_candidate.race_id = top.race_id AND gift.donor_id = top.donor_id
)
UNION ALL
SELECT 'candidate_top_donor', top.candidate_id, top.donor_id, top.amount
FROM candidate_top_donor AS top
WHERE top.amount IS DISTINCT FROM (
    SELECT sum(gift.amount)
    FROM gift
    WHERE gift.candidate_id = top.candidate_id AND gift.donor_id = top.donor_id
)
UNION ALL
SELECT 'committee_top_donor', top.committee_id, top.donor_id, top.amount
FROM committee_top_donor AS top
WHERE top.amount IS DISTINCT FROM (
    SELECT sum(gift.amount)
    FROM gift
    WHERE gift.recipient_committee_id = top.committee_id AND gift.donor_id = top.donor_id
);
