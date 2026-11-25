-- bundling_report's key (cycle, source_record_id) is never null and never repeated (NEU-2175):
-- the report's image number, unique in FEC's file (read 2026-11-25), which a Link_Image with no
-- digits would leave null.
SELECT cycle, source_record_id, count(*) AS copies
FROM bundling_report
GROUP BY cycle, source_record_id
HAVING source_record_id IS NULL OR count(*) > 1;
