-- committee_top_recipient (spec §7.1): the 100 candidates a committee gave most to, from the
-- disbursement side of committee_transfer summed by candidate. Committee recipients
-- (recipient_kind = 'committee') arrive with NEU-2057, which owns the rule against counting a 24K
-- row beside its `oth` twin.
CREATE TABLE committee_top_recipient AS
WITH given AS (
    SELECT from_committee_id AS committee_id, candidate_id, sum(amount) AS amount
    FROM silver.committee_transfer
    WHERE side = 'disbursement' AND candidate_id IS NOT NULL
    GROUP BY from_committee_id, candidate_id
),
ranked AS (
    SELECT
        *,
        row_number() OVER (PARTITION BY committee_id ORDER BY amount DESC, candidate_id) AS rank
    FROM given
)
SELECT
    ranked.committee_id,
    CAST({cycle} AS INTEGER) AS cycle,
    CAST(ranked.rank AS INTEGER) AS rank,
    'candidate' AS recipient_kind,
    ranked.candidate_id AS recipient_id,
    candidate.name,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount
FROM ranked
LEFT JOIN silver.candidate AS candidate USING (candidate_id)
WHERE ranked.rank <= 100;
