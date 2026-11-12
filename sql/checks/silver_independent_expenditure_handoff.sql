-- No expenditure on or after a handoff (fec/handoffs.csv), or undated, names the candidate the
-- committee was handed from: it is the candidate it was handed to's, as the committee's own money
-- is (NEU-2277). Committees kept filing Biden's id after he withdrew.
SELECT spending.source_record_id, spending.candidate_id, spending.date, handoff.handoff_date
FROM independent_expenditure AS spending
JOIN handoff ON handoff.from_candidate_id = spending.candidate_id
WHERE spending.date IS NULL OR spending.date >= handoff.handoff_date;
