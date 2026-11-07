-- candidate_top_donor (spec §7.1): the 100 donors who gave most to the committees raising for a
-- candidate in the cycle, net of refunds; the candidate's own money is never one (spec §2), and a
-- donor whose gifts net to nothing or less is left out. Ranked by amount, then donor id.
CREATE TABLE candidate_top_donor AS
WITH given AS (
    SELECT candidate_id, donor_id, sum(amount) AS amount
    FROM silver.contribution
    WHERE candidate_id IS NOT NULL AND NOT is_self_funding AND donor_id IS NOT NULL
    GROUP BY candidate_id, donor_id
    HAVING sum(amount) > 0
),
ranked AS (
    SELECT *, row_number() OVER (PARTITION BY candidate_id ORDER BY amount DESC, donor_id) AS rank
    FROM given
)
SELECT
    ranked.candidate_id,
    CAST({cycle} AS INTEGER) AS cycle,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.donor_id,
    donor.display_name,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount
FROM ranked
LEFT JOIN donor USING (donor_id)
WHERE ranked.rank <= 100;
