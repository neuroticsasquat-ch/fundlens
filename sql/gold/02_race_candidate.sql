-- race_candidate (spec §7.1): the candidates attached to a race, with candidate_cycle's money. A
-- race is one cycle's, so each row is the candidate as that cycle's `cn` lists them. Its reported
-- figures and coverage are candidate_cycle's (every-FEC-dollar spec §4.4), and so is its
-- total_operating_expenditures (§5.5), NULL where candidate_cycle's is.
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
    candidate_cycle.total_jfc_transfers,
    candidate_cycle.self_funding,
    candidate_cycle.ie_support,
    candidate_cycle.ie_oppose,
    candidate_cycle.total_operating_expenditures,
    candidate_cycle.reported_receipts,
    candidate_cycle.reported_disbursements,
    candidate_cycle.reported_cash_on_hand_end,
    candidate_cycle.reported_debts_owed_by,
    candidate_cycle.coverage
FROM candidate_cycle
JOIN silver.candidate AS candidate USING (cycle, candidate_id)
WHERE candidate_cycle.race_id IS NOT NULL;
