-- A candidate's five itemized gift-size buckets add up to their total_individual (every-FEC-dollar
-- spec §4.6), all five or none, and all five for a candidate with a counted contribution, even one
-- netting to $0: each donor in one bucket, by their net gifts to the candidate. A cycle loaded
-- before `resolve` (contributor_count NULL) has no buckets to check.
SELECT
    candidate_cycle.candidate_id,
    candidate_cycle.cycle,
    candidate_cycle.total_individual,
    buckets.amount,
    buckets.buckets
FROM candidate_cycle
LEFT JOIN (
    SELECT candidate_id, cycle, sum(amount) AS amount, count(*) AS buckets
    FROM candidate_gift_size
    WHERE bucket <> 'unitemized'
    GROUP BY candidate_id, cycle
) AS buckets USING (candidate_id, cycle)
WHERE candidate_cycle.contributor_count IS NOT NULL
    AND (
        coalesce(buckets.amount, 0) <> candidate_cycle.total_individual
        OR coalesce(buckets.buckets, 5) <> 5
        OR (
            buckets.buckets IS NULL
            AND EXISTS (
                SELECT 1
                FROM silver.contribution AS contribution
                WHERE contribution.cycle = candidate_cycle.cycle
                    AND contribution.candidate_id = candidate_cycle.candidate_id
                    AND NOT contribution.is_self_funding
                    AND NOT contribution.is_other_line
            )
        )
    );
