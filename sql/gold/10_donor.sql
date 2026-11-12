-- donor (spec §6.7, §6.11, §7.1): one row per donor_id among every cycle's contributions and JFC
-- attributions. A donor known only from attributions (spec §6.11) is a donor all the same, with no
-- money: an attribution is evidence, never money, so it adds to no total here or anywhere.
--
-- Each display column is the donor's raw variant of it with the most counted money (refunds net
-- out), then the one the most contributions report, then the one the most attributions report
-- (which decides alone for a donor with no money), then the first in order. A column chosen alone:
-- the name may come from one spelling and the employer from another. zip5 is the variant's key's
-- (every variant of a key shares its ZIP5, 07_contributor.sql). total_all_cycles is the donor's
-- counted money in every cycle; first_cycle and last_cycle the first and last cycle of any of
-- their lines, an attribution's too (NEU-2059).
--
-- donor_line and donor_variant outlive this file: the donor files after it and search_entity's
-- donor rows read them. A build loaded before `resolve` has no donor ids (the loader gives its
-- partitions a NULL donor_id), so no donors.
--
-- `contributor` holds a key once per cycle it is seen in, each with the key's ZIP5: key_zip5 is
-- the one row per key the lines join.
CREATE TEMP TABLE donor_line AS
WITH key_zip5 AS (
    SELECT contributor_key, any_value(zip5) AS zip5
    FROM silver.contributor
    GROUP BY contributor_key
)
SELECT
    contribution.cycle,
    contribution.donor_id,
    contribution.contributor_key,
    contribution.contributor_name AS name,
    contribution.contributor_employer AS employer,
    contribution.contributor_occupation AS occupation,
    contribution.contributor_city AS city,
    contribution.contributor_state AS state,
    contributor.zip5,
    contribution.amount,
    true AS counted
FROM silver.contribution AS contribution
LEFT JOIN key_zip5 AS contributor USING (contributor_key)
WHERE contribution.donor_id IS NOT NULL
UNION ALL
SELECT
    attribution.cycle,
    attribution.donor_id,
    attribution.contributor_key,
    attribution.contributor_name,
    attribution.contributor_employer,
    attribution.contributor_occupation,
    attribution.contributor_city,
    attribution.contributor_state,
    contributor.zip5,
    NULL,
    false
FROM silver.jfc_attribution AS attribution
LEFT JOIN key_zip5 AS contributor USING (contributor_key)
WHERE attribution.donor_id IS NOT NULL;

-- Every value a donor's lines report for each display column, with its money and its lines.
-- UNPIVOT leaves out NULLs, so a column is NULL only when no line reports it.
CREATE TEMP TABLE donor_variant AS
SELECT
    donor_id,
    field,
    value,
    coalesce(sum(amount), 0) AS amount,
    count(*) FILTER (WHERE counted) AS contributions,
    count(*) FILTER (WHERE NOT counted) AS attributions
FROM donor_line
UNPIVOT (value FOR field IN (name, employer, occupation, city, state, zip5))
GROUP BY donor_id, field, value;

CREATE TABLE donor AS
WITH chosen AS (
    SELECT donor_id, field, value
    FROM donor_variant
    QUALIFY row_number() OVER (
        PARTITION BY donor_id, field
        ORDER BY amount DESC, contributions DESC, attributions DESC, value
    ) = 1
),
display AS (
    SELECT
        donor_id,
        max(value) FILTER (WHERE field = 'name') AS display_name,
        max(value) FILTER (WHERE field = 'employer') AS employer,
        max(value) FILTER (WHERE field = 'occupation') AS occupation,
        max(value) FILTER (WHERE field = 'city') AS city,
        max(value) FILTER (WHERE field = 'state') AS state,
        max(value) FILTER (WHERE field = 'zip5') AS zip5
    FROM chosen
    GROUP BY donor_id
),
totals AS (
    SELECT
        donor_id,
        coalesce(sum(amount), 0) AS total,
        count(DISTINCT contributor_key) AS contributor_key_count,
        min(cycle) AS first_cycle,
        max(cycle) AS last_cycle
    FROM donor_line
    GROUP BY donor_id
)
SELECT
    totals.donor_id,
    display.display_name,
    display.employer,
    display.occupation,
    display.city,
    display.state,
    display.zip5,
    CAST(totals.total AS DECIMAL(16, 2)) AS total_all_cycles,
    CAST(totals.first_cycle AS INTEGER) AS first_cycle,
    CAST(totals.last_cycle AS INTEGER) AS last_cycle,
    CAST(totals.contributor_key_count AS INTEGER) AS contributor_key_count
FROM totals
LEFT JOIN display USING (donor_id);
