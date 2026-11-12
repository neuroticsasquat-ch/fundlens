-- independent_expenditure's key (cycle, source, source_record_id) is never null and never repeated.
SELECT cycle, source, source_record_id, count(*) AS copies
FROM independent_expenditure
GROUP BY cycle, source, source_record_id
HAVING source_record_id IS NULL OR count(*) > 1;
