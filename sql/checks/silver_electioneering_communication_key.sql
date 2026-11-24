-- electioneering_communication's key (cycle, source, source_record_id) is never null and never
-- repeated (NEU-2166): `<SB_IMAGE_NUM>:<n>`, n a row's place among its image number's kept rows,
-- which a blank image number would break.
SELECT cycle, source, source_record_id, count(*) AS copies
FROM electioneering_communication
GROUP BY cycle, source, source_record_id
HAVING source_record_id IS NULL OR count(*) > 1;
