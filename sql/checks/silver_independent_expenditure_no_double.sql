-- No 24/48-hour row counts what `pas2` or another filing already holds (every-FEC-dollar spec §6.2,
-- §6.3; NEU-2165). The 24/48-hour file restates spending a periodic report later puts in `pas2`,
-- and holds hoax filings, so a row of it in independent_expenditure must be one of the two rules':
-- dated after the period end of a spender with a track record, or a spender's with no `pas2`
-- independent expenditure behind the hoax screen. This fails on a row that is
-- - on a filing another row of the file names in prev_file_num: an amendment replaced it;
-- - at a spender with a counted `pas2` independent expenditure in the cycle, unless it is dated
--   after the spender's period end: `pas2` holds that spending;
-- - at a spender with neither a counted `pas2` independent expenditure nor a reported figure
--   above $0: the hoax screen keeps those out.
WITH added AS (
    SELECT
        source_record_id,
        committee_id,
        date,
        CAST(split_part(source_record_id, ':', 1) AS BIGINT) AS file_num
    FROM independent_expenditure
    WHERE source_file = 'ie_24_48'
),
pas2_spender AS (
    SELECT DISTINCT committee_id
    FROM independent_expenditure
    WHERE source_file = 'pas2' AND kind = 'ie'
),
judged AS (
    SELECT
        added.source_record_id,
        added.committee_id,
        CASE
            WHEN added.file_num IN (SELECT prev_file_num FROM ie_24_48)
                THEN 'replaced by an amendment'
            WHEN pas2_spender.committee_id IS NOT NULL
                AND NOT coalesce(added.date > reported.period_end, false)
                THEN 'in pas2 by its period end'
            WHEN pas2_spender.committee_id IS NULL
                AND NOT coalesce(reported.independent_expenditures > 0, false)
                THEN 'no track record'
        END AS counted_twice
    FROM added
    LEFT JOIN pas2_spender USING (committee_id)
    LEFT JOIN reported_total AS reported USING (committee_id)
)
SELECT source_record_id, committee_id, counted_twice
FROM judged
WHERE counted_twice IS NOT NULL;
