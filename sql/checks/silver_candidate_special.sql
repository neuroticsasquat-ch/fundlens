-- No Senate special held beside a regular race for the same seat is left with no candidate while
-- the regular race has one (NEU-2319). `cn` doesn't say which of the two races a filing is for, so
-- only `special_candidates.csv` puts anyone in the special (02_candidate.sql): a special with no
-- one in it is one the file has no row for, or whose rows name no filing in this cycle's `cn`.
-- A seat no one filed for (as in a test fixture) is a race with nothing in it, so passes. So does
-- a special whose every row is `race = 'regular'`: each of its candidates ran in both races and
-- stands in the regular one (2022's and 2024's California specials).
SELECT special.race_id
FROM race AS special
INNER JOIN race AS regular
    ON regular.office = special.office
    AND regular.state = special.state
    AND regular.district = special.district
    AND NOT regular.is_special
WHERE special.is_special
    AND NOT EXISTS (SELECT 1 FROM candidate WHERE candidate.race_id = special.race_id)
    AND EXISTS (SELECT 1 FROM candidate WHERE candidate.race_id = regular.race_id)
    AND NOT EXISTS (
        SELECT 1
        FROM special_candidate
        WHERE special_candidate.office = special.office
            AND special_candidate.state = special.state
        HAVING count(*) > 0 AND bool_and(special_candidate.race = 'regular')
    );
