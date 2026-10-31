-- Every race's count and totals are the sums over its race_candidate rows.
SELECT race.race_id, race.candidate_count, race.total_individual, race.total_committee
FROM race
LEFT JOIN (
    SELECT
        race_id,
        count(*) AS candidate_count,
        sum(total_individual) AS total_individual,
        sum(total_committee) AS total_committee,
        sum(ie_support) AS ie_support,
        sum(ie_oppose) AS ie_oppose
    FROM race_candidate
    GROUP BY race_id
) AS candidates USING (race_id)
WHERE race.candidate_count <> coalesce(candidates.candidate_count, 0)
    OR race.total_individual <> coalesce(candidates.total_individual, 0)
    OR race.total_committee <> coalesce(candidates.total_committee, 0)
    OR race.ie_support <> coalesce(candidates.ie_support, 0)
    OR race.ie_oppose <> coalesce(candidates.ie_oppose, 0);
