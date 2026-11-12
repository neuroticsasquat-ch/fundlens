-- Every expenditure is attached as its CAND_ID says (NEU-2057): to a candidate of the cycle that
-- is no alias (NEU-2127) and to that candidate's race, or, when CAND_ID names no candidate of the
-- cycle, to neither. A spender may target an id `cn` lacks or a candidate whose seat is not up
-- (1,282 of 2024's IE rows, $54.4M, name an id `cn` lacks or none), so an unattached row is kept,
-- in its spender's ie_total alone; what this fails on is a row attached to the wrong candidate or
-- race, or a kind or side its transaction type does not give.
SELECT spending.source_record_id, spending.candidate_id, spending.race_id, spending.kind
FROM independent_expenditure AS spending
LEFT JOIN candidate USING (candidate_id)
WHERE (
        spending.candidate_id IS NOT NULL
        AND (candidate.candidate_id IS NULL OR candidate.alias_of IS NOT NULL)
    )
    OR spending.race_id IS DISTINCT FROM candidate.race_id
    OR NOT EXISTS (
        SELECT 1
        FROM (VALUES
            ('24E', 'ie', 'S'),
            ('24A', 'ie', 'O'),
            ('24C', 'coordinated', 'S'),
            ('24F', 'communication_cost', 'S'),
            ('24N', 'communication_cost', 'O')
        ) AS rule (transaction_type, kind, support_oppose)
        WHERE rule.transaction_type = spending.transaction_type
            AND rule.kind = spending.kind
            AND rule.support_oppose = spending.support_oppose
    );
