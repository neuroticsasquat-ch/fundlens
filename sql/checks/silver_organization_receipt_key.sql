-- organization_receipt's key (cycle, source, source_record_id) is never null and never repeated
-- (NEU-2131).
SELECT cycle, source, source_record_id, count(*) AS copies
FROM organization_receipt
GROUP BY cycle, source, source_record_id
HAVING source_record_id IS NULL OR count(*) > 1;
