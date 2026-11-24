-- independent_expenditure's key (cycle, source, source_record_id) is never null and never repeated:
-- a `pas2` row's SUB_ID, and a 24/48-hour row's `<file_num>:<tran_id>` (NEU-2165), which a
-- filing's own repeated tran_id, or a blank file_num or tran_id, would break.
SELECT cycle, source, source_record_id, count(*) AS copies
FROM independent_expenditure
GROUP BY cycle, source, source_record_id
HAVING source_record_id IS NULL OR count(*) > 1;
