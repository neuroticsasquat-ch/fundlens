-- electioneering_communication (every-FEC-dollar spec §6.4, NEU-2166): one row per candidate an
-- electioneering communication's disbursement names, from `ElectioneeringComm` (2010 on): a
-- broadcast ad naming a candidate shortly before an election, paid for by a spender filing Form 9
-- (`cm` type E). It has no side: the filing does not say whether the ad is for or against.
--
-- A disbursement naming several candidates is one row per candidate, and `amount` is that row's
-- CALCULATED_CANDIDATE_SHARE, FEC's equal split, as filed: summing it counts the ad's cost once.
-- disbursement_amount is the whole disbursement, repeated on each of its rows, and never summed.
-- No check holds the split to its arithmetic: 2010, 2012 and 2018 have rows off by over a cent.
--
-- Every row counts, but a disbursement's copies. A disbursement is the rows equal on spender,
-- image number, payee, disbursement date and amount; its rows beyond NUMBER_OF_CANDIDATES, in order
-- of CANDIDATE_ID and then every column, are dropped (2024: 2 rows, $38,500, each a second row
-- naming the candidate its first row names). A disbursement with fewer rows than candidates keeps
-- what it has. One whose count is blank or below 1 has no copies known, and keeps every row (no
-- cycle 2010-2026 has a blank one). The date the
-- disbursement is told by is the row's parsed date, the one silver holds, so the copies check
-- (silver_electioneering_communication_copies.sql) groups as this does.
--
-- The file has no filing number and no amendment indicator, so no amendment rule applies: a
-- report an amendment restates is counted twice ($33,750 in 2024, 0.36%).
--
-- A row whose spender `cm` lacks is dropped, as an independent expenditure's is. The candidate is
-- §6.1's, as independent_expenditure's: CANDIDATE_ID's, or the id it is an alias of (NEU-2127),
-- when it is a candidate of the cycle, and past a handoff (fec/handoffs.csv) the candidate the
-- committee was handed to, on a row dated on or after the handoff or undated. A row naming no
-- candidate of the cycle (an ad naming no candidate, or an id `cn` lacks) is kept with candidate and
-- race NULL, in its spender's total alone.
--
-- The key is `<SB_IMAGE_NUM>:<n>`, n the row's place among its image number's kept rows, ordered
-- by every column as filed: an image number is one Schedule B page, which may itemize several
-- disbursements, and a disbursement for two candidates is two rows on it.
CREATE TABLE electioneering_communication AS
WITH filed AS (
    SELECT
        ec.*,
        -- FEC writes DD-MON-YY; a malformed date is null rather than a failed build.
        CAST(try_strptime(ec.DISBURSEMENT_DATE, '%d-%b-%y') AS DATE) AS spent_on
    FROM ElectioneeringComm AS ec
    WHERE ec.COMMITTEE_ID IN (SELECT committee_id FROM committee)
),
placed AS (
    SELECT
        *,
        row_number() OVER (
            PARTITION BY
                COMMITTEE_ID, SB_IMAGE_NUM, PAYEE_NAME, spent_on, REPORTED_DISBURSEMENT_AMOUNT
            ORDER BY
                CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE,
                CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME,
                PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION,
                DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE,
                REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE
        ) AS place_in_disbursement
    FROM filed
),
kept AS (
    SELECT
        *,
        row_number() OVER (
            PARTITION BY SB_IMAGE_NUM
            ORDER BY
                CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE,
                CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME,
                PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION,
                DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE,
                REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE
        ) AS place_on_image
    FROM placed
    WHERE coalesce(NUMBER_OF_CANDIDATES, 0) < 1 OR place_in_disbursement <= NUMBER_OF_CANDIDATES
),
spending AS (
    SELECT kept.*, coalesce(named.alias_of, named.candidate_id) AS named_candidate_id
    FROM kept
    LEFT JOIN candidate AS named ON named.candidate_id = nullif(trim(kept.CANDIDATE_ID), '')
),
handed_off AS (
    -- One row per pair of candidates and date, whichever committees were handed between them.
    SELECT DISTINCT from_candidate_id, to_candidate_id, handoff_date FROM handoff
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    spending.SB_IMAGE_NUM || ':' || CAST(spending.place_on_image AS VARCHAR) AS source_record_id,
    'US' AS jurisdiction,
    spending.COMMITTEE_ID AS committee_id,
    candidate.candidate_id,
    candidate.race_id,
    spending.CALCULATED_CANDIDATE_SHARE AS amount,
    spending.REPORTED_DISBURSEMENT_AMOUNT AS disbursement_amount,
    spending.NUMBER_OF_CANDIDATES AS candidate_count,
    spending.spent_on AS date,
    CAST(try_strptime(spending.COMMUNICATION_DATE, '%d-%b-%y') AS DATE) AS communication_date,
    CAST(try_strptime(spending.PUBLIC_DISBURSEMENT_DATE, '%d-%b-%y') AS DATE)
        AS public_distribution_date,
    spending.PAYEE_NAME AS payee_name,
    spending.DISBURSEMENT_DESCRIPTION AS description,
    spending.SB_IMAGE_NUM AS image_num
FROM spending
LEFT JOIN handed_off
    ON handed_off.from_candidate_id = spending.named_candidate_id
    AND (spending.spent_on IS NULL OR spending.spent_on >= handed_off.handoff_date)
LEFT JOIN candidate
    ON candidate.candidate_id = coalesce(handed_off.to_candidate_id, spending.named_candidate_id);
