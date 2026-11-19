-- A reported total's reporting period (CONTEXT.md) ends no earlier than it starts, where both
-- are known (every-FEC-dollar spec §4.1).
SELECT cycle, committee_id, period_start, period_end
FROM reported_total
WHERE period_end < period_start;
