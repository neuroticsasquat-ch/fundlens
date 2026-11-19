-- candidate_gift_size (every-FEC-dollar spec §4.6): a candidate's individual money by the size of
-- each donor's gifts, one row per bucket.
--
-- A donor's gift size is their net gifts to the candidate in the cycle: the sum, per donor_id, of
-- the rows candidate_cycle.total_individual counts for the candidate (not self-funding, not
-- other-lines money, refunds netting). The aggregate decides the bucket, so twenty $50 gifts are one
-- $1,000 donor in under_2000; one netting $0 or less is in 200_or_less. amount is the bucket's
-- donors' gift sizes added up, donors their count. The five itemized buckets add up to the
-- candidate's total_individual (gold_candidate_gift_size_total.sql), and a candidate with a counted
-- contribution has all five, a bucket with no donor at 0. A cycle loaded before `resolve`, whose
-- contributor_count is NULL, has no donor_ids and so no itemized rows. Organization money is in no
-- bucket: an organization is not a donor.
--
-- unitemized is the candidate's reported_individual_unitemized as filed, with no donor count: FEC's
-- lump beside the itemized buckets, never added to one. Only where the candidate has that figure,
-- 2008 on; a handoff's first candidate has none.
CREATE TABLE candidate_gift_size AS
WITH gift_size AS (
    SELECT cycle, candidate_id, donor_id, sum(amount) AS gift_size
    FROM silver.contribution
    WHERE candidate_id IS NOT NULL
        AND NOT is_self_funding
        AND NOT is_other_line
        AND donor_id IS NOT NULL
    GROUP BY cycle, candidate_id, donor_id
),
bucketed AS (
    SELECT
        cycle,
        candidate_id,
        CASE
            WHEN gift_size <= 200 THEN '200_or_less'
            WHEN gift_size < 500 THEN 'under_500'
            WHEN gift_size < 1000 THEN 'under_1000'
            WHEN gift_size < 2000 THEN 'under_2000'
            ELSE '2000_or_more'
        END AS bucket,
        gift_size
    FROM gift_size
),
bucket (bucket) AS (
    VALUES ('200_or_less'), ('under_500'), ('under_1000'), ('under_2000'), ('2000_or_more')
),
donated AS (
    SELECT DISTINCT cycle, candidate_id FROM gift_size
)
SELECT
    candidate_cycle.candidate_id,
    candidate_cycle.cycle,
    bucket.bucket,
    CAST(coalesce(sum(bucketed.gift_size), 0) AS DECIMAL(16, 2)) AS amount,
    CAST(count(bucketed.gift_size) AS INTEGER) AS donors
FROM candidate_cycle
JOIN donated USING (cycle, candidate_id)
CROSS JOIN bucket
LEFT JOIN bucketed
    ON bucketed.cycle = candidate_cycle.cycle
    AND bucketed.candidate_id = candidate_cycle.candidate_id
    AND bucketed.bucket = bucket.bucket
WHERE candidate_cycle.contributor_count IS NOT NULL
GROUP BY candidate_cycle.candidate_id, candidate_cycle.cycle, bucket.bucket
UNION ALL
SELECT
    candidate_id,
    cycle,
    'unitemized' AS bucket,
    reported_individual_unitemized AS amount,
    CAST(NULL AS INTEGER) AS donors
FROM candidate_cycle
WHERE reported_individual_unitemized IS NOT NULL;
