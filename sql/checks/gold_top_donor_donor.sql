-- Every donor in a top-donor list or with top recipients is a donor of the build, so it has a name
-- and a page.
SELECT listed."table", listed.donor_id
FROM (
    SELECT 'race_top_donor' AS "table", donor_id FROM race_top_donor
    UNION ALL
    SELECT 'candidate_top_donor', donor_id FROM candidate_top_donor
    UNION ALL
    SELECT 'committee_top_donor', donor_id FROM committee_top_donor
    UNION ALL
    SELECT 'donor_top_recipient', donor_id FROM donor_top_recipient
) AS listed
WHERE NOT EXISTS (SELECT 1 FROM donor WHERE donor.donor_id = listed.donor_id);
