-- Every candidate alias (NEU-2127) names a candidate of the cycle that is no alias itself: one hop
-- from an alias reaches the id that holds the person's money.
SELECT alias.candidate_id, alias.alias_of
FROM candidate AS alias
LEFT JOIN candidate AS canonical ON canonical.candidate_id = alias.alias_of
WHERE alias.alias_of IS NOT NULL
    AND (canonical.candidate_id IS NULL OR canonical.alias_of IS NOT NULL);
