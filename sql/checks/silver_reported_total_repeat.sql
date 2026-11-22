-- `committee_summary` repeats a committee once per linked candidate, and its repeats differ in
-- nothing but CAND_ID and Link_Image (every-FEC-dollar spec §4.1). It also lists a committee now
-- and then over two periods (NEU-2454), and reported_total keeps the row covering the cycle to
-- date, the earliest start and then the latest end. Rows over that period that differ elsewhere
-- would make the one kept an arbitrary choice. Each committee listed with how many different
-- rows the file holds for it over that period.
SELECT CMTE_ID, count(*) AS versions
FROM (
    SELECT DISTINCT * EXCLUDE (CAND_ID, Link_Image)
    FROM committee_summary
    QUALIFY rank() OVER (
        PARTITION BY CMTE_ID
        ORDER BY
            try_strptime(CVG_START_DT, '%Y%m%d') ASC NULLS LAST,
            try_strptime(CVG_END_DT, '%Y%m%d') DESC NULLS LAST
    ) = 1
)
GROUP BY CMTE_ID
HAVING count(*) > 1;
