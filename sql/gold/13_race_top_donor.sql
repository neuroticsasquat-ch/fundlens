-- race_top_donor (spec §7.1): the 100 donors who gave most to a race's candidates, net of refunds,
-- with what each gave to each candidate. A candidate's own money (is_self_funding) is never a top
-- donor (spec §2). A donor resolved across several spellings is one row (spec §6). A candidate the
-- donor's gifts net to exactly nothing is left out of candidates, which so always add up to amount
-- (one netting below nothing stays, and lowers it); a donor whose gifts to the race net to nothing
-- or less is left out. Ranked by amount, then donor id.
CREATE TABLE race_top_donor AS
WITH given AS (
    SELECT race_candidate.race_id, contribution.donor_id, contribution.candidate_id, sum(contribution.amount) AS amount
    FROM silver.contribution AS contribution
    JOIN race_candidate USING (candidate_id)
    WHERE NOT contribution.is_self_funding AND contribution.donor_id IS NOT NULL
    GROUP BY ALL
    HAVING sum(contribution.amount) <> 0
),
by_donor AS (
    SELECT
        race_id,
        donor_id,
        sum(amount) AS amount,
        to_json(
            list(
                struct_pack(candidate_id, amount := CAST(amount AS DECIMAL(16, 2)))
                ORDER BY amount DESC, candidate_id
            )
        ) AS candidates
    FROM given
    GROUP BY race_id, donor_id
    HAVING sum(amount) > 0
),
ranked AS (
    SELECT *, row_number() OVER (PARTITION BY race_id ORDER BY amount DESC, donor_id) AS rank
    FROM by_donor
)
SELECT
    ranked.race_id,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.donor_id,
    donor.display_name,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount,
    ranked.candidates
FROM ranked
LEFT JOIN donor USING (donor_id)
WHERE ranked.rank <= 100;
