-- race (spec §7.1): every race of the seat calendar, its totals summed over race_candidate.
-- A race no one filed for (the fixture's 2024-H-MD-08) is a row with 0s.
CREATE TABLE race AS
SELECT
    race.race_id,
    race.cycle,
    race.office,
    race.state,
    race.district,
    race.is_special,
    race.slug,
    CAST(count(race_candidate.candidate_id) AS INTEGER) AS candidate_count,
    CAST(coalesce(sum(race_candidate.total_individual), 0) AS DECIMAL(16, 2)) AS total_individual,
    CAST(coalesce(sum(race_candidate.total_committee), 0) AS DECIMAL(16, 2)) AS total_committee,
    CAST(coalesce(sum(race_candidate.ie_support), 0) AS DECIMAL(16, 2)) AS ie_support,
    CAST(coalesce(sum(race_candidate.ie_oppose), 0) AS DECIMAL(16, 2)) AS ie_oppose
FROM silver.race AS race
LEFT JOIN race_candidate USING (race_id)
GROUP BY ALL;
