-- leadership_pac (every-FEC-dollar spec §7.3, §7.4, NEU-2175): one row per committee of the
-- cycle's `leadership` file (2010 on, even years), FEC's list of leadership PACs and their
-- sponsors, with the sponsor's candidate id where fundlens can tell it. A committee `cm`
-- designates D that the file lacks is a leadership PAC too (§7.2), with no sponsor and no row
-- here: gold tells it by its designation. The PAC's money stays its own: the sponsor is a link,
-- never a dollar in the candidate's totals.
--
-- The sponsor's id (§7.4):
--   1. The name rule. Sponsor_Name is matched to the cycle's candidates, each resolved through
--      alias_of, on last name and first given name, compared as 03_candidate_committee_link.sql's
--      alias rule and 04_contribution.sql's self-funding test compare them ('HOVDE, ERIC D' is
--      'HOVDE, ERIC'). A name matching one person takes that person's id, the one alias_of points
--      to when the match is an alias. A name with no first given name (nothing after the comma)
--      matches nobody; a name matching several people, or one name under several ids, or none,
--      takes no id: picking the one standing in a race picks the wrong Dan Sullivan (Q14b).
--   2. The vendored list (`fec/leadership_sponsors.csv`, registered as `leadership_sponsor`, the
--      cycle's rows): a row overrides the rule for its committee, and names the sponsor where the
--      file leaves it blank. Its id may be one fundlens holds a candidate under in another cycle,
--      so a retired member's PAC links to their page.
-- sponsor_source says which gave the id, and is NULL with no id. The file's money figures are
-- reported_total's (§7.1) and are not read.
CREATE TABLE leadership_pac AS
WITH filed AS (
    SELECT
        trim(Committee_Id) AS committee_id,
        nullif(trim(Sponsor_Name), '') AS sponsor_name,
        regexp_replace(upper(split_part(Sponsor_Name, ',', 1)), '[^A-Z0-9]', '', 'g') AS last_name,
        regexp_replace(
            upper(split_part(trim(split_part(Sponsor_Name, ',', 2)), ' ', 1)), '[^A-Z0-9]', '', 'g'
        ) AS first_name
    FROM leadership
),
person AS (
    SELECT
        coalesce(alias_of, candidate_id) AS candidate_id,
        regexp_replace(upper(split_part(name, ',', 1)), '[^A-Z0-9]', '', 'g') AS last_name,
        regexp_replace(
            upper(split_part(trim(split_part(name, ',', 2)), ' ', 1)), '[^A-Z0-9]', '', 'g'
        ) AS first_name
    FROM candidate
),
by_rule AS (
    SELECT filed.committee_id, min(person.candidate_id) AS candidate_id
    FROM person
    JOIN filed
        ON filed.last_name = person.last_name AND filed.first_name = person.first_name
    WHERE filed.first_name <> ''
    GROUP BY filed.committee_id
    HAVING count(DISTINCT person.candidate_id) = 1
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    filed.committee_id,
    'fec' AS source,
    'US' AS jurisdiction,
    coalesce(filed.sponsor_name, listed.sponsor_name) AS sponsor_name,
    coalesce(listed.candidate_id, by_rule.candidate_id) AS sponsor_candidate_id,
    CASE
        WHEN listed.candidate_id IS NOT NULL THEN 'list'
        WHEN by_rule.candidate_id IS NOT NULL THEN 'rule'
    END AS sponsor_source
FROM filed
LEFT JOIN leadership_sponsor AS listed ON listed.committee_id = filed.committee_id
LEFT JOIN by_rule ON by_rule.committee_id = filed.committee_id;
