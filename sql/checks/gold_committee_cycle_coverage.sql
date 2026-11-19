-- A committee's coverage is NULL exactly when its reported itemized figure is 0 or NULL, or it is a
-- conduit (every-FEC-dollar spec §4.4): a figure wherever there is one to divide by, and never one
-- set against a conduit's earmarks, which fundlens counts at their recipients.
SELECT
    committee_cycle.committee_id,
    committee_cycle.cycle,
    committee_cycle.reported_individual_itemized,
    committee.is_conduit,
    committee_cycle.coverage
FROM committee_cycle
JOIN silver.committee AS committee USING (cycle, committee_id)
WHERE (committee_cycle.coverage IS NULL)
    <> (coalesce(committee_cycle.reported_individual_itemized, 0) = 0 OR committee.is_conduit);
