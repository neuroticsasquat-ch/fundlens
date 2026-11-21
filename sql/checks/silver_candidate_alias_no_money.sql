-- No candidate alias (NEU-2127) holds money: gold leaves aliases out of every race and total, so
-- money on one would vanish from them. Spending is credited by the same rule (NEU-2152).
SELECT 'contribution' AS source, candidate_id, count(*) AS row_count
FROM contribution
WHERE candidate_id IN (SELECT candidate_id FROM candidate WHERE alias_of IS NOT NULL)
GROUP BY candidate_id
UNION ALL
SELECT 'committee_transfer' AS source, candidate_id, count(*) AS row_count
FROM committee_transfer
WHERE candidate_id IN (SELECT candidate_id FROM candidate WHERE alias_of IS NOT NULL)
GROUP BY candidate_id
UNION ALL
SELECT 'operating_expenditure' AS source, candidate_id, count(*) AS row_count
FROM operating_expenditure
WHERE candidate_id IN (SELECT candidate_id FROM candidate WHERE alias_of IS NOT NULL)
GROUP BY candidate_id;
