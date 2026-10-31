-- race_top_committee (spec §7.1): the 100 committees that gave most to a race's candidates, from
-- the disbursement side of committee_transfer summed by giver. Ranked by amount, then committee
-- id, so the order is stable. kind is 'contribution' only until NEU-2057 adds the 'ie' rows.
CREATE TABLE race_top_committee AS
WITH given AS (
    SELECT race_candidate.race_id, transfer.from_committee_id AS committee_id, sum(transfer.amount) AS amount
    FROM silver.committee_transfer AS transfer
    JOIN race_candidate ON race_candidate.candidate_id = transfer.candidate_id
    WHERE transfer.side = 'disbursement' AND transfer.from_committee_id IS NOT NULL
    GROUP BY race_candidate.race_id, transfer.from_committee_id
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
