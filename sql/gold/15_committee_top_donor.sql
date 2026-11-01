-- committee_top_donor (spec §7.1): the 100 donors who gave most to a committee in the cycle, net of
-- refunds; a candidate's own money to their committee is never one (spec §2), and a donor whose
-- gifts net to nothing or less is left out. Ranked by amount, then donor id.
CREATE TABLE committee_top_donor AS
WITH given AS (
    SELECT recipient_committee_id AS committee_id, donor_id, sum(amount) AS amount
    FROM silver.contribution
    WHERE NOT is_self_funding AND donor_id IS NOT NULL
    GROUP BY recipient_committee_id, donor_id
    HAVING sum(amount) > 0
),
ranked AS (
    SELECT *, row_number() OVER (PARTITION BY committee_id ORDER BY amount DESC, donor_id) AS rank
    FROM given
)
SELECT
    ranked.committee_id,
    CAST({cycle} AS INTEGER) AS cycle,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.donor_id,
    donor.display_name,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount
FROM ranked
LEFT JOIN donor USING (donor_id)
WHERE ranked.rank <= 100;
