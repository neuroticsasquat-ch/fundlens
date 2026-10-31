-- candidate (spec §4): one row per `cn` candidate, attached to the race for the seat it files for.
--
-- The district is two characters: FEC pads it and files Senate and President as '00', and a
-- blank or one-digit one is padded the same way (as `transform.seats.Filing.seat` reads it, so a
-- filing left without a race here is one `fundlens seats --report` recorded as unmatched).
--
-- Only a filing for this cycle's election (or the odd year before it, for a special held then)
-- stands in one of its races: `cn` also lists candidates registered for later cycles. A filing
-- whose (office, state, district) is no seat in the calendar gets no race (spec §5.2).
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
        *,
        CASE
            WHEN length(trim(coalesce(CAND_OFFICE_DISTRICT, ''))) < 2
                THEN lpad(trim(coalesce(CAND_OFFICE_DISTRICT, '')), 2, '0')
            ELSE trim(CAND_OFFICE_DISTRICT)
        END AS district
    FROM cn
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
    filed.CAND_PCC AS principal_committee_id,
    race_for_seat.race_id
FROM filed
LEFT JOIN race_for_seat
    ON filed.CAND_ELECTION_YR IN ({cycle} - 1, {cycle})
    AND race_for_seat.office = filed.CAND_OFFICE
    AND race_for_seat.state = filed.CAND_OFFICE_ST
    AND race_for_seat.district = filed.district;
