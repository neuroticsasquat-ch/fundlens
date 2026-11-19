-- `committee_summary` repeats a committee once per linked candidate, and its repeats differ in
-- nothing but CAND_ID and Link_Image (every-FEC-dollar spec §4.1): reported_total keeps one of
-- them, so repeats that differ elsewhere would make the one kept an arbitrary choice. Each
-- committee listed with how many different rows the file holds for it.
SELECT CMTE_ID, count(*) AS versions
FROM (SELECT DISTINCT * EXCLUDE (CAND_ID, Link_Image) FROM committee_summary)
GROUP BY CMTE_ID
HAVING count(*) > 1;
