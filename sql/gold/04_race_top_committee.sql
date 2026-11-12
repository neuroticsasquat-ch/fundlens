-- race_top_committee (spec §7.1): the 100 committees that put most into a race, as gifts to its
-- candidates (kind 'contribution') or as independent expenditures for or against them (kind 'ie',
-- NEU-2057), one row per committee and kind, ranked together by amount, then committee id, then
-- kind, so the order is stable. A race is one cycle's: its candidates are that cycle's, and each
-- committee is named as that cycle's `cm` names it.
--
-- A contribution row is the disbursement side of committee_transfer summed by giver, less a
-- giver's 24Ks to a candidate netting below 0 for the cycle: returned gifts, voids of an earlier
-- cycle's, in no candidate's total_committee (NEU-2204), so the contribution rows add up to the
-- race's total_committee. A conduit's 24Ks are no gifts and never in committee_transfer, so
-- ActBlue and WinRed are in no list. An ie row is a spender's independent expenditures attached
-- to the race (24E and 24A alike, silver's kind 'ie'), net of corrections, a spender netting
-- below 0 left out, so the ie rows add up to the race's ie_support plus ie_oppose but for such a
-- spender. A committee both giving to a race's candidates and spending on it has a row of each.
CREATE TABLE race_top_committee AS
WITH pair AS (
    SELECT cycle, from_committee_id, candidate_id, sum(amount) AS amount
    FROM silver.committee_transfer
    WHERE side = 'disbursement' AND from_committee_id IS NOT NULL
    GROUP BY cycle, from_committee_id, candidate_id
    HAVING sum(amount) >= 0
),
given AS (
    SELECT
        candidate_cycle.race_id,
        pair.cycle,
        pair.from_committee_id AS committee_id,
        sum(pair.amount) AS amount,
        'contribution' AS kind
    FROM pair
    JOIN candidate_cycle USING (cycle, candidate_id)
    WHERE candidate_cycle.race_id IS NOT NULL
    GROUP BY candidate_cycle.race_id, pair.cycle, pair.from_committee_id
),
spent AS (
    SELECT race_id, cycle, committee_id, sum(amount) AS amount, 'ie' AS kind
    FROM silver.independent_expenditure
    WHERE kind = 'ie' AND race_id IS NOT NULL
    GROUP BY race_id, cycle, committee_id
    HAVING sum(amount) >= 0
),
ranked AS (
    SELECT
        *,
        row_number() OVER (PARTITION BY race_id ORDER BY amount DESC, committee_id, kind) AS rank
    FROM (
        SELECT * FROM given
        UNION ALL
        SELECT * FROM spent
    ) AS put_in
)
SELECT
    ranked.race_id,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.committee_id,
    committee.name,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount,
    ranked.kind
FROM ranked
LEFT JOIN silver.committee AS committee USING (cycle, committee_id)
WHERE ranked.rank <= 100;
