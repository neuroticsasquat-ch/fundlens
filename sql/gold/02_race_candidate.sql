-- race_candidate (spec §7.1): the candidates attached to a race, with candidate_cycle's money.
CREATE TABLE race_candidate AS
SELECT
    candidate_cycle.race_id,
    candidate_cycle.candidate_id,
    candidate.name,
    candidate.party,
    candidate.incumbent_challenger_open,
    candidate.principal_committee_id,
    candidate_cycle.total_individual,
    candidate_cycle.total_committee,
    candidate_cycle.self_funding,
    candidate_cycle.ie_support,
    candidate_cycle.ie_oppose
FROM candidate_cycle
JOIN silver.candidate AS candidate USING (candidate_id)
WHERE candidate_cycle.race_id IS NOT NULL;
