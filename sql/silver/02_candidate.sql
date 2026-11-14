-- candidate (spec §4): one row per `cn` candidate, attached to the race for the seat it files for.
--
-- The district is two characters: FEC pads it and files Senate and President as '00', and a
-- blank or one-digit one is padded the same way (as `transform.seats.Filing.seat` reads it, so a
-- filing left without a race here is one `fundlens seats --report` recorded as unmatched).
--
-- A House filing's district is `cn`'s CAND_OFFICE_DISTRICT, unless `house_district`
-- (`fec/seats/house_districts.csv`, NEU-2293) gives the one it ran in. `cn` keeps the district of
-- the candidate's statement of candidacy, and in the first cycle on a new map that is often the
-- old map's number: 2012's `cn` files Michael Grimm and Mark Murphy, who ran in NY-11, under
-- NY-13, and Linda Sánchez, who won CA-38, under CA-39, so their money counted in the wrong race.
-- FEC's per-cycle candidate history and DIME carry the same stale number; FEC's election results
-- list each candidate under the district they ran in, and the file holds the 2002, 2012 and 2022
-- filings where the two differ (1982's and 1992's results are PDF only: NEU-2294). The corrected
-- district is the one this table keeps.
--
-- Only a filing for this cycle's election (or the odd year before it, for a special held then)
-- stands in one of its races: `cn` also lists candidates registered for later cycles. But `cn`
-- gives each candidate only their latest election year, so a House member who won this cycle and
-- has already registered for the next election is listed with next cycle's year (NEU-2283: 25 of
-- 1998's incumbents, $14.30M), or now and then with the odd year after it (NEU-2287: Gene Taylor,
-- MS-05, 2001 in 2000's `cn`). A House filing for either year marked incumbent (`I`) held the
-- seat after this cycle's election, so it stands in this cycle's race for that seat too. That
-- holds in a census-year cycle as well, though the next election is the first on a new map:
-- NEU-2287 compared each of 1990–2020's 15 such filings with the same member's filing in the
-- previous cycle's `cn`, and none had moved district, so the census year's file still numbers
-- them from this cycle's map (1980's 10, with no 1978 file to compare, are taken to do the
-- same). A later filing marked `C` or `O`, and a Senate one (a senator whose seat isn't up),
-- stands in no race. `transform.seats.read_filings` applies the same rule, and
-- `sql/checks/silver_candidate_race.sql` checks every filing it covers.
-- A filing whose (office, state, district) is no seat in the calendar gets no race (spec §5.2).
--
-- principal_committee_id is the committee `cn` names principal (CAND_PCC). In a cycle with no `ccl`
-- (before 2000, spec §4), a candidate whose CAND_PCC is blank takes the committee `cm` names
-- principal (designation P) for them instead, the lowest id should there be two; with `ccl`, as
-- 03_candidate_committee_link.sql links, CAND_PCC alone.
--
-- alias_of is empty here: 03_candidate_committee_link.sql sets it, from the links it builds.
CREATE TABLE candidate AS
WITH race_for_seat AS (
    -- One race per seat. `cn` cannot tell a special's filing from the regular race for the same
    -- seat, so a filing goes to the regular race where there is one, and to a special only
    -- where it is the seat's one race this cycle.
    SELECT race_id, office, state, district
    FROM race
    QUALIFY row_number() OVER (PARTITION BY office, state, district ORDER BY is_special) = 1
),
filed AS (
    SELECT
        cn.*,
        CASE
            WHEN cn.CAND_OFFICE = 'H' AND house_district.district IS NOT NULL
                THEN house_district.district
            WHEN length(trim(coalesce(cn.CAND_OFFICE_DISTRICT, ''))) < 2
                THEN lpad(trim(coalesce(cn.CAND_OFFICE_DISTRICT, '')), 2, '0')
            ELSE trim(cn.CAND_OFFICE_DISTRICT)
        END AS district
    FROM cn
    LEFT JOIN house_district ON house_district.candidate_id = cn.CAND_ID
),
named_principal AS (
    SELECT CAND_ID, min(CMTE_ID) AS committee_id
    FROM cm
    WHERE CMTE_DSGN = 'P' AND NOT EXISTS (SELECT 1 FROM ccl)
    GROUP BY CAND_ID
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    filed.CAND_ID AS candidate_id,
    'fec' AS source,
    'US' AS jurisdiction,
    filed.CAND_NAME AS name,
    filed.CAND_PTY_AFFILIATION AS party,
    filed.CAND_ELECTION_YR AS election_year,
    filed.CAND_OFFICE AS office,
    filed.CAND_OFFICE_ST AS state,
    filed.district,
    filed.CAND_ICI AS incumbent_challenger_open,
    filed.CAND_STATUS AS status,
    coalesce(nullif(trim(filed.CAND_PCC), ''), named_principal.committee_id)
        AS principal_committee_id,
    race_for_seat.race_id,
    NULL::VARCHAR AS alias_of
FROM filed
LEFT JOIN race_for_seat
    ON (
        filed.CAND_ELECTION_YR IN ({cycle} - 1, {cycle})
        OR (
            filed.CAND_OFFICE = 'H'
            AND filed.CAND_ELECTION_YR IN ({cycle} + 1, {cycle} + 2)
            AND filed.CAND_ICI = 'I'
        )
    )
    AND race_for_seat.office = filed.CAND_OFFICE
    AND race_for_seat.state = filed.CAND_OFFICE_ST
    AND race_for_seat.district = filed.district
LEFT JOIN named_principal USING (CAND_ID);
