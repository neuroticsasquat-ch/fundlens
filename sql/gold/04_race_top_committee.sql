-- race_top_committee (spec §7.1): the 100 committees that gave most to a race's candidates, from
-- the disbursement side of committee_transfer summed by giver, less a giver's 24Ks to a candidate
-- netting below 0 for the cycle: returned gifts, voids of an earlier cycle's, in no candidate's
-- total_committee (NEU-2204), so the list adds up to the race's. Ranked by amount, then committee
-- id, so the order is stable. kind is 'contribution' only until NEU-2057 adds the 'ie' rows.
CREATE TABLE race_top_committee AS
WITH pair AS (
    SELECT from_committee_id, candidate_id, sum(amount) AS amount
    FROM silver.committee_transfer
    WHERE side = 'disbursement' AND from_committee_id IS NOT NULL
    GROUP BY from_committee_id, candidate_id
    HAVING sum(amount) >= 0
),
given AS (
    SELECT
        race_candidate.race_id,
        pair.from_committee_id AS committee_id,
        sum(pair.amount) AS amount
    FROM pair
    JOIN race_candidate USING (candidate_id)
    GROUP BY race_candidate.race_id, pair.from_committee_id
),
ranked AS (
    SELECT
        *,
        row_number() OVER (PARTITION BY race_id ORDER BY amount DESC, committee_id) AS rank
    FROM given
)
SELECT
    ranked.race_id,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.committee_id,
    committee.name,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount,
    'contribution' AS kind
FROM ranked
LEFT JOIN silver.committee AS committee USING (committee_id)
WHERE ranked.rank <= 100;
