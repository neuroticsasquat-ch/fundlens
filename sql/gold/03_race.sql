-- race (spec §7.1): every race of the seat calendar, its totals summed over race_candidate.
-- A race no one filed for (the fixture's 2024-H-MD-08) is a row with 0s. reported_cash_on_hand is
-- its candidates' reported_cash_on_hand_end added up, FEC's figures (every-FEC-dollar spec §4.4):
-- NULL when none has one, never 0, and in no other total. total_operating_expenditures is its
-- candidates' added up (every-FEC-dollar spec §5.5): spending, in no receipt total; NULL when none
-- of them has one, so a race before 2004 reads as not available, not as nothing spent.
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
    CAST(
        coalesce(sum(race_candidate.total_jfc_transfers), 0) AS DECIMAL(16, 2)
    ) AS total_jfc_transfers,
    CAST(coalesce(sum(race_candidate.ie_support), 0) AS DECIMAL(16, 2)) AS ie_support,
    CAST(coalesce(sum(race_candidate.ie_oppose), 0) AS DECIMAL(16, 2)) AS ie_oppose,
    CAST(sum(race_candidate.total_operating_expenditures) AS DECIMAL(16, 2))
        AS total_operating_expenditures,
    CAST(sum(race_candidate.reported_cash_on_hand_end) AS DECIMAL(16, 2)) AS reported_cash_on_hand
FROM silver.race AS race
LEFT JOIN race_candidate USING (race_id)
GROUP BY ALL;
