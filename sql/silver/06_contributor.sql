-- contributor (spec §4, §6.1): one row per contributor key in the cycle's contributions, the unit
-- resolution links. A key stands for every contribution reporting a name, ZIP, employer and
-- occupation that normalize to it; its raw columns are the variant most of them report (then the
-- one with the most money, then the first in order), and its normalized ones that variant's, read
-- from the `contributor_*` tables 04_contribution.sql built. Every variant of a key shares its
-- first, middle and last name, ZIP5, employer and occupation; only the suffix and the spelling
-- differ, so name_suffix is the chosen variant's. A partition holds one cycle, so first_cycle and
-- last_cycle are that cycle; resolution reads the contributor across every cycle's partition.
CREATE TABLE contributor AS
WITH variant AS (
    SELECT
        contributor_key,
        contributor_name,
        contributor_city,
        contributor_state,
        contributor_zip,
        contributor_employer,
        contributor_occupation,
        count(*) AS contributions,
        sum(amount) AS amount
    FROM contribution
    GROUP BY ALL
),
chosen AS (
    SELECT
        *,
        sum(contributions) OVER by_key AS contribution_count,
        sum(amount) OVER by_key AS amount_total
    FROM variant
    WINDOW by_key AS (PARTITION BY contributor_key)
    QUALIFY row_number() OVER (
        PARTITION BY contributor_key
        ORDER BY
            contributions DESC,
            amount DESC,
            contributor_name NULLS LAST,
            contributor_city NULLS LAST,
            contributor_state NULLS LAST,
            contributor_zip NULLS LAST,
            contributor_employer NULLS LAST,
            contributor_occupation NULLS LAST
    ) = 1
)
SELECT
    chosen.contributor_key,
    chosen.contributor_name AS name_raw,
    cname.name.first AS name_first,
    cname.name.last AS name_last,
    cname.name.suffix AS name_suffix,
    czip.zip5,
    chosen.contributor_city AS city,
    chosen.contributor_state AS state,
    chosen.contributor_employer AS employer_raw,
    cemployer.employer_norm,
    chosen.contributor_occupation AS occupation_raw,
    coccupation.occupation_norm,
    chosen.contribution_count,
    chosen.amount_total,
    CAST({cycle} AS INTEGER) AS first_cycle,
    CAST({cycle} AS INTEGER) AS last_cycle
FROM chosen
LEFT JOIN contributor_name AS cname ON cname.raw = chosen.contributor_name
LEFT JOIN contributor_zip AS czip ON czip.raw = chosen.contributor_zip
LEFT JOIN contributor_employer AS cemployer ON cemployer.raw = chosen.contributor_employer
LEFT JOIN contributor_occupation AS coccupation ON coccupation.raw = chosen.contributor_occupation;
