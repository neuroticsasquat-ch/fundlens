-- Every race's count and totals are the sums over its race_candidate rows; its
-- total_operating_expenditures NULL where none of theirs is a figure (every-FEC-dollar spec §5.5),
-- and its electioneering likewise (§6.5).
SELECT
    race.race_id,
    race.candidate_count,
    race.total_individual,
    race.total_committee,
    race.total_jfc_transfers,
    race.total_operating_expenditures,
    race.communication_cost_support,
    race.communication_cost_oppose,
    race.party_coordinated,
    race.electioneering
FROM race
LEFT JOIN (
    SELECT
        race_id,
        count(*) AS candidate_count,
        sum(total_individual) AS total_individual,
        sum(total_committee) AS total_committee,
        sum(total_jfc_transfers) AS total_jfc_transfers,
        sum(ie_support) AS ie_support,
        sum(ie_oppose) AS ie_oppose,
        sum(total_operating_expenditures) AS total_operating_expenditures,
        sum(communication_cost_support) AS communication_cost_support,
        sum(communication_cost_oppose) AS communication_cost_oppose,
        sum(party_coordinated) AS party_coordinated,
        sum(electioneering) AS electioneering
    FROM race_candidate
    GROUP BY race_id
) AS candidates USING (race_id)
WHERE race.candidate_count <> coalesce(candidates.candidate_count, 0)
    OR race.total_individual <> coalesce(candidates.total_individual, 0)
    OR race.total_committee <> coalesce(candidates.total_committee, 0)
    OR race.total_jfc_transfers <> coalesce(candidates.total_jfc_transfers, 0)
    OR race.ie_support <> coalesce(candidates.ie_support, 0)
    OR race.ie_oppose <> coalesce(candidates.ie_oppose, 0)
    OR race.total_operating_expenditures IS DISTINCT FROM candidates.total_operating_expenditures
    OR race.communication_cost_support <> coalesce(candidates.communication_cost_support, 0)
    OR race.communication_cost_oppose <> coalesce(candidates.communication_cost_oppose, 0)
    OR race.party_coordinated <> coalesce(candidates.party_coordinated, 0)
    OR race.electioneering IS DISTINCT FROM candidates.electioneering;
