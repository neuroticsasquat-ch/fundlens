-- reconciliation (every-FEC-dollar spec §4.5, §5.6): the committees whose fundlens figure exceeds
-- FEC's reported one by more than 1%, with both figures, one row per measure. Built by every load
-- and published, never a check that fails the build: FEC's figures lag amendments, and a filer's
-- line choice is not fundlens's to fix. A shortfall is not a row here: itemized figures sit below
-- reported ones by design (coverage below 1; payments of $200 or less a year go unitemized).
--
-- A committee is listed on a measure when the reported figure is not NULL (so 2008 on: no earlier
-- file has either measure) and fundlens - reported > 1% of reported, with no dollar floor. A
-- reported 0 beside fundlens money is listed with ratio NULL: a 0 is a figure FEC gives. ratio is
-- fundlens / reported.
--   - `individual_itemized`: itemized_total against reported_individual_itemized. Not at a
--     conduit, whose figure holds the earmarks fundlens counts at their recipients (ADR-0004).
--   - `operating_expenditures`: total_operating_expenditures against
--     reported_operating_expenditures, conduits included: the exclusion is the receipt measure's.
--     A committee with no counted spending (total NULL) is not listed.
CREATE TABLE reconciliation AS
WITH measured AS (
    SELECT
        committee_cycle.committee_id,
        committee_cycle.cycle,
        'individual_itemized' AS measure,
        committee_cycle.itemized_total AS fundlens,
        committee_cycle.reported_individual_itemized AS reported
    FROM committee_cycle
    JOIN silver.committee AS committee USING (cycle, committee_id)
    WHERE NOT committee.is_conduit
    UNION ALL
    SELECT
        committee_id,
        cycle,
        'operating_expenditures',
        total_operating_expenditures,
        reported_operating_expenditures
    FROM committee_cycle
)
SELECT
    committee_id,
    cycle,
    measure,
    fundlens,
    reported,
    CAST(fundlens AS DOUBLE) / CAST(nullif(reported, 0) AS DOUBLE) AS ratio
FROM measured
WHERE reported IS NOT NULL AND fundlens IS NOT NULL AND fundlens - reported > 0.01 * reported;
