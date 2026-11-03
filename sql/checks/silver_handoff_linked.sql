-- Every handoff of the cycle (fec/handoffs.csv) is of a committee `ccl` links principal (P) or
-- authorized (A) to both its candidates, each a candidate of the cycle: a stale row fails the build
-- instead of silently crediting no one (NEU-2126).
SELECT handoff_link.committee_id, handoff_link.candidate_id
FROM handoff_link
WHERE NOT EXISTS (
    SELECT 1
    FROM candidate_committee_link AS link
    JOIN candidate USING (candidate_id)
    WHERE link.committee_id = handoff_link.committee_id
        AND link.candidate_id = handoff_link.candidate_id
        AND link.designation IN ('P', 'A')
);
