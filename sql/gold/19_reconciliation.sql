-- reconciliation (every-FEC-dollar spec §4.5): the committees whose fundlens figure exceeds FEC's
-- reported one by more than 1%, with both figures. Built by every load and published, never a
-- check that fails the build: FEC's figures lag amendments, and a filer's line choice is not
-- fundlens's to fix. A shortfall is coverage below 1, not a row here.
--
-- One measure so far, `individual_itemized`: fundlens's itemized_total against
-- reported_individual_itemized, ratio their quotient. A committee is listed when the reported figure
-- is not NULL (so 2008 on: no earlier file has it), it is not a conduit (its figure holds the
-- earmarks fundlens counts at their recipients, ADR-0004), and fundlens - reported > 1% of
-- reported, with no dollar floor. A reported 0 beside fundlens money is listed with ratio NULL: a 0
-- is a figure FEC gives.
CREATE TABLE reconciliation AS
SELECT
    committee_cycle.committee_id,
    committee_cycle.cycle,
    'individual_itemized' AS measure,
    committee_cycle.itemized_total AS fundlens,
    committee_cycle.reported_individual_itemized AS reported,
    CAST(committee_cycle.itemized_total AS DOUBLE)
        / CAST(nullif(committee_cycle.reported_individual_itemized, 0) AS DOUBLE) AS ratio
FROM committee_cycle
JOIN silver.committee AS committee USING (cycle, committee_id)
WHERE committee_cycle.reported_individual_itemized IS NOT NULL
    AND NOT committee.is_conduit
    AND committee_cycle.itemized_total - committee_cycle.reported_individual_itemized
        > 0.01 * committee_cycle.reported_individual_itemized;
