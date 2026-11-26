-- A candidate's leadership PACs are the rows naming them sponsor (every-FEC-dollar spec §7.7): the
-- candidate page's lookup, over the few rows that have one.
CREATE INDEX committee_cycle_sponsor ON gold_build.committee_cycle (sponsor_candidate_id)
WHERE sponsor_candidate_id IS NOT NULL;
