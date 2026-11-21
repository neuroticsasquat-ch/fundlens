-- operating_expenditure's key (cycle, source, source_record_id) is never null and never repeated
-- (NEU-2152): SUB_ID is unique in `oppexp` (the measurement's Q1a).
SELECT cycle, source, source_record_id, count(*) AS copies
FROM operating_expenditure
GROUP BY cycle, source, source_record_id
HAVING source_record_id IS NULL OR count(*) > 1;
